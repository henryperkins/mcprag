"""CLI interface for Azure Integration functionality.

Usage:
    python -m enhanced_rag.azure_integration.cli <command> [options]

Commands:
    local-repo          Index a local repository
    changed-files       Index specific changed files
    create-enhanced-index   Create enhanced RAG index
    validate-index      Validate index vector dimensions
    create-indexer      Create Azure indexer for automated ingestion
"""

import argparse
import sys
import asyncio
from datetime import datetime
import logging
import os
import hashlib
from pathlib import Path
import ast
from typing import List, Dict, Any, Optional, Tuple, Set


from azure.core.exceptions import ResourceNotFoundError
from .rest_index_builder import EnhancedIndexBuilder
from .reindex_operations import ReindexOperations, ReindexMethod
from .automation import DataAutomation
from .rest import AzureSearchClient, SearchOperations
from mcprag.config import Config
from .cli_schema_automation import add_schema_commands
from .processing import extract_python_chunks, process_file, FileProcessor, find_repository_root

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------------------
# Local validation utilities
# ----------------------------
_ALLOWED_REPO_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
def _validate_repo_name(name: str) -> Optional[str]:
    """
    Validate repository name: non-empty, no slashes/backslashes, sane length,
    and only [_-.A-Za-z0-9] characters.
    Returns error string if invalid, or None if valid.
    """
    if not name or not isinstance(name, str):
        return "Repository name is required"
    if len(name) > 100:
        return "Repository name too long (max 100 chars)"
    if any(c in name for c in "/\\"):
        return "Repository name must not contain slashes"
    if any(c not in _ALLOWED_REPO_CHARS for c in name):
        return "Repository name contains invalid characters; allowed: letters, numbers, '-', '_', '.'"
    return None

def _repo_root_guard(repo_path: str, excluded_dirs: Set[str]) -> Optional[str]:
    """
    Warn/guard if the provided repo_path resolves within a known noisy/excluded directory,
    unless MCP_ALLOW_EXTERNAL_ROOTS=true is set in env.
    Returns warning string if guarded, or None to proceed.
    """
    allow_external = os.getenv("MCP_ALLOW_EXTERNAL_ROOTS", "false").lower() == "true"
    resolved = Path(repo_path).resolve()
    parts = set(p.name for p in resolved.parents) | {resolved.name}
    if any(d in parts for d in excluded_dirs):
        if not allow_external:
            return (f"Repository path '{resolved}' appears to be inside an excluded directory "
                    f"({', '.join(sorted(excluded_dirs))}). Set MCP_ALLOW_EXTERNAL_ROOTS=true to override.")
        else:
            logger.warning("Proceeding with repo_path inside excluded directory due to MCP_ALLOW_EXTERNAL_ROOTS=true")
    return None




async def index_repository(repo_path: str, repo_name: str, patterns: Optional[List[Tuple[str, str]]] = None) -> int:
    """Index an entire repository using REST API."""
    # Initialize REST client and operations
    rest_client = AzureSearchClient(
        endpoint=Config.ENDPOINT,
        api_key=Config.ADMIN_KEY
    )
    rest_ops = SearchOperations(rest_client)
    data_automation = DataAutomation(rest_ops)
    
    # Use FileProcessor with custom extensions if patterns provided
    extensions = None
    if patterns:
        extensions = set()
        for pattern, _ in patterns:
            if pattern.startswith('*.'):
                extensions.add(pattern[1:])
    
    # Use FileProcessor for consistent repository processing
    file_processor = FileProcessor(extensions=extensions)
    all_documents = file_processor.process_repository(repo_path, repo_name)
    
    logger.info(f"Collected {len(all_documents)} documents from repository")
    
    # Upload documents using async generator
    async def document_generator():
        for doc in all_documents:
            yield doc
    
    # Upload in batches
    result = await data_automation.bulk_upload(
        index_name=Config.INDEX_NAME,
        documents=document_generator(),
        batch_size=100
    )
    
    logger.info(f"Upload complete: {result['succeeded']} succeeded, {result['failed']} failed")
    
    return result['succeeded']


async def cmd_local_repo(args):
    """Index a local repository."""
    logger.info(f"Indexing repository: {args.repo_path}")

    # Validate repo name
    err = _validate_repo_name(args.repo_name)
    if err:
        logger.error(f"Invalid --repo-name: {err}")
        return 1

    # Guard against excluded roots unless explicitly allowed
    try:
        from .processing import FileProcessor  # reuse canonical excludes
        guard_msg = _repo_root_guard(args.repo_path, FileProcessor.DEFAULT_EXCLUDE_DIRS)
        if guard_msg:
            logger.error(guard_msg)
            return 1
    except Exception:
        # If import fails, proceed cautiously
        pass

    # Parse file patterns if provided
    patterns: Optional[List[Tuple[str, str]]] = None
    extensions: Optional[Set[str]] = None
    if args.patterns:
        patterns = []
        extensions = set()
        for pattern in args.patterns:
            # Infer language from extension
            if pattern.endswith('.py'):
                patterns.append((pattern, 'python'))
            elif pattern.endswith('.js'):
                patterns.append((pattern, 'javascript'))
            elif pattern.endswith('.ts'):
                patterns.append((pattern, 'typescript'))
            else:
                logger.warning(f"Unknown pattern {pattern}, skipping")
            if pattern.startswith('*.'):
                extensions.add(pattern[1:])

    # Optional dry-run path: produce sample list and exit
    if getattr(args, "dry_run", False):
        # Build file processor with the same extension filter as actual indexing
        fp = FileProcessor(extensions=extensions)
        # Collect documents but only keep unique relative file paths to avoid heavy output
        documents = fp.process_repository(args.repo_path, args.repo_name)
        unique_files: List[str] = []
        seen = set()
        for d in documents:
            rel = d.get("file_path")
            if rel and rel not in seen:
                seen.add(rel)
                unique_files.append(rel)
            if len(unique_files) >= args.sample:
                break

        out_dir = Path(".claude/state")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "index_dryrun_sample.txt"
        out_file.write_text("\n".join(unique_files), encoding="utf-8")
        logger.info(f"Dry-run complete. Wrote {len(unique_files)} paths to {out_file}")
        return 0

    # Index the repository
    doc_count = await index_repository(
        repo_path=args.repo_path,
        repo_name=args.repo_name,
        patterns=patterns
    )

    logger.info(f"Repository indexing completed: {doc_count} documents indexed")


async def index_changed_files(file_paths: List[str], repo_name: str) -> int:
    """Index specific changed files using REST API."""
    # Initialize REST client and operations
    rest_client = AzureSearchClient(
        endpoint=Config.ENDPOINT,
        api_key=Config.ADMIN_KEY
    )
    rest_ops = SearchOperations(rest_client)
    data_automation = DataAutomation(rest_ops)
    
    # Collect all documents
    all_documents = []
    
    # Find the repo root using shared helper
    repo_path = find_repository_root(file_paths)
    
    for file_path in file_paths:
        if os.path.exists(file_path) and os.path.isfile(file_path):
            docs = process_file(file_path, repo_path, repo_name)
            all_documents.extend(docs)
            
            if docs:
                logger.info(f"Processed {file_path} ({len(docs)} chunks)")
    
    # Upload documents using async generator
    async def document_generator():
        for doc in all_documents:
            yield doc
    
    # Upload in batches
    result = await data_automation.bulk_upload(
        index_name=Config.INDEX_NAME,
        documents=document_generator(),
        batch_size=100
    )
    
    logger.info(f"Upload complete: {result['succeeded']} succeeded, {result['failed']} failed")
    
    return result['succeeded']


async def cmd_changed_files(args):
    """Index specific changed files."""
    logger.info(f"Indexing {len(args.files)} changed files")

    # Validate repo name
    err = _validate_repo_name(args.repo_name)
    if err:
        logger.error(f"Invalid --repo-name: {err}")
        return 1

    # Additional guard: compute repo root from files and ensure not excluded unless allowed
    try:
        repo_root = find_repository_root(args.files)
        guard_msg = _repo_root_guard(repo_root, FileProcessor.DEFAULT_EXCLUDE_DIRS)
        if guard_msg:
            logger.error(guard_msg)
            return 1
    except Exception:
        # Proceed if guard fails unexpectedly
        pass

    # Index the changed files
    doc_count = await index_changed_files(
        file_paths=args.files,
        repo_name=args.repo_name
    )

    logger.info(f"Changed files indexing completed: {doc_count} documents indexed")


async def cmd_create_enhanced_index(args):
    """Create enhanced RAG index."""
    logger.info(f"Creating enhanced index: {args.name}")

    builder = EnhancedIndexBuilder()

    # Handle --recreate flag: delete existing index if it exists
    if args.recreate:
        try:
            builder.index_client.delete_index(args.name)
            logger.info(f"Deleted existing index '{args.name}'")
        except ResourceNotFoundError:
            logger.info(f"Index '{args.name}' does not exist, proceeding with creation")
        except Exception as e:
            logger.warning(f"Error deleting index '{args.name}': {e}")

    # Determine feature flags
    enable_vectors = not args.no_vectors
    enable_semantic = not args.no_semantic

    try:
        index = await builder.create_enhanced_rag_index(
            index_name=args.name,
            description=f"Enhanced RAG index {args.name}",
            enable_vectors=enable_vectors,
            enable_semantic=enable_semantic
        )
        logger.info(f"Successfully ensured index exists: {index.name}")
        # EnhancedIndexBuilder returns SimpleNamespace(name=..., operation=...)
        op = getattr(index, "operation", None)
        if isinstance(op, dict):
            if op.get("created"):
                logger.info("Index was created")
            elif op.get("updated"):
                logger.info("Index was updated")
            elif op.get("current"):
                logger.info("Index already current")
            # If the op payload includes a schema snapshot, log field count
            schema = op.get("schema") or op.get("index") or {}
            fields = schema.get("fields")
            if isinstance(fields, list):
                logger.info(f"Fields: {len(fields)}")
            vs = schema.get("vectorSearch")
            if isinstance(vs, dict):
                profiles = vs.get("profiles") or []
                logger.info(f"Vector profiles: {len(profiles)}")
            if schema.get("semanticSearch"):
                logger.info("Semantic search: Enabled")
    except Exception as e:
        logger.error(f"Failed to create index: {e}")
        return 1

    return 0


async def cmd_validate_index(args):
    """Validate index vector dimensions."""
    logger.info(f"Validating index: {args.name}")

    builder = EnhancedIndexBuilder()

    try:
        result = await builder.validate_vector_dimensions(
            index_name=args.name,
            expected_dimensions=args.check_dimensions
        )

        # Output JSON details if requested
        if args.json:
            import json
            print(json.dumps(result, indent=2))
        else:
            if result['valid']:
                logger.info(f"✓ Vector dimensions match: {result['actual_dimensions']}")
            else:
                logger.error(
                    f"✗ Vector dimension mismatch: "
                    f"expected {result['expected_dimensions']}, actual {result['actual_dimensions']}"
                )
            if 'error' in result:
                logger.error(f"Error: {result['error']}")

        # Return appropriate exit code
        return 0 if result['valid'] else 1

    except Exception as e:
        if args.json:
            import json
            error_result = {
                'ok': False,
                'error': str(e),
                'message': f'Validation failed: {e}'
            }
            print(json.dumps(error_result, indent=2))
        else:
            logger.error(f"Validation failed: {e}")
        return 1


async def cmd_create_indexer(args):
    """Create Azure indexer."""
    logger.info(f"Creating indexer: {args.name}")

    # Initialize REST client and operations
    rest_client = AzureSearchClient(
        endpoint=Config.ENDPOINT,
        api_key=Config.ADMIN_KEY
    )
    rest_ops = SearchOperations(rest_client)
    from .automation import IndexerAutomation
    indexer_automation = IndexerAutomation(rest_ops)

    try:
        # Create indexer pipeline based on source type
        if args.source == 'azureblob':
            result = await indexer_automation.create_blob_indexer_pipeline(
                name_prefix=args.name,
                index_name=args.index,
                connection_string=args.conn,
                container_name=args.container,
                schedule_hours=args.schedule_minutes // 60,  # Convert minutes to hours
                query=None
            )
            logger.info(f"Successfully created blob indexer pipeline")
            logger.info(f"Indexer: {result['indexer']}")
            logger.info(f"Target index: {args.index}")
            logger.info(f"Schedule: Every {args.schedule_minutes} minutes")
        else:
            logger.error(f"Unsupported source type: {args.source}")
            return 1

    except Exception as e:
        logger.error(f"Failed to create indexer: {e}")
        return 1

    return 0


async def cmd_reindex(args):
    """Reindex content using various methods."""
    logger.info(f"Starting reindex with method: {args.method}")

    reindex_ops = ReindexOperations()

    try:
        if args.method == 'drop-rebuild':
            # Drop and rebuild index
            success = await reindex_ops.drop_and_rebuild(args.schema)
            if not success:
                return 1
            logger.info("Index rebuilt. Use 'local-repo' command to repopulate.")

        elif args.method == 'clear':
            # Clear documents
            count = await reindex_ops.clear_documents(args.filter)
            logger.info(f"Cleared {count} documents")

        elif args.method == 'repository':
            # Reindex repository
            method = ReindexMethod.CLEAR_AND_RELOAD if args.clear_first else ReindexMethod.INCREMENTAL
            success = await reindex_ops.reindex_repository(
                repo_path=args.repo_path,
                repo_name=args.repo_name,
                method=method,
                clear_first=args.clear_first
            )
            if not success:
                return 1

        elif args.method == 'status':
            # Get index status
            info = await reindex_ops.get_index_info()
            print(f"\nIndex: {info.get('name', 'Unknown')}")
            print(f"Fields: {info.get('fields', 0)}")
            print(f"Documents: {info.get('document_count', 0)}")
            print(f"Vector Search: {info.get('vector_search', False)}")
            print(f"Semantic Search: {info.get('semantic_search', False)}")

        elif args.method == 'validate':
            # Validate schema
            validation = await reindex_ops.validate_index_schema()
            print(f"\nSchema Valid: {validation['valid']}")
            if validation.get('issues'):
                print("Issues:")
                for issue in validation['issues']:
                    print(f"  - {issue}")
            if validation.get('warnings'):
                print("Warnings:")
                for warning in validation['warnings']:
                    print(f"  - {warning}")

        elif args.method == 'backup':
            # Backup schema
            output_path = args.output or f"index_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            success = await reindex_ops.backup_index_schema(output_path)
            if success:
                logger.info(f"Schema backed up to {output_path}")
            else:
                return 1

    except Exception as e:
        logger.error(f"Reindex operation failed: {e}")
        return 1

    return 0


async def cmd_indexer_status(args):
    """Check indexer status."""
    logger.info(f"Checking indexer status: {args.name}")

    reindex_ops = ReindexOperations()

    try:
        status = await reindex_ops.get_indexer_status(args.name)
        if status:
            print(f"\nIndexer: {args.name}")
            print(f"Status: {status['status']}")
            print(f"Last Result: {status['last_result']}")
            print(f"Execution History: {status['execution_history']} runs")
            if status['errors']:
                print("Errors:")
                for error in status['errors'][:5]:  # Show first 5 errors
                    print(f"  - {error}")
            if status['warnings']:
                print("Warnings:")
                for warning in status['warnings'][:5]:  # Show first 5 warnings
                    print(f"  - {warning}")
        else:
            logger.error(f"Indexer '{args.name}' not found")
            return 1

    except Exception as e:
        logger.error(f"Failed to get indexer status: {e}")
        return 1

    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Azure Integration CLI for Enhanced RAG",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # local-repo command
    repo_parser = subparsers.add_parser(
        'local-repo',
        help='Index a local repository'
    )
    repo_parser.add_argument(
        '--repo-path',
        type=str,
        default='.',
        help='Path to repository (default: current directory)'
    )
    repo_parser.add_argument(
        '--repo-name',
        type=str,
        required=True,
        help='Repository name for indexing'
    )
    repo_parser.add_argument(
        '--patterns',
        nargs='+',
        help='File patterns to index (e.g., *.py *.js)'
    )
    repo_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Do not upload; output a sample of included files to .claude/state/index_dryrun_sample.txt'
    )
    repo_parser.add_argument(
        '--sample',
        type=int,
        default=200,
        help='Number of sample file paths to emit in dry-run (default: 200)'
    )
    # Mutually exclusive group for embed vectors
    embed_group = repo_parser.add_mutually_exclusive_group()
    embed_group.add_argument(
        '--embed-vectors',
        action='store_true',
        help='Force generation of embedding vectors'
    )
    embed_group.add_argument(
        '--no-embed-vectors',
        action='store_true',
        help='Disable generation of embedding vectors'
    )

    # changed-files command
    files_parser = subparsers.add_parser(
        'changed-files',
        help='Index specific changed files'
    )
    files_parser.add_argument(
        '--repo-name',
        type=str,
        default='current-repo',
        help='Repository name (default: current-repo)'
    )
    files_parser.add_argument(
        '--files',
        nargs='+',
        required=True,
        help='Files to index'
    )

    # create-enhanced-index command
    index_parser = subparsers.add_parser(
        'create-enhanced-index',
        help='Create enhanced RAG index'
    )
    index_parser.add_argument(
        '--name',
        type=str,
        default='codebase-mcp-sota',
        help='Index name (default: codebase-mcp-sota)'
    )
    index_parser.add_argument(
        '--no-vectors',
        action='store_true',
        help='Disable vector search'
    )
    index_parser.add_argument(
        '--no-semantic',
        action='store_true',
        help='Disable semantic search'
    )
    index_parser.add_argument(
        '--recreate',
        action='store_true',
        help='Drop index if it already exists before creating'
    )

    # validate-index command
    validate_parser = subparsers.add_parser(
        'validate-index',
        help='Validate index vector dimensions'
    )
    validate_parser.add_argument(
        '--name',
        type=str,
        required=True,
        help='Index name to validate'
    )
    validate_parser.add_argument(
        '--check-dimensions',
        type=int,
        required=True,
        help='Expected vector dimensions'
    )
    validate_parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    # create-indexer command
    indexer_parser = subparsers.add_parser(
        'create-indexer',
        help='Create Azure indexer for automated ingestion'
    )
    indexer_parser.add_argument(
        '--source',
        type=str,
        choices=['azureblob', 'cosmosdb'],
        required=True,
        help='Data source type'
    )
    indexer_parser.add_argument(
        '--name',
        type=str,
        required=True,
        help='Indexer name'
    )
    indexer_parser.add_argument(
        '--conn',
        type=str,
        required=True,
        help='Connection string'
    )
    indexer_parser.add_argument(
        '--container',
        type=str,
        required=True,
        help='Container/collection name'
    )
    indexer_parser.add_argument(
        '--index',
        type=str,
        required=True,
        help='Target index name'
    )
    indexer_parser.add_argument(
        '--schedule-minutes',
        type=int,
        default=60,
        help='Schedule interval in minutes (default: 60)'
    )
    indexer_parser.add_argument(
        '--include-git',
        action='store_true',
        help='Include git metadata extraction'
    )

    # reindex command
    reindex_parser = subparsers.add_parser(
        'reindex',
        help='Reindex content using various methods'
    )
    reindex_parser.add_argument(
        '--method',
        type=str,
        choices=['drop-rebuild', 'clear', 'repository', 'status', 'validate', 'backup'],
        required=True,
        help='Reindexing method'
    )
    reindex_parser.add_argument(
        '--schema',
        type=str,
        help='Path to schema JSON file (for drop-rebuild)'
    )
    reindex_parser.add_argument(
        '--filter',
        type=str,
        help='OData filter for clearing documents'
    )
    reindex_parser.add_argument(
        '--repo-path',
        type=str,
        default='.',
        help='Repository path (for repository method)'
    )
    reindex_parser.add_argument(
        '--repo-name',
        type=str,
        help='Repository name (for repository method)'
    )
    reindex_parser.add_argument(
        '--clear-first',
        action='store_true',
        help='Clear existing documents before reindexing'
    )
    reindex_parser.add_argument(
        '--output',
        type=str,
        help='Output path for backup'
    )

    # indexer-status command
    status_parser = subparsers.add_parser(
        'indexer-status',
        help='Check indexer status'
    )
    status_parser.add_argument(
        '--name',
        type=str,
        required=True,
        help='Indexer name'
    )

    # Add schema automation commands
    schema_commands = add_schema_commands(subparsers)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Command dispatch
    commands = {
        'local-repo': cmd_local_repo,
        'changed-files': cmd_changed_files,
        'create-enhanced-index': cmd_create_enhanced_index,
        'validate-index': cmd_validate_index,
        'create-indexer': cmd_create_indexer,
        'reindex': cmd_reindex,
        'indexer-status': cmd_indexer_status,
    }
    
    # Add schema commands to dispatch
    commands.update(schema_commands)

    if args.command in commands:
        try:
            # Run async command
            result = asyncio.run(commands[args.command](args))
            return result if result is not None else 0
        except KeyboardInterrupt:
            logger.info("\nOperation cancelled")
            return 1
        except Exception as e:
            logger.error(f"Command failed: {e}")
            return 1
    else:
        logger.error(f"Unknown command: {args.command}")
        return 1


if __name__ == '__main__':
    sys.exit(main())

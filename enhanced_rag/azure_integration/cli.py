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
from typing import List, Dict, Any, Optional, Tuple

from azure.core.exceptions import ResourceNotFoundError
from .rest_index_builder import EnhancedIndexBuilder
from .reindex_operations import ReindexOperations, ReindexMethod
from .automation import DataAutomation
from .rest import AzureSearchClient, SearchOperations
from mcprag.config import Config
from .cli_schema_automation import add_schema_commands

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_language_from_extension(file_path: str) -> str:
    """Determine language from file extension."""
    ext_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.mjs': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.cs': 'csharp',
        '.go': 'go',
        '.rs': 'rust',
        '.php': 'php',
        '.rb': 'ruby',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.r': 'r',
        '.md': 'markdown',
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.xml': 'xml',
        '.html': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.sass': 'sass'
    }
    
    ext = Path(file_path).suffix.lower()
    return ext_map.get(ext, 'text')


def extract_python_chunks(content: str, file_path: str) -> List[Dict[str, Any]]:
    """Extract semantic chunks from Python code."""
    chunks = []
    
    try:
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                chunk = {
                    "chunk_type": "function" if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else "class",
                    "function_name": node.name if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else None,
                    "class_name": node.name if isinstance(node, ast.ClassDef) else None,
                    "start_line": node.lineno,
                    "end_line": node.end_lineno or node.lineno,
                    "docstring": ast.get_docstring(node) or "",
                    "signature": f"def {node.name}" if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else f"class {node.name}"
                }
                
                # Extract code content
                lines = content.split('\n')
                chunk_content = '\n'.join(lines[chunk['start_line']-1:chunk['end_line']])
                chunk['content'] = chunk_content
                
                chunks.append(chunk)
    except (SyntaxError, ValueError):
        # If AST parsing fails, return whole file as single chunk
        chunks.append({
            "chunk_type": "file",
            "content": content,
            "start_line": 1,
            "end_line": len(content.split('\n'))
        })
    
    return chunks


def process_file(file_path: str, repo_path: str, repo_name: str) -> List[Dict[str, Any]]:
    """Process a single file and create document chunks."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except (IOError, OSError):
        return []
    
    language = get_language_from_extension(file_path)
    relative_path = os.path.relpath(file_path, repo_path)
    
    # Extract chunks based on language
    if language == 'python':
        chunks = extract_python_chunks(content, file_path)
    else:
        # For non-Python files, treat whole file as one chunk
        chunks = [{
            "chunk_type": "file",
            "content": content,
            "start_line": 1,
            "end_line": len(content.split('\n'))
        }]
    
    # Create documents for each chunk
    documents = []
    for i, chunk in enumerate(chunks):
        doc_id = hashlib.sha256(f"{repo_name}:{relative_path}:{i}".encode()).hexdigest()[:16]
        
        doc = {
            "id": doc_id,
            "content": chunk.get('content', ''),
            "file_path": relative_path,
            "repository": repo_name,
            "language": language,
            "chunk_type": chunk.get('chunk_type', 'file'),
            "chunk_id": f"{relative_path}:{i}",
            "last_modified": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + "Z",
            "file_extension": Path(file_path).suffix
        }
        
        # Add optional fields if they exist
        if chunk.get('function_name'):
            doc['function_name'] = chunk['function_name']
        if chunk.get('class_name'):
            doc['class_name'] = chunk['class_name']
        if chunk.get('docstring'):
            doc['docstring'] = chunk['docstring']
        if chunk.get('signature'):
            doc['signature'] = chunk['signature']
        if chunk.get('start_line'):
            doc['start_line'] = chunk['start_line']
        if chunk.get('end_line'):
            doc['end_line'] = chunk['end_line']
        
        documents.append(doc)
    
    return documents


async def index_repository(repo_path: str, repo_name: str, patterns: Optional[List[Tuple[str, str]]] = None) -> int:
    """Index an entire repository using REST API."""
    # Initialize REST client and operations
    rest_client = AzureSearchClient(
        endpoint=Config.ENDPOINT,
        api_key=Config.ADMIN_KEY
    )
    rest_ops = SearchOperations(rest_client)
    data_automation = DataAutomation(rest_ops)
    
    # Collect all documents
    all_documents = []
    
    # Default file extensions to process
    extensions = {'.py', '.js', '.mjs', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', 
                  '.cs', '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.scala', '.r',
                  '.md', '.json', '.yaml', '.yml', '.xml', '.html', '.css'}
    
    # If patterns provided, extract extensions from them
    if patterns:
        extensions = set()
        for pattern, _ in patterns:
            if pattern.startswith('*.'):
                extensions.add(pattern[1:])
    
    for root, dirs, files in os.walk(repo_path):
        # Skip hidden directories and common non-code directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', '.venv']]
        
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file)
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


async def cmd_local_repo(args):
    """Index a local repository."""
    logger.info(f"Indexing repository: {args.repo_path}")

    # Parse file patterns if provided
    patterns = None
    if args.patterns:
        patterns = []
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
    
    # Find the repo root (go up until we find .git or can't go further)
    repo_path = None
    for file_path in file_paths:
        current = Path(file_path).parent
        while current != current.parent:
            if (current / '.git').exists():
                repo_path = str(current)
                break
            current = current.parent
        if repo_path:
            break
    
    if not repo_path:
        # Fall back to common parent
        repo_path = os.path.commonpath([os.path.dirname(p) for p in file_paths])
    
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
        logger.info(f"Successfully created index: {index.name}")
        logger.info(f"Fields: {len(index.fields)}")
        if hasattr(index, 'vector_search') and index.vector_search:
            logger.info(f"Vector profiles: {len(index.vector_search.profiles)}")
        if hasattr(index, 'semantic_search') and index.semantic_search:
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
            if result['ok']:
                logger.info(f"✓ Vector dimensions match: {result['actual']}")
            else:
                logger.error(
                    f"✗ Vector dimension mismatch: "
                    f"expected {result['expected']}, actual {result['actual']}"
                )
            logger.info(result['message'])

        # Return appropriate exit code
        return 0 if result['ok'] else 1

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

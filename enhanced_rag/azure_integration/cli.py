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
from .automation import IndexAutomation
from .automation import ReindexAutomation
from .automation import DataAutomation
from .automation import EmbeddingAutomation
from .rest import AzureSearchClient, SearchOperations
from enhanced_rag.core.unified_config import get_config
from .processing import (
    extract_python_chunks, 
    process_file, 
    FileProcessor, 
    find_repository_root,
    validate_repo_name,
    validate_repo_path
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------------------
# Local validation utilities




async def index_repository(
    repo_path: str,
    repo_name: str,
    patterns: Optional[List[Tuple[str, str]]] = None,
    embed_vectors: bool = False,
    context_fields: Optional[List[str]] = None,
) -> int:
    """Index an entire repository using REST API.

    Optionally enrich documents with embeddings before upload.
    """
    # Initialize REST client and operations
    rest_client = AzureSearchClient(
        endpoint=get_config().acs_endpoint,
        api_key=get_config().acs_admin_key.get_secret_value()
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

    # Optionally enrich with embeddings (content_vector)
    if embed_vectors and all_documents:
        try:
            from enhanced_rag.core.unified_config import get_config as _get_unified
            batch_size = max(1, int(_get_unified().embedding_batch_size))
        except Exception:
            batch_size = 16

        emb_automation = EmbeddingAutomation(rest_ops)
        all_documents, stats = await emb_automation.enrich_documents_with_embeddings(
            all_documents,
            text_field="content",
            embedding_field="content_vector",
            context_fields=context_fields,
            batch_size=batch_size,
        )
        logger.info(
            "Embedding enrichment: processed=%s enriched=%s failed=%s in %ss",
            stats.get("processed"), stats.get("enriched"), stats.get("failed"), stats.get("elapsed_seconds")
        )

    # Upload documents using async generator
    async def document_generator():
        for doc in all_documents:
            yield doc
    
    # Upload in batches
    result = await data_automation.bulk_upload(
        index_name=get_config().acs_index_name,
        documents=document_generator(),
        batch_size=100
    )
    
    logger.info(f"Upload complete: {result['succeeded']} succeeded, {result['failed']} failed")
    
    return result['succeeded']


async def cmd_local_repo(args):
    """Index a local repository."""
    logger.info(f"Indexing repository: {args.repo_path}")

    # Validate repo name
    err = validate_repo_name(args.repo_name)
    if err:
        logger.error(f"Invalid --repo-name: {err}")
        return 1

    # Guard against excluded roots unless explicitly allowed
    guard_msg = validate_repo_path(args.repo_path)
    if guard_msg:
        logger.error(guard_msg)
        return 1

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

    # Determine whether to generate embeddings
    embed_vectors = bool(getattr(args, "embed_vectors", False) and not getattr(args, "no_embed_vectors", False))

    # Index the repository
    doc_count = await index_repository(
        repo_path=args.repo_path,
        repo_name=args.repo_name,
        patterns=patterns,
        embed_vectors=embed_vectors,
        context_fields=["file_path", "repository"] if embed_vectors else None,
    )

    logger.info(f"Repository indexing completed: {doc_count} documents indexed")


async def index_changed_files(file_paths: List[str], repo_name: str) -> int:
    """Index specific changed files using REST API."""
    # Initialize REST client and operations
    rest_client = AzureSearchClient(
        endpoint=get_config().acs_endpoint,
        api_key=get_config().acs_admin_key.get_secret_value()
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
        index_name=get_config().acs_index_name,
        documents=document_generator(),
        batch_size=100
    )
    
    logger.info(f"Upload complete: {result['succeeded']} succeeded, {result['failed']} failed")
    
    return result['succeeded']


async def cmd_changed_files(args):
    """Index specific changed files."""
    logger.info(f"Indexing {len(args.files)} changed files")

    # Validate repo name
    err = validate_repo_name(args.repo_name)
    if err:
        logger.error(f"Invalid --repo-name: {err}")
        return 1

    # Additional guard: compute repo root from files and ensure not excluded unless allowed
    repo_root = find_repository_root(args.files)
    guard_msg = validate_repo_path(repo_root)
    if guard_msg:
        logger.error(guard_msg)
        return 1

    # Index the changed files
    doc_count = await index_changed_files(
        file_paths=args.files,
        repo_name=args.repo_name
    )

    logger.info(f"Changed files indexing completed: {doc_count} documents indexed")


def _adapt_index_schema_for_api(index_def: Dict[str, Any], api_version: str) -> Dict[str, Any]:
    """Adapt index schema JSON to match the target API version.

    - For stable API versions (e.g. 2023-11-01), map 'semanticSearch' -> 'semantic'.
    - Preserve vectorSearch as-is.
    """
    adapted = dict(index_def)
    api_ver = (api_version or "").lower()

    # Map semanticSearch to semantic for stable API surfaces
    if "semanticSearch" in adapted and ("2023-" in api_ver or "2024-" in api_ver or "2022-" in api_ver):
        sem = adapted.pop("semanticSearch", None)
        if sem is not None:
            adapted["semantic"] = sem
    return adapted


async def cmd_create_enhanced_index(args):
    """Create enhanced RAG index using IndexAutomation (REST)."""
    logger.info(f"Creating enhanced index: {args.name}")

    cfg = get_config()
    api_version = args.api_version or cfg.acs_api_version

    # Initialize automation with explicit API version (if provided)
    automation = IndexAutomation(
        endpoint=cfg.acs_endpoint,
        api_key=cfg.acs_admin_key.get_secret_value(),
        api_version=api_version,
    )

    # Handle --recreate flag: delete existing index if it exists
    if args.recreate:
        try:
            await automation.ops.delete_index(args.name)
            logger.info(f"Deleted existing index '{args.name}'")
        except Exception as e:
            # Treat 404 (not found) as a no-op; avoid failing the flow
            logger.info(f"Index '{args.name}' may not exist or deletion skipped: {e}")

    # Determine feature flags (currently the canonical schema encodes these)
    _enable_vectors = not args.no_vectors
    _enable_semantic = not args.no_semantic
    if not _enable_vectors:
        logger.warning("--no-vectors specified; ensure schema reflects this if required")
    if not _enable_semantic:
        logger.warning("--no-semantic specified; ensure schema reflects this if required")

    try:
        from pathlib import Path
        import json
        schema_path = Path("azure_search_index_schema.json")
        if not schema_path.exists():
            raise FileNotFoundError("Index schema file 'azure_search_index_schema.json' not found")
        index_def = json.loads(schema_path.read_text())
        index_def["name"] = args.name

        # Adapt schema to match the configured API version
        index_def = _adapt_index_schema_for_api(index_def, api_version)

        # Avoid GET before PUT to prevent circuit-breaker trips on expected 404s.
        created = await automation.ops.create_index(index_def)
        logger.info(f"Created/updated index: {created.get('name', args.name)}")

        # Fetch and log summary
        current = await automation.ops.get_index(args.name)
        fields = current.get("fields", [])
        logger.info(f"Fields: {len(fields)}")
        if current.get("vectorSearch"):
            profiles = (current.get("vectorSearch", {}) or {}).get("profiles", [])
            logger.info(f"Vector profiles: {len(profiles)}")
        if current.get("semantic"):
            logger.info("Semantic search: Enabled")
        if current.get("semanticSearch"):
            logger.info("Semantic search (preview shape): Enabled")
    except Exception as e:
        # Fallback: if we targeted a preview API and failed, retry with stable mapping
        logger.error(f"Failed to create index (api={api_version}): {e}")
        try:
            if not ("2023-" in api_version):
                stable_ver = "2023-11-01"
                logger.info(f"Retrying creation with stable API {stable_ver} and schema adaptation…")
                automation_stable = IndexAutomation(
                    endpoint=cfg.acs_endpoint,
                    api_key=cfg.acs_admin_key.get_secret_value(),
                    api_version=stable_ver,
                )
                # Re-adapt schema for stable API
                index_def_stable = _adapt_index_schema_for_api(index_def, stable_ver)
                created = await automation_stable.ops.create_index(index_def_stable)
                logger.info(f"Created/updated index (stable): {created.get('name', args.name)}")
            else:
                raise
        except Exception as e2:
            logger.error(f"Failed to create index after fallback: {e2}")
            return 1

    return 0


async def cmd_validate_index(args):
    """Validate index vector dimensions using REST."""
    logger.info(f"Validating index: {args.name}")

    automation = IndexAutomation(endpoint=get_config().acs_endpoint, api_key=get_config().acs_admin_key.get_secret_value())

    try:
        current = await automation.ops.get_index(args.name)
        fields = current.get("fields", [])
        vector_field = next((f for f in fields if f.get("name") == "content_vector"), None)
        actual_dimensions = vector_field.get("dimensions") if vector_field else None
        result = {
            "valid": actual_dimensions == args.check_dimensions,
            "expected_dimensions": args.check_dimensions,
            "actual_dimensions": actual_dimensions,
            "vector_field_name": "content_vector",
        }

        # Output JSON details if requested
        if args.json:
            import json
            print(json.dumps(result, indent=2))
        else:
            if result['valid']:
                logger.info(f"✓ Vector dimensions match: {result['actual_dimensions']}")
            else:
                logger.error(
                    f"✗ Vector dimension mismatch: expected {result['expected_dimensions']}, "
                    f"actual {result['actual_dimensions']}"
                )

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
        endpoint=get_config().acs_endpoint,
        api_key=get_config().acs_admin_key.get_secret_value()
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
    """Reindex content using various methods via REST."""
    logger.info(f"Starting reindex with method: {args.method}")

    # Initialize REST client and operations
    rest_client = AzureSearchClient(
        endpoint=get_config().acs_endpoint,
        api_key=get_config().acs_admin_key.get_secret_value()
    )
    rest_ops = SearchOperations(rest_client)
    reindex = ReindexAutomation(rest_ops)

    try:
        if args.method == 'drop-rebuild':
            res = await reindex.perform_reindex('drop-rebuild', schema_path=args.schema)
            if res.get('status') != 'success':
                logger.error(f"Drop-rebuild failed: {res}")
                return 1
            logger.info("Index rebuilt. Use 'local-repo' command to repopulate.")

        elif args.method == 'clear':
            res = await reindex.perform_reindex('clear', clear_filter=args.filter)
            logger.info(f"Cleared {res.get('documents_cleared', 0)} documents")

        elif args.method == 'repository':
            clear_filter = f"repository eq '{args.repo_name}'" if args.clear_first else None
            res = await reindex.perform_reindex(
                'repository',
                repo_path=args.repo_path,
                repo_name=args.repo_name,
                clear_filter=clear_filter
            )
            if res.get('status') != 'success':
                logger.error(f"Repository reindex failed: {res}")
                return 1

        elif args.method == 'status':
            # Get index health summary
            info = await reindex.get_index_health()
            print(f"\nIndex: {info.get('name', 'Unknown')}")
            print(f"Fields: {info.get('field_count', 0)}")
            print(f"Documents: {info.get('document_count', 0)}")
            print(f"Vector Search: {info.get('vector_search_enabled', False)}")
            print(f"Semantic Search: {info.get('semantic_search_enabled', False)}")

        elif args.method == 'validate':
            health = await reindex.get_index_health()
            print(f"\nSchema Valid: {health['schema_valid']}")
            if health.get('schema_issues'):
                print("Issues:")
                for issue in health['schema_issues']:
                    print(f"  - {issue}")
            if health.get('schema_warnings'):
                print("Warnings:")
                for warning in health['schema_warnings']:
                    print(f"  - {warning}")

        elif args.method == 'backup':
            output_path = args.output or f"index_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            res = await reindex.backup_and_restore('backup', output_path)
            if not res.get('success'):
                logger.error(f"Backup failed: {res}")
                return 1
            logger.info(f"Schema backed up to {output_path}")

    except Exception as e:
        logger.error(f"Reindex operation failed: {e}")
        return 1

    return 0


async def cmd_indexer_status(args):
    """Check indexer status."""
    logger.info(f"Checking indexer status: {args.name}")

    rest_client = AzureSearchClient(
        endpoint=get_config().acs_endpoint,
        api_key=get_config().acs_admin_key.get_secret_value()
    )
    rest_ops = SearchOperations(rest_client)

    try:
        status = await rest_ops.get_indexer_status(args.name)
        if status:
            last_result = status.get('lastResult') or {}
            execution_history = status.get('executionHistory') or []
            print(f"\nIndexer: {args.name}")
            print(f"Status: {status.get('status', 'unknown')}")
            print(f"Last Result: {last_result.get('status')}")
            print(f"Execution History: {len(execution_history)} runs")
            errors = last_result.get('errors') or []
            warnings = last_result.get('warnings') or []
            if errors:
                print("Errors:")
                for error in errors[:5]:
                    print(f"  - {error}")
            if warnings:
                print("Warnings:")
                for warning in warnings[:5]:
                    print(f"  - {warning}")
        else:
            logger.error(f"Indexer '{args.name}' not found")
            return 1

    except Exception as e:
        logger.error(f"Failed to get indexer status: {e}")
        return 1

    return 0


async def cmd_backfill_embeddings(args):
    """Backfill content_vector for existing documents in an index.

    Streams documents in pages, generates embeddings, and merges updates.
    """
    cfg = get_config()
    index_name = args.index or cfg.acs_index_name
    page_size = max(1, int(args.batch_size))
    max_docs = args.max_docs if getattr(args, 'max_docs', None) and args.max_docs > 0 else None
    dry_run = bool(getattr(args, 'dry_run', False))

    # Initialize REST client and helpers
    rest_client = AzureSearchClient(
        endpoint=cfg.acs_endpoint,
        api_key=cfg.acs_admin_key.get_secret_value()
    )
    rest_ops = SearchOperations(rest_client)
    data_automation = DataAutomation(rest_ops)
    emb_automation = EmbeddingAutomation(rest_ops)

    # Determine expected embedding dimensions
    try:
        expected_dims = int(cfg.embedding_dimensions)
    except Exception:
        expected_dims = 1536

    processed = 0
    enriched_total = 0
    failed_total = 0
    skip = 0

    try:
        while True:
            if max_docs is not None and processed >= max_docs:
                break

            top = min(page_size, (max_docs - processed)) if max_docs else page_size

            # Select minimal fields; include content for embedding
            results = await rest_ops.search(
                index_name,
                query='*',
                top=top,
                skip=skip,
                select=['id', 'content', 'content_vector', 'file_path', 'repository']
            )
            docs = results.get('value', [])
            if not docs:
                break

            # Filter documents missing vectors or with mismatched dimensions
            candidates = []
            for d in docs:
                vec = d.get('content_vector')
                if not isinstance(vec, list) or len(vec) != expected_dims:
                    candidates.append(d)

            if candidates and not dry_run:
                ctx_fields = ["file_path", "repository"] if getattr(args, 'include_context', False) else None
                enriched_docs, stats = await emb_automation.enrich_documents_with_embeddings(
                    candidates,
                    text_field='content',
                    embedding_field='content_vector',
                    context_fields=ctx_fields,
                    batch_size=min(128, page_size)
                )

                # Prepare merge docs (id + content_vector only)
                merge_docs = [
                    {"id": t["id"], "content_vector": t.get("content_vector")}
                    for t in enriched_docs if t.get("content_vector")
                ]

                if merge_docs:
                    async def _gen():
                        for d in merge_docs:
                            yield d
                    await data_automation.bulk_upload(
                        index_name=index_name,
                        documents=_gen(),
                        batch_size=1000,
                        merge=True
                    )

                enriched_total += stats.get('enriched', 0)
                failed_total += stats.get('failed', 0)

            processed += len(docs)
            skip += len(docs)

            if len(docs) < top:
                break
    finally:
        await rest_client.close()

    logger.info(
        "Backfill complete: processed=%s enriched=%s failed=%s dry_run=%s",
        processed, enriched_total, failed_total, dry_run
    )
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
    index_parser.add_argument(
        '--api-version',
        type=str,
        help='Override Azure Search API version for this command'
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

    # backfill-embeddings command
    backfill_parser = subparsers.add_parser(
        'backfill-embeddings',
        help='Generate and backfill content_vector for existing documents'
    )
    backfill_parser.add_argument(
        '--index',
        type=str,
        help='Target index name (default: from config)'
    )
    backfill_parser.add_argument(
        '--batch-size',
        type=int,
        default=200,
        help='Batch size per page for fetching and embedding (default: 200)'
    )
    backfill_parser.add_argument(
        '--max-docs',
        type=int,
        help='Maximum documents to process (default: all)'
    )
    backfill_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Do not write updates; only report counts'
    )
    backfill_parser.add_argument(
        '--include-context',
        action='store_true',
        help='Include file_path and repository as embedding context'
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

    # Schema automation commands removed (legacy path)

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
        'backfill-embeddings': cmd_backfill_embeddings,
        'create-indexer': cmd_create_indexer,
        'reindex': cmd_reindex,
        'indexer-status': cmd_indexer_status,
    }
    
    # Schema commands removed; nothing to add to dispatch

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

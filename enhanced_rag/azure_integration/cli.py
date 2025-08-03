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
from pathlib import Path
from typing import List, Optional
import logging

from enhanced_rag.core.config import get_config
from .enhanced_index_builder import EnhancedIndexBuilder
from .indexer_integration import IndexerIntegration, DataSourceType, LocalRepositoryIndexer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def cmd_local_repo(args):
    """Index a local repository."""
    logger.info(f"Indexing repository: {args.repo_path}")
    
    indexer = LocalRepositoryIndexer()
    
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
    
    # Determine embed_vectors setting
    embed_vectors = None
    if args.embed_vectors:
        embed_vectors = True
    elif args.no_embed_vectors:
        embed_vectors = False
    # else: None = auto-detect based on provider
    
    # Run synchronous indexing in a thread pool to avoid blocking the event loop
    await asyncio.to_thread(
        indexer.index_repository,
        repo_path=args.repo_path,
        repo_name=args.repo_name,
        patterns=patterns,
        embed_vectors=embed_vectors
    )
    
    logger.info("Repository indexing completed")


async def cmd_changed_files(args):
    """Index specific changed files."""
    logger.info(f"Indexing {len(args.files)} changed files")
    
    indexer = LocalRepositoryIndexer()
    # Run synchronous indexing in a thread pool to avoid blocking the event loop
    await asyncio.to_thread(
        indexer.index_changed_files,
        file_paths=args.files,
        repo_name=args.repo_name
    )
    
    logger.info("Changed files indexing completed")


async def cmd_create_enhanced_index(args):
    """Create enhanced RAG index."""
    logger.info(f"Creating enhanced index: {args.name}")
    
    builder = EnhancedIndexBuilder()
    
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
            expected=args.check_dimensions
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
    
    integration = IndexerIntegration()
    
    try:
        indexer = await integration.create_code_repository_indexer(
            name=args.name,
            data_source_type=DataSourceType(args.source),
            connection_string=args.conn,
            container_name=args.container,
            index_name=args.index,
            schedule_interval_minutes=args.schedule_minutes,
            include_git_metadata=args.include_git
        )
        logger.info(f"Successfully created indexer: {indexer.name}")
        logger.info(f"Target index: {indexer.target_index_name}")
        logger.info(f"Schedule: Every {args.schedule_minutes} minutes")
        
    except Exception as e:
        logger.error(f"Failed to create indexer: {e}")
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
    }
    
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

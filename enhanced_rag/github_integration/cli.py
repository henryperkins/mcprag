"""CLI interface for GitHub Integration.

Usage:
    python -m enhanced_rag.github_integration.cli <command> [options]
    
Commands:
    index-repo      Index an entire remote repository
    index-files     Index specific files from a repository
    index-pr        Index files changed in a pull request
"""

import argparse
import sys
import logging
from typing import List

from .remote_indexer import RemoteIndexer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def cmd_index_repo(args):
    """Index an entire remote repository."""
    logger.info(f"Indexing repository: {args.owner}/{args.repo} (ref: {args.ref})")
    
    indexer = RemoteIndexer()
    result = indexer.index_remote_repository(
        owner=args.owner,
        repo=args.repo,
        ref=args.ref
    )
    
    logger.info(f"✅ Indexing completed:")
    logger.info(f"   Repository: {result['repository']}")
    logger.info(f"   Files processed: {result['files_processed']}")
    logger.info(f"   Chunks indexed: {result['chunks_indexed']}")
    if result['errors'] > 0:
        logger.warning(f"   Errors: {result['errors']}")
    
    return 0 if result['errors'] == 0 else 1


def cmd_index_files(args):
    """Index specific files from a repository."""
    logger.info(f"Indexing {len(args.files)} files from {args.owner}/{args.repo}")
    
    indexer = RemoteIndexer()
    result = indexer.index_changed_files_remote(
        owner=args.owner,
        repo=args.repo,
        file_paths=args.files
    )
    
    logger.info(f"✅ Indexing completed:")
    logger.info(f"   Repository: {result['repository']}")
    logger.info(f"   Files processed: {result['files_processed']}")
    logger.info(f"   Chunks indexed: {result['chunks_indexed']}")
    if result['errors'] > 0:
        logger.warning(f"   Errors: {result['errors']}")
    
    return 0 if result['errors'] == 0 else 1


def cmd_index_pr(args):
    """Index files changed in a pull request."""
    logger.info(f"Indexing PR #{args.pr} from {args.owner}/{args.repo}")
    
    indexer = RemoteIndexer()
    
    # Get PR files
    pr_files = indexer.get_pull_request_files(
        owner=args.owner,
        repo=args.repo,
        pr_number=args.pr
    )
    
    if not pr_files:
        logger.info("No code files found in PR")
        return 0
    
    logger.info(f"Found {len(pr_files)} code files in PR")
    
    # Index the files
    result = indexer.index_changed_files_remote(
        owner=args.owner,
        repo=args.repo,
        file_paths=pr_files
    )
    
    logger.info(f"✅ Indexing completed:")
    logger.info(f"   Repository: {result['repository']}")
    logger.info(f"   Files processed: {result['files_processed']}")
    logger.info(f"   Chunks indexed: {result['chunks_indexed']}")
    if result['errors'] > 0:
        logger.warning(f"   Errors: {result['errors']}")
    
    return 0 if result['errors'] == 0 else 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="GitHub Integration CLI for Enhanced RAG",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # index-repo command
    repo_parser = subparsers.add_parser(
        'index-repo',
        help='Index an entire remote repository'
    )
    repo_parser.add_argument(
        '--owner',
        type=str,
        required=True,
        help='Repository owner (user or organization)'
    )
    repo_parser.add_argument(
        '--repo',
        type=str,
        required=True,
        help='Repository name'
    )
    repo_parser.add_argument(
        '--ref',
        type=str,
        default='main',
        help='Git ref to index (branch, tag, or commit SHA)'
    )
    
    # index-files command
    files_parser = subparsers.add_parser(
        'index-files',
        help='Index specific files from a repository'
    )
    files_parser.add_argument(
        '--owner',
        type=str,
        required=True,
        help='Repository owner'
    )
    files_parser.add_argument(
        '--repo',
        type=str,
        required=True,
        help='Repository name'
    )
    files_parser.add_argument(
        '--files',
        nargs='+',
        required=True,
        help='File paths to index (e.g., src/main.py lib/utils.js)'
    )
    
    # index-pr command
    pr_parser = subparsers.add_parser(
        'index-pr',
        help='Index files changed in a pull request'
    )
    pr_parser.add_argument(
        '--owner',
        type=str,
        required=True,
        help='Repository owner'
    )
    pr_parser.add_argument(
        '--repo',
        type=str,
        required=True,
        help='Repository name'
    )
    pr_parser.add_argument(
        '--pr',
        type=int,
        required=True,
        help='Pull request number'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Command dispatch
    commands = {
        'index-repo': cmd_index_repo,
        'index-files': cmd_index_files,
        'index-pr': cmd_index_pr,
    }
    
    if args.command in commands:
        try:
            return commands[args.command](args)
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
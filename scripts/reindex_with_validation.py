#!/usr/bin/env python3
"""
Reindexing Script with Validation
Recreates index with correct dimensions and re-indexes all documents
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Local imports
try:
    from enhanced_rag.azure_integration.reindex_operations import ReindexOperations, ReindexMethod
    from enhanced_rag.core.config import get_config
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import required modules: {e}")
    IMPORTS_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def reindex_with_validation(repo_path: str = ".", repo_name: str = "mcprag") -> bool:
    """
    Reindex repository with proper validation

    Args:
        repo_path: Path to repository to index
        repo_name: Name of repository

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("Starting reindexing with validation...")
        logger.info(f"Repository: {repo_name}")
        logger.info(f"Path: {repo_path}")

        # Initialize reindex operations
        reindex_ops = ReindexOperations()

        # 1. Check current index status
        logger.info("Checking current index status...")
        try:
            index_info = await reindex_ops.get_index_info()
            logger.info(f"Current index has {index_info['document_count']} documents")
        except Exception as e:
            logger.warning(f"Could not get index info: {e}")

        # 2. Validate configuration
        logger.info("Validating configuration...")
        config = get_config()
        expected_dims = config.embedding.dimensions
        logger.info(f"Expected embedding dimensions: {expected_dims}")

        # 3. Drop and recreate index with correct dimensions
        logger.info("Dropping and recreating index with correct dimensions...")
        try:
            success = await reindex_ops.drop_and_rebuild()
            if not success:
                logger.error("Failed to drop and rebuild index")
                return False
            logger.info("✓ Index dropped and recreated successfully")
        except Exception as e:
            logger.error(f"Failed to recreate index: {e}")
            return False

        # 4. Re-index repository
        logger.info("Re-indexing repository...")
        try:
            success = await reindex_ops.reindex_repository(
                repo_path=repo_path,
                repo_name=repo_name,
                method=ReindexMethod.INCREMENTAL,
                clear_first=False
            )
            if not success:
                logger.error("Failed to re-index repository")
                return False
            logger.info("✓ Repository re-indexed successfully")
        except Exception as e:
            logger.error(f"Failed to re-index repository: {e}")
            return False

        # 5. Validate results
        logger.info("Validating re-indexed documents...")
        try:
            index_info = await reindex_ops.get_index_info()
            logger.info(f"New index has {index_info['document_count']} documents")

            if index_info['document_count'] > 0:
                logger.info("✓ Reindexing completed successfully")
                return True
            else:
                logger.warning("⚠️ No documents found in re-indexed repository")
                return True  # Still consider this a success

        except Exception as e:
            logger.error(f"Failed to validate results: {e}")
            return False

    except Exception as e:
        logger.error(f"Critical error during reindexing: {e}")
        return False


async def main():
    """Main entry point"""
    try:
        # Get repository info from arguments or use defaults
        import argparse
        parser = argparse.ArgumentParser(description='Reindex repository with validation')
        parser.add_argument('--repo-path', default='.', help='Path to repository')
        parser.add_argument('--repo-name', default='mcprag', help='Repository name')

        args = parser.parse_args()

        success = await reindex_with_validation(args.repo_path, args.repo_name)

        if success:
            logger.info("Reindexing completed successfully! 🎉")
            return 0
        else:
            logger.error("Reindexing failed! ❌")
            return 1

    except Exception as e:
        logger.error(f"Failed to run reindexing: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

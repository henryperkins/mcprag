#!/usr/bin/env python3
"""
Index Health Verification Script
Checks for embedding dimension mismatches and other index issues
"""

import asyncio
import logging
from typing import Dict, Any
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

from enhanced_rag.core.config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def verify_index_health(index_name: str = "codebase-mcp-sota") -> Dict[str, Any]:
    """
    Comprehensive index health check

    Args:
        index_name: Name of the Azure Search index to verify

    Returns:
        Dictionary containing health check results
    """
    config = get_config()
    results = {
        'index_name': index_name,
        'vector_field_checks': [],
        'sample_documents': [],
        'issues': [],
        'status': 'healthy'
    }

    try:
        # Initialize clients
        credential = AzureKeyCredential(config.azure.admin_key)
        index_client = SearchIndexClient(
            endpoint=config.azure.endpoint,
            credential=credential
        )
        search_client = SearchClient(
            endpoint=config.azure.endpoint,
            index_name=index_name,
            credential=credential
        )

        logger.info(f"Checking index: {index_name}")

        # 1. Check vector dimensions in index schema
        logger.info("Checking vector field dimensions...")
        try:
            index = index_client.get_index(index_name)
            expected_dims = config.embedding.dimensions

            for field in index.fields:
                if hasattr(field, 'vector_search_dimensions') and field.vector_search_dimensions:
                    field_info = {
                        'name': field.name,
                        'dimensions': field.vector_search_dimensions,
                        'expected': expected_dims,
                        'match': field.vector_search_dimensions == expected_dims
                    }
                    results['vector_field_checks'].append(field_info)

                    if not field_info['match']:
                        issue = f"Vector field '{field.name}' dimension mismatch: got {field_info['dimensions']}, expected {expected_dims}"
                        logger.warning(issue)
                        results['issues'].append(issue)
                        results['status'] = 'unhealthy'
                    else:
                        logger.info(f"✓ Vector field '{field.name}': {field.vector_search_dimensions} dimensions")

        except Exception as e:
            error_msg = f"Failed to check index schema: {e}"
            logger.error(error_msg)
            results['issues'].append(error_msg)
            results['status'] = 'unhealthy'

        # 2. Sample document check
        logger.info("Sampling documents for vector validation...")
        try:
            # Search for sample documents
            search_results = search_client.search(
                search_text="*",
                top=5,
                select=["id", "content", "content_vector", "file_path", "@search.score"]
            )

            for i, doc in enumerate(search_results):
                doc_info = {
                    'id': doc.get('id', 'unknown'),
                    'has_content': bool(doc.get('content')),
                    'file_path': doc.get('file_path', 'unknown'),
                    'score': doc.get('@search.score', 0.0)
                }

                vector = doc.get('content_vector')
                if vector:
                    doc_info['vector_dims'] = len(vector)
                    doc_info['is_zero_vector'] = all(v == 0 for v in vector[:10])  # Check first 10 elements
                    doc_info['expected_dims'] = config.embedding.dimensions
                    doc_info['dimension_match'] = len(vector) == config.embedding.dimensions

                    if not doc_info['dimension_match']:
                        issue = f"Document {doc_info['id']}: vector dimension mismatch - got {len(vector)}, expected {config.embedding.dimensions}"
                        logger.warning(issue)
                        results['issues'].append(issue)
                        results['status'] = 'unhealthy'

                    if doc_info['is_zero_vector']:
                        issue = f"Document {doc_info['id']}: contains zero vector (potential embedding failure)"
                        logger.warning(issue)
                        results['issues'].append(issue)
                        results['status'] = 'unhealthy'
                else:
                    doc_info['vector_dims'] = 0
                    doc_info['has_vector'] = False

                results['sample_documents'].append(doc_info)
                logger.info(f"Document {i+1}: id={doc_info['id']}, vector_dims={doc_info.get('vector_dims', 'N/A')}")

        except Exception as e:
            error_msg = f"Failed to sample documents: {e}"
            logger.error(error_msg)
            results['issues'].append(error_msg)
            results['status'] = 'unhealthy'

    except Exception as e:
        error_msg = f"Critical error during health check: {e}"
        logger.error(error_msg)
        results['issues'].append(error_msg)
        results['status'] = 'unhealthy'

    # Summary
    logger.info(f"Health check complete. Status: {results['status']}")
    if results['issues']:
        logger.info("Issues found:")
        for issue in results['issues']:
            logger.info(f"  - {issue}")
    else:
        logger.info("No issues found. Index appears healthy.")

    return results


def print_health_report(results: Dict[str, Any]) -> None:
    """Print a formatted health report"""
    print("\n" + "="*60)
    print(f"INDEX HEALTH REPORT: {results['index_name']}")
    print("="*60)
    print(f"Status: {results['status'].upper()}")

    if results['vector_field_checks']:
        print("\nVector Field Checks:")
        print("-" * 40)
        for check in results['vector_field_checks']:
            status = "✓" if check['match'] else "✗"
            print(f"  {status} {check['name']}: {check['dimensions']} (expected: {check['expected']})")

    if results['sample_documents']:
        print("\nSample Documents:")
        print("-" * 40)
        for doc in results['sample_documents']:
            vector_status = "N/A"
            if 'vector_dims' in doc:
                if doc.get('dimension_match', True) and not doc.get('is_zero_vector', False):
                    vector_status = f"✓ {doc['vector_dims']} dims"
                else:
                    vector_status = f"✗ {doc['vector_dims']} dims"
            print(f"  {doc['id'][:20]:20} | {vector_status:15} | {doc['file_path'][:30] if doc['file_path'] else 'N/A'}")

    if results['issues']:
        print("\nIssues Found:")
        print("-" * 40)
        for issue in results['issues']:
            print(f"  • {issue}")

    print("="*60)


async def main():
    """Main entry point"""
    try:
        results = await verify_index_health()
        print_health_report(results)

        # Return appropriate exit code
        return 0 if results['status'] == 'healthy' else 1

    except Exception as e:
        logger.error(f"Failed to run health check: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

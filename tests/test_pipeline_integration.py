#!/usr/bin/env python3
"""
Test the complete enhanced RAG pipeline with vector debugging queries
"""

import asyncio
import logging
from typing import Dict, Any

from enhanced_rag.pipeline import RAGPipeline
from enhanced_rag.core.models import QueryContext

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RAGPipelineTester:
    """Test harness for the enhanced RAG pipeline"""
    
    def __init__(self):
        # Configure pipeline with enhanced features
        self.config = {
            'retrieval': {
                'enable_vector_search': True,
                'enable_semantic_search': True,
                'enable_pattern_matching': True,
                'max_results': 20
            },
            'ranking': {
                'enable_contextual_boost': True,
                'enable_learning': False  # Disable for testing
            },
            'learning': {
                'enable_adaptive_ranking': False,  # Disable for testing
                'feedback_storage_path': './test_feedback'
            },
            'generation': {
                'enable_response_generation': True
            }
        }
        
        self.pipeline = RAGPipeline(self.config)
        
    async def run_test_queries(self):
        """Run a series of test queries focused on vector debugging"""
        
        # Test queries for vector debugging scenarios
        test_cases = [
            {
                'name': 'Vector dimension mismatch',
                'query': 'vector dimension mismatch error ValueError',
                'context': QueryContext(
                    current_file='embeddings/vector_search.py',
                    workspace_root='/project',
                    user_preferences={'language': 'python'}
                )
            },
            {
                'name': 'Embedding NaN issues',
                'query': 'embedding NaN values None check validation',
                'context': QueryContext(
                    current_file='models/embedder.py',
                    workspace_root='/project',
                    user_preferences={'language': 'python'}
                )
            },
            {
                'name': 'Vector search problems',
                'query': 'vector search issues empty results similarity threshold',
                'context': QueryContext(
                    current_file='search/similarity_search.py',
                    workspace_root='/project',
                    user_preferences={'language': 'python'}
                )
            },
            {
                'name': 'Index corruption',
                'query': 'vector index corrupt rebuild HNSW',
                'context': QueryContext(
                    current_file='indexing/vector_index.py',
                    workspace_root='/project'
                )
            },
            {
                'name': 'Cosine similarity implementation',
                'query': 'implement cosine similarity vector search',
                'context': QueryContext(
                    current_file='metrics/similarity.py',
                    workspace_root='/project'
                )
            }
        ]
        
        for test_case in test_cases:
            logger.info(f"\n{'='*60}")
            logger.info(f"Running test: {test_case['name']}")
            logger.info(f"Query: {test_case['query']}")
            logger.info(f"{'='*60}")
            
            try:
                result = await self.pipeline.process_query(
                    query=test_case['query'],
                    context=test_case['context'],
                    generate_response=True,
                    max_results=10
                )
                
                if result.success:
                    self._display_results(result)
                else:
                    logger.error(f"Query failed: {result.error}")
                    
            except Exception as e:
                logger.error(f"Test failed with exception: {e}", exc_info=True)
                
            # Small delay between tests
            await asyncio.sleep(1)
    
    def _display_results(self, result: Dict[str, Any]):
        """Display test results in a readable format"""
        
        # Show response if generated
        if result.response:
            logger.info(f"\n📝 Generated Response:")
            logger.info(f"{result.response.text[:500]}...")
        
        # Show result count and summary
        logger.info(f"\n📊 Results Summary:")
        logger.info(f"Total results: {len(result.results)}")
        
        if 'summary' in result.metadata:
            summary = result.metadata['summary']
            logger.info(f"By type: {summary.get('by_type', {})}")
            logger.info(f"Suggested terms: {summary.get('suggested_terms', [])}")
        
        # Show top 5 results in compact format
        logger.info(f"\n🔍 Top Results (Compact):")
        for i, res in enumerate(result.results[:5]):
            logger.info(f"{i+1}. {res.file_path}:{res.start_line if res.start_line else '?'}")
            logger.info(f"   Context: {res.relevance_explanation}")
            logger.info(f"   Score: {res.score:.3f}")
            
            # Show a snippet of the code
            if res.code_snippet:
                snippet_lines = res.code_snippet.strip().split('\n')
                preview = snippet_lines[0][:80] + '...' if len(snippet_lines[0]) > 80 else snippet_lines[0]
                logger.info(f"   Code: {preview}")
        
        # Show grouped results if available
        if hasattr(result, 'grouped_results') and result.grouped_results:
            logger.info(f"\n📁 Grouped Results:")
            for group_name, group_results in result.grouped_results.items():
                if group_results:
                    logger.info(f"  {group_name}: {len(group_results)} results")
                    for res in group_results[:2]:
                        logger.info(f"    - {res['file']}: {res['summary']}")
        
        # Show search stages used
        if 'stages_executed' in result.metadata:
            logger.info(f"\n🔧 Search Stages Executed:")
            for stage in result.metadata['stages_executed']:
                logger.info(f"  - {stage}")
    
    async def test_query_enhancement(self):
        """Test the query enhancement capabilities"""
        logger.info(f"\n{'='*60}")
        logger.info("Testing Query Enhancement")
        logger.info(f"{'='*60}")
        
        from enhanced_rag.semantic.query_enhancer import ContextualQueryEnhancer
        from enhanced_rag.core.models import CodeContext
        
        enhancer = ContextualQueryEnhancer()
        
        test_queries = [
            "vector issues",
            "embedding problems",
            "dimension mismatch",
            "NaN values in vector"
        ]
        
        for query in test_queries:
            logger.info(f"\nOriginal query: '{query}'")
            
            # Create a mock context
            context = CodeContext(
                current_file='test.py',
                language='python',
                imports=['numpy', 'sklearn.metrics.pairwise'],
                functions=['create_embedding', 'vector_search'],
                classes=['VectorIndex']
            )
            
            # Get enhancements
            enhancement_result = await enhancer.enhance_query(query, context)
            
            logger.info(f"Enhanced queries ({len(enhancement_result['queries'])}):")
            for i, enhanced in enumerate(enhancement_result['queries'][:5]):
                logger.info(f"  {i+1}. {enhanced}")
            
            if enhancement_result['exclude_terms']:
                logger.info(f"Exclude terms: {enhancement_result['exclude_terms']}")
    
    async def test_pattern_matching(self):
        """Test the pattern matching capabilities"""
        logger.info(f"\n{'='*60}")
        logger.info("Testing Pattern Matching")
        logger.info(f"{'='*60}")
        
        from enhanced_rag.retrieval.pattern_matcher import PatternMatcher
        
        matcher = PatternMatcher()
        
        test_queries = [
            "vector dimension mismatch error handling",
            "check if embedding is None",
            "cosine similarity implementation",
            "rebuild vector index"
        ]
        
        for query in test_queries:
            logger.info(f"\nQuery: '{query}'")
            
            patterns = await matcher.find_patterns(query)
            
            if patterns:
                logger.info(f"Found {len(patterns)} patterns:")
                for pattern in patterns[:3]:
                    logger.info(f"  - {pattern.pattern_type.value}: {pattern.pattern_name}")
                    logger.info(f"    Confidence: {pattern.confidence:.2f}")
                    logger.info(f"    Matched keywords: {pattern.context.get('matched_keywords', [])}")
            else:
                logger.info("  No patterns found")


async def main():
    """Run all tests"""
    tester = RAGPipelineTester()
    
    # Test query enhancement first
    await tester.test_query_enhancement()
    
    # Test pattern matching
    await tester.test_pattern_matching()
    
    # Run full pipeline tests
    await tester.run_test_queries()
    
    logger.info("\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
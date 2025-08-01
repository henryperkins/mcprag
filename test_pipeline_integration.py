#!/usr/bin/env python3
"""
Test script to verify MultiStageRetriever integration in RAGPipeline
"""

import asyncio
import logging
from enhanced_rag.pipeline import RAGPipeline, QueryContext
from enhanced_rag.core.models import SearchIntent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_retriever_integration():
    """Test just the MultiStageRetriever integration"""

    try:
        # Test MultiStageRetriever directly
        logger.info("Testing MultiStageRetriever directly...")

        from enhanced_rag.retrieval.multi_stage_pipeline import MultiStageRetriever
        from enhanced_rag.core.models import SearchQuery, SearchIntent

        # Create retriever with minimal config
        retriever_config = {
            'enable_vector_search': True,
            'enable_pattern_matching': True,
            'enable_dependency_resolution': True
        }

        retriever = MultiStageRetriever(retriever_config)
        logger.info("✅ MultiStageRetriever initialized successfully")

        # Create test search query
        search_query = SearchQuery(
            query="how to implement async function",
            intent=SearchIntent.IMPLEMENT,
            current_file="test_file.py",
            language="python",
            user_id="test-user"
        )

        logger.info(f"Testing retrieval with query: '{search_query.query}'")

        # Test retrieval (this will test the integration)
        results = await retriever.retrieve(search_query)

        # Check results
        logger.info(f"✅ Retrieval completed successfully")
        logger.info(f"Results count: {len(results)}")

        for i, result in enumerate(results[:3]):  # Show first 3 results
            logger.info(f"Result {i+1}: {result.file_path} (score: {result.score:.3f})")

        logger.info("🎉 MultiStageRetriever integration test PASSED")

        return True

    except Exception as e:
        logger.error(f"❌ MultiStageRetriever integration test FAILED: {e}")
        return False


async def test_pipeline_integration():
    """Test the RAGPipeline process_query method specifically"""

    try:
        # First test the retriever directly
        retriever_success = await test_retriever_integration()

        if not retriever_success:
            logger.error("Retriever test failed, skipping pipeline test")
            return

        logger.info("\n" + "="*50)
        logger.info("Testing pipeline process_query integration...")

        # Test just the process_query method with mocked components
        from enhanced_rag.pipeline import RAGPipeline, QueryContext
        from enhanced_rag.core.models import SearchQuery, SearchIntent, CodeContext

        # Create a minimal pipeline instance
        pipeline = RAGPipeline.__new__(RAGPipeline)  # Create without calling __init__

        # Mock the components we need
        class MockRetriever:
            async def retrieve(self, query):
                from enhanced_rag.core.models import SearchResult
                return [
                    SearchResult(
                        id="test-1",
                        score=0.9,
                        file_path="test_file.py",
                        code_snippet="async def example(): pass",
                        language="python"
                    )
                ]

        class MockRanker:
            async def rank_results(self, results, context, intent):
                return results  # Return as-is

        class MockExplainer:
            async def explain_ranking(self, result, query, context):
                return {"explanation": "Test explanation"}

        # Set up minimal pipeline
        pipeline.retriever = MockRetriever()
        pipeline.ranker = MockRanker()
        pipeline.result_explainer = MockExplainer()
        pipeline.feedback_collector = None

        # Create test context
        context = QueryContext(
            current_file="test_file.py",
            workspace_root="/test/workspace",
            session_id="test-session"
        )

        # Mock the context extraction
        async def mock_extract_context(ctx):
            return CodeContext(
                current_file=ctx.current_file,
                language="python",
                imports=[],
                functions=[],
                classes=[],
                recent_changes=[],
                project_root=ctx.workspace_root,
                open_files=[],
                session_id=ctx.session_id
            )

        pipeline._extract_context = mock_extract_context

        # Mock other components
        class MockIntentClassifier:
            async def classify_intent(self, query):
                return SearchIntent.IMPLEMENT

        class MockQueryEnhancer:
            async def enhance_query(self, query, context, intent):
                return [query]

        pipeline.intent_classifier = MockIntentClassifier()
        pipeline.query_enhancer = MockQueryEnhancer()

        # Test the process_query method
        test_query = "how to implement async function"
        logger.info(f"Testing process_query with: '{test_query}'")

        result = await pipeline.process_query(
            query=test_query,
            context=context,
            generate_response=False,  # Skip response generation
            max_results=5
        )

        # Check results
        logger.info(f"✅ process_query completed successfully")
        logger.info(f"Success: {result.success}")
        logger.info(f"Results count: {len(result.results)}")
        logger.info(f"Metadata: {result.metadata}")

        if result.success and len(result.results) > 0:
            logger.info("🎉 Pipeline process_query integration test PASSED")
        else:
            logger.warning(f"⚠️ Process query test had issues: {result.error}")

    except Exception as e:
        logger.error(f"❌ Pipeline integration test FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_pipeline_integration())

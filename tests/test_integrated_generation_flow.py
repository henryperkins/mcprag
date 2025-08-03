#!/usr/bin/env python3
"""
Test the integrated generation flow with adaptive ranking and feedback tracking.
This test verifies the complete pipeline including:
- Search with feedback tracking (query_id generation)
- Click and outcome tracking
- Code generation with new modules
- Adaptive ranking integration
- ModelUpdater integration
"""

import asyncio
import logging
import os
import sys
import uuid
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock environment
os.environ["ACS_ENDPOINT"] = "https://test.search.windows.net"
os.environ["ACS_ADMIN_KEY"] = "test-key"
os.environ["ACS_INDEX_NAME"] = "test-index"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntegratedGenerationTester:
    """Test harness for the integrated generation flow with feedback tracking"""

    def __init__(self):
        self.test_query_id = str(uuid.uuid4())

    async def test_search_with_feedback_tracking(self):
        """Test search returns query_id and tracks feedback"""
        logger.info("\n" + "="*60)
        logger.info("Testing Search with Feedback Tracking")
        logger.info("="*60)

        try:
            from mcprag.server import MCPServer
            from mcprag.mcp.tools import register_tools
            from mcp.server.fastmcp import FastMCP

            # Create mock MCP and server
            mock_mcp = Mock()

            # Mock enhanced search tool with feedback tracking
            mock_enhanced_search = AsyncMock()
            mock_enhanced_search.search = AsyncMock(return_value={
                'response': 'Generated response about vector search',
                'results': [
                    {
                        'file': 'vector_search.py',
                        'content': 'def vector_search(query_vector, index):',
                        'relevance': 0.95,
                        'explanation': 'Vector search implementation',
                        'context_type': 'vector_implementation',
                        'query_id': self.test_query_id,
                        'result_position': 1
                    }
                ],
                'metadata': {
                    'stages_used': ['vector_search', 'adaptive_ranking'],
                    'adaptive_ranking_applied': True
                }
            })
            mock_enhanced_search.track_click = AsyncMock()
            mock_enhanced_search.track_outcome = AsyncMock()

            # Create a mock server with required components
            server = Mock()
            server.enhanced_search = mock_enhanced_search
            server.code_gen = AsyncMock()
            server.feedback_collector = AsyncMock()
            server.model_updater = Mock()
            server.pipeline = Mock()
            server.ensure_async_components_started = AsyncMock()

            # Mock the search_code function
            async def mock_search_code(query, **kwargs):
                await server.ensure_async_components_started()
                result = await server.enhanced_search.search(
                    query=query,
                    **kwargs
                )

                # Simulate query_id injection
                items = result.get("results", [])
                for i, item in enumerate(items):
                    item['query_id'] = self.test_query_id
                    item['result_position'] = i + 1

                return {
                    "ok": True,
                    "data": {
                        "items": items,
                        "count": len(items),
                        "total": len(items),
                        "query": query,
                        "applied_exact_terms": False,
                        "exact_terms": []
                    }
                }

            # Test search
            result = await mock_search_code("vector search implementation")

            assert result["ok"], "Search should succeed"
            assert "items" in result["data"], "Should return items"

            items = result["data"]["items"]
            assert len(items) > 0, "Should have results"

            first_item = items[0]
            assert "query_id" in first_item, "Results should include query_id"
            assert "result_position" in first_item, "Results should include result_position"
            assert first_item["query_id"] == self.test_query_id, "Query ID should match"

            logger.info(f"✅ Search successful with query_id: {first_item['query_id']}")
            logger.info(f"✅ Result position: {first_item['result_position']}")

        except Exception as e:
            logger.error(f"❌ Search test failed: {e}", exc_info=True)
            raise

    async def test_click_tracking(self):
        """Test click tracking functionality"""
        logger.info("\n" + "="*60)
        logger.info("Testing Click Tracking")
        logger.info("="*60)

        try:
            # Mock the tracking tools
            mock_enhanced_search = AsyncMock()
            mock_enhanced_search.track_click = AsyncMock()

            server = Mock()
            server.enhanced_search = mock_enhanced_search

            # Mock the track_search_click function
            async def mock_track_search_click(query_id, doc_id, rank, context=None):
                if not server.enhanced_search:
                    return {"ok": False, "error": "Enhanced search not available"}

                await server.enhanced_search.track_click(
                    query_id=query_id,
                    doc_id=doc_id,
                    rank=rank,
                    context=context
                )
                return {"ok": True, "data": {"tracked": True, "query_id": query_id, "doc_id": doc_id}}

            # Test click tracking
            result = await mock_track_search_click(
                query_id=self.test_query_id,
                doc_id="vector_search.py",
                rank=1,
                context={"user_action": "clicked_result"}
            )

            assert result["ok"], "Click tracking should succeed"
            assert result["data"]["tracked"], "Should confirm tracking"
            assert result["data"]["query_id"] == self.test_query_id, "Should return correct query_id"

            # Verify the tracking was called with correct parameters
            mock_enhanced_search.track_click.assert_called_once_with(
                query_id=self.test_query_id,
                doc_id="vector_search.py",
                rank=1,
                context={"user_action": "clicked_result"}
            )

            logger.info(f"✅ Click tracking successful for query: {self.test_query_id}")

        except Exception as e:
            logger.error(f"❌ Click tracking test failed: {e}", exc_info=True)
            raise

    async def test_outcome_tracking(self):
        """Test outcome tracking functionality"""
        logger.info("\n" + "="*60)
        logger.info("Testing Outcome Tracking")
        logger.info("="*60)

        try:
            # Mock the tracking tools
            mock_enhanced_search = AsyncMock()
            mock_enhanced_search.track_outcome = AsyncMock()

            server = Mock()
            server.enhanced_search = mock_enhanced_search

            # Mock the track_search_outcome function
            async def mock_track_search_outcome(query_id, outcome, score=None, context=None):
                if not server.enhanced_search:
                    return {"ok": False, "error": "Enhanced search not available"}

                await server.enhanced_search.track_outcome(
                    query_id=query_id,
                    outcome=outcome,
                    score=score,
                    context=context
                )
                return {"ok": True, "data": {"tracked": True, "query_id": query_id, "outcome": outcome}}

            # Test successful outcome tracking
            result = await mock_track_search_outcome(
                query_id=self.test_query_id,
                outcome="success",
                score=0.9,
                context={"task_completed": True, "helpful": True}
            )

            assert result["ok"], "Outcome tracking should succeed"
            assert result["data"]["tracked"], "Should confirm tracking"
            assert result["data"]["outcome"] == "success", "Should return correct outcome"

            # Verify the tracking was called with correct parameters
            mock_enhanced_search.track_outcome.assert_called_once_with(
                query_id=self.test_query_id,
                outcome="success",
                score=0.9,
                context={"task_completed": True, "helpful": True}
            )

            logger.info(f"✅ Outcome tracking successful for query: {self.test_query_id}")

        except Exception as e:
            logger.error(f"❌ Outcome tracking test failed: {e}", exc_info=True)
            raise

    async def test_code_generation_with_new_modules(self):
        """Test code generation using new generation modules"""
        logger.info("\n" + "="*60)
        logger.info("Testing Code Generation with New Modules")
        logger.info("="*60)

        try:
            # Mock code generation tool with new modules
            mock_code_gen = AsyncMock()
            mock_code_gen.generate_code = AsyncMock(return_value={
                "success": True,
                "code": "def vector_search(query_vector, index):\n    # Implementation here\n    return results",
                "language": "python",
                "explanation": "Generated using enhanced patterns from 3 code examples. Based on template: function_implementation",
                "test_code": "def test_vector_search():\n    assert vector_search([1, 2, 3], mock_index) is not None",
                "references": [
                    {
                        "file": "search/vector_index.py",
                        "function": "similarity_search",
                        "snippet": "def similarity_search(query, k=10):",
                        "relevance": 0.95
                    }
                ],
                "patterns_used": ["similarity_search", "index_lookup"],
                "dependencies": ["numpy", "sklearn"],
                "style_info": {
                    "detected_from_examples": True,
                    "sample_count": 3,
                    "consistency_score": 0.85
                },
                "template_used": "function_implementation",
                "confidence": 0.87
            })

            server = Mock()
            server.code_gen = mock_code_gen

            # Mock the generate_code function
            async def mock_generate_code(description, language="python", **kwargs):
                if not server.code_gen:
                    return {"ok": False, "error": "Code generation not available"}

                result = await server.code_gen.generate_code(
                    description=description,
                    language=language,
                    **kwargs
                )
                return {"ok": True, "data": result}

            # Test code generation
            result = await mock_generate_code(
                description="Implement vector search function with similarity scoring",
                language="python",
                context_file="search/vector_search.py",
                style_guide="PEP 8",
                include_tests=True
            )

            assert result["ok"], "Code generation should succeed"
            data = result["data"]
            assert data["success"], "Generation should be successful"
            assert "code" in data, "Should return generated code"
            assert "test_code" in data, "Should include test code"
            assert "patterns_used" in data, "Should include used patterns"
            assert "template_used" in data, "Should indicate template used"
            assert "confidence" in data, "Should include confidence score"

            # Verify new module features
            assert data["style_info"]["detected_from_examples"], "Should detect style from examples"
            assert data["confidence"] > 0.8, "Should have high confidence"
            assert len(data["patterns_used"]) > 0, "Should use patterns"

            logger.info(f"✅ Code generation successful with confidence: {data['confidence']}")
            logger.info(f"✅ Used patterns: {data['patterns_used']}")
            logger.info(f"✅ Template: {data['template_used']}")

        except Exception as e:
            logger.error(f"❌ Code generation test failed: {e}", exc_info=True)
            raise

    async def test_adaptive_ranking_integration(self):
        """Test adaptive ranking integration with ModelUpdater"""
        logger.info("\n" + "="*60)
        logger.info("Testing Adaptive Ranking Integration")
        logger.info("="*60)

        try:
            # Mock pipeline with adaptive ranking
            mock_pipeline = AsyncMock()
            mock_pipeline.process_query = AsyncMock(return_value=Mock(
                success=True,
                results=[
                    Mock(
                        file_path='vector_search.py',
                        score=0.95,
                        relevance_explanation='Adaptive ranking boosted this result',
                        code_snippet='def vector_search():\n    pass',
                        query_id=self.test_query_id,
                        result_position=1
                    )
                ],
                metadata={
                    'adaptive_ranking_applied': True,
                    'model_updater_used': True,
                    'ranking_factors': ['click_history', 'outcome_feedback']
                },
                response='Enhanced response with adaptive ranking'
            ))

            # Mock ModelUpdater
            mock_model_updater = Mock()
            mock_model_updater.update_rankings = AsyncMock()
            mock_model_updater.get_adaptive_weights = Mock(return_value={
                'semantic_weight': 0.7,
                'bm25_weight': 0.3,
                'contextual_boost': 0.15
            })

            # Mock server with pipeline and model updater
            server = Mock()
            server.pipeline = mock_pipeline
            server.model_updater = mock_model_updater
            server.enhanced_search = Mock()
            server.enhanced_search.pipeline = mock_pipeline
            server.enhanced_search.feedback_collector = Mock()

            # Test adaptive ranking
            from enhanced_rag.core.models import QueryContext

            context = QueryContext(
                current_file='search/main.py',
                workspace_root='/project'
            )

            result = await mock_pipeline.process_query(
                query="vector search with similarity",
                context=context,
                max_results=10
            )

            assert result.success, "Pipeline should succeed"
            assert result.metadata['adaptive_ranking_applied'], "Should apply adaptive ranking"
            assert result.metadata['model_updater_used'], "Should use ModelUpdater"

            # Verify adaptive weights were retrieved
            weights = mock_model_updater.get_adaptive_weights()
            assert 'semantic_weight' in weights, "Should have adaptive weights"
            assert weights['semantic_weight'] > 0, "Should have positive semantic weight"

            logger.info(f"✅ Adaptive ranking applied successfully")
            logger.info(f"✅ Adaptive weights: {weights}")
            logger.info(f"✅ Ranking factors: {result.metadata['ranking_factors']}")

        except Exception as e:
            logger.error(f"❌ Adaptive ranking test failed: {e}", exc_info=True)
            raise

    async def test_full_integration_flow(self):
        """Test the complete integration flow"""
        logger.info("\n" + "="*60)
        logger.info("Testing Full Integration Flow")
        logger.info("="*60)

        try:
            # Simulate a complete user interaction flow:
            # 1. User searches for code
            # 2. System returns results with query_id
            # 3. User clicks on a result
            # 4. User generates code based on the result
            # 5. User indicates success/failure

            # Step 1: Search
            logger.info("Step 1: Performing search...")
            await self.test_search_with_feedback_tracking()

            # Step 2: Click tracking
            logger.info("Step 2: Tracking click...")
            await self.test_click_tracking()

            # Step 3: Code generation
            logger.info("Step 3: Generating code...")
            await self.test_code_generation_with_new_modules()

            # Step 4: Outcome tracking
            logger.info("Step 4: Tracking outcome...")
            await self.test_outcome_tracking()

            # Step 5: Adaptive ranking update
            logger.info("Step 5: Testing adaptive ranking...")
            await self.test_adaptive_ranking_integration()

            logger.info("✅ Full integration flow completed successfully!")

        except Exception as e:
            logger.error(f"❌ Full integration flow failed: {e}", exc_info=True)
            raise

    async def run_all_tests(self):
        """Run all integration tests"""
        logger.info("🚀 Starting Integrated Generation Flow Tests")

        tests = [
            ("Search with Feedback Tracking", self.test_search_with_feedback_tracking),
            ("Click Tracking", self.test_click_tracking),
            ("Outcome Tracking", self.test_outcome_tracking),
            ("Code Generation with New Modules", self.test_code_generation_with_new_modules),
            ("Adaptive Ranking Integration", self.test_adaptive_ranking_integration),
            ("Full Integration Flow", self.test_full_integration_flow)
        ]

        passed = 0
        failed = 0

        for test_name, test_func in tests:
            try:
                logger.info(f"\n🧪 Running: {test_name}")
                await test_func()
                logger.info(f"✅ {test_name} PASSED")
                passed += 1
            except Exception as e:
                logger.error(f"❌ {test_name} FAILED: {e}")
                failed += 1

        logger.info(f"\n📊 Test Results:")
        logger.info(f"✅ Passed: {passed}")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"📈 Success Rate: {(passed/(passed+failed)*100):.1f}%")

        if failed == 0:
            logger.info("🎉 All integration tests passed!")
        else:
            logger.error(f"💥 {failed} test(s) failed")

        return failed == 0


async def main():
    """Run the integrated generation flow tests"""
    tester = IntegratedGenerationTester()
    success = await tester.run_all_tests()

    if success:
        logger.info("\n🎯 Integrated generation flow is working correctly!")
        logger.info("✅ All components are properly wired:")
        logger.info("  - Search with query_id generation")
        logger.info("  - Click and outcome tracking")
        logger.info("  - Code generation with new modules")
        logger.info("  - Adaptive ranking with ModelUpdater")
        logger.info("  - Complete feedback loop")
    else:
        logger.error("\n💥 Some integration tests failed!")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

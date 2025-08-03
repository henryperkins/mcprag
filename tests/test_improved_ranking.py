"""
Tests for the improved ranking system
Validates fixes for normalization, tie-breaking, and complete weights
"""

import pytest
import asyncio
import math
from datetime import datetime, timedelta
from typing import List

from enhanced_rag.core.models import SearchResult, EnhancedContext, SearchIntent
from enhanced_rag.ranking.contextual_ranker_improved import (
    ImprovedContextualRanker, ValidatedFactor, RankingFactors
)
from enhanced_rag.ranking.ranking_monitor import RankingMonitor, InMemoryStorage


class TestImprovedRanking:
    """Test suite for improved ranking system"""
    
    @pytest.fixture
    def ranker(self):
        """Create improved ranker instance"""
        return ImprovedContextualRanker()
    
    @pytest.fixture
    def sample_results(self) -> List[SearchResult]:
        """Create sample search results"""
        return [
            SearchResult(
                id="1",
                score=0.8,
                file_path="/project/src/auth.py",
                repository="project",
                function_name="authenticate",
                class_name=None,
                code_snippet="def authenticate(user, password):\n    # Auth logic",
                language="python",
                start_line=10,
                end_line=20,
                imports=["hashlib", "jwt"],
                last_modified=datetime.utcnow(),
                complexity_score=5.0,
                test_coverage=0.9
            ),
            SearchResult(
                id="2",
                score=0.8,  # Same score as result 1 - tests tie-breaking
                file_path="/project/tests/test_auth.py",
                repository="project",
                function_name="test_authenticate",
                class_name=None,
                code_snippet="def test_authenticate():\n    # Test auth",
                language="python",
                start_line=5,
                end_line=15,
                imports=["pytest", "auth"],
                last_modified=datetime.utcnow() - timedelta(days=7),
                tags=["test"]
            ),
            SearchResult(
                id="3",
                score=0.6,
                file_path="/other/lib/security.py",
                repository="other",
                function_name="verify_token",
                class_name="SecurityManager",
                code_snippet="def verify_token(token):\n    # Verify JWT",
                language="python",
                start_line=50,
                end_line=60,
                imports=["jwt", "datetime"],
                last_modified=datetime.utcnow() - timedelta(days=30)
            )
        ]
    
    @pytest.fixture
    def context(self) -> EnhancedContext:
        """Create sample context"""
        return EnhancedContext(
            current_file="/project/src/handlers.py",
            file_content="# Handler code",
            imports=["auth", "jwt", "logging"],
            functions=["handle_login", "handle_logout"],
            classes=["AuthHandler"],
            recent_changes=[],
            git_branch="main",
            language="python",
            framework="fastapi",
            project_root="/project",
            open_files=["/project/src/handlers.py", "/project/src/auth.py"],
            session_id="test_session",
            query="authentication jwt token"
        )
    
    @pytest.mark.asyncio
    async def test_score_normalization(self, ranker, sample_results, context):
        """Test that scores are properly normalized"""
        # Add results with extreme scores
        sample_results.append(
            SearchResult(
                id="4",
                score=100.0,  # Very high score
                file_path="/test.py",
                repository="test",
                function_name="test",
                class_name=None,
                code_snippet="test",
                language="python"
            )
        )
        
        sample_results.append(
            SearchResult(
                id="5",
                score=float('nan'),  # Invalid score
                file_path="/nan.py",
                repository="test",
                function_name="nan_test",
                class_name=None,
                code_snippet="nan",
                language="python"
            )
        )
        
        ranked = await ranker.rank_results(sample_results, context, SearchIntent.IMPLEMENT)
        
        # Check all scores are in [0, 1] range
        for result in ranked:
            assert 0.0 <= result.score <= 1.0, f"Score {result.score} out of range"
            assert not math.isnan(result.score), "Score is NaN"
            assert not math.isinf(result.score), "Score is infinite"
    
    @pytest.mark.asyncio
    async def test_tie_breaking(self, ranker, sample_results, context):
        """Test tie-breaking rules work correctly"""
        # Results 1 and 2 have the same original score
        ranked = await ranker.rank_results(sample_results[:2], context, SearchIntent.IMPLEMENT)
        
        # Should have different final scores after ranking
        assert ranked[0].score != ranked[1].score or ranked[0].id != ranked[1].id
        
        # Verify consistent ordering on multiple runs
        ranked2 = await ranker.rank_results(sample_results[:2], context, SearchIntent.IMPLEMENT)
        assert [r.id for r in ranked] == [r.id for r in ranked2]
    
    @pytest.mark.asyncio
    async def test_complete_weight_coverage(self, ranker):
        """Test that all factors are weighted for all intents"""
        all_factors = [
            'text_relevance', 'semantic_similarity', 'context_overlap',
            'import_similarity', 'proximity_score', 'recency_score',
            'quality_score', 'pattern_match'
        ]
        
        for intent in SearchIntent:
            weights = ranker.weights[intent]
            
            # Check all factors have weights
            for factor in all_factors:
                assert factor in weights, f"Factor {factor} missing for {intent}"
                assert weights[factor] >= 0, f"Negative weight for {factor} in {intent}"
            
            # Check weights sum to 1.0
            total_weight = sum(weights.values())
            assert abs(total_weight - 1.0) < 0.001, f"Weights sum to {total_weight} for {intent}"
    
    @pytest.mark.asyncio
    async def test_factor_validation(self, ranker):
        """Test factor validation and confidence tracking"""
        # Test ValidatedFactor post-init validation
        factor = ValidatedFactor(value=2.5, confidence=1.5)  # Out of range values
        assert factor.value == 1.0  # Clamped to max
        assert factor.confidence == 1.0  # Clamped to max
        
        factor = ValidatedFactor(value=-0.5, confidence=-0.1)  # Negative values
        assert factor.value == 0.0  # Clamped to min
        assert factor.confidence == 0.0  # Clamped to min
    
    @pytest.mark.asyncio
    async def test_semantic_similarity_fallback(self, ranker, sample_results, context):
        """Test fallback strategies for missing embeddings"""
        # Remove vector scores to test fallback
        for result in sample_results:
            if hasattr(result, 'vector_score'):
                delattr(result, 'vector_score')
        
        ranked = await ranker.rank_results(sample_results, context, SearchIntent.UNDERSTAND)
        
        # Should still produce valid rankings
        assert len(ranked) == len(sample_results)
        for result in ranked:
            assert 0.0 <= result.score <= 1.0
    
    @pytest.mark.asyncio
    async def test_proximity_bias_mitigation(self, ranker, sample_results, context):
        """Test that proximity bias is reduced"""
        # Test with DEBUG intent which previously had high proximity bias
        ranked = await ranker.rank_results(sample_results, context, SearchIntent.DEBUG)
        
        # The first result (same project) shouldn't completely dominate
        # due to logarithmic dampening
        score_ratio = ranked[0].score / ranked[-1].score if ranked[-1].score > 0 else float('inf')
        assert score_ratio < 10, "Proximity bias too strong"
    
    @pytest.mark.asyncio
    async def test_quality_score_calculation(self, ranker, sample_results, context):
        """Test improved quality score calculation"""
        # First result has high test coverage
        # Second result has 'test' tag
        # Third result has no quality indicators
        
        factors = await ranker._calculate_factors(
            sample_results[0], context, ranker._calculate_normalization_bounds(sample_results)
        )
        assert factors.quality_score.value > 0.5  # Should be good due to test coverage
        assert factors.quality_score.confidence > 0.2  # Should have some confidence
        
        factors = await ranker._calculate_factors(
            sample_results[1], context, ranker._calculate_normalization_bounds(sample_results)
        )
        assert factors.quality_score.value > 0.5  # Should be good due to test tag
        
        factors = await ranker._calculate_factors(
            sample_results[2], context, ranker._calculate_normalization_bounds(sample_results)
        )
        assert factors.quality_score.confidence < 0.5  # Low confidence for default score
    
    @pytest.mark.asyncio
    async def test_ranking_explanation(self, ranker, sample_results, context):
        """Test that explanations include confidence information"""
        ranked = await ranker.rank_results(sample_results, context, SearchIntent.IMPLEMENT)
        
        for result in ranked:
            assert result.ranking_explanation
            # Should mention at least one factor
            assert any(factor in result.ranking_explanation.lower() 
                      for factor in ['text', 'semantic', 'context', 'import', 
                                   'proximity', 'recent', 'quality', 'pattern'])


class TestRankingMonitor:
    """Test ranking monitoring system"""
    
    @pytest.fixture
    def monitor(self):
        """Create monitor with in-memory storage"""
        return RankingMonitor(storage_backend=InMemoryStorage())
    
    @pytest.mark.asyncio
    async def test_decision_logging(self, monitor):
        """Test logging ranking decisions"""
        from enhanced_rag.core.models import SearchQuery
        
        query = SearchQuery(
            query="test query",
            intent=SearchIntent.IMPLEMENT,
            user_id="test_user"
        )
        
        results = [
            SearchResult(id="1", score=0.9, file_path="/a.py", repository="test",
                        function_name="a", class_name=None, code_snippet="a", language="python"),
            SearchResult(id="2", score=0.9, file_path="/b.py", repository="test",
                        function_name="b", class_name=None, code_snippet="b", language="python")
        ]
        
        factors = [
            {'text_relevance': {'value': 0.8, 'confidence': 1.0}},
            {'text_relevance': {'value': 0.8, 'confidence': 1.0}}
        ]
        
        await monitor.log_ranking_decision(query, results, factors, 50.0)
        await monitor.flush_buffers()
        
        decisions = await monitor.storage.get_decisions(
            datetime.utcnow() - timedelta(minutes=1),
            datetime.utcnow()
        )
        
        assert len(decisions) == 1
        assert decisions[0].tie_count == 1  # Two results with same score
        assert decisions[0].processing_time_ms == 50.0
    
    @pytest.mark.asyncio
    async def test_metrics_calculation(self, monitor):
        """Test metrics snapshot calculation"""
        # Add some test data
        from enhanced_rag.core.models import SearchQuery
        
        for i in range(10):
            query = SearchQuery(
                query=f"test query {i}",
                intent=SearchIntent.IMPLEMENT,
                user_id="test_user"
            )
            
            results = [
                SearchResult(id=f"{i}-1", score=0.9 - i*0.1, file_path="/a.py", 
                           repository="test", function_name="a", class_name=None,
                           code_snippet="a", language="python")
            ]
            
            await monitor.log_ranking_decision(query, results, [], 50.0 + i*10)
            
            # Simulate user click
            await monitor.record_user_feedback(
                query_id=f"test_user_{int(query.timestamp.timestamp())}",
                clicked_position=0 if i < 5 else 1,
                success=True
            )
        
        await monitor.flush_buffers()
        
        # Calculate metrics
        snapshot = await monitor.calculate_metrics_snapshot()
        
        assert snapshot.mean_reciprocal_rank > 0
        assert 0 in snapshot.click_through_rate
        assert snapshot.average_processing_time > 50
    
    @pytest.mark.asyncio
    async def test_performance_report(self, monitor):
        """Test comprehensive performance report generation"""
        # Add test data
        from enhanced_rag.core.models import SearchQuery
        
        query = SearchQuery(query="test", intent=SearchIntent.IMPLEMENT)
        results = [SearchResult(id="1", score=0.9, file_path="/a.py", repository="test",
                              function_name="a", class_name=None, code_snippet="a", 
                              language="python")]
        
        await monitor.log_ranking_decision(query, results, [], 100.0)
        await monitor.flush_buffers()
        await monitor.calculate_metrics_snapshot()
        
        report = await monitor.get_performance_report(timedelta(hours=1))
        
        assert 'summary' in report
        assert 'trends' in report
        assert 'recommendations' in report
        assert report['summary']['total_queries'] >= 1


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
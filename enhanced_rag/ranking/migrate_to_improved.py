"""
Migration script to switch to the improved ranking system
"""

import asyncio
import logging
from typing import Optional

from .contextual_ranker import ContextualRanker
from .contextual_ranker_improved import ImprovedContextualRanker
from .ranking_monitor import RankingMonitor

logger = logging.getLogger(__name__)


async def migrate_to_improved_ranker(
    config: Optional[dict] = None,
    enable_monitoring: bool = True
) -> ImprovedContextualRanker:
    """
    Migrate from the original ranker to the improved version
    
    Args:
        config: Optional configuration dictionary
        enable_monitoring: Whether to enable ranking monitoring
        
    Returns:
        ImprovedContextualRanker: Configured improved ranker instance
    """
    logger.info("Starting migration to improved ranking system")
    
    # Create improved ranker
    improved_ranker = ImprovedContextualRanker(config)
    
    # Set up monitoring if enabled
    monitor = None
    if enable_monitoring:
        monitor = RankingMonitor()
        logger.info("Ranking monitoring enabled")
    
    # Wrap ranker with monitoring
    if monitor:
        original_rank_results = improved_ranker.rank_results
        
        async def monitored_rank_results(results, context, intent):
            import time
            start_time = time.time()
            
            # Run original ranking
            ranked_results = await original_rank_results(results, context, intent)
            
            # Calculate processing time
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Log to monitor if we have query info
            if hasattr(context, 'query'):
                from ..core.models import SearchQuery
                query = SearchQuery(
                    query=context.query,
                    intent=intent,
                    current_file=context.current_file,
                    language=context.language,
                    framework=context.framework
                )
                
                # Extract factors from results
                factors = []
                for result in ranked_results:
                    if hasattr(result, '_ranking_factors'):
                        factors.append(result._ranking_factors)
                
                await monitor.log_ranking_decision(
                    query, ranked_results, factors, processing_time_ms
                )
            
            return ranked_results
        
        improved_ranker.rank_results = monitored_rank_results
    
    logger.info("Migration completed successfully")
    return improved_ranker


def update_imports_in_codebase():
    """
    Update import statements across the codebase
    This would typically be done with a code modification tool
    """
    updates = [
        {
            'file': 'enhanced_rag/pipeline.py',
            'old': 'from .ranking.contextual_ranker import ContextualRanker',
            'new': 'from .ranking.contextual_ranker_improved import ImprovedContextualRanker as ContextualRanker'
        },
        {
            'file': 'mcp_server_sota.py',
            'old': 'from enhanced_rag.ranking.contextual_ranker import ContextualRanker',
            'new': 'from enhanced_rag.ranking.contextual_ranker_improved import ImprovedContextualRanker as ContextualRanker'
        }
    ]
    
    print("To complete migration, update the following imports:")
    for update in updates:
        print(f"\nFile: {update['file']}")
        print(f"Old: {update['old']}")
        print(f"New: {update['new']}")


if __name__ == "__main__":
    # Example usage
    print("Improved Ranking System Migration")
    print("=================================")
    print()
    print("Key improvements:")
    print("1. ✓ Score normalization with validation")
    print("2. ✓ Multi-level tie-breaking rules")
    print("3. ✓ Complete weight coverage for all intents")
    print("4. ✓ Factor validation with confidence tracking")
    print("5. ✓ Fallback strategies for missing data")
    print("6. ✓ Bias mitigation (logarithmic proximity dampening)")
    print("7. ✓ Improved quality score calculation")
    print("8. ✓ Comprehensive monitoring and analytics")
    print()
    print("To migrate:")
    print("1. Run: python -m enhanced_rag.ranking.migrate_to_improved")
    print("2. Update imports as shown above")
    print("3. Test with sample queries")
    print("4. Monitor metrics via RankingMonitor")
    
    update_imports_in_codebase()
"""
Result explanation module for Enhanced RAG system
Explains why search results are relevant to the user's query
"""

import logging
from typing import Dict, Any, List, Optional
from ..core.models import SearchResult, SearchQuery, CodeContext

logger = logging.getLogger(__name__)


class ResultExplainer:
    """
    Explains why search results are relevant to queries
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    async def explain_ranking(
        self,
        result: SearchResult,
        query: SearchQuery,
        context: Optional[CodeContext] = None
    ) -> Dict[str, Any]:
        """
        Explain why a result is relevant to the query

        Args:
            result: The search result to explain
            query: The original search query
            context: Optional code context

        Returns:
            Dictionary with explanation details
        """
        explanation_parts = []
        factors = {}

        # Score-based explanation
        if result.score > 0.8:
            explanation_parts.append("High relevance match")
            factors['score_level'] = 'high'
        elif result.score > 0.5:
            explanation_parts.append("Good relevance match")
            factors['score_level'] = 'medium'
        else:
            explanation_parts.append("Partial relevance match")
            factors['score_level'] = 'low'

        # Function name match
        if result.function_name and query.query.lower() in result.function_name.lower():
            explanation_parts.append(f"Function name '{result.function_name}' matches query")
            factors['function_name_match'] = True

        # Language match
        if query.language and result.language == query.language:
            explanation_parts.append(f"Matches requested language ({result.language})")
            factors['language_match'] = True

        # Context similarity
        if result.context_similarity and result.context_similarity > 0.7:
            explanation_parts.append("Similar to current code context")
            factors['context_similarity'] = result.context_similarity

        # Import overlap
        if result.import_overlap and result.import_overlap > 0.5:
            explanation_parts.append("Uses similar imports/dependencies")
            factors['import_overlap'] = result.import_overlap

        # Pattern match
        if result.pattern_match and result.pattern_match > 0.6:
            explanation_parts.append("Follows similar architectural patterns")
            factors['pattern_match'] = result.pattern_match

        # Repository match
        if context and context.project_root and result.repository:
            if context.project_root in result.file_path:
                explanation_parts.append("From current project")
                factors['same_project'] = True

        # Combine explanation
        explanation = "; ".join(explanation_parts) if explanation_parts else "General relevance match"

        return {
            'explanation': explanation,
            'factors': factors,
            'confidence': min(result.score, 1.0)
        }

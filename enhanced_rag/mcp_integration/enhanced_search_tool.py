"""
Enhanced MCP search tool using the RAG pipeline
"""

import logging
import uuid
from typing import Dict, Any, List, Optional

from ..pipeline import RAGPipeline
from ..core.models import QueryContext

logger = logging.getLogger(__name__)


class EnhancedSearchTool:
    """
    MCP tool wrapper for enhanced RAG search
    """

    def __init__(self, config: Dict[str, Any]):
        self.pipeline = RAGPipeline(config)
        self.feedback_collector = getattr(self.pipeline, 'feedback_collector', None)

    async def search(
        self,
        query: str,
        current_file: Optional[str] = None,
        workspace_root: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute enhanced search through RAG pipeline
        """
        # Build preferences dict with all search parameters
        base_prefs = kwargs.get('preferences', {})
        if not isinstance(base_prefs, dict):
            base_prefs = {}

        # Pass through important search parameters
        passthrough_keys = [
            'repository', 'bm25_only', 'exact_terms', 'intent',
            'language', 'framework', 'disable_cache', 'simulate_failure',
            'max_results', 'skip', 'orderby'
        ]
        preferences = dict(base_prefs)
        for key in passthrough_keys:
            if key in kwargs:
                preferences[key] = kwargs[key]

        # Build context
        context = QueryContext(
            current_file=current_file,
            workspace_root=workspace_root,
            user_preferences=preferences
        )

        # Process through pipeline
        result = await self.pipeline.process_query(
            query=query,
            context=context,
            generate_response=kwargs.get('generate_response', True),
            max_results=kwargs.get('max_results', 10)
        )

        # Track query if feedback collector is available
        if self.feedback_collector and hasattr(result, 'results'):
            query_id = await self._track_query(query, kwargs.get('intent'), result.results)

            # Add query_id to results for tracking clicks
            if hasattr(result, 'results'):
                for i, res in enumerate(result.results):
                    if hasattr(res, '__dict__'):
                        res.query_id = query_id
                        # Only set result_position if not already set
                        if not hasattr(res, 'result_position') or res.result_position is None:
                            res.result_position = i + 1

        # Format for MCP
        return self._format_mcp_response(result)

    def _format_mcp_response(self, result) -> Dict[str, Any]:
        """Format pipeline result for MCP"""
        # Handle RAGPipelineResult object
        if hasattr(result, 'success'):
            if not result.success:
                return {
                    'error': result.error
                }

            results = result.results[:10]
        else:
            # Legacy dict format
            if not result['success']:
                return {
                    'error': result['error']
                }

            results = result['results'][:10]

        # Generate compact and ultra-compact formats
        results_compact = []
        results_ultra_compact = []

        for i, r in enumerate(results, start=1):
            # Infer context type from content and explanation
            context_type = self._infer_context_type(r)

            # Compact format: structured object with key info
            compact_entry = {
                'id': getattr(r, 'id', None),
                'rank': i,
                'file': f"{r.file_path}:{r.start_line}" if hasattr(r, 'start_line') and r.start_line else r.file_path,
                'repo': getattr(r, 'repository', None),
                'language': getattr(r, 'language', None),
                'lines': [getattr(r, 'start_line', None), getattr(r, 'end_line', None)],
                # Prefer original BM25 score for display when available; fall back to original/fused score
                'score': round(float(
                    getattr(r, 'bm25_score', None)
                    or getattr(r, '_original_score', None)
                    or getattr(r, 'score', 0)
                    or 0.0
                ), 4),
                'match': self._extract_match_summary(r),
                'context_type': context_type
            }

            # Add highlight information if available
            if hasattr(r, 'highlights') and r.highlights:
                for field, hls in r.highlights.items():
                    if hls:
                        compact_entry['why'] = hls[0][:120]
                        compact_entry['why_field'] = field
                        break

            results_compact.append(compact_entry)

            # Ultra-compact format: single line string
            line_ref = f":{r.start_line}" if hasattr(r, 'start_line') and r.start_line else ""
            snippet = self._get_snippet_headline(r.code_snippet)
            ultra_compact = f"{r.file_path}{line_ref} | {r.relevance_explanation or 'Match'} | {snippet}"
            results_ultra_compact.append(ultra_compact)

        # Calculate summary statistics
        metadata = result.metadata if hasattr(result, 'metadata') else result.get('metadata', {})
        summary = self._generate_summary(results, metadata)

        # Group results by problem/pattern
        grouped_results = self._group_results_by_pattern(results)

        # Get response based on result type
        if hasattr(result, 'response'):
            response_text = result.response
        else:
            response_text = result.get('response', {}).get('text') if result.get('response') else None

        return {
            'response': response_text,
            'results': [
                {
                    'file': r.file_path,
                    'content': r.code_snippet,
                    # Prefer BM25/original score for user-facing relevance
                    'relevance': (getattr(r, 'bm25_score', None)
                                  or getattr(r, '_original_score', None)
                                  or getattr(r, 'score', 0)),
                    'explanation': r.relevance_explanation,
                    'context_type': self._infer_context_type(r),
                    'highlights': getattr(r, 'highlights', {}) or {},
                    # Provide full metadata to avoid missing fields downstream
                    'repository': getattr(r, 'repository', None) or "",
                    'language': getattr(r, 'language', None) or "",
                    'function_name': getattr(r, 'function_name', None),
                    'class_name': getattr(r, 'class_name', None),
                    'start_line': getattr(r, 'start_line', None),
                    'end_line': getattr(r, 'end_line', None)
                }
                for r in results
            ],
            'results_compact': results_compact,
            'results_ultra_compact': results_ultra_compact,
            'grouped_results': grouped_results,
            'summary': summary,
            'metadata': result.metadata if hasattr(result, 'metadata') else result.get('metadata', {})
        }

    def _infer_context_type(self, result) -> str:
        """Infer the context type from result content and metadata"""
        content_lower = (result.code_snippet or '').lower()
        explanation_lower = (result.relevance_explanation or '').lower()

        # Check for error handling patterns
        if any(term in content_lower for term in ['try', 'except', 'catch', 'error', 'exception']):
            if any(term in content_lower for term in ['vector', 'embedding', 'dimension', 'nan']):
                return "vector_error_handling"
            return "error_handling"

        # Check for implementation patterns
        if any(term in content_lower for term in ['def', 'function', 'class', 'implement']):
            if any(term in content_lower for term in ['vector_search', 'similarity', 'embedding']):
                return "vector_implementation"
            return "implementation"

        # Check for configuration
        if any(term in content_lower for term in ['config', 'settings', 'index', 'schema']):
            return "configuration"

        # Check for test patterns
        if any(term in content_lower for term in ['test_', 'assert', 'mock', 'fixture']):
            return "testing"

        # Check for documentation
        if any(term in explanation_lower for term in ['documentation', 'readme', 'comment']):
            return "documentation"

        # Default
        return "general"

    def _extract_match_summary(self, result) -> str:
        """Extract a brief summary of what matched"""
        if hasattr(result, 'function_name') and result.function_name:
            return f"Function: {result.function_name}"
        elif hasattr(result, 'class_name') and result.class_name:
            return f"Class: {result.class_name}"
        elif hasattr(result, 'highlights') and result.highlights:
            # Use first highlight
            for field, highlights in result.highlights.items():
                if highlights:
                    return f"{field}: {highlights[0][:50]}..."
        return "Code match"

    def _get_snippet_headline(self, content: str) -> str:
        """Get a one-line headline from content"""
        if not content:
            return "No content"

        # Take first non-empty line
        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('//'):
                # Truncate long lines
                if len(line) > 60:
                    return line[:57] + "..."
                return line

        return lines[0][:60] if lines else "No content"

    def _generate_summary(self, results: List, metadata: Dict) -> Dict[str, Any]:
        """Generate summary statistics and insights"""
        # Count by context type
        by_type = {}
        for r in results:
            ctx_type = self._infer_context_type(r)
            by_type[ctx_type] = by_type.get(ctx_type, 0) + 1

        # Suggest related terms based on what was found
        suggested_terms = []
        if any(self._infer_context_type(r) == "vector_error_handling" for r in results):
            suggested_terms.extend(["dimension_mismatch", "embedding_validation", "vector_config"])
        if any(self._infer_context_type(r) == "vector_implementation" for r in results):
            suggested_terms.extend(["similarity_search", "vector_index", "embedder"])

        return {
            'total': len(results),
            'by_type': by_type,
            'top_files': list(set(r.file_path for r in results[:5])),
            'suggested_terms': list(set(suggested_terms)),
            'search_stages_used': metadata.get('stages_used', [])
        }

    def _group_results_by_pattern(self, results: List) -> Dict[str, List[Dict]]:
        """Group results by problem/pattern for better organization"""
        groups = {
            'vector_initialization': [],
            'vector_errors': [],
            'vector_search': [],
            'configuration': [],
            'implementation': [],
            'testing': [],
            'documentation': [],
            'other': []
        }

        for r in results:
            content_lower = (r.code_snippet or '').lower()
            explanation_lower = (r.relevance_explanation or '').lower()
            context_type = self._infer_context_type(r)

            # Create a compact representation for grouping
            compact_result = {
                'file': f"{r.file_path}:{r.start_line}" if hasattr(r, 'start_line') and r.start_line else r.file_path,
                'summary': self._extract_match_summary(r),
                'score': r.score
            }

            # Categorize based on content and context
            if context_type == "vector_error_handling" or any(term in content_lower for term in ['dimension mismatch', 'nan', 'none embedding']):
                groups['vector_errors'].append(compact_result)
            elif any(term in content_lower for term in ['create_embedding', 'initialize_vector', 'embedder', 'vectorizer']):
                groups['vector_initialization'].append(compact_result)
            elif any(term in content_lower for term in ['vector_search', 'similarity_search', 'knn', 'cosine']):
                groups['vector_search'].append(compact_result)
            elif context_type == "configuration":
                groups['configuration'].append(compact_result)
            elif context_type == "implementation" or context_type == "vector_implementation":
                groups['implementation'].append(compact_result)
            elif context_type == "testing":
                groups['testing'].append(compact_result)
            elif context_type == "documentation":
                groups['documentation'].append(compact_result)
            else:
                groups['other'].append(compact_result)

        # Remove empty groups and sort results within groups by score
        filtered_groups = {}
        for group_name, group_results in groups.items():
            if group_results:
                # Sort by score descending
                group_results.sort(key=lambda x: x['score'], reverse=True)
                filtered_groups[group_name] = group_results

        return filtered_groups

    async def _track_query(self, query: str, intent: Optional[str], results: List[Any]) -> str:
        """Track query for feedback collection"""
        if not self.feedback_collector:
            return str(uuid.uuid4())  # Return a UUID even if no collector

        try:
            # Extract doc IDs and scores from results
            doc_ids = []
            scores = []
            metadata = {}

            for result in results[:10]:  # Top 10 for tracking
                doc_ids.append(getattr(result, 'id', result.file_path))
                scores.append(getattr(result, 'score', 0.0))

            # Collect metadata about the query
            metadata.update({
                'intent': intent,
                'result_count': len(results),
                'top_scores': scores[:5],
                'query_length': len(query),
                'has_code_terms': any(term in query.lower() for term in ['def', 'class', 'function', 'import'])
            })

            # Use feedback collector to track the query
            query_id = await self.feedback_collector.track_query(
                query=query,
                intent=intent,
                doc_ids=doc_ids,
                scores=scores,
                metadata=metadata
            )

            return query_id

        except Exception as e:
            logger.warning(f"Failed to track query: {e}")
            return str(uuid.uuid4())  # Fallback UUID

    async def track_click(self, query_id: str, doc_id: str, rank: int, context: Optional[Dict[str, Any]] = None) -> None:
        """Track user click on search result"""
        if not self.feedback_collector:
            logger.debug(f"No feedback collector available to track click: {query_id} -> {doc_id}")
            return

        try:
            await self.feedback_collector.track_click(
                query_id=query_id,
                doc_id=doc_id,
                rank=rank,
                context=context or {}
            )
            logger.debug(f"Tracked click: query={query_id}, doc={doc_id}, rank={rank}")
        except Exception as e:
            logger.error(f"Failed to track click: {e}")

    async def track_outcome(self, query_id: str, outcome: str, score: Optional[float] = None, context: Optional[Dict[str, Any]] = None) -> None:
        """Track search outcome (success/failure)"""
        if not self.feedback_collector:
            logger.debug(f"No feedback collector available to track outcome: {query_id} -> {outcome}")
            return

        try:
            await self.feedback_collector.track_outcome(
                query_id=query_id,
                outcome=outcome,
                score=score,
                context=context or {}
            )
            logger.debug(f"Tracked outcome: query={query_id}, outcome={outcome}, score={score}")
        except Exception as e:
            logger.error(f"Failed to track outcome: {e}")

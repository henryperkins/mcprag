"""
Search Agent for MCPRag

Specialist agent for code search operations with enhanced RAG pipeline.
"""

import logging
from typing import Dict, Any, Optional

from ...enhanced_rag.core.models import QueryContext

logger = logging.getLogger(__name__)


class SearchAgent:
    """
    Specialist agent for code search operations.
    
    Responsibilities:
    - General code search and exploration
    - Finding examples and patterns
    - Locating specific functions/classes
    - Discovering related code
    """
    
    SYSTEM_PROMPT = """You are a specialized search agent for the MCPRag system.
Your role is to find relevant code, examples, and patterns based on user queries.

You excel at:
- Understanding search intent and context
- Finding the most relevant code snippets
- Identifying patterns and similar implementations
- Providing comprehensive search results

You have access to:
- Enhanced RAG pipeline with semantic search
- Multi-stage retrieval strategies
- Context-aware ranking
- Code understanding capabilities

When searching:
1. Analyze the query for key concepts
2. Consider the current context (file, language, framework)
3. Use appropriate search strategies
4. Rank results by relevance
5. Provide clear explanations for each result
"""

    def __init__(self, server):
        """Initialize search agent with server reference"""
        self.server = server
        self.pipeline = server.pipeline if hasattr(server, 'pipeline') else None
        self.enhanced_search = server.enhanced_search if hasattr(server, 'enhanced_search') else None
        
    async def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute search request with specialized strategies.
        
        Args:
            request: Request from routing agent containing:
                - query: Search query
                - intent: Detected intent
                - routing_context: Context from router
                - agent_objective: Specific objective
                
        Returns:
            Search results with explanations
        """
        query = request.get("query", "")
        intent = request.get("intent")
        routing_context = request.get("routing_context", {})
        objective = request.get("agent_objective", "")
        
        logger.info(f"SearchAgent executing: {objective}")
        
        # Build query context
        context = QueryContext(
            current_file=routing_context.get("current_file"),
            workspace_root=routing_context.get("workspace_root"),
            session_id=routing_context.get("session_id"),
            user_preferences={
                "intent": intent.value if intent else None,
                "complexity": routing_context.get("complexity", "medium")
            }
        )
        
        # Configure search based on objective
        search_config = self._configure_search(intent, routing_context)
        
        # Execute search through enhanced pipeline
        if self.enhanced_search:
            try:
                result = await self.enhanced_search.search(
                    query=query,
                    current_file=context.current_file,
                    workspace_root=context.workspace_root,
                    max_results=search_config.get("max_results", 10),
                    intent=intent.value if intent else None,
                    **search_config
                )
                
                # Enhance results with agent-specific insights
                enhanced_result = self._enhance_results(result, objective)
                
                return {
                    "success": True,
                    "agent": "search_agent",
                    "objective": objective,
                    **enhanced_result
                }
                
            except Exception as e:
                logger.error(f"Search failed: {e}")
                return {
                    "success": False,
                    "agent": "search_agent",
                    "error": str(e),
                    "fallback": self._get_fallback_suggestions(query, intent)
                }
        else:
            return {
                "success": False,
                "agent": "search_agent",
                "error": "Enhanced search not available",
                "fallback": self._get_fallback_suggestions(query, intent)
            }
    
    def _configure_search(
        self, 
        intent: Any, 
        routing_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Configure search parameters based on context"""
        config = {
            "max_results": 10,
            "include_dependencies": False,
            "detail_level": "full"
        }
        
        # Adjust based on intent
        if intent:
            intent_value = intent.value if hasattr(intent, 'value') else str(intent)
            
            if intent_value == "implement":
                config["max_results"] = 15
                config["include_dependencies"] = True
                config["boost_examples"] = True
                
            elif intent_value == "debug":
                config["max_results"] = 20
                config["include_stack_traces"] = True
                config["boost_error_handling"] = True
                
            elif intent_value == "understand":
                config["include_documentation"] = True
                config["boost_well_documented"] = True
        
        # Adjust based on complexity
        complexity = routing_context.get("complexity", "medium")
        if complexity == "high":
            config["max_results"] = 20
            config["detail_level"] = "full"
        elif complexity == "low":
            config["max_results"] = 5
            config["detail_level"] = "compact"
            
        return config
    
    def _enhance_results(
        self, 
        result: Dict[str, Any], 
        objective: str
    ) -> Dict[str, Any]:
        """Enhance search results with agent-specific insights"""
        if not result.get("results"):
            return result
            
        # Add search strategy explanation
        result["search_strategy"] = {
            "objective": objective,
            "strategies_used": result.get("metadata", {}).get("search_stages_used", []),
            "ranking_factors": self._explain_ranking_factors(result)
        }
        
        # Group results by relevance category
        if "grouped_results" not in result:
            result["grouped_results"] = self._group_by_relevance(result["results"])
            
        # Add usage suggestions
        result["usage_suggestions"] = self._generate_usage_suggestions(
            result["results"], 
            objective
        )
        
        return result
    
    def _explain_ranking_factors(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Explain why results were ranked as they were"""
        factors = {
            "primary_factors": [],
            "boost_factors": []
        }
        
        # Extract from metadata if available
        metadata = result.get("metadata", {})
        if "intent" in metadata:
            factors["primary_factors"].append(f"Intent-based ranking: {metadata['intent']}")
            
        if "context_used" in metadata:
            factors["boost_factors"].append("Context-aware ranking applied")
            
        return factors
    
    def _group_by_relevance(self, results: list) -> Dict[str, list]:
        """Group results by relevance category"""
        groups = {
            "exact_matches": [],
            "high_relevance": [],
            "moderate_relevance": [],
            "related": []
        }
        
        for result in results:
            score = result.get("relevance", 0)
            
            if score >= 0.9:
                groups["exact_matches"].append(result)
            elif score >= 0.7:
                groups["high_relevance"].append(result)
            elif score >= 0.5:
                groups["moderate_relevance"].append(result)
            else:
                groups["related"].append(result)
                
        # Remove empty groups
        return {k: v for k, v in groups.items() if v}
    
    def _generate_usage_suggestions(
        self, 
        results: list, 
        objective: str
    ) -> list:
        """Generate suggestions for using the search results"""
        suggestions = []
        
        if not results:
            suggestions.append("No results found. Try broadening your search terms.")
            return suggestions
            
        # Analyze result patterns
        has_examples = any("example" in str(r).lower() for r in results[:5])
        has_tests = any("test" in str(r).lower() for r in results[:5])
        
        if has_examples:
            suggestions.append("Found example implementations - review these for patterns")
            
        if has_tests:
            suggestions.append("Found test cases - these show usage patterns")
            
        if len(results) > 10:
            suggestions.append("Many results found - consider refining your search")
            
        return suggestions
    
    def _get_fallback_suggestions(self, query: str, intent: Any) -> Dict[str, Any]:
        """Provide fallback suggestions when search fails"""
        suggestions = {
            "try_these": [],
            "tips": []
        }
        
        # General suggestions
        suggestions["try_these"].extend([
            f"Simplify to key terms: {' '.join(query.split()[:3])}",
            f"Search for function names mentioned in: {query}",
            "Use different terminology or synonyms"
        ])
        
        # Intent-specific suggestions
        if intent:
            intent_value = intent.value if hasattr(intent, 'value') else str(intent)
            
            if intent_value == "implement":
                suggestions["tips"].append("Look for 'example', 'sample', or 'tutorial'")
            elif intent_value == "debug":
                suggestions["tips"].append("Include error message or exception type")
            elif intent_value == "understand":
                suggestions["tips"].append("Search for documentation or README files")
                
        return suggestions
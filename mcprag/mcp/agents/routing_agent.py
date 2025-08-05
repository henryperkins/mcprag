"""
Routing Agent for MCPRag

Primary agent that analyzes requests and delegates to specialist agents.
Implements the routing pattern from Claude sub-agents best practices.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum

from ...enhanced_rag.semantic.intent_classifier import IntentClassifier
from ...enhanced_rag.core.models import SearchIntent, QueryContext

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Available specialist agents"""
    SEARCH = "search_agent"
    IMPLEMENT = "implementation_agent"
    DEBUG = "debug_agent"
    UNDERSTAND = "understanding_agent"
    REFACTOR = "refactor_agent"
    TEST = "test_agent"
    ADMIN = "admin_agent"


class RoutingAgent:
    """
    Primary routing agent that delegates tasks to specialist agents.
    
    This agent:
    1. Analyzes incoming requests for intent and context
    2. Selects the appropriate specialist agent(s)
    3. Manages handoffs between agents
    4. Aggregates results from multiple agents
    """
    
    # System prompt for the routing agent
    SYSTEM_PROMPT = """You are the primary routing agent for the MCPRag system.
Your role is to analyze incoming requests and delegate them to the most appropriate specialist agents.

You have access to these specialist agents:
- Search Agent: General code search and exploration
- Implementation Agent: Creating new code, features, and examples
- Debug Agent: Analyzing errors, debugging issues, and fixes
- Understanding Agent: Explaining code, architecture, and concepts
- Refactor Agent: Improving code quality and performance
- Test Agent: Writing tests and test strategies
- Admin Agent: Index management and system administration

For each request:
1. Identify the primary intent
2. Consider the context (current file, workspace, session history)
3. Select one or more specialist agents
4. Define clear objectives for each agent
5. Handle results and errors appropriately
"""

    def __init__(self, server):
        """Initialize routing agent with server reference"""
        self.server = server
        self.intent_classifier = IntentClassifier()
        
        # Agent selection rules
        self.intent_to_agents = {
            SearchIntent.IMPLEMENT: [AgentType.IMPLEMENT, AgentType.SEARCH],
            SearchIntent.DEBUG: [AgentType.DEBUG, AgentType.SEARCH],
            SearchIntent.UNDERSTAND: [AgentType.UNDERSTAND, AgentType.SEARCH],
            SearchIntent.REFACTOR: [AgentType.REFACTOR, AgentType.SEARCH],
            SearchIntent.TEST: [AgentType.TEST, AgentType.IMPLEMENT],
            SearchIntent.DOCUMENT: [AgentType.UNDERSTAND]
        }
        
        # Track agent performance
        self.agent_metrics = {agent: {"calls": 0, "errors": 0, "avg_time": 0} 
                              for agent in AgentType}
    
    async def route_request(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Route a request to appropriate specialist agents.
        
        Args:
            query: The user's request
            context: Current context (file, workspace, etc.)
            **kwargs: Additional parameters
            
        Returns:
            Aggregated results from specialist agents
        """
        # 1. Classify intent
        intent = await self.intent_classifier.classify_intent(query)
        logger.info(f"Routing request with intent: {intent.value}")
        
        # 2. Analyze context for additional routing hints
        routing_context = self._analyze_context(query, context, intent)
        
        # 3. Select appropriate agents
        selected_agents = self._select_agents(intent, routing_context)
        logger.info(f"Selected agents: {[a.value for a in selected_agents]}")
        
        # 4. Prepare agent-specific requests
        agent_requests = self._prepare_agent_requests(
            query, intent, routing_context, selected_agents
        )
        
        # 5. Execute requests (could be parallel for independent agents)
        results = {}
        errors = []
        
        for agent_type, request in agent_requests.items():
            try:
                result = await self._execute_agent_request(agent_type, request)
                results[agent_type] = result
            except Exception as e:
                logger.error(f"Agent {agent_type.value} failed: {e}")
                errors.append({"agent": agent_type.value, "error": str(e)})
                self.agent_metrics[agent_type]["errors"] += 1
        
        # 6. Aggregate and synthesize results
        final_result = self._aggregate_results(results, errors, intent)
        
        # 7. Record metrics
        self._update_metrics(selected_agents, results)
        
        return final_result
    
    def _analyze_context(
        self, 
        query: str, 
        context: Optional[Dict[str, Any]], 
        intent: SearchIntent
    ) -> Dict[str, Any]:
        """Analyze context to enhance routing decisions"""
        routing_context = {
            "has_current_file": bool(context and context.get("current_file")),
            "has_error_context": self._detect_error_context(query, context),
            "is_admin_request": self._detect_admin_request(query),
            "complexity": self._estimate_complexity(query),
            "requires_multiple_agents": False
        }
        
        # Check if multiple agents needed
        if routing_context["complexity"] == "high":
            routing_context["requires_multiple_agents"] = True
        
        if "and" in query.lower() or "then" in query.lower():
            routing_context["requires_multiple_agents"] = True
            
        return routing_context
    
    def _detect_error_context(self, query: str, context: Optional[Dict]) -> bool:
        """Check if request includes error context"""
        error_indicators = ["error", "exception", "traceback", "failed", "bug"]
        query_lower = query.lower()
        
        # Check query
        if any(indicator in query_lower for indicator in error_indicators):
            return True
            
        # Check context
        if context:
            if context.get("error_context") or context.get("last_error"):
                return True
                
        return False
    
    def _detect_admin_request(self, query: str) -> bool:
        """Check if request is for admin operations"""
        admin_keywords = ["index", "reindex", "backup", "restore", "manage", 
                         "admin", "configuration", "setup"]
        return any(keyword in query.lower() for keyword in admin_keywords)
    
    def _estimate_complexity(self, query: str) -> str:
        """Estimate query complexity"""
        word_count = len(query.split())
        
        if word_count < 10:
            return "low"
        elif word_count < 30:
            return "medium"
        else:
            return "high"
    
    def _select_agents(
        self, 
        intent: SearchIntent, 
        routing_context: Dict[str, Any]
    ) -> List[AgentType]:
        """Select appropriate agents based on intent and context"""
        # Start with intent-based selection
        agents = self.intent_to_agents.get(intent, [AgentType.SEARCH])
        
        # Add agents based on context
        if routing_context["has_error_context"]:
            if AgentType.DEBUG not in agents:
                agents.append(AgentType.DEBUG)
                
        if routing_context["is_admin_request"]:
            agents = [AgentType.ADMIN]  # Admin takes precedence
            
        # Limit agents unless explicitly multi-agent
        if not routing_context["requires_multiple_agents"] and len(agents) > 1:
            agents = agents[:1]  # Take primary agent only
            
        return agents
    
    def _prepare_agent_requests(
        self,
        query: str,
        intent: SearchIntent,
        routing_context: Dict[str, Any],
        agents: List[AgentType]
    ) -> Dict[AgentType, Dict[str, Any]]:
        """Prepare specific requests for each selected agent"""
        requests = {}
        
        for agent in agents:
            request = {
                "query": query,
                "intent": intent,
                "routing_context": routing_context,
                "agent_objective": self._get_agent_objective(agent, intent, query)
            }
            
            # Add agent-specific parameters
            if agent == AgentType.IMPLEMENT:
                request["include_dependencies"] = True
                request["generate_example"] = True
                
            elif agent == AgentType.DEBUG:
                request["include_stack_trace"] = routing_context["has_error_context"]
                request["analyze_patterns"] = True
                
            elif agent == AgentType.TEST:
                request["coverage_analysis"] = True
                request["test_framework"] = "auto-detect"
                
            requests[agent] = request
            
        return requests
    
    def _get_agent_objective(
        self, 
        agent: AgentType, 
        intent: SearchIntent, 
        query: str
    ) -> str:
        """Define clear objective for each agent"""
        objectives = {
            AgentType.SEARCH: f"Find relevant code for: {query}",
            AgentType.IMPLEMENT: f"Create implementation for: {query}",
            AgentType.DEBUG: f"Debug and fix issue: {query}",
            AgentType.UNDERSTAND: f"Explain and document: {query}",
            AgentType.REFACTOR: f"Improve code quality for: {query}",
            AgentType.TEST: f"Create test strategy for: {query}",
            AgentType.ADMIN: f"Execute admin operation: {query}"
        }
        
        return objectives.get(agent, f"Process request: {query}")
    
    async def _execute_agent_request(
        self,
        agent_type: AgentType,
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute request through appropriate specialist agent"""
        # Update metrics
        self.agent_metrics[agent_type]["calls"] += 1
        
        # Route to appropriate agent implementation
        if agent_type == AgentType.SEARCH:
            from .search_agent import SearchAgent
            agent = SearchAgent(self.server)
            return await agent.execute(request)
            
        elif agent_type == AgentType.IMPLEMENT:
            from .implementation_agent import ImplementationAgent
            agent = ImplementationAgent(self.server)
            return await agent.execute(request)
            
        elif agent_type == AgentType.DEBUG:
            from .debug_agent import DebugAgent
            agent = DebugAgent(self.server)
            return await agent.execute(request)
            
        elif agent_type == AgentType.UNDERSTAND:
            from .understanding_agent import UnderstandingAgent
            agent = UnderstandingAgent(self.server)
            return await agent.execute(request)
            
        elif agent_type == AgentType.REFACTOR:
            from .refactor_agent import RefactorAgent
            agent = RefactorAgent(self.server)
            return await agent.execute(request)
            
        elif agent_type == AgentType.TEST:
            from .test_agent import TestAgent
            agent = TestAgent(self.server)
            return await agent.execute(request)
            
        elif agent_type == AgentType.ADMIN:
            from .admin_agent import AdminAgent
            agent = AdminAgent(self.server)
            return await agent.execute(request)
            
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
    
    def _aggregate_results(
        self,
        results: Dict[AgentType, Dict[str, Any]],
        errors: List[Dict[str, Any]],
        intent: SearchIntent
    ) -> Dict[str, Any]:
        """Aggregate results from multiple agents"""
        if not results and errors:
            return {
                "success": False,
                "errors": errors,
                "message": "All agents failed to process the request"
            }
        
        # Single agent result
        if len(results) == 1:
            agent_type, result = next(iter(results.items()))
            result["routing_metadata"] = {
                "primary_agent": agent_type.value,
                "intent": intent.value,
                "errors": errors
            }
            return result
        
        # Multiple agent results - synthesize
        aggregated = {
            "success": True,
            "results": {},
            "routing_metadata": {
                "agents_used": [a.value for a in results.keys()],
                "intent": intent.value,
                "errors": errors
            }
        }
        
        # Combine results based on intent
        if intent == SearchIntent.IMPLEMENT:
            # Combine search results with implementation
            if AgentType.SEARCH in results:
                aggregated["search_results"] = results[AgentType.SEARCH]
            if AgentType.IMPLEMENT in results:
                aggregated["implementation"] = results[AgentType.IMPLEMENT]
                
        else:
            # Generic aggregation
            for agent_type, result in results.items():
                aggregated["results"][agent_type.value] = result
        
        return aggregated
    
    def _update_metrics(
        self, 
        agents: List[AgentType], 
        results: Dict[AgentType, Dict[str, Any]]
    ):
        """Update agent performance metrics"""
        for agent in agents:
            if agent in results:
                # Simple success tracking for now
                # Could be enhanced with timing, quality scores, etc.
                pass
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        return {
            "agent_metrics": {
                agent.value: metrics 
                for agent, metrics in self.agent_metrics.items()
            },
            "routing_rules": {
                intent.value: [a.value for a in agents]
                for intent, agents in self.intent_to_agents.items()
            }
        }
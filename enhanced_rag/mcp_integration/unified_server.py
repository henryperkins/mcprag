"""
Unified MCP Server Bridge - Combines direct Azure Search and enhanced RAG pipeline
"""

import logging
import os
from typing import Dict, Any, Optional, List
from enum import Enum

from mcp.server.fastmcp import FastMCP
from ...mcp_server_sota import EnhancedMCPServer
from .enhanced_search_tool import EnhancedSearchTool
from .code_gen_tool import CodeGenerationTool
from .context_aware_tool import ContextAwareTool

logger = logging.getLogger(__name__)


class SearchMode(Enum):
    """Search mode selection"""
    DIRECT = "direct"  # Use direct Azure Search
    ENHANCED = "enhanced"  # Use enhanced RAG pipeline
    AUTO = "auto"  # Automatically choose based on query


class UnifiedMCPServer:
    """
    Unified server combining direct Azure Search and enhanced RAG pipeline
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Initialize both search systems
        self.direct_server = EnhancedMCPServer()
        self.enhanced_search = EnhancedSearchTool(self.config)
        self.code_gen = CodeGenerationTool(self.config)
        self.context_tool = ContextAwareTool(self.config)
        
        # Initialize FastMCP server
        self.mcp = FastMCP("unified-code-search")
        self.setup_tools()
        
        # Configuration
        self.default_mode = SearchMode(
            self.config.get('default_search_mode', SearchMode.AUTO.value)
        )
        self.fallback_enabled = self.config.get('fallback_enabled', True)
        
    def setup_tools(self):
        """Register all MCP tools"""
        
        # Unified search tool
        @self.mcp.tool()
        async def search_code(
            query: str,
            intent: Optional[str] = None,
            language: Optional[str] = None,
            repository: Optional[str] = None,
            max_results: int = 10,
            include_dependencies: bool = False,
            current_file: Optional[str] = None,
            workspace_root: Optional[str] = None,
            search_mode: Optional[str] = None
        ) -> List[Dict[str, Any]]:
            """
            Unified code search with automatic mode selection
            
            Args:
                query: Search query
                intent: Search intent (implement/debug/understand/refactor)
                language: Filter by language
                repository: Filter by repository
                max_results: Maximum results
                include_dependencies: Include dependency resolution
                current_file: Current file for context
                workspace_root: Workspace root path
                search_mode: Force specific mode (direct/enhanced/auto)
            """
            mode = self._determine_search_mode(query, search_mode, current_file)
            
            try:
                if mode == SearchMode.ENHANCED:
                    return await self._enhanced_search(
                        query=query,
                        intent=intent,
                        language=language,
                        repository=repository,
                        max_results=max_results,
                        include_dependencies=include_dependencies,
                        current_file=current_file,
                        workspace_root=workspace_root
                    )
                else:
                    return await self._direct_search(
                        query=query,
                        intent=intent,
                        language=language,
                        repository=repository,
                        max_results=max_results,
                        include_dependencies=include_dependencies
                    )
            except Exception as e:
                logger.error(f"Search error in {mode} mode: {e}")
                
                # Try fallback if enabled
                if self.fallback_enabled and mode == SearchMode.ENHANCED:
                    logger.info("Falling back to direct search")
                    return await self._direct_search(
                        query=query,
                        intent=intent,
                        language=language,
                        repository=repository,
                        max_results=max_results,
                        include_dependencies=include_dependencies
                    )
                raise
        
        # Code generation tool
        @self.mcp.tool()
        async def generate_code(
            description: str,
            language: str = "python",
            context_file: Optional[str] = None,
            style_guide: Optional[str] = None,
            include_tests: bool = False,
            workspace_root: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Generate code using enhanced RAG pipeline
            
            Args:
                description: What code to generate
                language: Target programming language
                context_file: Current file for context
                style_guide: Specific style guide to follow
                include_tests: Whether to generate tests
                workspace_root: Workspace root path
            """
            return await self.code_gen.generate_code(
                description=description,
                language=language,
                context_file=context_file,
                style_guide=style_guide,
                include_tests=include_tests,
                workspace_root=workspace_root
            )
        
        # Refactoring tool
        @self.mcp.tool()
        async def refactor_code(
            code: str,
            refactor_type: str,
            language: str = "python",
            context_file: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Refactor code using enhanced RAG pipeline
            
            Args:
                code: Code to refactor
                refactor_type: Type of refactoring
                language: Programming language
                context_file: Current file for context
            """
            return await self.code_gen.refactor_code(
                code=code,
                refactor_type=refactor_type,
                language=language,
                context_file=context_file
            )
        
        # Context analysis tool
        @self.mcp.tool()
        async def analyze_context(
            file_path: str,
            include_dependencies: bool = True,
            depth: int = 2,
            include_imports: bool = True,
            include_git_history: bool = False
        ) -> Dict[str, Any]:
            """
            Analyze hierarchical context for a file
            
            Args:
                file_path: Path to analyze
                include_dependencies: Include dependency analysis
                depth: Depth of context analysis (1-3)
                include_imports: Include import analysis
                include_git_history: Include recent git changes
            """
            return await self.context_tool.analyze_context(
                file_path=file_path,
                include_dependencies=include_dependencies,
                depth=depth,
                include_imports=include_imports,
                include_git_history=include_git_history
            )
        
        # Improvement suggestions tool
        @self.mcp.tool()
        async def suggest_improvements(
            file_path: str,
            focus: Optional[str] = None,
            include_examples: bool = True
        ) -> Dict[str, Any]:
            """
            Suggest improvements for a file
            
            Args:
                file_path: File to analyze
                focus: Specific area to focus on
                include_examples: Include code examples
            """
            return await self.context_tool.suggest_improvements(
                file_path=file_path,
                focus=focus,
                include_examples=include_examples
            )
        
        # Similar code finder
        @self.mcp.tool()
        async def find_similar_code(
            file_path: str,
            scope: str = "project",
            threshold: float = 0.7,
            max_results: int = 10
        ) -> Dict[str, Any]:
            """
            Find similar code patterns
            
            Args:
                file_path: Reference file
                scope: Search scope (project/module/all)
                threshold: Similarity threshold (0-1)
                max_results: Maximum results
            """
            return await self.context_tool.find_similar_code(
                file_path=file_path,
                scope=scope,
                threshold=threshold,
                max_results=max_results
            )
        
        # Change tracking
        @self.mcp.tool()
        async def track_file_change(
            file_path: str,
            event_type: str = "edit",
            content: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Track file changes for context awareness
            
            Args:
                file_path: File that changed
                event_type: Type of change (edit/create/delete/rename)
                content: New content (for edit/create)
            """
            return await self.context_tool.track_changes(
                file_path=file_path,
                event_type=event_type,
                content=content
            )
        
        # Microsoft Docs search (from direct server)
        @self.mcp.tool()
        async def search_microsoft_docs(
            query: str,
            max_results: int = 10
        ) -> List[Dict[str, Any]]:
            """Search Microsoft documentation"""
            return await self.direct_server.search_microsoft_docs(
                query=query,
                max_results=max_results
            )
    
    def _determine_search_mode(
        self,
        query: str,
        requested_mode: Optional[str],
        current_file: Optional[str]
    ) -> SearchMode:
        """Determine which search mode to use"""
        # Use requested mode if provided
        if requested_mode:
            try:
                return SearchMode(requested_mode)
            except ValueError:
                logger.warning(f"Invalid search mode: {requested_mode}")
        
        # Use default if not auto
        if self.default_mode != SearchMode.AUTO:
            return self.default_mode
        
        # Auto mode logic
        # Use enhanced for complex queries or when context is available
        if current_file or self._is_complex_query(query):
            return SearchMode.ENHANCED
        
        # Use direct for simple lookups
        return SearchMode.DIRECT
    
    def _is_complex_query(self, query: str) -> bool:
        """Check if query benefits from enhanced search"""
        complex_indicators = [
            'implement', 'refactor', 'similar to',
            'like', 'pattern', 'example of',
            'how to', 'best practice', 'optimize'
        ]
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in complex_indicators)
    
    async def _enhanced_search(self, **kwargs) -> List[Dict[str, Any]]:
        """Execute search through enhanced RAG pipeline"""
        result = await self.enhanced_search.search(
            query=kwargs['query'],
            current_file=kwargs.get('current_file'),
            workspace_root=kwargs.get('workspace_root'),
            generate_response=True,
            intent=kwargs.get('intent'),
            language=kwargs.get('language'),
            repository=kwargs.get('repository'),
            max_results=kwargs.get('max_results', 10),
            include_dependencies=kwargs.get('include_dependencies', False)
        )
        
        # Convert to expected format
        if result.get('success') and 'results' in result:
            return result['results']
        return []
    
    async def _direct_search(self, **kwargs) -> List[Dict[str, Any]]:
        """Execute search through direct Azure Search"""
        return await self.direct_server.search_code(
            query=kwargs['query'],
            intent=kwargs.get('intent'),
            language=kwargs.get('language'),
            repository=kwargs.get('repository'),
            max_results=kwargs.get('max_results', 10),
            include_dependencies=kwargs.get('include_dependencies', False)
        )
    
    async def start(self):
        """Start the unified MCP server"""
        # Initialize both systems
        await self.direct_server.initialize()
        
        # Start MCP server
        await self.mcp.run()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        return {
            'default_mode': self.default_mode.value,
            'fallback_enabled': self.fallback_enabled,
            'direct_server_ready': hasattr(self.direct_server, 'search_client'),
            'enhanced_pipeline_ready': hasattr(self.enhanced_search, 'pipeline')
        }


# Integration with Azure MCP tools
class AzureMCPIntegration:
    """
    Integrate Azure MCP tools with enhanced RAG pipeline
    """
    
    def __init__(self, unified_server: UnifiedMCPServer):
        self.server = unified_server
        self.available_tools = self._discover_azure_tools()
        
    def _discover_azure_tools(self) -> Dict[str, List[str]]:
        """Discover available Azure MCP tools from environment"""
        # Read from cline_mcp_settings.json if available
        tools = {
            'search': [
                'azmcp_search_index_query',
                'azmcp_search_index_describe',
                'azmcp_search_index_list',
                'azmcp_search_service_list'
            ],
            'cosmos': [
                'azmcp_cosmos_database_container_item_query',
                'azmcp_cosmos_database_list'
            ],
            'monitor': [
                'azmcp_monitor_metrics_query',
                'azmcp_monitor_resource_log_query'
            ]
        }
        return tools
    
    async def enhance_search_with_metrics(
        self,
        query: str,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Enhance search results with Azure Monitor metrics"""
        # Would integrate with azmcp_monitor_metrics_query
        # to add performance data to results
        return results
    
    async def cross_service_search(self, query: str) -> Dict[str, Any]:
        """Search across multiple Azure services"""
        results = {}
        
        # Search in AI Search
        if 'azmcp_search_index_query' in self.available_tools.get('search', []):
            # Would call the Azure MCP tool
            results['search'] = []
        
        # Search in Cosmos if applicable
        if self._is_data_query(query) and 'azmcp_cosmos_database_container_item_query' in self.available_tools.get('cosmos', []):
            # Would call the Cosmos MCP tool
            results['cosmos'] = []
        
        return results
    
    def _is_data_query(self, query: str) -> bool:
        """Check if query is data-related"""
        data_keywords = ['data', 'record', 'document', 'database', 'collection']
        return any(kw in query.lower() for kw in data_keywords)


# Main entry point
async def create_unified_server(config: Optional[Dict[str, Any]] = None) -> UnifiedMCPServer:
    """Create and configure unified MCP server"""
    server = UnifiedMCPServer(config)
    
    # Add Azure integration if available
    if os.getenv('ENABLE_AZURE_MCP_INTEGRATION', 'false').lower() == 'true':
        azure_integration = AzureMCPIntegration(server)
        server.azure_integration = azure_integration
    
    return server
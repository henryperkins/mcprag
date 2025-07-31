"""
Enhanced MCP search tool using the RAG pipeline
"""

import logging
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
        # Build context
        context = QueryContext(
            current_file=current_file,
            workspace_root=workspace_root,
            user_preferences=kwargs.get('preferences', {})
        )
        
        # Process through pipeline
        result = await self.pipeline.process_query(
            query=query,
            context=context,
            generate_response=kwargs.get('generate_response', True)
        )
        
        # Format for MCP
        return self._format_mcp_response(result)
    
    def _format_mcp_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format pipeline result for MCP"""
        if not result['success']:
            return {
                'error': result['error']
            }
            
        return {
            'response': result['response'].text if result['response'] else None,
            'results': [
                {
                    'file': r.file_path,
                    'content': r.content,
                    'relevance': r.score,
                    'explanation': r.ranking_explanation
                }
                for r in result['results'][:10]
            ],
            'metadata': result['metadata']
        }

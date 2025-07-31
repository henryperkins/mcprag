"""
Core interfaces for Enhanced RAG system
Defines abstract base classes that all modules must implement
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from .models import (
    SearchQuery, 
    SearchResult, 
    CodeContext, 
    EnhancedContext,
    RankingMetrics,
    UserPreferences
)


class ContextProvider(ABC):
    """Interface for context extraction and analysis"""
    
    @abstractmethod
    async def get_context(
        self, 
        file_path: str,
        open_files: Optional[List[str]] = None,
        recent_edits: Optional[List[Tuple[str, datetime]]] = None
    ) -> CodeContext:
        """Extract context from current work environment"""
        pass
    
    @abstractmethod
    async def get_hierarchical_context(
        self,
        file_path: str,
        depth: int = 3
    ) -> EnhancedContext:
        """Get multi-level hierarchical context"""
        pass


class QueryEnhancer(ABC):
    """Interface for query enhancement and rewriting"""
    
    @abstractmethod
    async def classify_intent(self, query: str) -> str:
        """Classify query intent (implement/debug/understand/refactor)"""
        pass
    
    @abstractmethod
    async def enhance_query(
        self,
        query: str,
        context: CodeContext,
        intent: Optional[str] = None
    ) -> List[str]:
        """Generate enhanced query variants"""
        pass
    
    @abstractmethod
    async def generate_variants(
        self,
        query: str,
        max_variants: int = 10
    ) -> List[str]:
        """Generate multiple query variants for better coverage"""
        pass


class Retriever(ABC):
    """Interface for multi-stage retrieval"""
    
    @abstractmethod
    async def search(
        self,
        queries: List[str],
        context: Optional[CodeContext] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Execute multi-stage retrieval pipeline"""
        pass
    
    @abstractmethod
    async def get_dependencies(
        self,
        code_chunk: str,
        language: str
    ) -> List[SearchResult]:
        """Resolve code dependencies"""
        pass


class Ranker(ABC):
    """Interface for result ranking and filtering"""
    
    @abstractmethod
    async def rank_results(
        self,
        results: List[SearchResult],
        query: SearchQuery,
        context: CodeContext
    ) -> List[SearchResult]:
        """Rank results based on relevance and context"""
        pass
    
    @abstractmethod
    async def explain_ranking(
        self,
        result: SearchResult,
        query: SearchQuery,
        context: CodeContext
    ) -> Dict[str, Any]:
        """Explain why a result is relevant"""
        pass
    
    @abstractmethod
    async def get_ranking_metrics(
        self,
        results: List[SearchResult]
    ) -> RankingMetrics:
        """Get detailed ranking metrics"""
        pass


class CodeAnalyzer(ABC):
    """Interface for code understanding and analysis"""
    
    @abstractmethod
    async def analyze_ast(
        self,
        code: str,
        language: str
    ) -> Dict[str, Any]:
        """Perform AST analysis on code"""
        pass
    
    @abstractmethod
    async def extract_patterns(
        self,
        code: str,
        language: str
    ) -> List[str]:
        """Extract design patterns from code"""
        pass
    
    @abstractmethod
    async def build_dependency_graph(
        self,
        file_paths: List[str]
    ) -> Dict[str, List[str]]:
        """Build dependency graph for files"""
        pass


class FeedbackCollector(ABC):
    """Interface for learning and feedback collection"""
    
    @abstractmethod
    async def record_interaction(
        self,
        query: SearchQuery,
        selected_results: List[SearchResult],
        context: CodeContext,
        outcome: str
    ) -> None:
        """Record user interaction for learning"""
        pass
    
    @abstractmethod
    async def get_user_preferences(
        self,
        user_id: str
    ) -> UserPreferences:
        """Get learned user preferences"""
        pass
    
    @abstractmethod
    async def update_ranking_model(
        self,
        feedback_data: List[Dict[str, Any]]
    ) -> None:
        """Update ranking model based on feedback"""
        pass


class Generator(ABC):
    """Interface for code generation"""
    
    @abstractmethod
    async def generate_code(
        self,
        description: str,
        context: CodeContext,
        style_examples: List[SearchResult]
    ) -> str:
        """Generate code based on context and examples"""
        pass
    
    @abstractmethod
    async def adapt_to_style(
        self,
        code: str,
        target_style: Dict[str, Any]
    ) -> str:
        """Adapt code to match project style"""
        pass
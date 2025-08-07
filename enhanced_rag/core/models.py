"""
Pydantic models for Enhanced RAG system
Provides type-safe data structures used throughout the system
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class SearchIntent(str, Enum):
    """Search intent classification"""
    IMPLEMENT = "implement"
    DEBUG = "debug"
    UNDERSTAND = "understand"
    REFACTOR = "refactor"
    TEST = "test"
    DOCUMENT = "document"


class ContextLevel(str, Enum):
    """Hierarchical context levels"""
    FILE = "file"
    MODULE = "module"
    PROJECT = "project"
    CROSS_PROJECT = "cross_project"


class SearchQuery(BaseModel):
    """Enhanced search query with context"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    query: str
    intent: Optional[SearchIntent] = None
    current_file: Optional[str] = None
    open_files: List[str] = Field(default_factory=list)
    language: Optional[str] = None
    framework: Optional[str] = None
    task_context: Optional[str] = None
    user_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    exclude_terms: List[str] = Field(default_factory=list)  # Terms to exclude from search results


class CodeContext(BaseModel):
    """Context information for current coding session"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    current_file: str
    file_content: Optional[str] = None
    imports: List[str] = Field(default_factory=list)
    functions: List[str] = Field(default_factory=list)
    classes: List[str] = Field(default_factory=list)
    recent_changes: List[Dict[str, Any]] = Field(default_factory=list)
    git_branch: Optional[str] = None
    language: str
    framework: Optional[str] = None
    project_root: Optional[str] = None
    open_files: List[str] = Field(default_factory=list)
    session_id: Optional[str] = None


class EnhancedContext(CodeContext):
    """Multi-level hierarchical context"""
    module_context: Optional[Dict[str, Any]] = None
    project_context: Optional[Dict[str, Any]] = None
    cross_project_patterns: List[str] = Field(default_factory=list)
    dependency_graph: Dict[str, List[str]] = Field(default_factory=dict)
    architectural_patterns: List[str] = Field(default_factory=list)
    context_weights: Dict[ContextLevel, float] = Field(default_factory=dict)


class SearchResult(BaseModel):
    """Enhanced search result with metadata"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    score: float
    file_path: str
    repository: Optional[str] = None
    function_name: Optional[str] = None
    class_name: Optional[str] = None
    code_snippet: str
    language: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None

    # Relevance information
    relevance_explanation: Optional[str] = None
    ranking_explanation: Optional[str] = None
    context_similarity: Optional[float] = None
    import_overlap: Optional[float] = None
    pattern_match: Optional[float] = None

    # Code structure information
    signature: Optional[str] = None
    semantic_context: Optional[str] = None
    imports: List[str] = Field(default_factory=list)

    # Additional metadata
    last_modified: Optional[datetime] = None
    complexity_score: Optional[float] = None
    test_coverage: Optional[float] = None
    dependencies: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    result_position: Optional[int] = None

    # Highlighting
    highlights: Dict[str, List[str]] = Field(default_factory=dict)

    # Semantic search results
    caption: Optional[str] = None
    answer: Optional[str] = None

    # MCP tracking
    query_id: Optional[str] = None
    citations: List[Dict[str, Any]] = Field(default_factory=list)


class RankingMetrics(BaseModel):
    """Metrics for ranking performance"""
    total_results: int
    filtered_count: int
    context_boost_applied: int
    average_score: float
    score_distribution: Dict[str, int]
    ranking_factors: Dict[str, float]
    processing_time_ms: float


class UserPreferences(BaseModel):
    """Learned user preferences"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    user_id: str
    preferred_languages: List[str] = Field(default_factory=list)
    preferred_frameworks: List[str] = Field(default_factory=list)
    coding_style: Dict[str, Any] = Field(default_factory=dict)
    common_patterns: List[str] = Field(default_factory=list)
    search_history: List[Dict[str, Any]] = Field(default_factory=list)
    success_patterns: List[Dict[str, Any]] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GeneratedCode(BaseModel):
    """Generated code with metadata"""
    code: str
    language: str
    imports: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    style_matched: bool = True
    confidence_score: float
    explanation: Optional[str] = None
    test_code: Optional[str] = None
    documentation: Optional[str] = None


class FeedbackRecord(BaseModel):
    """User feedback record for learning"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    query: SearchQuery
    results_shown: List[SearchResult]
    results_selected: List[str]  # IDs of selected results
    context: CodeContext
    outcome: str  # success/failure/partial
    time_to_selection_ms: Optional[float] = None
    user_satisfaction: Optional[int] = None  # 1-5 scale
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class IndexingRequest(BaseModel):
    """Request to index new or updated files"""
    file_paths: List[str]
    repository: str
    branch: Optional[str] = None
    force_reindex: bool = False
    include_dependencies: bool = True
    extract_patterns: bool = True


class GeneratedResponse(BaseModel):
    """Response generated by the generation module"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    text: str
    sources: List[SearchResult]
    intent: SearchIntent
    confidence: float
    metadata: Dict[str, Any]


class QueryContext(BaseModel):
    """Context for a search query."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    current_file: Optional[str] = None
    workspace_root: Optional[str] = None
    session_id: Optional[str] = None
    user_preferences: Dict[str, Any] = Field(default_factory=dict)


class FileContext(BaseModel):
    """Context information for a specific file"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    file_path: str
    language: str
    imports: List[str] = Field(default_factory=list)
    functions: List[Dict[str, Any]] = Field(default_factory=list)
    classes: List[Dict[str, Any]] = Field(default_factory=list)
    variables: List[str] = Field(default_factory=list)
    file_type: Optional[str] = None  # 'source', 'test', 'config', etc.
    complexity_score: Optional[float] = None
    last_modified: Optional[datetime] = None
    size_bytes: Optional[int] = None
    encoding: str = "utf-8"


class ModuleContext(BaseModel):
    """Context information for a module/package"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    module_name: str
    module_path: str
    files: List[str] = Field(default_factory=list)
    submodules: List[str] = Field(default_factory=list)
    exported_symbols: List[str] = Field(default_factory=list)
    module_type: Optional[str] = None  # 'package', 'module', 'namespace'
    init_file: Optional[str] = None
    total_lines: Optional[int] = None
    dependencies: List[str] = Field(default_factory=list)


class ProjectContext(BaseModel):
    """Context information for an entire project"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    root_path: str
    project_type: Optional[str] = None  # 'python', 'javascript', 'mixed'
    main_language: Optional[str] = None
    frameworks: List[str] = Field(default_factory=list)
    dependencies: Dict[str, str] = Field(default_factory=dict)  # package: version
    modules: List[str] = Field(default_factory=list)
    config_files: List[str] = Field(default_factory=list)
    test_framework: Optional[str] = None
    build_system: Optional[str] = None
    vcs_type: Optional[str] = None  # 'git', 'svn', etc.
    total_files: Optional[int] = None
    total_lines: Optional[int] = None

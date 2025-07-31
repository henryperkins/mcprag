"""
Enhanced Index Builder for Azure AI Search
Implements advanced index features based on createindex.md documentation
"""

import logging
from datetime import timedelta
from typing import Dict, List, Any, Optional


from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    HnswParameters,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch,
    ScoringProfile,
    TextWeights,
    FreshnessScoringFunction,
    FreshnessScoringParameters,
    MagnitudeScoringFunction,
    MagnitudeScoringParameters,
    TagScoringFunction,
    TagScoringParameters,
    ScoringFunctionAggregation,
    SearchSuggester,
    CorsOptions,
    CustomAnalyzer,
    LexicalTokenizerName,
    TokenFilterName
)
from azure.core.credentials import AzureKeyCredential

from enhanced_rag.core.config import get_config
from enhanced_rag.core.models import SearchIntent

logger = logging.getLogger(__name__)


class EnhancedIndexBuilder:
    """
    Builds optimized search indexes with all advanced features
    Based on Azure AI Search best practices from createindex.md
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or get_config().azure.model_dump()
        self.index_client = self._create_index_client()
        
    def _create_index_client(self) -> SearchIndexClient:
        """Create Azure Search index client"""
        endpoint = self.config['endpoint']
        api_key = self.config['admin_key']
        
        return SearchIndexClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(api_key)
        )
    
    async def create_enhanced_rag_index(
        self,
        index_name: str,
        description: str,
        enable_vectors: bool = True,
        enable_semantic: bool = True,
        custom_analyzers: Optional[List[CustomAnalyzer]] = None
    ) -> SearchIndex:
        """
        Create an enhanced index optimized for RAG scenarios
        
        Args:
            index_name: Name of the index
            description: Human-readable description
            enable_vectors: Enable vector search capabilities
            enable_semantic: Enable semantic ranking
            custom_analyzers: Optional custom analyzers
            
        Returns:
            Created search index
        """
        # Build comprehensive field collection
        fields = self._build_enhanced_fields()
        
        # Add vector search configuration
        vector_search = (
            self._build_vector_search_config()
            if enable_vectors else None
        )
        
        # Add semantic configuration
        semantic_search = (
            self._build_semantic_config()
            if enable_semantic else None
        )
        
        # Build scoring profiles
        scoring_profiles = self._build_scoring_profiles()
        
        # Build suggesters
        suggesters = self._build_suggesters()
        
        # Build analyzers
        analyzers = self._build_code_analyzers()
        if custom_analyzers:
            analyzers.extend(custom_analyzers)
        
        # Configure CORS for browser-based access
        cors_options = CorsOptions(
            allowed_origins=["*"],  # Configure appropriately for production
            max_age_in_seconds=300
        )
        
        # Create the index
        index = SearchIndex(
            name=index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search,
            scoring_profiles=scoring_profiles,
            default_scoring_profile="code_quality_boost",
            suggesters=suggesters,
            analyzers=analyzers,
            cors_options=cors_options,
            e_tag=None
        )
        
        # SDK lacks a typed 'description' field on SearchIndex; skipping.
        
        try:
            result = self.index_client.create_or_update_index(index)
            logger.info(f"Created enhanced index '{index_name}'")
            return result
        except Exception as e:
            logger.error(f"Error creating index '{index_name}': {e}")
            raise
    
    def _build_enhanced_fields(self) -> List[SearchField]:
        """Build comprehensive field collection for enhanced RAG"""
        fields = []
        
        # Document key (required)
        fields.append(
            SimpleField(
                name="id",
                type=SearchFieldDataType.String,
                key=True,
                filterable=True,
                retrievable=True
            )
        )
        
        # Core content fields
        fields.extend([
            SearchableField(
                name="content",
                type=SearchFieldDataType.String,
                searchable=True,
                retrievable=True,
                analyzer_name="en.microsoft"
            ),
            SearchableField(
                name="title",
                type=SearchFieldDataType.String,
                searchable=True,
                retrievable=True,
                filterable=True,
                sortable=True,
                facetable=True,
                analyzer_name="en.microsoft"
            ),
            SearchableField(
                name="description",
                type=SearchFieldDataType.String,
                searchable=True,
                retrievable=True,
                analyzer_name="en.microsoft"
            ),
            # Code-specific fields
            SearchableField(
                name="code_content",
                type=SearchFieldDataType.String,
                searchable=True,
                retrievable=True,
                analyzer_name="code_content_analyzer"
            ),
            SimpleField(
                name="file_path",
                type=SearchFieldDataType.String,
                filterable=True,
                sortable=True,
                facetable=True,
                retrievable=True
            ),
            SimpleField(
                name="file_extension",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
                retrievable=True
            ),
            SimpleField(
                name="language",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
                retrievable=True
            ),
            # Metadata fields
            SimpleField(
                name="last_modified",
                type=SearchFieldDataType.DateTimeOffset,
                filterable=True,
                sortable=True,
                retrievable=True
            ),
            SimpleField(
                name="size_bytes",
                type=SearchFieldDataType.Int64,
                filterable=True,
                sortable=True,
                retrievable=True
            ),
            SimpleField(
                name="quality_score",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True,
                retrievable=True
            )
        ])
        
        fields.append(
            SimpleField(
                name="chunk_id",
                type=SearchFieldDataType.String,
                filterable=True,
                retrievable=True
            )
        )
        
        fields.append(
            SearchableField(
                name="semantic_context",
                type=SearchFieldDataType.String,
                searchable=True,
                retrievable=True
            )
        )
        
        fields.append(
            SimpleField(
                name="chunk_type",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
                retrievable=True
            )
        )
        
        # Code-specific searchable fields
        fields.append(
            SearchableField(
                name="function_name",
                type=SearchFieldDataType.String,
                searchable=True,
                retrievable=True,
                filterable=True,
                facetable=True
            )
        )
        
        fields.append(
            SearchableField(
                name="class_name",
                type=SearchFieldDataType.String,
                searchable=True,
                retrievable=True,
                filterable=True,
                facetable=True
            )
        )
        
        # Import/dependency tracking
        fields.append(
            SearchField(
                name="imports",
                type=SearchFieldDataType.Collection(
                    SearchFieldDataType.String
                ),
                searchable=True,
                retrievable=True
                # Note: Custom analyzers not supported on Collection fields
            )
        )
        
        fields.append(
            SimpleField(
                name="dependencies",
                type=SearchFieldDataType.Collection(
                    SearchFieldDataType.String
                ),
                retrievable=True
            )
        )
        
        # Documentation fields
        fields.append(
            SearchableField(
                name="docstring",
                type=SearchFieldDataType.String,
                searchable=True,
                retrievable=True,
                analyzer_name="en.microsoft"
            )
        )
        
        fields.append(
            SimpleField(
                name="signature",
                type=SearchFieldDataType.String,
                retrievable=True
            )
        )
        
        fields.append(
            SearchableField(
                name="comments",
                type=SearchFieldDataType.String,
                searchable=True,
                retrievable=True,
                analyzer_name="en.microsoft"
            )
        )
        
        # Metadata fields (filterable/facetable)
        fields.append(
            SimpleField(
                name="file_path",
                type=SearchFieldDataType.String,
                filterable=True,
                sortable=True,
                facetable=True,
                retrievable=True
            )
        )
        
        fields.append(
            SimpleField(
                name="file_name",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
                retrievable=True
            )
        )
        
        fields.append(
            SimpleField(
                name="language",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
                retrievable=True
            )
        )
        
        fields.append(
            SimpleField(
                name="framework",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
                retrievable=True
            )
        )
        
        fields.append(
            SimpleField(
                name="repository",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
                retrievable=True
            )
        )
        
        # Scoring-related fields
        fields.append(
            SimpleField(
                name="last_modified",
                type=SearchFieldDataType.DateTimeOffset,
                filterable=True,
                sortable=True,
                retrievable=True
            )
        )
        
        fields.append(
            SimpleField(
                name="complexity_score",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True,
                retrievable=True
            )
        )
        
        fields.append(
            SimpleField(
                name="quality_score",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True,
                retrievable=True
            )
        )
        
        fields.append(
            SimpleField(
                name="test_coverage",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True,
                retrievable=True
            )
        )
        
        fields.append(
            SimpleField(
                name="reference_count",
                type=SearchFieldDataType.Int32,
                filterable=True,
                sortable=True,
                retrievable=True
            )
        )
        
        # Tag collection for boost scoring
        fields.append(
            SimpleField(
                name="tags",
                type=SearchFieldDataType.Collection(
                    SearchFieldDataType.String
                ),
                filterable=True,
                facetable=True,
                retrievable=True
            )
        )
        
        # Vector field for semantic similarity
        fields.append(
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(
                    SearchFieldDataType.Single
                ),
                searchable=True,
                retrievable=True,  # Set based on needs
                vector_search_dimensions=self.config.get(
                    'vector_dimensions', 1536
                ),
                vector_search_profile_name="vector-profile-hnsw"
            )
        )
        
        # Line number tracking
        fields.append(
            SimpleField(
                name="start_line",
                type=SearchFieldDataType.Int32,
                filterable=True,
                retrievable=True
            )
        )
        
        fields.append(
            SimpleField(
                name="end_line",
                type=SearchFieldDataType.Int32,
                filterable=True,
                retrievable=True
            )
        )
        
        # Git metadata
        fields.append(
            SimpleField(
                name="git_branch",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
                retrievable=True
            )
        )
        
        fields.append(
            SimpleField(
                name="git_commit",
                type=SearchFieldDataType.String,
                filterable=True,
                retrievable=True
            )
        )
        fields.append(
            SimpleField(
                name="git_commit_count",
                type=SearchFieldDataType.Int32,
                filterable=True,
                sortable=True,
                retrievable=True
            )
        )
        fields.append(
            SimpleField(
                name="git_last_modified",
                type=SearchFieldDataType.DateTimeOffset,
                filterable=True,
                sortable=True,
                retrievable=True
            )
        )
        
        fields.append(
            SimpleField(
                name="git_authors",
                type=SearchFieldDataType.Collection(
                    SearchFieldDataType.String
                ),
                filterable=True,
                facetable=True,
                retrievable=True
            )
        )
        
        # Patterns and intent optimization
        fields.append(
            SimpleField(
                name="detected_patterns",
                type=SearchFieldDataType.Collection(
                    SearchFieldDataType.String
                ),
                filterable=True,
                facetable=True,
                retrievable=True
            )
        )
        
        fields.append(
            SimpleField(
                name="intent_keywords",
                type=SearchFieldDataType.Collection(
                    SearchFieldDataType.String
                ),
                searchable=True,
                retrievable=True
            )
        )
        
        return fields
    
    def _build_vector_search_config(self) -> VectorSearch:
        """Build vector search configuration"""
        profile = VectorSearchProfile(
            name="vector-profile-hnsw",
            algorithm_configuration_name="hnsw-config"
        )

        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="hnsw-config",
                    parameters=HnswParameters(
                        m=4,
                        ef_construction=400,
                        ef_search=500,
                        metric="cosine"
                    )
                )
            ],
            profiles=[profile]
        )

        # Custom Web API vectorizer via additional properties isn't supported.
        # Consider query-time vectorization or skillset-based enrichment.
        # embedding enrichment instead.

        return vector_search
    
    def _build_semantic_config(self) -> SemanticSearch:
        """Build semantic search configuration"""
        return SemanticSearch(
            configurations=[
                SemanticConfiguration(
                    name="semantic-config",
                    prioritized_fields=SemanticPrioritizedFields(
                        title_field=SemanticField(field_name="function_name"),
                        content_fields=[
                            SemanticField(field_name="content"),
                            SemanticField(field_name="docstring")
                        ],
                        keywords_fields=[
                            SemanticField(field_name="tags"),
                            SemanticField(field_name="language"),
                            SemanticField(field_name="framework")
                        ]
                    )
                )
            ]
        )
    
    def _build_scoring_profiles(self) -> List[ScoringProfile]:
        """Build scoring profiles for different scenarios"""
        return [
            # Boost high-quality, well-tested code
            ScoringProfile(
                name="code_quality_boost",
                text_weights=TextWeights(
                    weights={
                        "function_name": 3.0,
                        "class_name": 2.5,
                        "content": 2.0,
                        "docstring": 1.5,
                        "comments": 1.0
                    }
                ),
                functions=[
                    MagnitudeScoringFunction(
                        field_name="quality_score",
                        boost=2.0,
                        parameters=MagnitudeScoringParameters(
                            boosting_range_start=0.7,
                            boosting_range_end=1.0
                        ),
                        interpolation="linear"
                    ),
                    MagnitudeScoringFunction(
                        field_name="test_coverage",
                        boost=1.5,
                        parameters=MagnitudeScoringParameters(
                            boosting_range_start=0.8,
                            boosting_range_end=1.0
                        ),
                        interpolation="linear"
                    )
                ],
                function_aggregation=ScoringFunctionAggregation.SUM
            ),
            
            # Boost recent code
            ScoringProfile(
                name="freshness_boost",
                text_weights=TextWeights(
                    weights={
                        "content": 2.0,
                        "function_name": 2.0
                    }
                ),
                functions=[
                    FreshnessScoringFunction(
                        field_name="last_modified",
                        boost=2.5,
                        parameters=FreshnessScoringParameters(
                            boosting_duration=timedelta(days=30)
                        ),
                        interpolation="linear"
                    )
                ]
            ),
            
            # Boost popular/referenced code
            ScoringProfile(
                name="popularity_boost",
                functions=[
                    MagnitudeScoringFunction(
                        field_name="reference_count",
                        boost=2.0,
                        parameters=MagnitudeScoringParameters(
                            boosting_range_start=5,
                            boosting_range_end=100,
                            should_boost_beyond_range_by_constant=True
                        ),
                        interpolation="logarithmic"
                    )
                ]
            ),
            
            # Tag-based boosting
            ScoringProfile(
                name="tag_boost",
                functions=[
                    TagScoringFunction(
                        field_name="tags",
                        boost=3.0,
                        parameters=TagScoringParameters(
                            tags_parameter="boosttags"
                        ),
                        interpolation="linear"
                    )
                ]
            )
        ]
    
    def _build_suggesters(self) -> List[SearchSuggester]:
        """Build suggesters for autocomplete"""
        return [
            SearchSuggester(
                name="code_suggester",
                source_fields=["function_name", "class_name", "file_name"]
            )
        ]
    
    def _build_code_analyzers(self) -> List[CustomAnalyzer]:
        """Build custom analyzers for code"""
        return [
            # Analyzer for code content (preserves some structure)
            CustomAnalyzer(
                name="code_content_analyzer",
                tokenizer_name=LexicalTokenizerName.WHITESPACE,
                token_filters=[
                    TokenFilterName.LOWERCASE,
                    TokenFilterName.STOPWORDS
                ]
            ),
            
            # Analyzer for code identifiers (camelCase, snake_case)
            CustomAnalyzer(
                name="code_identifier_analyzer",
                tokenizer_name=LexicalTokenizerName.PATTERN,
                token_filters=[
                    TokenFilterName.LOWERCASE
                ]
            ),
            
            # Analyzer for import paths
            CustomAnalyzer(
                name="import_path_analyzer",
                tokenizer_name=LexicalTokenizerName.PATH_HIERARCHY,
                token_filters=[TokenFilterName.LOWERCASE]
            )
        ]
    
    async def create_intent_optimized_indexes(
        self,
        base_name: str,
        description_template: str
    ) -> Dict[SearchIntent, str]:
        """
        Create separate indexes optimized for different intents
        
        Args:
            base_name: Base name for indexes
            description_template: Template for descriptions
            
        Returns:
            Mapping of intent to index name
        """
        intent_indexes = {}
        
        # Define intent-specific optimizations
        intent_configs = {
            SearchIntent.IMPLEMENT: {
                'suffix': 'implement',
                'description': (
                    f"{description_template} - Optimized for finding "
                    "implementation examples"
                ),
                'boost_profile': 'code_quality_boost',
                'emphasis_fields': ['function_name', 'content', 'imports']
            },
            SearchIntent.DEBUG: {
                'suffix': 'debug',
                'description': (
                    f"{description_template} - Optimized for debugging and "
                    "error resolution"
                ),
                'boost_profile': 'freshness_boost',
                'emphasis_fields': ['comments', 'docstring', 'tags']
            },
            SearchIntent.UNDERSTAND: {
                'suffix': 'understand',
                'description': (
                    f"{description_template} - Optimized for code "
                    "comprehension"
                ),
                'boost_profile': 'popularity_boost',
                'emphasis_fields': ['docstring', 'comments', 'class_name']
            },
            SearchIntent.REFACTOR: {
                'suffix': 'refactor',
                'description': (
                    f"{description_template} - Optimized for refactoring "
                    "patterns"
                ),
                'boost_profile': 'code_quality_boost',
                'emphasis_fields': [
                    'detected_patterns',
                    'quality_score',
                    'complexity_score'
                ]
            }
        }
        
        for intent, config in intent_configs.items():
            index_name = f"{base_name}-{config['suffix']}"
            
            # Create intent-specific index
            await self.create_enhanced_rag_index(
                index_name=index_name,
                description=str(config['description']),
                enable_vectors=True,
                enable_semantic=True
            )
            
            intent_indexes[intent] = index_name
            
        return intent_indexes
    
    async def update_index_analyzers(
        self,
        index_name: str,
        new_analyzers: List[CustomAnalyzer]
    ) -> bool:
        """
        Update analyzers on existing index
        Note: Only searchAnalyzer can be updated on existing fields
        
        Returns:
            True if successful
        """
        try:
            # Get existing index
            index = self.index_client.get_index(index_name)
            
            # Add new analyzers
            if not index.analyzers:
                index.analyzers = []
            index.analyzers.extend(new_analyzers)
            
            # Update the index
            self.index_client.create_or_update_index(index)
            
            logger.info(f"Updated analyzers for index '{index_name}'")
            return True
            
        except Exception as e:
            logger.error(
                f"Error updating analyzers for index '{index_name}': {e}"
            )
            return False
    
    async def validate_index_schema(
        self,
        index_name: str,
        expected_fields: List[str]
    ) -> Dict[str, Any]:
        """
        Validate that index has expected schema
        
        Returns:
            Validation results
        """
        try:
            index = self.index_client.get_index(index_name)
            
            existing_fields = {field.name for field in index.fields}
            expected_set = set(expected_fields)
            
            return {
                'valid': expected_set.issubset(existing_fields),
                'missing_fields': list(expected_set - existing_fields),
                'extra_fields': list(existing_fields - expected_set),
                'total_fields': len(index.fields),
                'has_vector_search': index.vector_search is not None,
                'has_semantic_search': index.semantic_search is not None,
                'scoring_profiles': [
                    p.name for p in (index.scoring_profiles or [])
                ]
            }
            
        except Exception as e:
            logger.error(f"Error validating index '{index_name}': {e}")
            return {'error': str(e)}
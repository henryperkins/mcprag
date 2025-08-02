#!/usr/bin/env python3
"""
Enhanced Azure Cognitive Search implementation with advanced features
Demonstrates how to better utilize Azure Search capabilities for code search
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import timedelta
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
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
    SynonymMap,
    CustomAnalyzer,
    InputFieldMappingEntry,
    OutputFieldMappingEntry,
    SearchIndexerSkillset,
    KeyPhraseExtractionSkill,
    SentimentSkill,
    WebApiSkill,
    CorsOptions
)
from azure.core.credentials import AzureKeyCredential


class EnhancedAzureSearch:
    """Enhanced Azure Cognitive Search with advanced features"""

    def __init__(self, endpoint: str, api_key: str):
        self.endpoint = endpoint
        self.credential = AzureKeyCredential(api_key)
        self.index_client = SearchIndexClient(endpoint, self.credential)
        self.index_name = "codebase-enhanced"

    def create_enhanced_index(self):
        """Create an enhanced index with all advanced features"""
        # Already implemented below by building analyzers, synonym maps, fields,
        # scoring profiles, suggesters, vector and semantic configurations, and
        # issuing create_or_update_index.

        # Define custom analyzers for code
        code_analyzers = [
            # CamelCase analyzer for Java/C# style code
            CustomAnalyzer(
                name="code_camelcase_analyzer",
                tokenizer_name="pattern",
                token_filters=["lowercase", "code_synonym_filter"]
            ),

            # Snake_case analyzer for Python style
            CustomAnalyzer(
                name="code_snakecase_analyzer",
                tokenizer_name="pattern",
                token_filters=["lowercase", "code_synonym_filter"]
            ),

            # Import path analyzer
            CustomAnalyzer(
                name="import_path_analyzer",
                tokenizer_name="path_hierarchy",
                token_filters=["lowercase"]
            )
        ]

        # Synonym maps for programming terms
        synonym_maps = [
            SynonymMap(
                name="code_synonyms",
                synonyms="""
                auth,authentication,authorize,authorization
                db,database,storage
                api,endpoint,route,service
                func,function,method,procedure
                var,variable,param,parameter
                err,error,exception,fault
                config,configuration,settings,options
                init,initialize,setup,bootstrap
                """
            )
        ]

        # Enhanced fields with better analyzers
        fields = [
            # Basic fields
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SimpleField(
                name="chunk_id",
                type=SearchFieldDataType.String,
                filterable=True
            ),

            # Searchable fields with custom analyzers
            SearchableField(
                name="code_content",
                type=SearchFieldDataType.String,
                searchable=True,
                analyzer_name="code_camelcase_analyzer",
                search_analyzer_name="code_camelcase_analyzer"
            ),
            SearchableField(
                name="function_name",
                type=SearchFieldDataType.String,
                searchable=True,
                facetable=True,
                analyzer_name="code_camelcase_analyzer"
            ),
            SearchableField(
                name="class_name",
                type=SearchFieldDataType.String,
                searchable=True,
                facetable=True,
                analyzer_name="code_camelcase_analyzer"
            ),
            SearchableField(
                name="imports",
                type=SearchFieldDataType.String,
                searchable=True,
                analyzer_name="import_path_analyzer"
            ),
            SearchableField(
                name="comments",
                type=SearchFieldDataType.String,
                searchable=True,
                analyzer_name="en.microsoft"
            ),
            SearchableField(
                name="docstring",
                type=SearchFieldDataType.String,
                searchable=True,
                analyzer_name="en.microsoft"
            ),

            # Facetable fields
            SimpleField(
                name="language",
                type=SearchFieldDataType.String,
                facetable=True,
                filterable=True
            ),
            SimpleField(
                name="repository",
                type=SearchFieldDataType.String,
                facetable=True,
                filterable=True
            ),
            SimpleField(
                name="file_path",
                type=SearchFieldDataType.String,
                facetable=True,
                filterable=True
            ),
            SimpleField(
                name="chunk_type",
                type=SearchFieldDataType.String,
                facetable=True,
                filterable=True
            ),

            # Scoring fields
            SimpleField(
                name="last_modified",
                type=SearchFieldDataType.DateTimeOffset,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="complexity_score",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="import_count",
                type=SearchFieldDataType.Int32,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="reference_count",
                type=SearchFieldDataType.Int32,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="lines_of_code",
                type=SearchFieldDataType.Int32,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="test_coverage",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True
            ),

            # Collection fields
            SimpleField(
                name="tags",
                type=SearchFieldDataType.Collection(
                    SearchFieldDataType.String
                ),
                facetable=True,
                filterable=True
            ),
            SimpleField(
                name="called_functions",
                type=SearchFieldDataType.Collection(
                    SearchFieldDataType.String
                ),
                searchable=True
            ),

            # Vector field for semantic search
            SearchField(
                name="code_vector",
                type=SearchFieldDataType.Collection(
                    SearchFieldDataType.Single
                ),
                searchable=True,
                vector_search_dimensions=3072,
                vector_search_profile_name="code-vector-profile"
            ),

            # Geo field for developer locations (optional)
            SimpleField(
                name="developer_location",
                type=SearchFieldDataType.GeographyPoint,
                filterable=True,
                sortable=True
            )
        ]

        # Scoring profiles for relevance tuning
        scoring_profiles = [
            # Boost recent code
            ScoringProfile(
                name="code_freshness",
                text_weights=TextWeights(
                    weights={
                        "function_name": 3.0,
                        "code_content": 2.0,
                        "comments": 1.5,
                        "docstring": 1.5
                    }
                ),
                functions=[
                    FreshnessScoringFunction(
                        field_name="last_modified",
                        boost=2.0,
                        parameters=FreshnessScoringParameters(
                            boosting_duration=timedelta(days=30)
                        ),
                        interpolation="linear"
                    )
                ]
            ),

            # Boost popular/well-tested code
            ScoringProfile(
                name="code_quality",
                text_weights=TextWeights(
                    weights={
                        "function_name": 2.5,
                        "docstring": 2.0,
                        "code_content": 1.5
                    }
                ),
                functions=[
                    MagnitudeScoringFunction(
                        field_name="reference_count",
                        boost=2.0,
                        parameters=MagnitudeScoringParameters(
                            boosting_range_start=0,
                            boosting_range_end=100,
                            should_boost_beyond_range_by_constant=True
                        ),
                        interpolation="logarithmic"
                    ),
                    MagnitudeScoringFunction(
                        field_name="test_coverage",
                        boost=1.5,
                        parameters=MagnitudeScoringParameters(
                            boosting_range_start=0.0,
                            boosting_range_end=1.0
                        ),
                        interpolation="linear"
                    )
                ],
                function_aggregation=ScoringFunctionAggregation.SUM
            ),

            # Boost by tags (e.g., "security", "performance")
            ScoringProfile(
                name="tag_boost",
                functions=[
                    TagScoringFunction(
                        field_name="tags",
                        boost=2.5,
                        parameters=TagScoringParameters(
                            tags_parameter="boost_tags"
                        ),
                        interpolation="linear"
                    )
                ]
            )
        ]

        # Suggesters for autocomplete
        suggesters = [
            SearchSuggester(
                name="function_suggester",
                source_fields=["function_name", "class_name"]
            ),
            SearchSuggester(
                name="import_suggester",
                source_fields=["imports"]
            )
        ]

        # Vector search configuration
        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="code-hnsw",
                    parameters=HnswParameters(
                        m=4,
                        ef_construction=400,
                        ef_search=500,
                        metric="cosine"
                    )
                )
            ],
            profiles=[
                VectorSearchProfile(
                    name="code-vector-profile",
                    algorithm_configuration_name="code-hnsw"
                )
            ]
        )

        # Semantic search configuration
        semantic_config = SemanticConfiguration(
            name="code-semantic-config",
            prioritized_fields=SemanticPrioritizedFields(
                title_field=SemanticField(field_name="function_name"),
                content_fields=[
                    SemanticField(field_name="code_content"),
                    SemanticField(field_name="docstring")
                ],
                keywords_fields=[
                    SemanticField(field_name="tags"),
                    SemanticField(field_name="language")
                ]
            )
        )

        # Create the enhanced index
        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            scoring_profiles=scoring_profiles,
            default_scoring_profile="code_quality",
            suggesters=suggesters,
            analyzers=code_analyzers,
            synonym_maps=synonym_maps,
            vector_search=vector_search,
            semantic_search=SemanticSearch(
                configurations=[semantic_config],
                default_configuration_name="code-semantic-config"
            ),
            cors_options=CorsOptions(
                allowed_origins=["*"],
                max_age_in_seconds=300
            )
        )

        # Create or update the index
        self.index_client.create_or_update_index(index)
        print(f"Enhanced index '{self.index_name}' created successfully")

    def search_with_advanced_features(
        self,
        query: str,
        filters: Optional[str] = None,
        facets: Optional[List[str]] = None,
        scoring_profile: Optional[str] = None,
        boost_tags: Optional[List[str]] = None,
        include_highlights: bool = True,
        include_suggestions: bool = True,
        fuzzy_search: bool = True,
        semantic_search: bool = True
    ) -> Dict[str, Any]:
        """Perform search with all advanced features"""

        def _sanitize(d: Dict[str, Any]) -> Dict[str, Any]:
            """Compatibility shim for legacy params and unknown keys"""
            if not d:
                return {}
            out: Dict[str, Any] = {}
            for k, v in d.items():
                if k == "count":
                    out["include_total_count"] = bool(v)
                elif k in {
                    "search_text",
                    "query_type",
                    "semantic_configuration_name",
                    "query_caption",
                    "query_answer",
                    "filter",
                    "top",
                    "include_total_count",
                    "disable_randomization",
                    "timeout",
                    "vector_queries",
                    "facets",
                    "highlight_fields",
                    "highlight_pre_tag",
                    "highlight_post_tag",
                    "scoring_profile",
                    "scoring_parameters",
                    "search_fields",
                }:
                    if v is not None:
                        out[k] = v
            return out

        search_client = SearchClient(
            self.endpoint,
            self.index_name,
            self.credential
        )

        # Build the search query
        search_text = query

        # Add fuzzy search for typo tolerance
        if fuzzy_search:
            search_text = f"{query}~"

        # Prepare search parameters (use proper typed kwargs instead of dict of mixed types)
        search_kwargs: Dict[str, Any] = {
            "search_text": search_text,
            "include_total_count": True,
            "top": 20
        }

        # Add filters
        if filters:
            search_kwargs["filter"] = filters

        # Add facets for result analysis
        if facets:
            search_kwargs["facets"] = facets
        else:
            # Default facets
            search_kwargs["facets"] = [
                "language,count:10",
                "repository,count:10",
                "chunk_type,count:5",
                "tags,count:20"
            ]

        # Add scoring profile
        if scoring_profile:
            search_kwargs["scoring_profile"] = scoring_profile
            if boost_tags and scoring_profile == "tag_boost":
                search_kwargs["scoring_parameters"] = [
                    f"boost_tags-{','.join(boost_tags)}"
                ]

        # Add highlighting
        if include_highlights:
            search_kwargs["highlight_fields"] = "code_content,function_name,docstring"
            search_kwargs["highlight_pre_tag"] = "<mark>"
            search_kwargs["highlight_post_tag"] = "</mark>"

        # Add semantic search
        if semantic_search:
            search_kwargs["query_type"] = "semantic"
            search_kwargs["semantic_configuration_name"] = "code-semantic-config"
            search_kwargs["query_caption"] = "extractive"
            search_kwargs["query_answer"] = "extractive"

        # Execute search
        results = search_client.search(**_sanitize(search_kwargs))

        # Process results
        output: Dict[str, Any] = {
            "query": query,
            "total_count": results.get_count(),
            "facets": results.get_facets() if facets else {},
            "results": [],   # type: ignore[assignment]
            "suggestions": []  # type: ignore[assignment]
        }

        # Add search results with highlights
        for result in results:
            item = {
                "id": result["id"],
                "score": result["@search.score"],
                "function_name": result.get("function_name"),
                "file_path": result.get("file_path"),
                "language": result.get("language"),
                "code_snippet": result.get("code_content", "")[:200] + "...",
                "highlights": result.get("@search.highlights", {})
            }

            # Add semantic search captions
            if semantic_search:
                item["caption"] = result.get("@search.caption", {})
                item["answer"] = result.get("@search.answer", {})

            output["results"].append(item)

        # Get suggestions for autocomplete
        if include_suggestions:
            suggest_items: List[Dict[str, Any]] = []
            suggest_results = search_client.suggest(
                search_text=query[:20],  # Limit suggestion text
                suggester_name="function_suggester",
                top=5
            )
            for s in suggest_results:
                text_val = s.get("function_name") or s.get("class_name") or ""
                type_val = "function" if s.get("function_name") else ("class" if s.get("class_name") else "unknown")
                suggest_items.append({"text": text_val, "type": type_val})
            output["suggestions"] = suggest_items

        return output

    def create_code_enrichment_skillset(self):
        """Create a cognitive skillset for code enrichment"""

        # Define skills for code analysis
        skills = [
            # Extract key phrases from comments and docstrings
            KeyPhraseExtractionSkill(
                description="Extract key phrases from code documentation",
                context="/document",
                inputs=[
                    InputFieldMappingEntry(name="text", source="/document/docstring"),
                    InputFieldMappingEntry(name="languageCode", source="/document/language")
                ],
                outputs=[
                    OutputFieldMappingEntry(name="keyPhrases", target_name="key_phrases")
                ]
            ),

            # Analyze sentiment of code comments (for detecting TODOs, FIXMEs, etc.)
            SentimentSkill(
                description="Analyze sentiment of code comments",
                context="/document",
                inputs=[
                    InputFieldMappingEntry(name="text", source="/document/comments"),
                    InputFieldMappingEntry(name="languageCode", source="/document/language")
                ],
                outputs=[
                    OutputFieldMappingEntry(name="sentiment", target_name="comment_sentiment")
                ]
            ),

            # Custom skill for code complexity analysis (webhook-based)
            WebApiSkill(
                description="Analyze code complexity",
                uri="https://your-function-app.azurewebsites.net/api/analyze-complexity",
                http_method="POST",
                context="/document",
                inputs=[
                    InputFieldMappingEntry(name="code", source="/document/code_content"),
                    InputFieldMappingEntry(name="language", source="/document/language")
                ],
                outputs=[
                    OutputFieldMappingEntry(name="complexity", target_name="complexity_metrics"),
                    OutputFieldMappingEntry(name="metrics", target_name="code_metrics")
                ]
            )
        ]

        # Create the skillset
        skillset = SearchIndexerSkillset(
            name="code-enrichment-skillset",
            description="Enriches code documents with AI insights",
            skills=skills  # type: ignore[arg-type]
        )

        return skillset

    def analyze_search_performance(self):
        """Analyze search performance and query patterns"""

        # This would integrate with Azure Monitor/Application Insights
        # to track:
        # - Query patterns
        # - Click-through rates
        # - Search latency
        # - Popular search terms
        # - Failed queries

        analysis = {
            "top_queries": [],
            "avg_latency": 0,
            "failed_query_rate": 0,
            "suggestions": []
        }

        return analysis


# Example usage
if __name__ == "__main__":
    # Initialize enhanced search
    endpoint = os.getenv("ACS_ENDPOINT")
    api_key = os.getenv("ACS_ADMIN_KEY")

    # Guard example usage to avoid None arguments at runtime
    if not endpoint or not api_key:
        raise RuntimeError("ACS_ENDPOINT and ACS_ADMIN_KEY must be set for example usage")
    enhanced_search = EnhancedAzureSearch(endpoint, api_key)

    # Create enhanced index
    enhanced_search.create_enhanced_index()

    # Example advanced search
    results = enhanced_search.search_with_advanced_features(
        query="authentication middleware",
        filters="language eq 'python' and repository eq 'main-app'",
        facets=["language", "tags"],
        scoring_profile="code_quality",
        boost_tags=["security", "auth"],
        include_highlights=True,
        fuzzy_search=True,
        semantic_search=True
    )

    print(json.dumps(results, indent=2))

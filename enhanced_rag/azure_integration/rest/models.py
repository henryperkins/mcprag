"""Minimal data models for Azure AI Search operations."""

from typing import Dict, Any, List, Optional, Union
from enum import Enum


class FieldType(str, Enum):
    """Azure Search field data types."""
    STRING = "Edm.String"
    INT32 = "Edm.Int32"
    INT64 = "Edm.Int64"
    DOUBLE = "Edm.Double"
    BOOLEAN = "Edm.Boolean"
    DATETIME = "Edm.DateTimeOffset"
    GEOGRAPHY_POINT = "Edm.GeographyPoint"
    COMPLEX = "Edm.ComplexType"
    COLLECTION_STRING = "Collection(Edm.String)"
    COLLECTION_INT32 = "Collection(Edm.Int32)"
    COLLECTION_INT64 = "Collection(Edm.Int64)"
    COLLECTION_DOUBLE = "Collection(Edm.Double)"
    COLLECTION_DATETIME = "Collection(Edm.DateTimeOffset)"
    COLLECTION_GEOGRAPHY_POINT = "Collection(Edm.GeographyPoint)"
    COLLECTION_SINGLE = "Collection(Edm.Single)"
    SINGLE = "Edm.Single"


def create_field(
    name: str,
    field_type: Union[str, FieldType],
    key: bool = False,
    searchable: bool = False,
    filterable: bool = False,
    sortable: bool = False,
    facetable: bool = False,
    retrievable: bool = True,
    analyzer: Optional[str] = None,
    search_analyzer: Optional[str] = None,
    index_analyzer: Optional[str] = None,
    synonym_maps: Optional[List[str]] = None,
    dimensions: Optional[int] = None,
    vector_search_profile: Optional[str] = None
) -> Dict[str, Any]:
    """Create a field definition.

    Args:
        name: Field name
        field_type: Field data type
        key: Whether this is the key field
        searchable: Whether the field is searchable
        filterable: Whether the field can be filtered
        sortable: Whether the field can be sorted
        facetable: Whether the field can be faceted
        retrievable: Whether the field is returned in results
        analyzer: Analyzer for the field
        search_analyzer: Search-time analyzer
        index_analyzer: Index-time analyzer
        synonym_maps: Synonym maps to apply
        dimensions: Vector dimensions (for vector fields)
        vector_search_profile: Vector search profile name

    Returns:
        Field definition dictionary
    """
    field = {
        "name": name,
        "type": field_type.value if isinstance(field_type, FieldType) else field_type,
        "key": key,
        "searchable": searchable,
        "filterable": filterable,
        "sortable": sortable,
        "facetable": facetable,
        "retrievable": retrievable
    }

    # Add optional properties
    if analyzer:
        field["analyzer"] = analyzer
    if search_analyzer:
        field["searchAnalyzer"] = search_analyzer
    if index_analyzer:
        field["indexAnalyzer"] = index_analyzer
    if synonym_maps:
        field["synonymMaps"] = synonym_maps

    # Vector field properties
    if dimensions:
        field["dimensions"] = dimensions
    if vector_search_profile:
        field["vectorSearchProfile"] = vector_search_profile

    return field


def create_vector_search_profile(
    name: str,
    algorithm: str = "hnsw",
    vectorizer: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a vector search profile aligned with REST API (2025-05-01-preview).

    Args:
        name: Profile name
        algorithm: Algorithm configuration name to reference (must match algorithms[].name)
        vectorizer: Optional vectorizer name to reference (must match vectorizers[].name)
        parameters: Unused placeholder for compatibility

    Returns:
        Vector search profile definition
    """
    profile = {
        "name": name,
        "algorithm": algorithm
    }
    if vectorizer:
        profile["vectorizer"] = vectorizer
    return profile


def create_hnsw_algorithm(
    name: str = "hnsw-config",
    m: int = 4,
    ef_construction: int = 400,
    ef_search: int = 500,
    metric: str = "cosine"
) -> Dict[str, Any]:
    """Create HNSW algorithm configuration.

    Args:
        name: Configuration name
        m: Number of bi-directional links
        ef_construction: Size of dynamic candidate list
        ef_search: Size of the neighbor list for search
        metric: Distance metric (cosine, euclidean, dotProduct)

    Returns:
        HNSW algorithm configuration
    """
    return {
        "name": name,
        "kind": "hnsw",
        "hnswParameters": {
            "m": m,
            "efConstruction": ef_construction,
            "efSearch": ef_search,
            "metric": metric
        }
    }


def create_semantic_configuration(
    name: str,
    title_field: str,
    content_fields: List[str],
    keyword_fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Create a semantic search configuration.

    Args:
        name: Configuration name
        title_field: Field to use as title
        content_fields: Fields to use as content
        keyword_fields: Optional keyword fields

    Returns:
        Semantic configuration definition
    """
    config = {
        "name": name,
        "prioritizedFields": {
            "titleField": {
                "fieldName": title_field
            },
            "prioritizedContentFields": [
                {"fieldName": field} for field in content_fields
            ]
        }
    }

    if keyword_fields:
        config["prioritizedFields"]["prioritizedKeywordsFields"] = [
            {"fieldName": field} for field in keyword_fields
        ]

    return config


def create_scoring_profile(
    name: str,
    text_weights: Optional[Dict[str, float]] = None,
    functions: Optional[List[Dict[str, Any]]] = None,
    function_aggregation: str = "sum"
) -> Dict[str, Any]:
    """Create a scoring profile.

    Args:
        name: Profile name
        text_weights: Field weights for text scoring
        functions: Scoring functions
        function_aggregation: How to aggregate function scores

    Returns:
        Scoring profile definition
    """
    profile = {
        "name": name,
        "functionAggregation": function_aggregation
    }

    if text_weights:
        profile["text"] = {"weights": text_weights}

    if functions:
        profile["functions"] = functions

    return profile


def create_indexer_schedule(
    interval: str = "PT1H",
    start_time: Optional[str] = None
) -> Dict[str, Any]:
    """Create an indexer schedule.

    Args:
        interval: ISO 8601 duration (e.g., PT1H for 1 hour)
        start_time: Optional start time (ISO 8601)

    Returns:
        Schedule definition
    """
    schedule = {"interval": interval}

    if start_time:
        schedule["startTime"] = start_time

    return schedule


def create_blob_datasource(
    name: str,
    connection_string: str,
    container_name: str,
    query: Optional[str] = None,
    delete_detection_policy: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create an Azure Blob Storage data source.

    Args:
        name: Data source name
        connection_string: Storage account connection string
        container_name: Container name
        query: Optional virtual folder path
        delete_detection_policy: Optional deletion detection policy

    Returns:
        Data source definition
    """
    datasource = {
        "name": name,
        "type": "azureblob",
        "credentials": {
            "connectionString": connection_string
        },
        "container": {
            "name": container_name
        }
    }

    if query:
        datasource["container"]["query"] = query

    if delete_detection_policy:
        datasource["dataDeletionDetectionPolicy"] = delete_detection_policy

    return datasource


def create_sql_datasource(
    name: str,
    connection_string: str,
    table_or_view: str,
    change_detection_policy: Optional[Dict[str, Any]] = None,
    delete_detection_policy: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create an Azure SQL data source.

    Args:
        name: Data source name
        connection_string: SQL connection string
        table_or_view: Table or view name
        change_detection_policy: Optional change detection policy
        delete_detection_policy: Optional deletion detection policy

    Returns:
        Data source definition
    """
    datasource = {
        "name": name,
        "type": "azuresql",
        "credentials": {
            "connectionString": connection_string
        },
        "container": {
            "name": table_or_view
        }
    }

    if change_detection_policy:
        datasource["dataChangeDetectionPolicy"] = change_detection_policy

    if delete_detection_policy:
        datasource["dataDeletionDetectionPolicy"] = delete_detection_policy

    return datasource


def create_text_split_skill(
    name: str,
    text_split_mode: str = "pages",
    maximum_page_length: int = 5000,
    page_overlap_length: int = 0,
    default_language_code: str = "en"
) -> Dict[str, Any]:
    """Create a text split cognitive skill.

    Args:
        name: Skill name
        text_split_mode: Split mode (pages or sentences)
        maximum_page_length: Maximum characters per page
        page_overlap_length: Overlap between pages
        default_language_code: Default language

    Returns:
        Skill definition
    """
    return {
        "@odata.type": "#Microsoft.Skills.Text.SplitSkill",
        "name": name,
        "description": "Split text into chunks",
        "context": "/document",
        "textSplitMode": text_split_mode,
        "maximumPageLength": maximum_page_length,
        "pageOverlapLength": page_overlap_length,
        "defaultLanguageCode": default_language_code,
        "inputs": [
            {
                "name": "text",
                "source": "/document/content"
            }
        ],
        "outputs": [
            {
                "name": "textItems",
                "targetName": "pages"
            }
        ]
    }


def create_language_detection_skill(name: str) -> Dict[str, Any]:
    """Create a language detection skill.

    Args:
        name: Skill name

    Returns:
        Skill definition
    """
    return {
        "@odata.type": "#Microsoft.Skills.Text.LanguageDetectionSkill",
        "name": name,
        "description": "Detect language",
        "context": "/document",
        "inputs": [
            {
                "name": "text",
                "source": "/document/content"
            }
        ],
        "outputs": [
            {
                "name": "languageCode",
                "targetName": "language"
            }
        ]
    }


def create_entity_recognition_skill(
    name: str,
    categories: Optional[List[str]] = None,
    default_language_code: str = "en"
) -> Dict[str, Any]:
    """Create an entity recognition skill.

    Args:
        name: Skill name
        categories: Entity categories to extract
        default_language_code: Default language

    Returns:
        Skill definition
    """
    skill = {
        "@odata.type": "#Microsoft.Skills.Text.EntityRecognitionSkill",
        "name": name,
        "description": "Extract entities",
        "context": "/document",
        "defaultLanguageCode": default_language_code,
        "inputs": [
            {
                "name": "text",
                "source": "/document/content"
            }
        ],
        "outputs": [
            {
                "name": "entities",
                "targetName": "entities"
            }
        ]
    }

    if categories:
        skill["categories"] = categories

    return skill

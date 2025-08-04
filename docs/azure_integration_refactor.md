## 1. Duplication Report

### A. Client Initialization Patterns

**Duplicated in:**
- `index_management.py` lines 49-55
- `index_operations.py` lines 38-42
- `indexer_integration.py` lines 82-86
- `enhanced_index_builder.py` lines 67-73
- `reindex_operations.py` lines 46-50

**Why it exists:** Each module independently creates Azure Search clients with similar credential patterns.

**Canonical implementation:** Create a single client factory module.

### B. Field Schema Definitions

**Duplicated in:**
- `enhanced_index_builder.py` lines 164-443 (_build_enhanced_fields method)
- `index_operations.py` lines 63-253 (create_codebase_index_schema method)

**Why it exists:** Historical evolution where different modules needed similar schemas.

**Canonical implementation:** Single schema definition module with field builders.

### C. Document Size Validation

**Duplicated in:**
- `indexer_integration.py` lines 1052-1062
- `remote_indexer.py` (similar pattern)
- `get_document_byte_size` function repeated

**Why it exists:** Multiple ingestion paths need the same 16MB payload limit check.

**Canonical implementation:** Document utilities module.

### D. Configuration Access

**Duplicated pattern:**
```python
config = get_config()
self.endpoint = config.azure.endpoint
self.admin_key = config.azure.admin_key
self.index_name = config.azure.index_name or "codebase-mcp-sota"
```

Appears in all 5 modules with slight variations.

**Why it exists:** No centralized configuration management.

**Canonical implementation:** Configuration provider with typed access.

### E. Error Handling Patterns

**Inconsistent approaches:**
- `@with_retry` decorator with bool returns (index_operations.py)
- Try/catch with logging and re-raise (enhanced_index_builder.py)
- Try/catch with dict error returns (index_management.py)

**Why it exists:** Different modules evolved independently.

**Canonical implementation:** Unified error handling strategy.

## 2. Refactoring Plan

### Architecture Overview

```
enhanced_rag/
├── azure_integration/
│   ├── core/
│   │   ├── client_factory.py      # Azure client management
│   │   ├── auth.py                # Authentication handling
│   │   ├── config.py              # Configuration provider
│   │   ├── errors.py              # Error types and handling
│   │   └── constants.py           # API versions, limits
│   ├── models/
│   │   ├── fields.py              # Field definitions
│   │   ├── schemas.py             # Index schemas
│   │   ├── requests.py            # Request models
│   │   └── responses.py           # Response models
│   ├── operations/
│   │   ├── base.py                # Base operation class
│   │   ├── index.py               # Index CRUD
│   │   ├── indexer.py             # Indexer operations
│   │   ├── datasource.py          # Data source operations
│   │   └── skillset.py            # Skillset operations
│   ├── workflows/
│   │   ├── reindex.py             # Reindexing workflows
│   │   ├── ingestion.py           # Document ingestion
│   │   └── maintenance.py         # Index maintenance
│   └── utils/
│       ├── documents.py           # Document utilities
│       ├── retry.py               # Retry logic
│       └── validation.py          # Input validation
```

### Core Components

#### client_factory.py
```python
from typing import Optional, Dict, Any
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient

class AzureSearchClientFactory:
    """Centralized client creation with connection pooling."""

    _clients: Dict[str, Any] = {}

    @classmethod
    def get_index_client(
        cls,
        endpoint: str,
        credential: AzureKeyCredential,
        **kwargs
    ) -> SearchIndexClient:
        key = f"index_{endpoint}"
        if key not in cls._clients:
            cls._clients[key] = SearchIndexClient(
                endpoint=endpoint,
                credential=credential,
                **kwargs
            )
        return cls._clients[key]

    @classmethod
    def get_search_client(
        cls,
        endpoint: str,
        index_name: str,
        credential: AzureKeyCredential,
        **kwargs
    ) -> SearchClient:
        key = f"search_{endpoint}_{index_name}"
        if key not in cls._clients:
            cls._clients[key] = SearchClient(
                endpoint=endpoint,
                index_name=index_name,
                credential=credential,
                **kwargs
            )
        return cls._clients[key]
```

#### schemas.py
```python
from dataclasses import dataclass
from typing import List, Optional
from azure.search.documents.indexes.models import SearchField

@dataclass
class CodebaseSchema:
    """Canonical codebase index schema."""

    VECTOR_DIMENSIONS = 3072

    @staticmethod
    def get_fields() -> List[SearchField]:
        """Return canonical field definitions."""
        return [
            # Single source of truth for all fields
            SearchField(
                name="id",
                type=SearchFieldDataType.String,
                key=True,
                filterable=True
            ),
            # ... rest of fields
        ]
```

## 3. REST API Management Plan

### API Client Design

```python
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

@dataclass
class AzureSearchConfig:
    endpoint: str
    api_key: str
    api_version: str = "2025-05-01-preview"
    timeout: int = 30
    max_retries: int = 3

class AzureSearchRestClient:
    """Low-level REST client for Azure AI Search."""

    def __init__(self, config: AzureSearchConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=f"{config.endpoint}",
            headers={
                "api-key": config.api_key,
                "Content-Type": "application/json"
            },
            timeout=config.timeout
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def create_index(self, index: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update an index."""
        response = await self.client.put(
            f"/indexes/{index['name']}",
            params={"api-version": self.config.api_version},
            json=index
        )
        response.raise_for_status()
        return response.json()

    async def list_indexes(
        self,
        select: Optional[List[str]] = None,
        top: Optional[int] = None
    ) -> Dict[str, Any]:
        """List indexes with optional filtering."""
        params = {"api-version": self.config.api_version}
        if select:
            params["$select"] = ",".join(select)
        if top:
            params["$top"] = str(top)

        response = await self.client.get("/indexes", params=params)
        response.raise_for_status()
        return response.json()
```

### Request/Response Models

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class IndexDefinition(BaseModel):
    """Index creation/update request model."""
    name: str
    fields: List[Dict[str, Any]]
    vector_search: Optional[Dict[str, Any]] = None
    semantic_search: Optional[Dict[str, Any]] = None
    scoring_profiles: Optional[List[Dict[str, Any]]] = None
    analyzers: Optional[List[Dict[str, Any]]] = None
    cors_options: Optional[Dict[str, Any]] = None
    etag: Optional[str] = Field(None, alias="@odata.etag")

class IndexerStatus(BaseModel):
    """Indexer status response model."""
    status: str
    last_result: Optional[Dict[str, Any]]
    execution_history: List[Dict[str, Any]]
    limits: Dict[str, Any]
```

### Error Handling

```python
from enum import Enum
from typing import Optional, Dict, Any

class AzureSearchErrorCode(Enum):
    INDEX_NOT_FOUND = "IndexNotFound"
    INVALID_REQUEST = "InvalidRequest"
    QUOTA_EXCEEDED = "QuotaExceeded"
    CONFLICT = "Conflict"
    SERVICE_UNAVAILABLE = "ServiceUnavailable"

class AzureSearchError(Exception):
    """Structured error for Azure Search operations."""

    def __init__(
        self,
        code: AzureSearchErrorCode,
        message: str,
        status_code: int,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(f"{code.value}: {message}")
```

## 4. Code Organization Blueprint

```
enhanced_rag/
├── azure_integration/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── client_factory.py      # Client lifecycle management
│   │   ├── auth.py                # Azure AD + API key auth
│   │   ├── config.py              # Typed configuration
│   │   ├── errors.py              # Error types and handlers
│   │   ├── constants.py           # API versions, limits
│   │   └── http_client.py         # Low-level REST client
│   ├── models/
│   │   ├── __init__.py
│   │   ├── common.py              # Shared model types
│   │   ├── fields.py              # Field definitions
│   │   ├── schemas.py             # Complete schemas
│   │   ├── index.py               # Index models
│   │   ├── indexer.py             # Indexer models
│   │   ├── datasource.py          # Data source models
│   │   └── skillset.py            # Skillset models
│   ├── operations/
│   │   ├── __init__.py
│   │   ├── base.py                # BaseOperation class
│   │   ├── index.py               # IndexOperations
│   │   ├── indexer.py             # IndexerOperations
│   │   ├── datasource.py          # DataSourceOperations
│   │   ├── skillset.py            # SkillsetOperations
│   │   └── documents.py           # DocumentOperations
│   ├── workflows/
│   │   ├── __init__.py
│   │   ├── reindex.py             # Reindexing strategies
│   │   ├── ingestion.py           # Bulk ingestion
│   │   ├── migration.py           # Schema migration
│   │   └── maintenance.py         # Index optimization
│   └── utils/
│       ├── __init__.py
│       ├── documents.py           # Document helpers
│       ├── retry.py               # Retry policies
│       ├── validation.py          # Schema validation
│       └── telemetry.py           # Metrics and logging
```

## 5. Migration Strategy

### Phase 1: Core Infrastructure (Week 1)
1. Create `core/` module with client factory
2. Implement centralized configuration
3. Set up error handling framework
4. Add comprehensive logging

### Phase 2: Models and Schemas (Week 2)
1. Extract all field definitions to `models/fields.py`
2. Create canonical schemas in `models/schemas.py`
3. Implement request/response models
4. Add validation layer

### Phase 3: Operations Refactor (Week 3-4)
1. Create `BaseOperation` class with common patterns
2. Refactor index operations to use base class
3. Refactor indexer operations
4. Update document operations

### Phase 4: Workflow Layer (Week 5)
1. Extract high-level workflows
2. Implement reindexing strategies
3. Add maintenance workflows
4. Create migration tools

### Regression Safeguards
- Feature flags for gradual rollout
- Parallel run of old/new code with comparison
- Comprehensive integration tests
- Rollback procedures documented

## 6. Documentation Updates

### README Structure
```markdown
# Azure AI Search Integration

## Quick Start
- Installation
- Basic configuration
- Common operations examples

## Architecture
- Component overview
- Design patterns
- Extension points

## API Reference
- Index Operations
- Indexer Operations
- Document Operations
- Error Handling

## Examples
- Create an index
- Configure indexers
- Bulk ingestion
- Schema migration

## Troubleshooting
- Common errors
- Performance tuning
- Debug logging

## Migration Guide
- From v1 to v2
- Breaking changes
- Compatibility layer
```

### Operation Examples

```python
# Create index with integrated vectorization
async def create_vector_index():
    config = AzureSearchConfig.from_env()
    client = AzureSearchRestClient(config)

    index = IndexDefinition(
        name="my-index",
        fields=CodebaseSchema.get_fields(),
        vector_search={
            "profiles": [{
                "name": "vector-profile",
                "algorithm": "hnsw",
                "vectorizer": "text-embedding-3-large"
            }]
        }
    )

    try:
        result = await client.create_index(index.model_dump())
        logger.info(f"Created index: {result['name']}")
    except AzureSearchError as e:
        if e.code == AzureSearchErrorCode.CONFLICT:
            logger.warning("Index already exists")
        else:
            raise
```

This refactoring plan addresses all the duplications found, provides a clean architecture aligned with Azure AI Search REST API best practices, and includes concrete implementation examples with proper error handling, typing, and extensibility.

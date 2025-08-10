# Enhanced RAG Search Pipeline Issues and Fixes

## Critical Issues Identified with Exact Locations

### 1. Undefined Variable `vq` in Hybrid Searcher
**File:** `enhanced_rag/retrieval/hybrid_searcher.py`
**Lines:** 362, 369

**Issue:**
```python
# Line 362 - vq is used but never defined in this scope
"vector_queries": [vq] if vq else None,

# Line 369 - vq referenced again without definition  
if vq and emb:
```

**Root Cause:** The variable `vq` is referenced but never assigned in the vector search section starting around line 334.

### 2. Inconsistent REST API Key Casing
**File:** `enhanced_rag/retrieval/hybrid_searcher.py`
**Lines:** 58 (whitelist), 255, 318, 361

**Issues:**
- Line 58: Whitelist includes `"vector_queries"` (snake_case) - should be `"vectorQueries"`
- Line 255: Uses `"query_type"` alongside correct `"queryType"` at line 267  
- Line 361: Uses `"vector_queries"` instead of `"vectorQueries"`
- Lines 346-358: Correctly uses `"vectorQueries"` but inconsistent with other parts

### 3. Zero-Vector Fallback Creates Misleading Results
**File:** `enhanced_rag/retrieval/hybrid_searcher.py`
**Lines:** 353-358

**Issue:**
```python
else:
    options["vectorQueries"] = [{
        "kind": "vector",
        "vector": [0.0] * 1536,  # Zero vector fallback
        "k": 1,
        "fields": "content_vector"
    }]
```
**Problem:** Sends meaningless zero vectors when embeddings unavailable, producing arbitrary search results.

### 4. Missing Import Statement  
**File:** `enhanced_rag/retrieval/hybrid_searcher.py`
**Lines:** 255, 319 (QueryType usage)

**Issue:** `QueryType.SEMANTIC` and `QueryType.SIMPLE` are used but `QueryType` is not imported.

### 5. Undefined `embed_func` Attribute
**File:** `enhanced_rag/retrieval/hybrid_searcher.py`
**Line:** 342

**Issue:** 
```python
if vector_weight > 0 and self.embed_func:
```
`self.embed_func` is never defined in the class but referenced in conditional.

### 6. Undefined `_get_embedding` Method
**File:** `enhanced_rag/retrieval/hybrid_searcher.py`
**Line:** 343

**Issue:** 
```python
emb = await self._get_embedding(query)
```
This method is called but never defined in the class.

### 7. Inconsistent Vector Query Construction
**File:** `enhanced_rag/retrieval/hybrid_searcher.py`
**Lines:** 346-370

**Issue:** Vector queries are built in multiple places:
- Lines 346-350: Builds in `options["vectorQueries"]`  
- Line 362: Tries to use undefined `vq` variable
- Line 370: Rebuilds `options["vectorQueries"]` again

### 8. Unused Variable Assignment in Embeddings
**File:** `enhanced_rag/azure_integration/automation/embedding_manager.py`
**Line:** 126

**Issue:**
```python
results[i]  # Line 126 - Dangling expression with no effect
```

### 9. Incorrect Async/Sync Callback Handling
**File:** `enhanced_rag/azure_integration/automation/embedding_manager.py`
**Line:** 102, 156

**Issue:** 
- Line 102: Type hint shows `Callable[[Dict[str, Any]], Awaitable[None]]` (should be async)
- Line 156: Code does `await progress_callback(...)` assuming async
- But actual usage may pass sync functions

### 10. Dimension Default Inconsistency
**File:** `enhanced_rag/azure_integration/automation/embedding_manager.py`
**Line:** 249

**Issue:** 
```python
expected_dimensions: int = 3072  # Line 249
```
Uses 3072 as default, but OpenAI text embeddings typically use 1536 dimensions.

### 11. Redundant Search Parameter Construction
**File:** `enhanced_rag/retrieval/hybrid_searcher.py`
**Lines:** 253-275

**Issue:** The code builds both `kw_sem_kwargs` using `_sanitize_search_kwargs()` and a separate `body` dict, creating redundant parameter handling and potential conflicts.

## Critical Fixes Applied

### Fix 1: Add Missing Import
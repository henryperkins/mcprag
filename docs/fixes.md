Concise end-to-end remediation guide grounded in current codebase. Each step includes exact file/function references, minimal diffs for critical fixes, config/env hardening, tests, and verification.

1) Triage summary

Top issues blocking reliability/correctness
- Blocking I/O in async retrieval:
  - HybridSearcher uses Azure SDK SearchClient (sync) inside async flows.
    - [`enhanced_rag/retrieval/hybrid_searcher.py.HybridSearcher._initialize_client()`](enhanced_rag/retrieval/hybrid_searcher.py:86) creates SDK client at [`131`–`135`](enhanced_rag/retrieval/hybrid_searcher.py:131).
    - `.search()` uses SDK calls via with_retry wrapper: [`203`](enhanced_rag/retrieval/hybrid_searcher.py:203), [`236`](enhanced_rag/retrieval/hybrid_searcher.py:236), [`261`](enhanced_rag/retrieval/hybrid_searcher.py:261); legacy paths at [`333`](enhanced_rag/retrieval/hybrid_searcher.py:333), [`383`](enhanced_rag/retrieval/hybrid_searcher.py:383).
  - Impact: Event loop stalls, degraded concurrency.
- Potential sync network in embedding:
  - `self.embedder.generate_embedding(query)` called without await: [`249`](enhanced_rag/retrieval/hybrid_searcher.py:249), [`487`](enhanced_rag/retrieval/hybrid_searcher.py:487).
  - Impact: Possible loop blocking if provider does HTTP.
- REST client logs entire error bodies:
  - [`enhanced_rag/azure_integration/rest/client.py.AzureSearchClient.request()`](enhanced_rag/azure_integration/rest/client.py:41) logs `e.response.text` and full JSON: [`87`–`92`](enhanced_rag/azure_integration/rest/client.py:87).
  - Impact: Sensitive data/PII leakage risk in logs.
- No backend wait/poll for indexer run:
  - [`enhanced_rag/azure_integration/rest/operations.py.SearchOperations.run_indexer`](enhanced_rag/azure_integration/rest/operations.py:243) posts and returns immediately.
  - Impact: MCP manage_indexer(wait) cannot confirm completion.
- REST client lifecycle not closed in pipeline:
  - Pipeline creates AzureSearchClient/SearchOperations at [`117`–`123`](enhanced_rag/pipeline.py:117) but `cleanup()` doesn’t close it [`254`–`265`](enhanced_rag/pipeline.py:254).
  - Impact: Persistent connections; resource pressure.
- OData filter construction risk:
  - Exact-term filter escapes quotes only: [`enhanced_rag/retrieval/hybrid_searcher.py:217`](enhanced_rag/retrieval/hybrid_searcher.py:217).
  - Impact: Malformed filter risk; low injection risk.
- Config/env defense gaps (REST path):
  - Server validates SDK fallback values; REST backend constructors accept strings directly. Pipeline constructs REST clients from config without local non-empty checks: [`enhanced_rag/pipeline.py:117`–`123`](enhanced_rag/pipeline.py:117).
  - Impact: If config validation fails upstream, late runtime errors.

2) Step-by-step remediation plan

Step 1: Switch HybridSearcher to async REST calls (no SDK blocking)
Purpose: Remove sync I/O from async retrieval; use existing async REST layer.

Changes:
- Accept optional SearchOperations; create internal AzureSearchClient when absent.
- Store endpoint/index_name; replace SDK search calls with REST `SearchOperations.search()` and map body.

File: [`enhanced_rag/retrieval/hybrid_searcher.py`](enhanced_rag/retrieval/hybrid_searcher.py:33)

Minimal diffs (key hunks):

a) Imports and ctor signature:

```
<<<<<<< SEARCH
from azure.search.documents import SearchClient
from azure.search.documents.models import (
    VectorizedQuery,
    VectorizableTextQuery,
    QueryType,
)
from azure.core.credentials import AzureKeyCredential
from enhanced_rag.utils.error_handler import with_retry
=======
from enhanced_rag.azure_integration.rest.operations import SearchOperations
from enhanced_rag.azure_integration.rest.client import AzureSearchClient
from azure.search.documents.models import (
    VectorizedQuery,
    VectorizableTextQuery,
    QueryType,
)
from enhanced_rag.utils.error_handler import with_retry
>>>>>>> REPLACE
```

```
<<<<<<< SEARCH
def __init__(
    self,
    config: Optional[Dict[str, Any]] = None,
    performance_monitor: Optional[PerformanceMonitor] = None
):
    self.performance_monitor = performance_monitor or PerformanceMonitor()
    self.config = config or get_config()
    self._initialize_client()
    self.embedder = None
    self._setup_embedder()
=======
def __init__(
    self,
    config: Optional[Dict[str, Any]] = None,
    performance_monitor: Optional[PerformanceMonitor] = None,
    rest_ops: Optional[SearchOperations] = None
):
    self.performance_monitor = performance_monitor or PerformanceMonitor()
    self.config = config or get_config()
    self.rest_ops = rest_ops
    self._initialize_client()
    self.embedder = None
    self._setup_embedder()
>>>>>>> REPLACE
```

b) Initialize REST client instead of SDK; keep endpoint/index_name:

```
<<<<<<< SEARCH
credential = AzureKeyCredential(admin_key)
self.search_client = SearchClient(
    endpoint=endpoint,
    index_name=index_name,
    credential=credential
)
=======
self._endpoint = endpoint
self._index_name = index_name
self.search_client = None
if self.rest_ops is None:
    self._rest_client = AzureSearchClient(endpoint=endpoint, api_key=admin_key)
    self.rest_ops = SearchOperations(self._rest_client)
>>>>>>> REPLACE
```

c) Replace SDK search usage within async search() with REST:

Semantic/keyword path:

```
<<<<<<< SEARCH
kw_sem = with_retry(op_name="acs.semantic")(self.search_client.search)(**kw_sem_kwargs)
kw_sem_results = self._process_results(kw_sem)
=======
body = {
    "queryType": "semantic",
    "semanticConfiguration": "semantic-config",
    "queryCaption": "extractive",
    "queryAnswer": "extractive",
    "filter": kw_sem_kwargs.get("filter"),
    "top": kw_sem_kwargs.get("top", top_k * 2),
    "includeTotalCount": kw_sem_kwargs.get("include_total_count", include_total_count),
}
resp = await self.rest_ops.search(self._index_name, query=kw_sem_kwargs.get("search_text", query), **body)
kw_sem_results = self._process_results(resp.get("value", []))
>>>>>>> REPLACE
```

Exact fallback:

```
<<<<<<< SEARCH
ex = with_retry(op_name="acs.exact")(self.search_client.search)(**exact_kwargs)
exact_results = self._process_results(ex)
=======
resp = await self.rest_ops.search(self._index_name, query="*", filter=combined_filter, top=exact_kwargs.get("top", top_k * 2))
exact_results = self._process_results(resp.get("value", []))
>>>>>>> REPLACE
```

Vector path:

```
<<<<<<< SEARCH
vec = with_retry(op_name="acs.vector")(self.search_client.search)(**vec_kwargs)
vec_results = self._process_results(vec)
=======
options = {"top": vec_kwargs.get("top", top_k * 2)}
if vq and emb:
    options["vectorQueries"] = [{"vector": emb, "k": top_k * 2, "fields": "content_vector"}]
resp = await self.rest_ops.search(self._index_name, query="*", **options)
vec_results = self._process_results(resp.get("value", []))
>>>>>>> REPLACE
```

Config/env:
- None needed if Config.get_config() is already validated; else ensure config.azure values are non-empty before constructing AzureSearchClient (handled by _initialize_client() validation at [`127`–`129`](enhanced_rag/retrieval/hybrid_searcher.py:127)).

Tests:
- Unit: mock SearchOperations.search to return {"value":[...]} and assert `_process_results` maps correctly; assert concurrency (no blocking) by running gather over multiple calls.
- Integration: run pipeline fallback (force retriever failure) and ensure responses returned.

Verification:
- Simulate 10 concurrent `HybridSearcher.search()` calls; measure event loop responsiveness and latency scaling.

Step 2: Sanitize REST error logging (no response bodies)
Purpose: Avoid leaking sensitive data.

File: [`enhanced_rag/azure_integration/rest/client.py.AzureSearchClient.request`](enhanced_rag/azure_integration/rest/client.py:41)

Diff:

```
<<<<<<< SEARCH
except httpx.HTTPStatusError as e:
    logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
    try:
        error_detail = e.response.json()
        logger.error(f"Error details: {error_detail}")
    except:
        pass
    raise
=======
except httpx.HTTPStatusError as e:
    status = getattr(e.response, "status_code", "unknown")
    logger.error(f"HTTP error {status} during Azure Search request")
    raise
>>>>>>> REPLACE
```

Config:
- None.

Tests:
- Unit: mock response with 401 and body; assert log message does not include body text.

Verification:
- Trigger a 4xx/5xx and inspect logs.

Step 3: Add optional wait/poll to run_indexer
Purpose: Support MCP manage_indexer(wait=True) semantics.

File: [`enhanced_rag/azure_integration/rest/operations.py.SearchOperations`](enhanced_rag/azure_integration/rest/operations.py:243)

Diff:

```
<<<<<<< SEARCH
async def run_indexer(self, name: str) -> None:
    logger.info(f"Running indexer: {name}")
    await self.client.request("POST", f"/indexers/{name}/run")
=======
async def run_indexer(self, name: str, wait: bool = False, poll_interval: float = 2.0, timeout: float = 300.0) -> Dict[str, Any]:
    logger.info(f"Running indexer: {name}")
    await self.client.request("POST", f"/indexers/{name}/run")
    if not wait:
        return {"started": True}
    import asyncio, time
    start = time.time()
    while time.time() - start < timeout:
        status = await self.get_indexer_status(name)
        last = (status.get("lastResult") or {}).get("status") or (status.get("executionStatus") or "")
        if str(last).lower() in {"success", "transientfailure", "error"}:
            return {"completed": True, "status": status}
        await asyncio.sleep(poll_interval)
    return {"timeout": True}
>>>>>>> REPLACE
```

Config:
- Expose defaults via Config if desired later.

Tests:
- Unit: mock get_indexer_status to flip status after N polls; verify returns completed; verify timeout case.

Verification:
- Call via MCP tool manage_indexer(run, wait=True) and observe result.

Step 4: Close Azure REST client in pipeline.cleanup
Purpose: Prevent resource leaks.

File: [`enhanced_rag/pipeline.py.RAGPipeline.cleanup`](enhanced_rag/pipeline.py:254)

Diff:

```
<<<<<<< SEARCH
try:
    # Cleanup feedback collector if available
    if hasattr(self, 'feedback_collector') and self.feedback_collector is not None:
        await self.feedback_collector.cleanup()
        logger.info("✅ RAG Pipeline cleanup completed")
except Exception as e:
    logger.error(f"❌ Error during RAG Pipeline cleanup: {e}")
=======
try:
    if hasattr(self, 'feedback_collector') and self.feedback_collector is not None:
        await self.feedback_collector.cleanup()
    if self._azure_operations and hasattr(self._azure_operations, "client"):
        try:
            await self._azure_operations.client.close()
        except Exception:
            pass
    logger.info("✅ RAG Pipeline cleanup completed")
except Exception:
    logger.error("❌ Error during RAG Pipeline cleanup")
>>>>>>> REPLACE
```

Tests:
- Unit: mock _azure_operations.client.close; assert called.
- Integration: run pipeline.start() then cleanup(); observe no open clients.

Verification:
- Run in dev; check open connections drop.

Step 5: Clamp exact-term filters to reduce malformed queries
Purpose: Basic input sanitization.

File: [`enhanced_rag/retrieval/hybrid_searcher.py.search`](enhanced_rag/retrieval/hybrid_searcher.py:160)

Insert after exact_terms creation at [`184`–`185`](enhanced_rag/retrieval/hybrid_searcher.py:184):

```
# Clamp length and ASCII range to avoid malformed filters
def _clamp_term(t: str) -> str:
    t = t[:200]
    return "".join(ch for ch in t if 32 <= ord(ch) <= 126)
exact_terms = [_clamp_term(t) for t in exact_terms]
```

Tests:
- Unit: include pathological quoted/numeric terms; verify clamping output.

Verification:
- Manual: query with very long quoted string; confirm no error.

Step 6: Harden HybridSearcher logging messages
Purpose: Avoid logging exception bodies.

File: [`enhanced_rag/retrieval/hybrid_searcher.py`](enhanced_rag/retrieval/hybrid_searcher.py:136)

Diff:

```
<<<<<<< SEARCH
logger.error(f"Failed to initialize search client: {e}")
=======
logger.error("Failed to initialize Azure Search client for HybridSearcher")
>>>>>>> REPLACE
```

Tests: none (log string check optional).

Step 7: MCP alignment (optional but recommended)
Purpose: Ensure tools can benefit from backend changes.

Files:
- [`mcprag/mcp/tools/azure_management.py.manage_indexer`](mcprag/mcp/tools/azure_management.py:206)
  - Pass wait flag through to rest_ops.run_indexer once backend supports it.
  - Already calls `server.rest_ops.run_indexer(indexer_name, wait=wait)` at [`261`](mcprag/mcp/tools/azure_management.py:261) — no change needed.

- Ensure async components started before pipeline-using tools
  - Add `await server.ensure_async_components_started()` at entry of:
    - [`mcprag/mcp/tools/search.py.search_code`](mcprag/mcp/tools/search.py:15)
    - [`search_code_raw`](mcprag/mcp/tools/search.py:71)
    - [`mcprag/mcp/tools/analysis.py.analyze_context`](mcprag/mcp/tools/analysis.py:15)
    - [`explain_ranking`](mcprag/mcp/tools/analysis.py:43)
    - [`preview_query_processing`](mcprag/mcp/tools/analysis.py:63)
    - [`mcprag/mcp/tools/generation.py.generate_code`](mcprag/mcp/tools/generation.py:14)

Minimal snippet to insert after docstring in each relevant function:
```
await server.ensure_async_components_started()
```

Tests:
- Run a tool immediately after server boot; ensure no “not started” scenarios.

3) Environment and configuration hardening

Required env/config (single source of truth via Config)
- Azure:
  - ENDPOINT (str, non-empty URL) – Azure Search service endpoint
  - ADMIN_KEY (str, non-empty) – Azure Search admin API key
  - INDEX_NAME (str, defaults to “codebase-mcp-sota” if missing in HybridSearcher; prefer explicit)
- Timeouts:
  - REST_TIMEOUT_SECONDS (float, default 30) – httpx AsyncClient timeout
  - CLI_TIMEOUT_SECONDS (int, default 900) – for MCP CLI wrappers (already recommended earlier)
  - INDEXER_TIMEOUT_SECONDS (int, default 300) – for waitable indexer runs (optional)
- Logging:
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR)
- Learning:
  - FEEDBACK_DIR (path), ADMIN_MODE (bool) — for MCP admin tools

Validation rules:
- Use Config.validate() at startup: server already does at [`mcprag/server.py:181`](mcprag/server.py:181).
- Backend constructors (HybridSearcher._initialize_client) already ensure endpoint/admin_key non-empty: [`127`–`129`](enhanced_rag/retrieval/hybrid_searcher.py:127).
- Add similar non-empty checks when constructing pipeline AzureSearchClient if desired; current failure is caught and warned at [`124`](enhanced_rag/pipeline.py:124).

TLS/secrets:
- Secrets only via env/config injection; never logged (after REST log patch).
- If using secret store (e.g., Azure Key Vault), wire retrieval inside Config loader (not in scope; keep env).

4) Data and interface contracts

Retrieval (HybridSearcher)
- search(query: str, filter_expr: Optional[str], top_k: int, ...) -> List[HybridSearchResult]
  - Inputs: query (non-empty str), top_k > 0; optional filter_expr (string OData), weights float.
  - Output: list of HybridSearchResult(id:str, score:float, content:str, metadata:dict)
- Enforce type hints (already present) and runtime guards:
  - Clamp exact terms and safe defaults for weights.
  - `_process_results` expects Azure Search document dicts; ensures presence of keys with defaults: [`446`–`473`](enhanced_rag/retrieval/hybrid_searcher.py:446).

Pipeline
- process_query(query: str, context: QueryContext, generate_response: bool, max_results: int) -> RAGPipelineResult
  - Input schema via Pydantic models in core.models (SearchQuery, QueryContext).
  - Output: RAGPipelineResult(success:bool, results:List[SearchResult], response:Optional[str], metadata:Dict[str,Any], error:Optional[str]) — implemented at [`38`–`53`](enhanced_rag/pipeline.py:38).
- Contract between retriever and pipeline:
  - retriever.retrieve returns list[dict] or list[SearchResult]; pipeline normalizes dicts at [`377`–`401`](enhanced_rag/pipeline.py:377).

5) Observability and diagnostics

Structured logging
- Add contextual fields: operation, session_id(user), query_id, latency, retry counts.

Where to add:
- HybridSearcher.search(): log per-path timings and fused result count after [`304`–`305`](enhanced_rag/retrieval/hybrid_searcher.py:304):
  - logger.info("search.completed op=hybrid session_id=%s top_k=%d results=%d", context_session_id, top_k, len(fused)) — if session_id known via args (else omit).
- Pipeline.process_query():
  - Already logs several steps; add info log with latency total at return: [`558`–`563`](enhanced_rag/pipeline.py:558)

Metrics hooks (stubs)
- Add counters/histograms via a small adapter (e.g., prometheus_client if used elsewhere) — out-of-scope for code change here; plan:
  - pipeline.process_query: duration histogram; error counter; results count histogram.
  - HybridSearcher: semantic/vector/exact durations.

Example grep checks:
- grep -E "search\.completed|RAG Pipeline async components started|HTTP error" logs during tests.

6) Testing and verification

Unit tests
- HybridSearcher with REST ops:
  - Mock SearchOperations.search to return {"value":[{id:'1','@search.score':1.2,'content': '...', ...}]}; assert `_process_results()` mapping.
  - Exact filter clamping: inject long/invalid terms; ensure combined filter formed and no exceptions.
- REST client logging: simulate 401 and assert logs don’t include body.
- Operations.run_indexer(wait): mock get_indexer_status progression; assert completion/timeout dicts.

Integration tests
- Pipeline fallback path:
  - Mock retriever.retrieve to raise; ensure HybridSearcher.hybrid_search is used and returns SearchResult list.
- MCP tool manage_indexer(wait=True): with mocked backend, ensure returned dict has completed:true.

Load/smoke
- Run 20 concurrent process_query with small query; assert event loop remains responsive; collect average latency.

CI updates
- Ensure tests added under tests/ pass with typecheck (mypy/pyright) and lint.
- Add secrets scanning (ensure no logs include API key patterns).

7) Security and robustness

- Secrets handling:
  - After REST logging patch, no response bodies logged; ensure no code logs ADMIN_KEY/headers anywhere.
- Input sanitization:
  - Clamp exact terms in HybridSearcher; prefer default deterministic search options (disable_randomization true used in SDK path).
- Least privilege:
  - Use Azure Search admin key for admin; query keys for read-only where possible (future enhancement).
- Dependency pinning:
  - Pin httpx, tenacity, azure* versions compatible; run vulnerability scan (pip-audit).

8) Rollout plan

Phased deployment
- Feature-flag HybridSearcher REST path if desired (env: USE_REST_HYBRID=true); current patch defaults to REST when rest_ops constructed; keep SDK fallback if rest_ops creation fails.
- Stage in dev; run unit/integration suite; perform smoke/load tests.
- Promote to staging; monitor logs for HTTP error rates and latency histograms; verify no sensitive bodies logged.

Rollback
- If issues arise, set feature flag to disable REST hybrid path (fall back to SDK) or revert commit; since diffs are minimal, rollback is safe.

Final verification checklist

- Startup
  - Server starts; Config.validate() passes: [`mcprag/server.py:181`](mcprag/server.py:181)
  - Pipeline starts async components: [`enhanced_rag/pipeline.py.start`](enhanced_rag/pipeline.py:218)
- Retrieval
  - Run a search via MCP search_code tool (ensuring `await server.ensure_async_components_started()` added): results return; no event loop block; logs show search.completed.
- Admin
  - manage_indexer(run, wait=true): returns completed or timeout dict, not just 200 OK.
- Cleanup
  - Stop server; ensure REST clients closed in pipeline and server cleanup: [`mcprag/server.py.cleanup_async_components`](mcprag/server.py:428), [`enhanced_rag/pipeline.py.cleanup`](enhanced_rag/pipeline.py:254)

Example end-to-end run

1) Start server (stdio transport):
- python -m mcprag.server
- Logs: “MCP Server initialized - Features …”, “✅ RAGPipeline async components started”

2) Search request (through MCP tool):
- Call search_code with a simple query (e.g., “vector search API”).
- Expect ~<500ms, results list with items count; no warnings about blocked loop.

3) Run indexer (wait):
- Call manage_indexer action=run indexer_name=<name> wait=true
- Expect: {"indexer": "<name>", "run_started": True, "result": {"completed": true, ...}} or timeout.

Assumptions noted
- Azure REST vectorQueries body keys are accepted by `SearchOperations.search()` as passed-through options; if the service version requires different casing (e.g., "vectorQueries" vs "vector_queries"), adjust mapping in HybridSearcher accordingly.
- AzureOpenAIEmbeddingProvider is synchronous; if it’s async, convert calls to await.

This guide breaks remediation into atomic, testable steps, with precise code references and minimal diffs to implement the critical fixes: async-safe retrieval, sanitized logging, indexer run wait semantics, and proper resource cleanup.

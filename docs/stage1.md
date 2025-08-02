Step-by-step implementation guide to add Stage 1 MCP integrations into [`mcp_server_sota.py`](mcp_server_sota.py)

Goal
Add the following tools/resources with safe defaults and graceful fallbacks:
- Tools: explain_ranking, diagnose_query, preview_query_processing, search_code_hybrid, search_code_raw
- Resource: resource://runtime_diagnostics

Conventions and gating
- Do NOT block search_code_raw or runtime_diagnostics on ENHANCED_RAG_SUPPORT; they must work in base ACS mode.
- The other Stage 1 tools should attempt to use enhanced_rag and gracefully fall back to base ACS data or return a structured unavailable error when enhanced components aren’t present.
- Return JSON-serializable dicts to align with Claude Code SDK usage (--output-format json / stream-json).

1) Add helper utilities near the top-level (after server instantiation)
Insert after mcp = FastMCP(...) and server = EnhancedMCPServer():

- Admin/diagnostic helpers
```python
def _is_admin() -> bool:
    return os.getenv("MCP_ADMIN_MODE", "0").lower() in {"1", "true", "yes"}

def _ok(data: Any) -> Dict[str, Any]:
    return {"ok": True, "data": data}

def _err(msg: str, code: str = "error") -> Dict[str, Any]:
    return {"ok": False, "error": msg, "code": code}
```

- Lightweight timer utility for diagnostics
```python
import time

class _Timer:
    def __init__(self):
        self._marks = {"start": time.perf_counter()}
    def mark(self, name: str):
        self._marks[name] = time.perf_counter()
    def durations(self) -> Dict[str, float]:
        keys = list(self._marks.keys())
        out = {}
        for i in range(1, len(keys)):
            out[f"{keys[i-1]}→{keys[i]}"] = (self._marks[keys[i]] - self._marks[keys[i-1]]) * 1000.0
        out["total"] = (time.perf_counter() - self._marks["start"]) * 1000.0
        return out
```

2) Implement search_code_raw (always available, base ACS)
Place in “Tool Implementations” section, near existing search_code tool.

- Function signature and behavior
```python
@mcp.tool()
async def search_code_raw(
    query: str,
    intent: Optional[str] = None,
    language: Optional[str] = None,
    repository: Optional[str] = None,
    max_results: int = 10,
    include_dependencies: bool = False,
    skip: int = 0,
    orderby: Optional[str] = None,
    highlight_code: bool = False
) -> Dict[str, Any]:
    """
    Raw JSON results for code search (base ACS path).
    Returns structured SearchResult objects for SDK-friendly consumption.
    """
    params = SearchCodeParams(
        query=query,
        intent=SearchIntent(intent) if intent else None,
        language=language,
        repository=repository,
        max_results=max_results,
        include_dependencies=include_dependencies,
        skip=skip,
        orderby=orderby,
        highlight_code=highlight_code
    )
    results = await server.search_code(params)
    return _ok({
        "results": [r.model_dump() for r in results],
        "count": len(results),
        "query": query,
        "intent": intent
    })
```

3) Implement runtime_diagnostics resource (always available)
Place in “Resources” section near existing resources.

- Behavior: report feature flags, index, asyncio policy, socketpair patch, versions.

```python
@mcp.resource("resource://runtime_diagnostics")
async def runtime_diagnostics() -> str:
    try:
        import platform
        diag = {
            "feature_flags": {
                "ENHANCED_RAG_SUPPORT": ENHANCED_RAG_SUPPORT,
                "VECTOR_SUPPORT": VECTOR_SUPPORT,
                "DOCS_SUPPORT": DOCS_SUPPORT,
            },
            "index": {
                "name": os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota"),
            },
            "asyncio": {
                "policy": type(asyncio.get_event_loop_policy()).__name__,
                "socketpair_patched": (socket.socketpair is _safe_socketpair),
            },
            "versions": {
                "python": platform.python_version(),
                "azure_sdk": "azure-search-documents",
                "mcp": "fastmcp" if MCP_SDK_AVAILABLE else "fallback",
            },
        }
        try:
            # Safe to attempt; ignore errors
            diag["index"]["document_count"] = server.search_client.get_document_count()
        except Exception as _:
            diag["index"]["document_count"] = None

        return json.dumps(_ok(diag), indent=2)
    except Exception as e:
        return json.dumps(_err(str(e)), indent=2)
```

4) Implement explain_ranking (uses enhanced if present; fallback)
Place under the Enhanced RAG block if ENHANCED_RAG_SUPPORT, but ensure a fallback path works even without it.

- Import result explainer guarded
At the top with other optional imports:
```python
try:
    from enhanced_rag.ranking.result_explainer import ResultExplainer  # type: ignore
    RESULT_EXPLAINER_AVAILABLE = True
except Exception:
    ResultExplainer = None
    RESULT_EXPLAINER_AVAILABLE = False
```

- Tool implementation
```python
@mcp.tool()
async def explain_ranking(
    query: str,
    mode: str = "enhanced",
    max_results: int = 10,
    intent: Optional[str] = None,
    language: Optional[str] = None,
    repository: Optional[str] = None
) -> Dict[str, Any]:
    """
    Explain ranking factors for results. Uses Enhanced RAG explainer when available,
    otherwise provides a heuristic explanation from base ACS metadata.
    """
    # Get results from chosen mode
    if mode == "enhanced" and ENHANCED_RAG_SUPPORT:
        try:
            # Reuse EnhancedSearchTool if already instantiated (see existing code)
            result = await enhanced_search_tool.search(
                query=query,
                intent=intent,
                language=language,
                repository=repository,
                max_results=max_results,
                include_dependencies=False,
                generate_response=False,
            )
            raw_items = result.get("results", []) or result.get("final_results", []) or []
        except Exception as e:
            raw_items = []
    else:
        # Base ACS path
        params = SearchCodeParams(
            query=query,
            intent=SearchIntent(intent) if intent else None,
            language=language,
            repository=repository,
            max_results=max_results,
            include_dependencies=False
        )
        base_results = await server.search_code(params)
        raw_items = [r.model_dump() for r in base_results]

    # Try proper explainer
    if RESULT_EXPLAINER_AVAILABLE and ENHANCED_RAG_SUPPORT:
        try:
            explainer = ResultExplainer()
            explanations = explainer.explain(raw_items, query=query)
            return _ok({
                "mode": mode if ENHANCED_RAG_SUPPORT else "base",
                "query": query,
                "explanations": explanations
            })
        except Exception as e:
            pass

    # Fallback heuristic explanation
    explanations = []
    q_terms = set((query or "").lower().split())
    for item in raw_items:
        content = (item.get("content") or "").lower()
        signature = (item.get("signature") or "").lower()
        repo = item.get("repository")
        file_path = item.get("file_path")
        score = item.get("score", 0.0)
        overlap = sum(1 for t in q_terms if t in content or t in signature)
        factors = []
        if overlap:
            factors.append({"name": "term_overlap", "weight": 0.4, "contribution": overlap * 0.1})
        if repo:
            factors.append({"name": "repo_presence", "weight": 0.2, "contribution": 0.1})
        if signature:
            factors.append({"name": "signature_match", "weight": 0.2, "contribution": 0.1})
        factors.append({"name": "base_score", "weight": 0.2, "contribution": score * 0.1})
        explanations.append({
            "file_path": file_path,
            "repository": repo,
            "score": score,
            "factors": factors,
            "summary": f"Heuristic explanation: {overlap} query-term overlaps; base score {score:.2f}"
        })
    return _ok({"mode": "base" if mode != "enhanced" or not ENHANCED_RAG_SUPPORT else "enhanced", "query": query, "explanations": explanations})
```

5) Implement diagnose_query (timings; enhanced or base)
- If enhanced available, call enhanced_search_tool with a diagnostics flag if supported, otherwise time sections manually.
- For base, time server.search_code only and return timings.

```python
@mcp.tool()
async def diagnose_query(
    query: str,
    mode: str = "enhanced",
    intent: Optional[str] = None,
    language: Optional[str] = None,
    repository: Optional[str] = None,
    max_results: int = 10
) -> Dict[str, Any]:
    """
    Run a query and return approximate stage timings and cache hints.
    """
    timer = _Timer()
    cache_hit = False
    try:
        if mode == "enhanced" and ENHANCED_RAG_SUPPORT:
            # If enhanced supports diagnostics param, use it; else just time the call
            result = await enhanced_search_tool.search(
                query=query,
                intent=intent,
                language=language,
                repository=repository,
                max_results=max_results,
                include_dependencies=False,
                generate_response=False
            )
            timer.mark("enhanced_search")
            stages = result.get("stages") or []
            out = {
                "mode": "enhanced",
                "query": query,
                "timings_ms": timer.durations(),
                "stages": stages,
                "cache": {"hit": cache_hit, "cache_key": None}
            }
            return _ok(out)
        else:
            # Base ACS
            params = SearchCodeParams(
                query=query,
                intent=SearchIntent(intent) if intent else None,
                language=language,
                repository=repository,
                max_results=max_results,
                include_dependencies=False
            )
            # Try to detect simple cache use
            cache_key = f"{params.query}:{params.intent}:{params.repository}:{params.language}"
            cache_hit = cache_key in server._query_cache
            res = await server.search_code(params)
            timer.mark("base_search")
            out = {
                "mode": "base",
                "query": query,
                "timings_ms": timer.durations(),
                "stages": [{"stage": "base_search", "count": len(res), "duration_ms": timer.durations().get("start→base_search", 0.0)}],
                "cache": {"hit": cache_hit, "cache_key": cache_key if cache_hit else None}
            }
            return _ok(out)
    except Exception as e:
        return _err(str(e))
```

6) Implement preview_query_processing (enhanced preferred; base fallback)
- Try to import intent/query modules; fallback to server._enhance_query.

Add guarded imports at top:
```python
try:
    from enhanced_rag.semantic.intent_classifier import IntentClassifier  # type: ignore
    from enhanced_rag.semantic.query_enhancer import QueryEnhancer  # type: ignore
    from enhanced_rag.semantic.query_rewriter import QueryRewriter  # type: ignore
    SEMANTIC_TOOLS_AVAILABLE = True
except Exception:
    IntentClassifier = QueryEnhancer = QueryRewriter = None
    SEMANTIC_TOOLS_AVAILABLE = False
```

Tool:
```python
@mcp.tool()
async def preview_query_processing(
    query: str,
    intent: Optional[str] = None,
    language: Optional[str] = None,
    repository: Optional[str] = None
) -> Dict[str, Any]:
    """
    Show intent classification, enhancements, rewrites, and applied rules for a query.
    """
    try:
        if ENHANCED_RAG_SUPPORT and SEMANTIC_TOOLS_AVAILABLE:
            try:
                classifier = IntentClassifier()
                detected = classifier.classify(query)
            except Exception:
                detected = intent

            enhancements = {}
            rewrites = []
            rules = []
            try:
                enhancer = QueryEnhancer()
                enhanced = enhancer.enhance(query, intent=detected or intent, language=language)
                enhancements = enhanced or {}
            except Exception:
                pass
            try:
                rewriter = QueryRewriter()
                rw = rewriter.rewrite(query, intent=detected or intent, language=language)
                if isinstance(rw, dict):
                    rewrites = rw.get("rewrites", [])
                    rules = rw.get("applied_rules", [])
                elif isinstance(rw, list):
                    rewrites = rw
            except Exception:
                pass

            return _ok({
                "input_query": query,
                "detected_intent": detected,
                "enhancements": enhancements,
                "rewritten_queries": rewrites,
                "applied_rules": rules
            })
        else:
            # Base fallback using server._enhance_query
            enhanced = server._enhance_query(query, SearchIntent(intent) if intent else None)
            boost_terms = []
            if intent:
                if intent == "implement":
                    boost_terms = ["function", "class", "method", "def", "async"]
                elif intent == "debug":
                    boost_terms = ["try", "except", "catch", "error", "exception", "raise", "throw"]
                elif intent == "understand":
                    boost_terms = ["docstring", "comment", "README", "example", "usage"]
                elif intent == "refactor":
                    boost_terms = ["pattern", "design", "architecture", "best practice"]
            return _ok({
                "input_query": query,
                "detected_intent": intent,
                "enhancements": {"prefix": None, "boost_terms": boost_terms},
                "rewritten_queries": [enhanced] if enhanced and enhanced != query else [],
                "applied_rules": []
            })
    except Exception as e:
        return _err(str(e))
```

7) Implement search_code_hybrid (enhanced preferred; base emulation)
- Preferred: use enhanced_rag.retrieval.hybrid_searcher or multi_stage_pipeline via EnhancedSearchTool if it accepts a mode/flag.
- If not available, emulate by running base ACS twice (bm25: without vector_queries; vector: with vector; then merge by score). Because ACS SDK here bundles both via semantic + vector_queries together, emulate by: a) run normal semantic search; b) if vector available (VectorizableTextQuery or embedder), run with vector_queries only by setting query_type="simple", search_text="*" and vector_only flag; this requires lower-level control—if that’s not supported, fall back to a single pass and annotate that hybrid couldn’t be separated.

Implementation (best-effort, with graceful fallback):
```python
@mcp.tool()
async def search_code_hybrid(
    query: str,
    bm25_weight: float = 0.5,
    vector_weight: float = 0.5,
    max_results: int = 10,
    intent: Optional[str] = None,
    language: Optional[str] = None,
    repository: Optional[str] = None,
    include_stage_results: bool = True
) -> Dict[str, Any]:
    """
    Hybrid BM25 + Vector search. Uses Enhanced RAG when available; base fallback merges available signals.
    """
    try:
        if ENHANCED_RAG_SUPPORT:
            try:
                result = await enhanced_search_tool.search(
                    query=query,
                    intent=intent,
                    language=language,
                    repository=repository,
                    max_results=max_results,
                    include_dependencies=False,
                    generate_response=False
                )
                # Expect result to possibly contain stage breakdown
                out = {
                    "weights": {"bm25": bm25_weight, "vector": vector_weight},
                    "final_results": result.get("results") or result.get("final_results") or [],
                    "stages": result.get("stages") if include_stage_results else None
                }
                return _ok(out)
            except Exception:
                pass

        # Base fallback: one pass (semantic + possibly vector). We cannot split stages reliably, but return the results.
        params = SearchCodeParams(
            query=query,
            intent=SearchIntent(intent) if intent else None,
            language=language,
            repository=repository,
            max_results=max_results,
            include_dependencies=False
        )
        results = await server.search_code(params)
        out = {
            "weights": {"bm25": bm25_weight, "vector": vector_weight},
            "final_results": [r.model_dump() for r in results],
            "stages": None
        }
        return _ok(out)
    except Exception as e:
        return _err(str(e))
```

8) Wire imports and flags
Ensure the new guarded imports and flags (RESULT_EXPLAINER_AVAILABLE, SEMANTIC_TOOLS_AVAILABLE) are added near similar try/except import blocks at the top.

9) Testing checklist with Claude Code MCP/SDK
- Allow tools with Claude Code flags:
  - search_code_raw: Include in --allowedTools as mcp__azure-code-search-enhanced__search_code_raw
  - runtime_diagnostics: reference with @azure-code-search-enhanced:resource://runtime_diagnostics in prompts
  - explain_ranking / diagnose_query / preview_query_processing / search_code_hybrid: add to allowedTools as needed
- Run non-interactive JSON tests:
  - claude -p '...' --mcp-config mcp-servers.json --allowedTools "mcp__azure-code-search-enhanced__search_code_raw" --output-format json
- Validate enhanced_rag unavailable path:
  - Unset/enforce ImportError by running without enhanced_rag installed; search_code_raw and runtime_diagnostics should still work; others return base or heuristic.

10) Error messages and UX
- For enhanced-only logic when ENHANCED_RAG_SUPPORT is False, never crash; either return base explanation/diagnostic or:
  - return _err("enhanced_rag_unavailable", code="enhanced_unavailable")
- Always JSON-return data to align with docs/claudecodesdk.md. The legacy formatted search_code tool remains as-is for human-friendly consumption.

11) Security notes per docs/claudecodemcp.md
- No admin/index/github operations added in Stage 1 to minimize risk.
- Tools are discoverable and must be explicitly allowed with --allowedTools.

12) Summary of additions
- New helpers: _is_admin, _ok, _err, _Timer
- Tools:
  - search_code_raw(...) -> JSON list of SearchResult
  - explain_ranking(...) -> Enhanced explainer when available; heuristic fallback
  - diagnose_query(...) -> timing and cache info
  - preview_query_processing(...) -> intent/enhancement/rewrites; base fallback uses server._enhance_query
  - search_code_hybrid(...) -> Enhanced hybrid when available; base fallback returns single pass
- Resource:
  - resource://runtime_diagnostics -> environment/runtime feature flags and index info

You can now implement Stage 2 (feedback/learning and admin/index/github tools) following the previously provided plan. This staged rollout keeps Stage 1 safe and SDK-friendly while providing immediate value and transparency.
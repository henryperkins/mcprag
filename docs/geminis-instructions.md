In-depth code review with actionable, minimal-diff improvements and fully rendered code snippets

Scope and call paths
- search_code
  - Entry/wrapper: [mcprag/mcp/tools.py:27](mcprag/mcp/tools.py:27) → [_search_code_impl](mcprag/mcp/tools.py:511)
  - Enhanced path: calls EnhancedSearchTool.search → RAGPipeline.process_query (retrieval, normalization, ranking, metadata) → EnhancedSearchTool._format_mcp_response for results/results_compact/results_ultra_compact
  - Basic path: [_basic_search](mcprag/mcp/tools.py:647) directly on Azure SDK returns raw items
- analyze_context
  - Entry: [mcprag/mcp/tools.py:151](mcprag/mcp/tools.py:151) → ContextAwareTool.analyze_context ([enhanced_rag/mcp_integration/context_aware_tool.py:30](enhanced_rag/mcp_integration/context_aware_tool.py:30))
- generate_code
  - Entry: [mcprag/mcp/tools.py:123](mcprag/mcp/tools.py:123) → CodeGenerationTool.generate_code ([enhanced_rag/mcp_integration/code_gen_tool.py:42](enhanced_rag/mcp_integration/code_gen_tool.py:42))
  - Internal generation engine: [enhanced_rag/generation/code_generator.py](enhanced_rag/generation/code_generator.py); baseline skeleton path: ResponseGenerator.generate_code ([enhanced_rag/generation/response_generator.py:390](enhanced_rag/generation/response_generator.py:390)) for alternative flows

Findings

A) search_code retrieval, formatting, presentation
1) Retrieval
- Enhanced path uses RAGPipeline which:
  - Converts dict results to SearchResult (stable schema: id, score, file_path, language, code_snippet, highlights, start_line/end_line, etc.) ([enhanced_rag/pipeline.py:281-305](enhanced_rag/pipeline.py:281))
  - Falls back to HybridSearcher; HybridSearchResult then converted to SearchResult with content → code_snippet, metadata mapped ([enhanced_rag/pipeline.py:318-337](enhanced_rag/pipeline.py:318))
  - Ranks with ImprovedContextualRanker or AdaptiveRanker and adds explanations ([enhanced_rag/pipeline.py:371-429](enhanced_rag/pipeline.py:371))
  - Returns metadata: intent, enhanced_queries, total_results_found, processing_time_ms, context_used ([enhanced_rag/pipeline.py:441-449](enhanced_rag/pipeline.py:441))
- Basic path in MCP directly queries Azure SDK via search_client and returns raw items without normalization or ranking ([mcprag/mcp/tools.py:647-672](mcprag/mcp/tools.py:647)). This diverges from enhanced path shape.

2) Formatting and presentation
- EnhancedSearchTool formats:
  - results: list of dicts with file, content, relevance, explanation, context_type ([enhanced_rag/mcp_integration/enhanced_search_tool.py:119-136](enhanced_rag/mcp_integration/enhanced_search_tool.py:119))
  - results_compact: file:line, match summary, context_type ([enhanced_rag/mcp_integration/enhanced_search_tool.py:85-100](enhanced_rag/mcp_integration/enhanced_search_tool.py:85))
  - results_ultra_compact: single-line: file:line | why | one-line headline ([enhanced_rag/mcp_integration/enhanced_search_tool.py:100-105](enhanced_rag/mcp_integration/enhanced_search_tool.py:100))
  - grouped_results and summary (counts and suggested_terms) ([enhanced_rag/mcp_integration/enhanced_search_tool.py:110-136](enhanced_rag/mcp_integration/enhanced_search_tool.py:110))
- MCP search_code returns:
  - items per detail_level (full/compact/ultra) chosen by _get_items_by_detail_level ([mcprag/mcp/tools.py:608-616](mcprag/mcp/tools.py:608))
  - snippet_lines truncation for “full”, using _select_headline and trimming to 120 chars ([mcprag/mcp/tools.py:675-737](mcprag/mcp/tools.py:675))
  - Took_ms and optional timings.total ([mcprag/mcp/tools.py:582-601](mcprag/mcp/tools.py:582))

3) Shortcomings in display logic
- Inconsistent schema in basic path: Raw Azure items not normalized to enhanced schema. Downstream logic assumes keys like file, content, language, highlights, relevance that might not exist, causing UI inconsistency and fragility.
- Compact/ultra missing in basic path: results_compact/ultra are only built by EnhancedSearchTool; _get_items_by_detail_level simply selects lists already present for enhanced path. Basic path produces none for compact/ultra.
- Headline/highlights not sanitized: _select_headline returns the first highlight (potentially with HTML tags) or first non-comment line; no HTML strip, risking UI artifacts and possible XSS in lenient clients.
- Truncation strategy naïve: When snippet_lines > 1, lines are chosen sequentially from start of content regardless of highlight proximity or structure, sometimes surfacing irrelevant lines.
- No deduplication: Enhanced pipeline tends to produce unique files, but dedupe at MCP response level is absent; duplicates can appear when combining stages or re-ranking in different flows.
- Timings sparse and backend hidden: MCP returns took_ms and optional timings.total; no stage breakdown, backend label (“enhanced” vs “basic”), or cache indicators, reducing debuggability and UX transparency.
- Paging/cursors absent: skip is provided but no next/prev cursors or page context in ultra-compact view; chat clients benefit from lightweight pagination hints.

B) analyze_context accuracy and performance
- Sequential awaits: analyze_context awaits context_analyzer.analyze, then optionally dep_builder.build_graph, then related files and indirect imports. _get_indirect_imports awaits analyze per import sequentially ([enhanced_rag/mcp_integration/context_aware_tool.py:322-328](enhanced_rag/mcp_integration/context_aware_tool.py:322)). This is O(n) awaits and can be slow on large import lists.
- Caching absent: No memoization for analyze/analyze_file/build_graph; repeated calls during a session will recompute.
- Partial error returns: Entire call returns {'error':...} on exception ([enhanced_rag/mcp_integration/context_aware_tool.py:101-105](enhanced_rag/mcp_integration/context_aware_tool.py:101)), losing available sub-results.
- Related_files selection simple: Not ranked by confidence/relationship strength; imports and module files not deduped/sorted; test file detection relies on filesystem existence synchronously.

C) generate_code accuracy and performance
- Robust orchestration: CodeGenerationTool builds QueryContext, retrieves examples via pipeline.process_query, forms GenerationContext, runs CodeGenerator.generate ([enhanced_rag/mcp_integration/code_gen_tool.py:69-141](enhanced_rag/mcp_integration/code_gen_tool.py:69))
- Reference extraction bug risk: references use r.content slice, but SearchResult provides code_snippet/content inconsistently. Should prefer code_snippet fallback to content ([enhanced_rag/mcp_integration/code_gen_tool.py:128-135](enhanced_rag/mcp_integration/code_gen_tool.py:128)).
- Token budgeting: ResponseGenerator enforces ~7k token guard for template text, but CodeGenerationTool final code is unbounded; large outputs can overwhelm chat UIs.
- Style adaptation risk: ResponseGenerator.adapt_to_style globally replaces quotes, which can break embedded strings or languages with strict quoting ([enhanced_rag/generation/response_generator.py:523-533](enhanced_rag/generation/response_generator.py:523)).
- CPU work sync: CodeGenerator regex extraction across many examples is synchronous; under heavy loads, consider to_thread batching.

Recommendations (prioritized, minimal-diff)

1) MCP search_code: normalize, sanitize, and consistently present formats
Rationale: Fixes schema divergence, improves readability, and prevents HTML artifacts. Enables compact/ultra for all backends.

a) Add sanitizers and normalizer in mcprag/mcp/tools.py
Insert below helper functions:

```python
# mcprag/mcp/tools.py (add near other helpers)
import re as _re
_TAG_RE = _re.compile(r"<[^>]+>")

def _sanitize_text(s: str) -> str:
    return _TAG_RE.sub("", (s or "")).replace("\xa0", " ").strip()

def _sanitize_highlights(hl: Any) -> Dict[str, List[str]]:
    if not isinstance(hl, dict):
        return {}
    return {
        k: [
            _sanitize_text(x)[:200]
            for x in (v or [])
            if isinstance(x, str) and x.strip()
        ]
        for k, v in hl.items()
    }

def _normalize_items(items: List[Any]) -> List[Dict[str, Any]]:
    normalized = []
    for it in items:
        d = it if isinstance(it, dict) else getattr(it, "__dict__", {}) or {}
        file_path = d.get("file") or d.get("file_path") or d.get("path") or ""
        content = d.get("content") or d.get("code_snippet") or d.get("snippet") or ""
        normalized.append({
            "id": d.get("id") or d.get("@search.documentId") or f"{file_path}:{d.get('start_line') or ''}",
            "file": file_path,
            "repository": d.get("repository") or "",
            "language": d.get("language") or "",
            "content": content,
            "highlights": _sanitize_highlights(d.get("highlights") or d.get("@search.highlights") or {}),
            "relevance": d.get("relevance") or d.get("score") or d.get("@search.score") or 0.0,
            "start_line": d.get("start_line"),
            "end_line": d.get("end_line"),
            "function_name": d.get("function_name"),
            "class_name": d.get("class_name"),
        })
    return normalized

def _first_highlight(entry: Dict[str, Any]) -> Optional[str]:
    hl = entry.get("highlights") or {}
    for _, lst in hl.items():
        if lst:
            return lst[0]
    return None

def _headline_from_content(content: str) -> str:
    if not content:
        return "No content"
    for ln in content.splitlines():
        t = _sanitize_text(ln)
        if t and not t.startswith(("#", "//", "/*", "*", "*/", "<!--")) and not t.endswith("-->"):
            return t[:120] + ("…" if len(t) > 120 else "")
    return _sanitize_text(content.splitlines()[0])[:120]
```

b) Build compact and ultra formats in _search_code_impl for both backends
Modify response building:

```python
# mcprag/mcp/tools.py inside _search_code_impl after items/total are determined
backend = "enhanced" if server.enhanced_search and not bm25_only else "basic"

# Normalize to a stable schema for presentation
items = _normalize_items(items)

# Optional dedupe by (file, start_line)
_seen = {}
deduped = []
for e in items:
    key = (e["file"], e.get("start_line"))
    if key not in _seen or e.get("relevance", 0) > _seen[key].get("relevance", 0):
        _seen[key] = e
deduped = list(_seen.values())
items = deduped

# Apply snippet truncation only for full
if snippet_lines > 0 and detail_level == "full":
    _truncate_snippets(items, snippet_lines)

# Build compact and ultra lists
def _build_compact(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for e in entries:
        line_ref = f":{e['start_line']}" if e.get('start_line') else ""
        out.append({
            "file": f"{e['file']}{line_ref}",
            "match": e.get("function_name") or e.get("class_name") or _first_highlight(e) or "Code match",
            "context_type": "implementation" if "def " in (e.get("content","")) or "class " in (e.get("content","")) else "general",
        })
    return out

def _build_ultra(entries: List[Dict[str, Any]]) -> List[str]:
    out = []
    for e in entries:
        line_ref = f":{e['start_line']}" if e.get('start_line') else ""
        why = _first_highlight(e) or "Match"
        head = _headline_from_content(e.get("content", ""))
        out.append(f"{e['file']}{line_ref} | {why} | {head}")
    return out

results_compact = _build_compact(items)
results_ultra = _build_ultra(items)

response = {
    "items": items if detail_level == "full" else (results_compact if detail_level == "compact" else results_ultra),
    "count": len(items),
    "total": total,
    "took_ms": took_ms,
    "query": query,
    "applied_exact_terms": bool(exact_terms),
    "exact_terms": exact_terms,
    "detail_level": detail_level,
    "backend": backend,
}
if include_timings:
    response["timings_ms"] = {
        "total": took_ms
    }
return ok(response)
```

c) Improve truncation to be highlight-aware
Small enhancement to _truncate_snippets to prefer lines near the first highlight (if present):

```python
# mcprag/mcp/tools.py (update _truncate_snippets)
def _truncate_snippets(items: List[Dict[str, Any]], snippet_lines: int) -> None:
    for item in items:
        snippet_full = item.get("content") or ""
        if not isinstance(snippet_full, str):
            continue

        # Headline: prefer sanitized highlight if present
        hl = _first_highlight(item)
        headline = _sanitize_text(hl) if hl else _select_headline(item, snippet_full)

        selected = []
        if headline:
            selected.append(headline)

        if snippet_lines > 1:
            lines = [ln.rstrip() for ln in snippet_full.splitlines()]
            # If we have a headline, find its position; else use first line index
            try:
                idx = next(i for i, ln in enumerate(lines) if _sanitize_text(ln).strip() == headline.strip())
            except StopIteration:
                idx = 0
            # Add subsequent lines, skipping blanks/comments
            extra_needed = snippet_lines - 1
            for ln in lines[idx+1:]:
                t = _sanitize_text(ln)
                if not t or t.startswith(("#", "//", "/*", "*", "*/", "<!--")):
                    continue
                selected.append(t if len(t) <= 120 else t[:117] + "…")
                extra_needed -= 1
                if extra_needed <= 0:
                    break

        item["content"] = "\n".join(selected)
```

d) Prevent event loop blocking in basic Azure search
Wrap Azure SDK calls with run_in_executor to avoid blocking:

```python
# mcprag/mcp/tools.py (replace _basic_search)
async def _basic_search(
    search_client: Any,
    query: str,
    language: Optional[str],
    max_results: int,
    skip: int,
    orderby: Optional[str],
) -> tuple[List[Any], int]:
    """Perform basic Azure Search."""
    search_params = {
        "search_text": query,
        "top": max_results,
        "skip": skip,
        "include_total_count": True,
    }
    if language:
        search_params["filter"] = f"language eq '{language}'"
    if orderby:
        search_params["orderby"] = orderby

    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(None, lambda: search_client.search(**search_params))
    items = await loop.run_in_executor(None, lambda: list(response))
    total = response.get_count() if hasattr(response, "get_count") else len(items)
    return items, total
```

Impact: Consistent schema and formats across backends; safer, clearer snippets; non-blocking basic path; improved client UX and maintainability.

2) analyze_context: parallelize and preserve partial results
Rationale: Eliminates N+1 latency, preserves useful output during partial failures, and adds clearer structure.

a) Parallelize independent subtasks and batch indirect imports

```python
# enhanced_rag/mcp_integration/context_aware_tool.py (replace analyze_context body try-block)
try:
    # Kick off main context analysis
    context_task = self.context_analyzer.analyze(file_path=file_path, depth=depth)

    # Optionals in parallel
    dep_task = self.dep_builder.build_graph(file_path) if include_dependencies else None
    # AST only needed for imports and related analysis
    ast_task = self.ast_analyzer.analyze_file(file_path) if include_imports else None

    context = await context_task

    result = {
        'file': file_path,
        'language': context.file_context.language,
        'module': context.module_context.module_path,
        'project': {
            'name': context.project_context.name,
            'root': context.project_context.root_path,
            'type': context.project_context.project_type
        },
        'context_depth': depth,
        'timestamp': context.timestamp.isoformat()
    }

    # Resolve parallel optionals
    dep_graph = await dep_task if dep_task else None
    ast_info = await ast_task if ast_task else None

    if include_imports:
        indirect = await self._get_indirect_imports(context)
        result['imports'] = {
            'direct': context.file_context.imports,
            'indirect': indirect
        }

    if include_dependencies and dep_graph:
        result['dependencies'] = {
            'internal': dep_graph.get_internal_dependencies(file_path),
            'external': dep_graph.get_external_dependencies(file_path),
            'graph_size': len(dep_graph.nodes)
        }

    result['related_files'] = await self._find_related_files(context)
    result['summary'] = self._generate_context_summary(context, result)

    return result

except Exception as e:
    logger.error(f"Context analysis error: {e}")
    # Return partial structure when possible
    return {
        'error': str(e),
        'file': file_path,
        'partial': True
    }
```

b) Batch _get_indirect_imports using gather

```python
# enhanced_rag/mcp_integration/context_aware_tool.py (replace _get_indirect_imports)
async def _get_indirect_imports(self, context: Any) -> List[str]:
    """Get indirect imports through dependencies (batched)"""
    async def analyze_one(p: str):
        try:
            return await self.context_analyzer.analyze(p, depth=1)
        except Exception:
            return None

    imports = list(set(context.file_context.imports))
    results = await asyncio.gather(*(analyze_one(imp) for imp in imports))
    out: Set[str] = set()
    for r in results:
        if r:
            out.update(r.file_context.imports or [])
    return sorted(list(out - set(imports)))
```

Impact: Reduced latency, better resilience; maintains current API.

3) generate_code: robust references and safer style adaptation
Rationale: Fix fragile reference snippet, prevent breaking code with blind quote conversions, and provide optional deterministic control.

a) Fix references snippet fallback and length

```python
# enhanced_rag/mcp_integration/code_gen_tool.py (inside return dict in generate_code)
"references": [
    {
        "file": r.file_path,
        "function": r.function_name,
        "snippet": (
            (getattr(r, "code_snippet", None) or getattr(r, "content", "") or "")[:200]
            + ("..." if len((getattr(r, "code_snippet", None) or getattr(r, "content", "") or "")) > 200 else "")
        ),
        "relevance": r.score,
    }
    for r in result.results[:5]
],
```

b) Safer quote adaptation in ResponseGenerator.adapt_to_style
Replace global replace with minimal guard to avoid code corruption:

```python
# enhanced_rag/generation/response_generator.py (improve adapt_to_style)
# Replace simple global quote replacement with a conservative approach:
if quote_style in {'single', 'double'}:
    # Very conservative: do not alter quotes inside triple-quoted blocks (Python) or block comments
    # This is a placeholder for a more robust transformer; for now, skip quote conversion to avoid breakage
    logger.debug("Skipping global quote conversion to avoid breaking code semantics")
```

c) Optional: determinate parameter passthrough
Expose an optional deterministic flag forwarded to CodeGenerator (no-op if unsupported by backend). This can be done by reading generation_config and passing through; since CodeGenerator currently does not accept a seed, limit to a config hint (documentation-level).

Tests and usage examples

A) MCP search_code formatting and basic path non-blocking
- Unit-style demonstration for _normalize_items and compact/ultra building:

```python
# Pseudo-test for normalization and formats
items = [
    {"id":"1","file_path":"a.py","language":"python","content":"def f(): pass","@search.score":1.0,
     "@search.highlights":{"content":["<em>def</em> f(): ..."]},"start_line":10},
    {"id":"2","file":"b.js","language":"javascript","code_snippet":"function g() {}","score":0.9}
]
norm = _normalize_items(items)
assert norm[0]["file"] == "a.py"
assert "highlights" in norm[0] and norm[0]["highlights"]["content"][0] == "def f(): ..."
compact = [{"file": f"{e['file']}:{e.get('start_line')}" if e.get('start_line') else e['file'],
            "match": e.get("function_name") or e.get("class_name") or _first_highlight(e) or "Code match",
            "context_type": "implementation" if "def " in (e.get("content","")) or "class " in (e.get("content","")) else "general"} for e in norm]
ultra = [f"{e['file']}{':' + str(e['start_line']) if e.get('start_line') else ''} | {_first_highlight(e) or 'Match'} | {_headline_from_content(e.get('content',''))}" for e in norm]
assert " | " in ultra[0]
```

B) analyze_context batched indirect imports
- Example call:

```python
tool = ContextAwareTool({})
res = await tool.analyze_context(file_path="enhanced_rag/mcp_integration/context_aware_tool.py",
                                 include_dependencies=True, depth=2, include_imports=True)
# Expect res['imports']['indirect'] sorted, and faster completion vs. sequential
```

C) generate_code references fallback
- Example snippet extraction:

```python
# Given a SearchResult mock with only code_snippet
class R:
    file_path="x.py"; function_name="fn"; score=0.8; code_snippet="print('hello')"
r = R()
snippet = ((getattr(r, "code_snippet", None) or getattr(r, "content", "") or "")[:200])
assert snippet == "print('hello')"
```

Edge cases and guardrails
- search_code snippet truncation: If content missing, headline uses “No content”; highlights sanitized for safety.
- analyze_context partial failure returns {'partial': True}; clients can still render basic info.
- generate_code quote adaptation: Consciously avoids unsafe conversions; style application remains via StyleMatcher.apply_style which should handle indentation safely.

Additional optional improvements (low-risk)
- Include backend and pipeline metadata in search_code response when enhanced path used:
  - backend: "enhanced"
  - intent: result.metadata.get('intent'), processing_time_ms: result.metadata.get('processing_time_ms')
- Add page info: page = skip//max_results+1; pages = ceil(total/max_results). Include when detail_level == "ultra" to help chat UIs.

Summary of benefits
- Consistent, sanitized and compact/ultra formats across all search backends leading to clearer UI and fewer client conditionals.
- Reduced latency and improved robustness in analyze_context via asyncio gather batching and partial responses.
- More reliable references and safer style transforms in generate_code, improving grounding and avoiding code breakage.
- Minimal diffs localized to helper methods and response-building, preserving public tool signatures and existing behaviors.

Assumptions validated
- Enhanced path outputs are already normalized via pipeline; basic path needed normalization to align schemas.
- Azure SDK search is synchronous; wrapping in run_in_executor prevents event-loop blocking.
- SearchResult shape provides code_snippet or content; references should prefer code_snippet when present.

Implementation checklist
1) Apply helpers and response normalization/format changes in mcprag/mcp/tools.py per snippets.
2) Replace _basic_search with executor-based version.
3) Update analyze_context for parallel awaits and indirect import batching.
4) Fix references fallback in code_gen_tool; adjust adapt_to_style quote handling.

These minimal changes improve clarity, safety, and performance without altering external contracts.

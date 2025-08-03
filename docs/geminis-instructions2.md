## In-depth, Markdown-formatted review with precise improvements

Below is a refined analysis focused on how results are retrieved, formatted, and presented to users across the search and generation surfaces, with targeted, code-level recommendations.

### Files reviewed
- Search tool and wrappers:
  - [mcprag/mcp.tools.register_tools()](mcprag/mcp/tools.py:24)
  - [mcprag/mcp.tools._search_code_impl()](mcprag/mcp/tools.py:566)
  - [enhanced_rag/mcp_integration/enhanced_search_tool.EnhancedSearchTool.search()](enhanced_rag/mcp_integration/enhanced_search_tool.py:24)
- Retrieval and scoring:
  - [enhanced_rag/retrieval/hybrid_searcher.HybridSearcher.search()](enhanced_rag/retrieval/hybrid_searcher.py:129)
  - [enhanced_rag/pipeline.RAGPipeline.process_query()](enhanced_rag/pipeline.py:226)
- Explanations and models:
  - [enhanced_rag/ranking/result_explainer.ResultExplainer.explain_ranking()](enhanced_rag/ranking/result_explainer.py:21)
  - [enhanced_rag/core/models.SearchResult](enhanced_rag/core/models.py:74)
- Context analysis and code generation:
  - [enhanced_rag/mcp_integration/context_aware_tool.ContextAwareTool.analyze_context()](enhanced_rag/mcp_integration/context_aware_tool.py:30)
  - [enhanced_rag/generation/response_generator.ResponseGenerator.generate_code()](enhanced_rag/generation/response_generator.py:390)
  - [enhanced_rag/mcp_integration/code_gen_tool.CodeGenerationTool.generate_code()](enhanced_rag/mcp_integration/code_gen_tool.py:42)

---

## A) search_code: retrieval, formatting, and presentation

### Strengths
- Tiered detail levels with adaptive formatting are implemented correctly at the MCP layer [mcprag/mcp.tools._search_code_impl()](mcprag/mcp/tools.py:566).
- Proper normalization and deduplication reduce noise [mcprag/mcp.tools._normalize_items()](mcprag/mcp/tools.py:498).
- Enhanced search pipeline provides compact and ultra-compact variants suited to chat UIs [enhanced_rag/mcp_integration/enhanced_search_tool.py:84].

### Problems and UX gaps

1) Double-compaction and data loss risk
- The EnhancedSearchTool returns pre-formatted compact/ultra outputs [enhanced_rag/mcp_integration/enhanced_search_tool.py:119], but the MCP layer may still attempt to normalize or reformat them [mcprag/mcp.tools._search_code_impl()](mcprag/mcp/tools.py:641). If items are strings (ultra), normalization loses metadata (score, repo, language).

2) Compact lacks key fields
- Current compact keys are file, match, context_type [enhanced_rag/mcp_integration/enhanced_search_tool.py:92]. Missing id, rank, score, repo, language, line range. This limits sorting, faceting, and telemetry.

3) Ultra line readability
- Current format is "{file}:{line} | why | head" [enhanced_rag/mcp_integration/enhanced_search_tool.py:101]. Missing rank and score; long paths reduce scan-ability.

4) Highlights are sanitized but not contextualized
- The MCP normalization strips tags and truncates highlights [mcprag/mcp.tools._sanitize_highlights()](mcprag/mcp/tools.py:486), but neither layer carries which field the highlight came from or provides context window/line numbers.

5) Deduplication may collapse distinct matches
- Dedup key (file, start_line) [mcprag/mcp.tools._search_code_impl()](mcprag/mcp/tools.py:644) collapses multiple matches lacking start_line into one entry, potentially hiding valid hits.

6) Exact-term boosting not surfaced
- HybridSearcher implements an exact-term filter pass and boost [enhanced_rag/retrieval/hybrid_searcher.py:181,257], but UI layers don’t indicate which items benefited.

### Precise formatting improvements

Compact dictionary shape (recommended)
- Include rank, id, score, repo, language, and line range for robust UI/telemetry.

Pseudocode: [mcprag/mcp.tools._search_code_impl()](mcprag/mcp/tools.py:659)
- python
  def _build_compact(entries):
      out = []
      for i, e in enumerate(entries, start=1):
          line_ref = f":{e['start_line']}" if e.get('start_line') else ""
          out.append({
              "id": e.get("id"),
              "rank": i,
              "file": f"{e['file']}{line_ref}",
              "repo": e.get("repository"),
              "language": e.get("language"),
              "lines": [e.get("start_line"), e.get("end_line")],
              "score": round(float(e.get("relevance", 0) or 0), 4),
              "match": e.get("function_name") or e.get("class_name") or _first_highlight(e) or "Code match",
              "why": _first_highlight(e),
              "headline": _headline_from_content(e.get("content",""))
          })
      return out

Ultra string line (recommended)
- Add rank, language, and score.

Pseudocode: [mcprag/mcp.tools._search_code_impl()](mcprag/mcp/tools.py:670)
- python
  def _build_ultra(entries):
      out = []
      for i, e in enumerate(entries, start=1):
          line_ref = f":{e['start_line']}" if e.get('start_line') else ""
          why = _first_highlight(e) or "Match"
          head = _headline_from_content(e.get("content", ""))
          out.append(f"#{i} {e['file']}{line_ref} [{e.get('language','?')}] score={e.get('relevance',0):.3f} | {why} || {head}")
      return out

Pass-through of pre-ultra from EnhancedSearchTool
- If items are strings (already ultra), bypass normalization to avoid corruption.

Guard: [mcprag/mcp.tools._search_code_impl()](mcprag/mcp/tools.py:641)
- python
  if detail_level == "ultra" and items and isinstance(items[0], str):
      return ok({...})  # Short-circuit with metadata

Highlight fidelity
- In EnhancedSearchTool compact, include why and why_field when highlights exist; preserve first highlight field and short text.

Patch: [enhanced_rag/mcp_integration/enhanced_search_tool.py:92]
- python
  compact_entry = {...}
  if getattr(r, "highlights", None):
      for field, hls in r.highlights.items():
          if hls:
              compact_entry["why"] = hls[0][:120]
              compact_entry["why_field"] = field
              break

Exact-boost visibility
- Tag items boosted by exact-pass. Set metadata["exact_boost"]=True in HybridSearcher when exact path contributed.

Injection point: [enhanced_rag/retrieval/hybrid_searcher.py:257-268]

Additional response metadata
- Add has_more and next_skip for pagination in MCP response.

Where: [mcprag/mcp.tools._search_code_impl()](mcprag/mcp/tools.py:682)
- python
  response["has_more"] = skip + len(items) < total
  response["next_skip"] = skip + len(items) if response["has_more"] else None

Snippet truncation alignment
- Fuzzy locate the headline within raw lines using difflib before appending extra lines.

Where: [mcprag/mcp.tools._truncate_snippets()](mcprag/mcp/tools.py:769)
- python
  import difflib
  def _find_index(lines, headline):
      norm = lambda s: _sanitize_text(s).lower()
      h = norm(headline)
      for i, ln in enumerate(lines):
          if h in norm(ln) or difflib.SequenceMatcher(None, norm(ln), h).ratio() >= 0.6:
              return i
      return -1
  idx = _find_index(lines, headline)
  if idx < 0: idx = 0

Performance
- Consolidate the two run_in_executor calls into one to fetch items and total together.

Where: [mcprag/mcp.tools._basic_search()](mcprag/mcp/tools.py:742)
- python
  def _exec_search(sc, sp):
      resp = sc.search(**sp)
      items = list(resp)
      total = resp.get_count() if hasattr(resp, "get_count") else len(items)
      return items, total
  items, total = await loop.run_in_executor(None, lambda: _exec_search(search_client, search_params))

---

## B) analyze_context: accuracy and speed

### Issues
- Missing `import asyncio` used by _get_indirect_imports → NameError [enhanced_rag/mcp_integration/context_aware_tool.py:331].
- _get_indirect_imports launches unbounded parallel tasks; can overload analyzer and event loop.
- include_git_history flag unused in response.
- _get_search_paths returns [] for project/all scopes, limiting find_similar_code utility.
- Several placeholders return empty results, reducing usefulness.

### Recommendations

1) Add missing import and throttle parallelism
- Use a semaphore and memoize shallow analyses; cap the number of imports analyzed (e.g., top 20).

Where: [enhanced_rag/mcp_integration/context_aware_tool.py:5,322]
- python
  import asyncio
  ...
  sem = asyncio.Semaphore(8)
  cache = {}
  async def analyze_one(p: str):
      if p in cache: return cache[p]
      async with sem:
          try:
              res = await self.context_analyzer.analyze(p, depth=1)
          except Exception:
              res = None
          cache[p] = res
          return res

2) Surface git history when requested
- After result assembly, attach git_history if include_git_history.

Where: [enhanced_rag/mcp_integration/context_aware_tool.py:96]
- python
  if include_git_history:
      result["git_history"] = await self._get_git_history(file_path)

3) Populate search paths
- Use context.project_context fields if present to build lists for project/all scopes; fallback to scanning within project root with limits.

Where: [enhanced_rag/mcp_integration/context_aware_tool.py:483]
- python
  if scope == 'project' and hasattr(context.project_context, 'files'):
      return context.project_context.files
  if scope == 'all' and hasattr(context.project_context, 'indexed_files'):
      return context.project_context.indexed_files

4) Implement lightweight similarity
- Jaccard over identifier sets from AST, cached per file, to make find_similar_code actionable.

---

## C) generate_code: functional and performance review

### Surfaces
- MCP tool wrapper delegates cleanly to server.code_gen [mcprag/mcp.tools.generate_code()](mcprag/mcp/tools.py:123).
- ResponseGenerator.generate_code is a stub-style generator using language templates [enhanced_rag/generation/response_generator.py:390].
- CodeGenerationTool.generate_code executes a RAG flow, examples, style matching, and template management [enhanced_rag/mcp_integration/code_gen_tool.py:42].

### Issues and improvements

1) Parallelize style analysis with generation
- Analyze style in parallel to generation and merge style_info if successful.

Where: [enhanced_rag/mcp_integration/code_gen_tool.py:110]
- python
  style_task = asyncio.create_task(self.style_matcher.analyze_style(result.results[:5], language))
  generation_task = asyncio.create_task(self.code_generator.generate(generation_context))
  style_info = None
  try:
      style_info = await style_task
  except Exception:
      style_info = None
  generation_result = await generation_task
  if generation_result.get("success") and style_info:
      generation_result["style_info"] = style_info

2) Enrich references with start/end lines when available
- r.start_line / r.end_line exist in SearchResult and should be included.

Where: [enhanced_rag/mcp_integration/code_gen_tool.py:121]
- python
  "references": [
      {
          "file": r.file_path,
          "function": r.function_name,
          "snippet": (getattr(r, "code_snippet", None) or getattr(r, "content", "") or "")[:200] + ("..." if ... else ""),
          "relevance": r.score,
          "start_line": getattr(r, "start_line", None),
          "end_line": getattr(r, "end_line", None),
      }
      for r in result.results[:5]
  ],

3) Pluggable latency budget
- Add time_budget_ms in kwargs; pass through to pipeline and optionally to HybridSearcher fallback via deadline_ms to bound long-running retrieval.

Where: [enhanced_rag/mcp_integration/code_gen_tool.py:88] and [enhanced_rag/retrieval/hybrid_searcher.HybridSearcher.search()](enhanced_rag/retrieval/hybrid_searcher.py:139)

4) Imports extraction precision
- Already filters relative JS/TS imports, but Python extraction should drop __future__ and local relative imports. The regex exists; add a small allowlist/denylist filter after parsing.

---

## D) Defect: compatibility shim import path

- The shim imports `register_tools` from `.mcp.mcp.tools` which is incorrect. Use `.mcp.tools`.

Where: [mcprag/mcp_server_sota_compat.py:33]
- python
  from .mcp.tools import register_tools

---

## Quick-win implementation map

- mcprag/mcp/tools.py
  - Guard pass-through for ultra string items.
  - Enhance compact/ultra builders with rank/id/score/repo/language/lines.
  - Add has_more/next_skip.
  - Fuzzy alignment in _truncate_snippets.
  - Single executor in _basic_search.

- enhanced_rag/mcp_integration/enhanced_search_tool.py
  - Enrich results_compact with id/score/repo/language/lines and why/why_field.

- enhanced_rag/retrieval/hybrid_searcher.py
  - Mark exact_boost in metadata where applied.

- enhanced_rag/mcp_integration/context_aware_tool.py
  - Add asyncio import.
  - Throttle and cache _get_indirect_imports.
  - Attach git_history.
  - Populate project/all scopes.

- enhanced_rag/mcp_integration/code_gen_tool.py
  - Parallelize style analysis and generation; attach style_info.
  - Enrich references with start/end lines.
  - Add optional time_budget_ms.

- mcprag/mcp_server_sota_compat.py
  - Fix register_tools import path.

These targeted changes enhance clarity and usability of search results, improve performance predictability, and increase the practical value of analyze_context and generate_code outputs without requiring structural rewrites.

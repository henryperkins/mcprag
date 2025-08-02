Stage 2 implementation guide: feedback/learning + admin/index/github + cache controls for [`mcp_server_sota.py`](mcp_server_sota.py)

Objective
Add the remaining integrations in a secure, Claude-Code-friendly way:
- Feedback & learning tools (safe writes)
- Admin/index/github/document tools (guarded by admin mode)
- Cache management

Guiding principles
- Respect security: Gate administrative and side-effectful operations behind MCP_ADMIN_MODE.
- Keep enhanced_rag optional: If modules aren’t available, return a structured unavailable error instead of raising.
- SDK-friendly: All tools return JSON-serializable dicts: {"ok": true/false, "data": ..., "error": "...", "code": "..."}.
- Claude Code alignment: Tools are discoverable and must be whitelisted via --allowedTools; provide concise input shapes and structured outputs for non-interactive runs.
- Idempotency where possible: status queries and dry-run modes.

Prerequisites added in Stage 1
- Helper functions: _is_admin(), _ok(data), _err(msg, code="error")
- Existing enhanced tool instances when ENHANCED_RAG_SUPPORT: enhanced_search_tool, code_gen_tool, context_aware_tool
- Optional: timing helper _Timer

Additions in Stage 2

A) Feedback and learning tools
Intended modules:
- enhanced_rag/learning/feedback_collector.py
- enhanced_rag/learning/usage_analyzer.py
- enhanced_rag/learning/model_updater.py

1) Guarded imports near other optional imports
Add after ENHANCED_RAG_SUPPORT try-blocks:

```python
try:
    from enhanced_rag.learning.feedback_collector import FeedbackCollector  # type: ignore
    from enhanced_rag.learning.usage_analyzer import UsageAnalyzer  # type: ignore
    from enhanced_rag.learning.model_updater import ModelUpdater  # type: ignore
    LEARNING_SUPPORT = True
except Exception:
    FeedbackCollector = None
    UsageAnalyzer = None
    ModelUpdater = None
    LEARNING_SUPPORT = False
```

2) Feedback storage configuration
Decide on a safe, local storage strategy if FeedbackCollector expects a path. Add defaults:

```python
FEEDBACK_DIR = os.getenv("MCP_FEEDBACK_DIR", ".mcp_feedback")
Path(FEEDBACK_DIR).mkdir(parents=True, exist_ok=True)
```

3) submit_feedback tool
- Purpose: Store relevance/quality ratings with optional notes/context (safe write).
- Available if LEARNING_SUPPORT; otherwise return an unavailable error.
- No admin required.

Implementation:

```python
@mcp.tool()
async def submit_feedback(
    target_id: str,
    kind: str,  # "search_result" | "code_gen"
    rating: int,  # e.g., 1-5
    notes: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Store user feedback for learning loops.
    """
    if not LEARNING_SUPPORT or not FeedbackCollector:
        return _err("enhanced_rag_learning_unavailable", code="enhanced_unavailable")

    try:
        collector = FeedbackCollector(storage_dir=FEEDBACK_DIR)
        record = collector.store(
            target_id=target_id,
            kind=kind,
            rating=rating,
            notes=notes,
            context=context or {}
        )
        return _ok({"stored": True, "record": record})
    except Exception as e:
        return _err(str(e))
```

Notes:
- If FeedbackCollector has different signature, adapt keys accordingly.
- Ensure rating validation if needed (e.g., 1..5). If invalid, return _err("invalid_rating", code="validation").

4) usage_report tool
- Purpose: Summarize recent usage stats (counts, latencies, top queries, tool counts).
- Safe read; no admin required.

```python
@mcp.tool()
async def usage_report(
    range: str = "7d"  # e.g., "24h", "7d", "30d"
) -> Dict[str, Any]:
    """
    Summarize usage analytics from stored feedback/usage data.
    """
    if not LEARNING_SUPPORT or not UsageAnalyzer:
        return _err("enhanced_rag_learning_unavailable", code="enhanced_unavailable")

    try:
        analyzer = UsageAnalyzer(storage_dir=FEEDBACK_DIR)
        summary = analyzer.summarize(range=range)
        return _ok({"range": range, "summary": summary})
    except Exception as e:
        return _err(str(e))
```

5) update_learning_model tool
- Purpose: Trigger model updates (ranking/weights). Keep safe: default dry-run; require admin for actual updates.

```python
@mcp.tool()
async def update_learning_model(
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Update ranking/learning artifacts. Requires admin when dry_run is False.
    """
    if not LEARNING_SUPPORT or not ModelUpdater:
        return _err("enhanced_rag_learning_unavailable", code="enhanced_unavailable")

    if not dry_run and not _is_admin():
        return _err("admin_required", code="admin_required")

    try:
        updater = ModelUpdater(storage_dir=FEEDBACK_DIR)
        result = updater.update(dry_run=dry_run)
        return _ok({"dry_run": dry_run, "result": result})
    except Exception as e:
        return _err(str(e))
```

B) Admin: Azure index management and document operations
Modules:
- enhanced_rag/azure_integration/index_operations.py
- enhanced_rag/azure_integration/indexer_integration.py
- enhanced_rag/azure_integration/document_operations.py
- enhanced_rag/azure_integration/enhanced_index_builder.py (optional)

1) Guarded imports

```python
try:
    from enhanced_rag.azure_integration.index_operations import IndexOperations  # type: ignore
    from enhanced_rag.azure_integration.indexer_integration import IndexerIntegration  # type: ignore
    from enhanced_rag.azure_integration.document_operations import DocumentOperations  # type: ignore
    AZURE_ADMIN_SUPPORT = True
except Exception:
    IndexOperations = None
    IndexerIntegration = None
    DocumentOperations = None
    AZURE_ADMIN_SUPPORT = False
```

2) Common admin guard utility (already available: _is_admin)
Pattern for each admin tool:
- If not _is_admin(): return _err("admin_required", code="admin_required")
- If not AZURE_ADMIN_SUPPORT: return _err("azure_admin_unavailable", code="enhanced_unavailable")

3) index_status tool
- Purpose: Return index/document counts, indexer status if accessible.

```python
@mcp.tool()
async def index_status() -> Dict[str, Any]:
    if not _is_admin():
        return _err("admin_required", code="admin_required")
    if not AZURE_ADMIN_SUPPORT or not IndexOperations:
        return _err("azure_admin_unavailable", code="enhanced_unavailable")
    try:
        ops = IndexOperations(
            endpoint=os.getenv("ACS_ENDPOINT"),
            key=os.getenv("ACS_ADMIN_KEY"),
            index_name=os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota")
        )
        status = ops.get_status()  # adapt to actual API; else compute minimal: doc count, fields
        # Fallback if get_status not available:
        if not status:
            status = {
                "index_name": os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota"),
                "document_count": server.search_client.get_document_count()
            }
        return _ok(status)
    except Exception as e:
        return _err(str(e))
```

4) index_create_or_update tool
- Purpose: Create/update index schema; optional profile param; admin-only.

```python
@mcp.tool()
async def index_create_or_update(profile: Optional[str] = None) -> Dict[str, Any]:
    if not _is_admin():
        return _err("admin_required", code="admin_required")
    if not AZURE_ADMIN_SUPPORT or not IndexOperations:
        return _err("azure_admin_unavailable", code="enhanced_unavailable")
    try:
        ops = IndexOperations(
            endpoint=os.getenv("ACS_ENDPOINT"),
            key=os.getenv("ACS_ADMIN_KEY"),
            index_name=os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota")
        )
        result = ops.create_or_update(profile=profile)  # adapt as needed
        return _ok({"profile": profile, "result": result})
    except Exception as e:
        return _err(str(e))
```

5) index_rebuild tool
- Purpose: Trigger indexer re-run or full rebuild; admin-only.

```python
@mcp.tool()
async def index_rebuild(repository: Optional[str] = None) -> Dict[str, Any]:
    if not _is_admin():
        return _err("admin_required", code="admin_required")
    if not AZURE_ADMIN_SUPPORT or not IndexerIntegration:
        return _err("azure_admin_unavailable", code="enhanced_unavailable")
    try:
        idx = IndexerIntegration(
            endpoint=os.getenv("ACS_ENDPOINT"),
            key=os.getenv("ACS_ADMIN_KEY"),
            index_name=os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota")
        )
        result = idx.rebuild(repository=repository)  # adapt to actual API
        return _ok({"repository": repository, "result": result})
    except Exception as e:
        return _err(str(e))
```

6) document_upsert tool
- Purpose: Insert/update a single document; admin-only.

```python
@mcp.tool()
async def document_upsert(document: Dict[str, Any]) -> Dict[str, Any]:
    if not _is_admin():
        return _err("admin_required", code="admin_required")
    if not AZURE_ADMIN_SUPPORT or not DocumentOperations:
        return _err("azure_admin_unavailable", code="enhanced_unavailable")
    try:
        docs = DocumentOperations(
            endpoint=os.getenv("ACS_ENDPOINT"),
            key=os.getenv("ACS_ADMIN_KEY"),
            index_name=os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota")
        )
        result = docs.upsert(document)  # adapt to actual API
        return _ok({"upserted": True, "result": result})
    except Exception as e:
        return _err(str(e))
```

7) document_delete tool
- Purpose: Delete document by id; admin-only.

```python
@mcp.tool()
async def document_delete(doc_id: str) -> Dict[str, Any]:
    if not _is_admin():
        return _err("admin_required", code="admin_required")
    if not AZURE_ADMIN_SUPPORT or not DocumentOperations:
        return _err("azure_admin_unavailable", code="enhanced_unavailable")
    try:
        docs = DocumentOperations(
            endpoint=os.getenv("ACS_ENDPOINT"),
            key=os.getenv("ACS_ADMIN_KEY"),
            index_name=os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota")
        )
        result = docs.delete(doc_id)  # adapt to actual API
        return _ok({"deleted": True, "doc_id": doc_id, "result": result})
    except Exception as e:
        return _err(str(e))
```

C) Admin: GitHub integration (remote indexing)
Modules:
- enhanced_rag/github_integration/api_client.py
- enhanced_rag/github_integration/remote_indexer.py

1) Guarded imports

```python
try:
    from enhanced_rag.github_integration.api_client import GitHubClient  # type: ignore
    from enhanced_rag.github_integration.remote_indexer import RemoteIndexer  # type: ignore
    GITHUB_SUPPORT = True
except Exception:
    GitHubClient = None
    RemoteIndexer = None
    GITHUB_SUPPORT = False
```

2) Environment variables
- GITHUB_TOKEN likely required; read from env but do not log.
- You may accept org/repo identifiers.

3) github_list_repos tool
- Admin-only due to external API usage risk.

```python
@mcp.tool()
async def github_list_repos(org: str, max_repos: int = 50) -> Dict[str, Any]:
    if not _is_admin():
        return _err("admin_required", code="admin_required")
    if not GITHUB_SUPPORT or not GitHubClient:
        return _err("github_integration_unavailable", code="enhanced_unavailable")
    try:
        token = os.getenv("GITHUB_TOKEN")
        client = GitHubClient(token=token)
        repos = client.list_repos(org=org, max_repos=max_repos)  # adapt to API
        return _ok({"org": org, "count": len(repos), "repos": repos})
    except Exception as e:
        return _err(str(e))
```

4) github_index_repo tool
- Admin-only; triggers remote indexing for org/repo.

```python
@mcp.tool()
async def github_index_repo(
    repo: str,  # "org/name"
    branch: Optional[str] = None,
    mode: str = "full"  # "full" | "incremental"
) -> Dict[str, Any]:
    if not _is_admin():
        return _err("admin_required", code="admin_required")
    if not GITHUB_SUPPORT or not RemoteIndexer:
        return _err("github_integration_unavailable", code="enhanced_unavailable")
    try:
        token = os.getenv("GITHUB_TOKEN")
        indexer = RemoteIndexer(
            endpoint=os.getenv("ACS_ENDPOINT"),
            key=os.getenv("ACS_ADMIN_KEY"),
            index_name=os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota"),
            github_token=token
        )
        result = indexer.index_repository(repo=repo, branch=branch, mode=mode)  # adapt to API
        return _ok({"repo": repo, "branch": branch, "mode": mode, "result": result})
    except Exception as e:
        return _err(str(e))
```

5) github_index_status tool
- Admin-only; check progress/status of last index run for a repo.

```python
@mcp.tool()
async def github_index_status(repo: str) -> Dict[str, Any]:
    if not _is_admin():
        return _err("admin_required", code="admin_required")
    if not GITHUB_SUPPORT or not RemoteIndexer:
        return _err("github_integration_unavailable", code="enhanced_unavailable")
    try:
        token = os.getenv("GITHUB_TOKEN")
        indexer = RemoteIndexer(
            endpoint=os.getenv("ACS_ENDPOINT"),
            key=os.getenv("ACS_ADMIN_KEY"),
            index_name=os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota"),
            github_token=token
        )
        status = indexer.status(repo=repo)  # adapt to API
        return _ok({"repo": repo, "status": status})
    except Exception as e:
        return _err(str(e))
```

D) Cache management tools
Modules:
- enhanced_rag/utils/cache_manager.py (optional; Stage 1 used internal caches)

1) Guarded import

```python
try:
    from enhanced_rag.utils.cache_manager import CacheManager  # type: ignore
    RAG_CACHE_SUPPORT = True
except Exception:
    CacheManager = None
    RAG_CACHE_SUPPORT = False
```

2) cache_stats tool
- Report both server-level caches and RAG cache if present.

```python
@mcp.tool()
async def cache_stats() -> Dict[str, Any]:
    try:
        rag_cache = None
        if ENHANCED_RAG_SUPPORT and RAG_CACHE_SUPPORT and CacheManager:
            try:
                rag_cache = CacheManager.get_stats()  # adapt: might be instance method
            except Exception:
                rag_cache = None
        data = {
            "server_query_cache": len(server._query_cache),
            "repo_cache": len(server._repo_cache),
            "rag_cache": rag_cache
        }
        return _ok(data)
    except Exception as e:
        return _err(str(e))
```

3) cache_clear tool
- Scope: "all" | "queries" | "repos" | "rag"
- Non-admin safe; but if you prefer stricter behavior, guard with admin.

```python
@mcp.tool()
async def cache_clear(scope: str = "all") -> Dict[str, Any]:
    try:
        cleared = []
        if scope in ("all", "queries"):
            server._query_cache.clear()
            cleared.append("queries")
        if scope in ("all", "repos"):
            server._repo_cache.clear()
            cleared.append("repos")
        if scope in ("all", "rag") and ENHANCED_RAG_SUPPORT and RAG_CACHE_SUPPORT and CacheManager:
            try:
                CacheManager.clear()  # adapt to actual API
                cleared.append("rag")
            except Exception:
                pass
        remaining = {
            "server_query_cache": len(server._query_cache),
            "repo_cache": len(server._repo_cache),
        }
        return _ok({"cleared": cleared, "remaining": remaining})
    except Exception as e:
        return _err(str(e))
```

Placement and ordering
- Keep related imports near existing optional imports.
- Place tools in the “Tool Implementations” section.
- Admin tools can be grouped under a comment banner “Admin/Index/GitHub tools (ADMIN_MODE required)”.
- Cache tools can be near statistics and runtime_diagnostics for discoverability.

Testing with Claude Code (MCP)
- Update or verify mcp-servers.json to include this server; ensure you can start it via stdio.
- Allow tools during SDK runs:
  - Example: claude -p "..." --mcp-config mcp-servers.json --allowedTools "mcp__azure-code-search-enhanced__search_code_raw,mcp__azure-code-search-enhanced__explain_ranking"
- Admin enablement:
  - MCP_ADMIN_MODE=1 claude -p "..." --mcp-config mcp-servers.json --allowedTools "mcp__azure-code-search-enhanced__index_status,mcp__azure-code-search-enhanced__github_list_repos"
- Validate unavailable paths:
  - Uninstall or rename enhanced_rag to simulate missing modules; tools should return {"ok": false, "code": "enhanced_unavailable"} where expected.

Operational notes and safeguards
- Never log secrets (ACS keys, GitHub tokens).
- Return clear errors for misconfiguration:
  - Missing ACS credentials: reuse existing server init error.
  - Missing GITHUB_TOKEN: return _err("missing_github_token", code="config").
- Consider rate limiting for admin tools if they trigger expensive operations.
- For long-running index operations, return an operation ID and provide a status check tool (github_index_status) instead of blocking.

Reference to locations
- Base file to edit: [`mcp_server_sota.py`](mcp_server_sota.py)
- Enhanced RAG entry points already used in Stage 1:
  - [`EnhancedSearchTool.search()`](enhanced_rag/mcp_integration/enhanced_search_tool.py:1)
  - Learning modules: [`feedback_collector`](enhanced_rag/learning/feedback_collector.py:1), [`usage_analyzer`](enhanced_rag/learning/usage_analyzer.py:1), [`model_updater`](enhanced_rag/learning/model_updater.py:1)
  - Azure admin modules: [`index_operations`](enhanced_rag/azure_integration/index_operations.py:1), [`indexer_integration`](enhanced_rag/azure_integration/indexer_integration.py:1), [`document_operations`](enhanced_rag/azure_integration/document_operations.py:1)
  - GitHub modules: [`api_client`](enhanced_rag/github_integration/api_client.py:1), [`remote_indexer`](enhanced_rag/github_integration/remote_indexer.py:1)
  - Cache manager: [`cache_manager`](enhanced_rag/utils/cache_manager.py:1)

Completion
Following this guide will add:
- Feedback/learning: submit_feedback, usage_report, update_learning_model
- Admin/index/github/document: index_status, index_create_or_update, index_rebuild, document_upsert, document_delete, github_list_repos, github_index_repo, github_index_status
- Cache controls: cache_stats, cache_clear
All with proper gating, graceful fallbacks, and JSON responses compatible with Claude Code workflows.
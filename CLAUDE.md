# CLAUDE.md

This file guides Claude Code and subagents working in this repository. It defines coding standards, protected areas, workflows, and expectations for planning, testing, and documentation.

## Project overview
**MCP RAG (Model Context Protocol - Retrieval Augmented Generation) Server**
- Purpose: Advanced code search and retrieval system with Azure AI Search integration
- Architecture: MCP server providing semantic code search with adaptive ranking
- Stack: Python 3.12+, FastMCP, Azure AI Search, Azure OpenAI
- Entry points:
  - Server: `mcprag/server.py` - Main MCP server implementation
  - CLI: `mcprag/__main__.py` - Command-line interface
  - Tools: `mcprag/mcp/tools/` - MCP tool implementations
- Build/Run:
  - Install: `pip install -e .`
  - Run server: `python -m mcprag` or via MCP client
  - Dev mode: Set `MCP_LOG_LEVEL=DEBUG`
- Code quality:
  - Type checking: mypy (partial coverage)
  - Tests: `pytest tests/` (limited coverage)
  - Async: Uses asyncio throughout

## System Architecture

### Core Components
1. **MCP Server** (`mcprag/server.py`)
   - FastMCP framework for tool registration
   - Transport modes: stdio, SSE, streamable-http
   - Async component lifecycle management
   - Tool categories: search, generation, analysis, admin, cache, feedback

2. **RAG Pipeline** (`enhanced_rag/pipeline.py`)
   - Multi-stage retrieval (vector, keyword, semantic, pattern, dependency)
   - 8-factor ranking system with adaptive learning
   - Context extraction and query enhancement
   - Response generation with explanations

3. **Ranking Subsystem** (`enhanced_rag/ranking/`)
   - `contextual_ranker_improved.py`: Multi-factor scoring (text relevance, semantic similarity, context overlap, imports, proximity, recency, quality, patterns)
   - `adaptive_ranker.py`: Learning from user feedback with weight adjustments
   - `ranking_monitor.py`: Performance tracking and metrics
   - `pattern_matcher_integration.py`: Code pattern detection
   - `result_explainer.py`: Human-readable explanations

4. **Azure Integration** (`enhanced_rag/azure_integration/`)
   - REST API client with retry logic (API version: 2025-08-01-preview)
   - Index, document, and indexer management
   - Embedding generation with caching
   - Repository processing and file chunking
   - **Consolidated modules** (as of 2025-08-12):
     - `processing.py`: Single source of truth for file processing, language detection, repository traversal, and validation
     - `lib/index_utils.py`: Shared index lifecycle helpers (ensure_index_exists, recreate_index, schema_differs)
     - `lib/search_models.py`: Unified search model builders and index definitions

### Data Flow
```
MCP Client Request → FastMCP Router → Tool Implementation → 
RAG Pipeline → Context Analysis → Query Enhancement → 
Multi-Stage Retrieval → Ranking → Response Generation → 
MCP Client Response
```

### External Services
- **Azure AI Search**: Primary data storage and retrieval
- **Azure OpenAI**: Embedding generation (text-embedding-3-large)
- **GitHub API**: Repository indexing (optional)

## Protected paths and rules
Never write to or delete the following without explicit human approval:
- `.env`, `.env.*`, `.git/`, `.github/`
- Configuration: `mcprag/config.py` (core loading logic), `.mcp.json`
- Azure schemas: `azure_search_index_schema.json`
- Secrets/keys/certs directories: `secrets/`, `keys/`, `certs/`

Additional rules:
- Always use absolute file paths for Edit/Write.
- Large logs and artifacts must be written under `.claude/state/` and referenced by path, not inlined.
- Never log API keys or credentials, even partially

## Configuration

### Environment Variables
```bash
# Azure Search (Required)
ACS_ENDPOINT=https://<name>.search.windows.net
ACS_ADMIN_KEY=<admin-key>
ACS_INDEX_NAME=codebase-mcp-sota  # default
ACS_API_VERSION=2025-08-01-preview  # optional, override default API version
AZURE_RESOURCE_GROUP=<your-resource-group>
# Optional: explicitly set if not inferrable from ACS_ENDPOINT
AZURE_SEARCH_SERVICE_NAME=<your-search-service-name>

# Azure OpenAI (Optional - for embeddings)
AZURE_OPENAI_ENDPOINT=https://<name>.openai.azure.com
AZURE_OPENAI_KEY=<api-key>
AZURE_OPENAI_DEPLOYMENT=text-embedding-3-large

# MCP Settings
MCP_ADMIN_MODE=true  # Enable destructive operations
MCP_LOG_LEVEL=INFO   # DEBUG, INFO, WARNING, ERROR
MCP_CACHE_TTL_SECONDS=60
MCP_CACHE_MAX_ENTRIES=500
MCP_FEEDBACK_DIR=.mcp_feedback
MCP_ALLOW_EXTERNAL_ROOTS=false  # Allow indexing from excluded directories

# Performance
MCP_DEBUG_TIMINGS=false  # Enable timing logs
MCP_INDEX_DEFAULT_EXCLUDES=true  # Use default exclude patterns
MCP_RESPECT_GITIGNORE=true  # Respect .gitignore files
```

### Key Configuration Files
- `.mcp.json`: MCP server configuration
- `azure_search_index_schema.json`: Index schema definition
- `enhanced_rag/core/config.py`: RAG pipeline configuration
- `mcprag/config.py`: Server configuration loader

## MCP Tools Available

### Search Tools
- `search_code`: Enhanced code search with RAG pipeline
  - Parameters: query, intent, language, repository, max_results (10), include_dependencies, skip, orderby, highlight_code, bm25_only, exact_terms, disable_cache, include_timings, dependency_mode ("auto"), detail_level ("full"/"compact"/"ultra"), snippet_lines (0)
  - detail_level controls output format: "full" (rich objects), "compact" (minimal dict), "ultra" (single-line strings)
  - snippet_lines: If >0, applies smart truncation using highlights or first meaningful line
- `search_code_raw`: Raw search results without formatting
  - Simplified wrapper around search_code returning unformatted results
- `search_microsoft_docs`: Microsoft Learn documentation search
  - Parameters: query, max_results (10)

### Generation Tools
- `generate_code`: Code generation using RAG context
  - Parameters: description, language ("python"), context_file, style_guide, include_tests, workspace_root
  - Requires: code_gen component

### Analysis Tools  
- `analyze_context`: File context analysis with dependency tracking
  - Parameters: file_path, include_dependencies (true), depth (2), include_imports (true), include_git_history (false)
  - Requires: context_aware component
- `explain_ranking`: Explain ranking factors for search results
  - Parameters: query, mode ("enhanced"), max_results (10), intent, language, repository
- `preview_query_processing`: Show intent classification and query enhancements
  - Parameters: query, intent, language, repository

### Admin Tools (require MCP_ADMIN_MODE=true)
- `index_rebuild`: Rebuild search indexer (requires confirmation)
  - Parameters: repository, confirm (false)
  - Triggers full crawl and may overwrite existing data
- `github_index_repo`: Index GitHub repository (requires confirmation)
  - Parameters: repo, branch, mode ("full"), confirm (false)
- `manage_index`: Index lifecycle management
  - Actions: create, ensure, recreate, delete, optimize, validate, list
  - Parameters: action, index_definition, index_name, update_if_different (true), backup_documents (false)
- `manage_documents`: Document operations in Azure Search
  - Actions: upload, delete, cleanup, count, verify
  - Parameters: action, index_name, documents, document_keys, filter_query, batch_size (1000), merge (false), days_old, date_field, dry_run (false)
- `manage_indexer`: Indexer operations
  - Actions: list, status, run, reset, create, delete
  - Parameters: action, indexer_name, datasource_name, target_index, schedule, parameters, wait (false)
  - Note: Status responses are automatically truncated to prevent token limit issues

### Azure Management Tools (require MCP_ADMIN_MODE=true)
- `create_datasource`: Create or update Azure Search data source
  - Parameters: name, datasource_type, connection_info, container, credentials, description, refresh, test_connection (true), update_if_exists (true)
- `create_skillset`: Create or update cognitive skillset
  - Parameters: name, skills, cognitive_services_key, description, knowledge_store, encryption_key, update_if_exists (true)
- `index_status`: Get current index status (no admin required)
  - Returns: index_name, fields count, documents count, storage_size_mb, vector_search enabled, semantic_search enabled
- `validate_index_schema`: Validate index schema against expected
  - Parameters: expected_schema (optional)
- `index_repository`: Index local repository via CLI automation
  - Parameters: repo_path ("."), repo_name ("mcprag"), patterns (optional file patterns)
- `index_changed_files`: Index specific changed files
  - Parameters: files (required list), repo_name ("mcprag")
- `backup_index_schema`: Backup current index schema to file
  - Parameters: output_file ("schema_backup.json")
- `clear_repository_documents`: Clear documents from specific repository
  - Parameters: repository_filter (required, e.g., "repository eq 'old-repo'")
- `rebuild_index`: Complete index drop and rebuild (requires confirmation)
  - Parameters: confirm (false)
  - ⚠️ CAUTION: Deletes all data in the index
- `health_check`: Check health of search components (no admin required)
  - Returns component availability status

### Cache Tools
- `cache_stats`: Get cache statistics
  - Returns cache hit rates, sizes, and entry counts
- `cache_clear`: Clear cache entries
  - Parameters: scope ("all"/"search"/"embeddings"/"results"), pattern (optional)
  - Pattern parameter used when clearing specific cache keys

### Feedback Tools
- `submit_feedback`: Submit user feedback
  - Parameters: target_id, kind ("positive"/"negative"/"neutral"/"bug"/"feature"/"other"), rating (1-5), notes, context
- `track_search_click`: Track user click on search result
  - Parameters: query_id, doc_id, rank, context
- `track_search_outcome`: Track search outcome
  - Parameters: query_id, outcome, score, context

### Service Management Tools (require Azure CLI authentication)
- `configure_semantic_search`: Enable/disable semantic search at service level
  - Parameters: action ("status"/"enable"/"disable"), plan ("free"/"standard"), resource_group, search_service_name
  - Requires: Azure CLI authenticated with Owner/Contributor permissions
  - Note: Free plan allows up to 1000 queries/month, Standard is pay-per-query
- `get_service_info`: Get detailed Azure Search service information
  - Parameters: resource_group, search_service_name
  - Returns: Service tier, capacity, features, semantic search status

## Tool Component Dependencies

The MCP tools require specific server components to be initialized:

### Component Requirements by Tool

**Note**: Components are checked once with `check_component()`; subsequent uses can assert non-None for type checking.

| Tool | Required Component | Fallback Behavior |
|------|-------------------|-------------------|
| search_code | enhanced_search | Returns error if unavailable |
| search_code_raw | enhanced_search | Returns error if unavailable |
| search_microsoft_docs | None (standalone) | Always available |
| generate_code | code_gen | Returns error if unavailable |
| analyze_context | context_aware | Returns error if unavailable |
| explain_ranking | enhanced_search | Returns error if unavailable |
| preview_query_processing | intent_classifier, query_rewriter | Partial results if components missing |
| index_rebuild | indexer_automation | Returns error if unavailable |
| github_index_repo | remote_indexer | Returns error if unavailable |
| manage_index | index_automation, rest_ops | Returns error if unavailable |
| manage_documents | data_automation, rest_ops | Returns error if unavailable |
| manage_indexer | rest_ops, indexer_automation | Returns error if unavailable |
| create_datasource | rest_ops | Returns error if unavailable |
| create_skillset | rest_ops | Returns error if unavailable |
| index_status | index_automation | Returns error if unavailable |
| validate_index_schema | index_automation | Returns error if unavailable |
| health_check | None (checks all) | Always available |
| cache_stats | cache_manager | Returns error if unavailable |
| cache_clear | cache_manager | Returns error if unavailable |
| submit_feedback | feedback_collector | Returns error if unavailable |
| track_search_click | enhanced_search or feedback_collector | Tries both backends |
| track_search_outcome | enhanced_search or feedback_collector | Tries both backends |

### Admin Mode Requirements
Tools requiring `MCP_ADMIN_MODE=true` environment variable:
- All tools under "Admin Tools" category
- All tools under "Azure Management Tools" category except `health_check` and `index_status`
- Document modification operations in `manage_documents` (upload, delete, cleanup)
- Index modification operations in `manage_index` (create, recreate, delete)
- Indexer modification operations in `manage_indexer` (run, reset, create, delete)

### Confirmation Requirements
Tools requiring explicit `confirm=true` parameter:
- `index_rebuild` - Full indexer rebuild
- `github_index_repo` - GitHub repository indexing
- `rebuild_index` - Complete index drop and rebuild

## Coding standards
- Language: Python 3.12+ with type hints
- Style:
  - Prefer small, pure functions; clear names; single responsibility.
  - Avoid duplicated code; extract shared utilities. Check for existing helpers in:
    - `enhanced_rag/azure_integration/lib/` - Index and search model utilities
    - `enhanced_rag/azure_integration/processing.py` - File processing and validation
    - `mcprag/utils/` - Response helpers and general utilities
    - Tool base modules before implementing new functions
  - Handle errors explicitly; avoid silent failures.
  - Validate inputs; sanitize outputs for security.
  - Use dataclasses for structured data
- Imports:
  - Use explicit, minimal imports; avoid unused symbols.
  - Prefer absolute imports for cross-module references
  - Use TYPE_CHECKING for circular import prevention
  - Import shared utilities from their canonical locations rather than reimplementing
  - Never import deprecated or legacy functions if a canonical version exists
  - Module-level constants (like `DEFAULT_EXCLUDE_DIRS`) should be imported, not redefined
- Async:
  - Use `async/await` throughout; handle rejections
  - Add timeouts for all external calls (default 30s)
  - Properly cleanup async resources in finally blocks
- Performance:
  - Avoid N+1 patterns; batch Azure Search operations
  - Cache embeddings with SHA256 keys
  - Use streaming for large document sets
  - File processing limits configured via environment (e.g., MCP_MAX_INDEX_FILES)

## Testing standards
- Add or update tests for new behavior and bug fixes.
- Include negative cases and edge cases.
- Keep tests deterministic; avoid sleeping; use fakes/mocks where appropriate.
- When refactoring to remove duplication, ensure all call sites are updated and tested.
- Minimal acceptance for change:
  - Tests pass locally for impacted area(s).
  - No flakiness introduced.

### Universal MCP Tool Testing Framework
The project includes a comprehensive universal testing framework for all 31 MCP tools located in `.claude/state/`:

- **`universal_mcp_tool_evaluator.py`**: Universal test framework supporting all MCP tool categories with automatic discovery, comprehensive test execution, and performance monitoring
- **`mcp_tool_coverage_report.py`**: Tool coverage analyzer that discovers tools via regex patterns, reports coverage statistics, and generates test templates for untested tools
- **`test_templates/`**: Directory containing generated test templates for expanding coverage to untested tools

#### Testing Capabilities
1. **Tool Discovery**: Automatic detection of all MCP tools via `@mcp.tool()` decorators
2. **Coverage Analysis**: Real-time reporting of tested vs untested tools (currently 16.1% coverage - 5/31 tools)
3. **Test Categories**:
   - Search tools (search_code, search_code_raw, search_microsoft_docs)
   - Generation tools (generate_code)
   - Analysis tools (analyze_context, explain_ranking, preview_query_processing)
   - Admin tools (index_rebuild, github_index_repo, manage_index, manage_documents, manage_indexer)
   - Azure management tools (create_datasource, create_skillset, index_status, validate_index_schema, etc.)
   - Cache tools (cache_stats, cache_clear)
   - Feedback tools (submit_feedback, track_search_click, track_search_outcome)
   - Service management tools (configure_semantic_search, get_service_info)

#### Running Tests
```bash
# Run universal test framework for all tools
python .claude/state/universal_mcp_tool_evaluator.py

# Generate coverage report and test templates
python .claude/state/mcp_tool_coverage_report.py

# Run specific tool test suites
python .claude/state/universal_mcp_tool_evaluator.py --tool search_code --suite search
```

#### Test Result Format
- Each test produces a `ToolTestResult` with:
  - Tool name, test name, status (passed/failed/error/skipped)
  - Error messages, performance metrics
  - Response validation results
  - Business value metrics (optional)

#### Known Issues to Monitor
- Repository filtering currently broken (P1 issue) 
- Enhanced mode relevance scores very low (0.016 vs BM25 scores >1.0)
- 26 tools remain untested (83.9% of tools lack test coverage)
- Cross-tool integration tests not yet implemented

### Recent Improvements (2025-08-12)
- **Code duplication reduced**: From 4% to under 1% through consolidation
- **Shared utilities created**: 14 new utility functions in `lib/` subdirectory
- **API version updated**: Now using 2025-08-01-preview (latest)
- **Validation consolidated**: Repository name/path validation centralized in `processing.py`
- **Total LOC removed**: ~360 lines of duplicated code eliminated

## Documentation standards
- Update README and relevant docs when behavior changes.
- Keep code comments concise and accurate.
- For significant changes:
  - Include “What changed” and “Why” in PR description.
  - Add migration notes or rollbacks if applicable.

## Commit and PR guidance
- Commit messages: imperative mood, concise subject, optional body with rationale.
- PR checklist:
  - [ ] Tests updated/added
  - [ ] Docs updated (if behavior changed)
  - [ ] Security implications reviewed
  - [ ] No edits to protected paths without approval
  - [ ] Check for code duplication - use existing utilities from `lib/` and `processing.py`
  - [ ] Verify imports use canonical locations (no local redefinitions)

## Security checklist (quick)
- No secrets or tokens in code or config.
- Avoid `eval`, dynamic `Function`, unsafe deserialization.
- Validate all external inputs; sanitize outputs when reflected.
- For HTTP:
  - Use safe URL handling; prevent SSRF (no arbitrary fetch of user-controlled URLs).
- File system/path:
  - No path traversal; validate/normalize joins.

## Key Implementation Patterns

### Async Component Lifecycle
```python
# Server startup pattern
server = MCPServer()
await server.start_async_components()  # Start feedback, ranking monitor
try:
    # Run server
finally:
    await server.cleanup_async_components()  # Cleanup
```

### Ranking Factor Calculation
The system uses 8 weighted factors for ranking with confidence tracking:

1. **Text Relevance**: BM25/TF-IDF score from Azure Search
   - Normalized using min-max across result set
   - Confidence: 1.0 (from search engine)

2. **Semantic Similarity**: Vector embeddings cosine similarity
   - Primary: Azure OpenAI embeddings
   - Fallback: Keyword overlap (Jaccard coefficient)
   - Confidence: 1.0 (vector) or 0.6 (keyword)

3. **Context Overlap**: Shared imports, functions, classes
   - Import overlap: 30% weight
   - Function/class usage: 30% weight
   - Framework match: 20% weight
   - Language match: 20% weight
   - Confidence: 0.9

4. **Import Similarity**: Jaccard coefficient of imports
   - Set intersection over union
   - Confidence: 0.9

5. **Proximity Score**: File/directory distance with logarithmic dampening
   - Same file: 1.0
   - Same directory: 0.7
   - Same module: 0.5
   - Same project: 0.3
   - Logarithmic dampening: log(1 + score * 4) / log(5)
   - Confidence: 0.8

6. **Recency Score**: Normalized modification time
   - Timestamp normalization across result set
   - Neutral score (0.5) for unknown dates
   - Confidence: 0.9

7. **Quality Score**: Test coverage, complexity, documentation
   - Test coverage: 30% weight
   - Complexity (inverted): 20% weight
   - Documentation presence: 20% weight
   - Test tag presence: 10% weight
   - Confidence: varies by signals available

8. **Pattern Match**: Design pattern detection
   - Registry-based pattern recognition
   - Keyword-based fallback detection
   - Structural pattern analysis (regex)
   - Confidence: 0.7

### Search Intent Classification
- `IMPLEMENT`: Focus on examples and implementations
- `DEBUG`: Prioritize error handling and recent changes
- `UNDERSTAND`: Emphasize documentation and context
- `REFACTOR`: Look for similar code structures
- `TEST`: Find test examples and patterns
- `DOCUMENT`: Search documentation and comments

### Caching Strategy
- **Embedding Cache**: SHA256 keys, 1-hour TTL, LRU eviction
- **Context Cache**: File-based caching with session tracking
- **Search Cache**: Query-based with exact term handling

### Adaptive Learning System
The system includes feedback-based learning components:

1. **Feedback Collection** (`enhanced_rag/learning/feedback_collector.py`)
   - Records search interactions and outcomes
   - Tracks: clicks, refinements, code copies, dwell time
   - Persistent storage in JSONL format
   - Deque-based memory buffer (10K records)

2. **Model Updater** (`enhanced_rag/learning/model_updater.py`)
   - Updates ranking weights based on feedback
   - Reward signals:
     - Click in top 3: +0.3
     - Click in top 5: +0.1
     - Code copy: +0.5
     - No click: -0.05
   - Exponential moving average with learning rate 0.1
   - Minimum 5 feedback items per intent for updates

3. **Adaptive Ranker** (`enhanced_rag/ranking/adaptive_ranker.py`)
   - Real-time weight adjustment per search intent
   - Weight bounds: 0.05 to 0.5 per factor
   - Automatic normalization to sum to 1.0
   - Background updates every 5 minutes
   - Rollback capability for weight regression

### Performance Monitoring
- **Ranking Monitor** (`enhanced_rag/ranking/ranking_monitor.py`)
  - Tracks: CTR, MRR, NDCG, P@K metrics
  - Session-based performance tracking
  - Anomaly detection with thresholds
  - Performance history retention (100 entries)

### Code Deduplication Patterns

#### Shared Utilities
- **Repository root detection**: Use `find_repository_root()` from `enhanced_rag/azure_integration/processing.py`
- **Repository validation**: Use `validate_repo_name()` and `validate_repo_path()` from `enhanced_rag/azure_integration/processing.py`
- **Response helpers**: Import `ok`/`err` from `mcprag/utils/response_helpers.py` - never redefine locally
- **CLI subprocess invocation**: Use `_run_enhanced_cli()` from `mcprag/mcp/tools/azure_management.py` for invoking enhanced_rag CLI
- **Azure service resolution**: Use `_resolve_search_service_name()` and `_build_mgmt_context()` from `mcprag/mcp/tools/service_management.py`

#### File Processing
- **FileProcessor class** (`enhanced_rag/azure_integration/processing.py`) is the single source of truth for:
  - Repository traversal via `process_repository()`
  - Extension filtering via `DEFAULT_EXTENSIONS`
  - Language detection via `get_language_from_extension()`
  - Repository name and path validation
  - Never duplicate directory walking, extension filtering, or validation logic

#### Index Management Utilities
- **Index lifecycle** (`enhanced_rag/azure_integration/lib/index_utils.py`):
  - `ensure_index_exists()` - Create or update index with schema validation
  - `recreate_index()` - Drop and recreate index with optional backup
  - `schema_differs()` - Compare index schemas for differences
  - `validate_index_schema()` - Validate schema and surface issues
- **Search models** (`enhanced_rag/azure_integration/lib/search_models.py`):
  - `create_standard_index_definition()` - Complete index definition builder
  - `create_default_vector_search_config()` - Standard vector search setup
  - `create_default_semantic_config()` - Standard semantic search setup

#### Component Validation
- Use `check_component()` for all component availability checks
- After check_component, use `assert component is not None` for type checker
- Never add redundant manual None-checks after check_component
- This pattern eliminates duplicate error messages

## Orchestrator expectations (subagent)
Use the orchestrator for multi-file/multi-step tasks requiring planning and delegation.

- MUST:
  - Create `.claude/state/plan.md` with objective, acceptance criteria, risks, rollback.
  - Create `.claude/state/todo.md` with steps, owners (subagent), and outputs.
  - Pause for approval before cross-module refactors, migrations, config changes, dependency upgrades, or any protected path touches.
- Delegate chain (typical):
  1) dependency-mapper → scope blast radius and tests
  2) code-reviewer (+ security-screener in parallel) → preflight issues
  3) minimal implementation edits
  4) test-runner → focused tests, then wider
  5) doc-writer → README/CHANGELOG/docs updates
- Context:
  - Keep heavy logs under `.claude/state/` and link by path.
  - Summarize long outputs with file:line citations.

## Subagent expectations

### dependency-mapper
- Purpose: fast, minimal blast-radius analysis.
- Inputs: symbol/file/diff; produce JSON with entities, edges, files, hotspots, testsToRun, and a short summary.
- Use absolute paths and include file:line anchors.
- Store large grep outputs under `.claude/state/depmap/`.

### code-reviewer
- Purpose: immediate review after changes.
- Review only modified files and directly related code.
- Output prioritized findings with file:line and concrete fix snippets:
  - Critical: must fix
  - Warnings: should fix
  - Suggestions: nice-to-have
- Reference CLAUDE.md rules in recommendations.

### test-runner
- Purpose: run impacted tests and propose minimal fixes.
- Log to `.claude/state/tests.json`.
- Summarize failure signatures; iterate up to 2 fixes before asking for approval to broaden scope.

### security-screener
- Purpose: parallel scan for risky patterns and secrets in modified files.
- Output critical findings with file:line and remediation advice.
- Never echo secrets; advise rotation.

### doc-writer
- Purpose: update docs in lockstep with code changes.
- Propose concrete patches/snippets; preserve anchors and links.

## Tools and hooks
- Tools to prefer:
  - Grep/Glob for fast file discovery; `rg` if available.
  - Bash for git diff, basic scripting (never destructive without explicit ask).
- Hooks (recommended):
  - PreToolUse (Edit|Write): block protected paths (exit code 2 with reason).
  - PostToolUse (Edit|Write|MultiEdit): run formatter/lint on changed files.
  - SessionStart: inject CLAUDE.md highlights into context.
  - PreCompact: trigger summarization when near context limit.

## MCP Tool Testing
When working with MCP tools or debugging issues:

### Quick Manual Tests
```bash
# Test search_code functionality using the universal framework
python -c "
import asyncio
from claude.state.universal_mcp_tool_evaluator import UniversalMCPToolEvaluator

async def test_search():
    evaluator = UniversalMCPToolEvaluator()
    await evaluator.initialize()
    # Run search tool tests
    results = await evaluator.run_tool_tests('search_code')
    evaluator.print_summary()
    await evaluator.cleanup()

asyncio.run(test_search())
"

# Generate coverage report for all tools
python .claude/state/mcp_tool_coverage_report.py

# Run comprehensive test suite
python .claude/state/universal_mcp_tool_evaluator.py
```

### Tool-Specific Testing
- Search tools: Test with various queries, repositories, and detail levels
- Admin tools: Require MCP_ADMIN_MODE=true, test with mock/sandbox environments
- Azure management tools: Test connection and authentication before operations
- Cache tools: Verify cache behavior and TTL settings
- Feedback tools: Test with sample feedback data

## Routing cues for subagent selection
- Orchestrator: “plan”, “orchestrate”, “multi-file”, “refactor across modules”, “end-to-end”, “first…then…”, “migration”, “config/dependency upgrade”, protected paths.
- dependency-mapper: “find usages”, “who calls X”, “what files impacted”, “blast radius”.
- code-reviewer: “review this diff”, “anything risky here?”, “ready to ship?”.
- test-runner: “run tests for this change”, “fix failing tests”.
- security-screener: “scan for secrets”, “security risks in this change”.
- doc-writer: “update docs/README/CHANGELOG”.

## Examples (quick)

Run focused review after edits:
- code-reviewer: check only files in `git diff`, cite file:line, suggest concrete fix snippets.

Before refactor:
- dependency-mapper: map callers/imports; list `testsToRun`.
- orchestrator: propose plan + todo, pause for approval with rollback steps.

After implementation:
- test-runner: run impacted tests; add/update tests as needed.
- doc-writer: update README/CHANGELOG.

## Contact and approvals
- For any change touching protected paths or high-risk categories, request human approval with:
  - Short summary of intent
  - Diff preview of key files
  - Rollback steps (commands/files)
  - Risk assessment (1–2 bullets)

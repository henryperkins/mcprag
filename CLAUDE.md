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
   - REST API client with retry logic
   - Index, document, and indexer management
   - Embedding generation with caching
   - Repository processing and file chunking

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
- Configuration: `mcprag/config.py`, `.mcp.json`
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

# Performance
MCP_DEBUG_TIMINGS=false  # Enable timing logs
```

### Key Configuration Files
- `.mcp.json`: MCP server configuration
- `azure_search_index_schema.json`: Index schema definition
- `enhanced_rag/core/config.py`: RAG pipeline configuration
- `mcprag/config.py`: Server configuration loader

## MCP Tools Available

### Search Tools
- `search_code`: Enhanced code search with RAG pipeline
- `search_code_raw`: Raw search results without formatting
- `search_microsoft_docs`: Microsoft Learn documentation search

### Generation Tools
- `generate_code`: Code generation using RAG context
- `analyze_context`: File context analysis

### Analysis Tools
- `explain_ranking`: Explain why results are ranked
- `preview_query_processing`: Show query enhancement

### Admin Tools (require MCP_ADMIN_MODE=true)
- `index_rebuild`: Rebuild search indexer
- `github_index_repo`: Index GitHub repository
- `manage_index`: Index lifecycle management
- `manage_documents`: Document operations
- `manage_indexer`: Indexer operations

### Cache Tools
- `cache_stats`: Cache statistics
- `cache_clear`: Clear cache

### Feedback Tools
- `submit_feedback`: User feedback submission
- `track_search_click`: Click tracking
- `track_search_outcome`: Outcome tracking

## Coding standards
- Language: Python 3.12+ with type hints
- Style:
  - Prefer small, pure functions; clear names; single responsibility.
  - Avoid duplicated code; extract shared utilities.
  - Handle errors explicitly; avoid silent failures.
  - Validate inputs; sanitize outputs for security.
  - Use dataclasses for structured data
- Imports:
  - Use explicit, minimal imports; avoid unused symbols.
  - Prefer absolute imports for cross-module references
  - Use TYPE_CHECKING for circular import prevention
- Async:
  - Use `async/await` throughout; handle rejections
  - Add timeouts for all external calls (default 30s)
  - Properly cleanup async resources in finally blocks
- Performance:
  - Avoid N+1 patterns; batch Azure Search operations
  - Cache embeddings with SHA256 keys
  - Limit context cache size (1000 entries default)
  - Use streaming for large document sets

## Testing standards
- Add or update tests for new behavior and bug fixes.
- Include negative cases and edge cases.
- Keep tests deterministic; avoid sleeping; use fakes/mocks where appropriate.
- Minimal acceptance for change:
  - Tests pass locally for impacted area(s).
  - No flakiness introduced.

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

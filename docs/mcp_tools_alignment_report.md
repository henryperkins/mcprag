# MCP Tools Alignment Report

## Executive Summary
After reviewing all MCP tool implementations and comparing them with documentation in CLAUDE.md and system prompts, I found several discrepancies and areas where documentation could be improved for better alignment.

## Tool Coverage Analysis

### Documented vs Implemented Tools

#### Search Tools (`search.py`)
✅ **Aligned:**
- `search_code` - Parameters and functionality match documentation
- `search_code_raw` - Properly documented as raw results wrapper
- `search_microsoft_docs` - Simple interface as documented

#### Generation Tools (`generation.py`)
✅ **Aligned:**
- `generate_code` - Parameters match documentation

#### Analysis Tools (`analysis.py`)
✅ **Aligned:**
- `analyze_context` - Parameters match
- `explain_ranking` - Parameters match
- `preview_query_processing` - Parameters match

#### Admin Tools (`admin.py`)
✅ **Aligned:**
- `index_rebuild` - Confirmation requirement documented
- `github_index_repo` - Confirmation requirement documented

#### Azure Management Tools (`azure_management.py`)
🔍 **Additional tools found not in CLAUDE.md:**
- `index_repository` - Indexes local repository
- `index_changed_files` - Indexes specific changed files
- `backup_index_schema` - Backs up current schema
- `clear_repository_documents` - Clears documents by repository filter
- `rebuild_index` - Complete index rebuild (different from index_rebuild)

✅ **Aligned:**
- `manage_index` - Actions and parameters match
- `manage_documents` - Actions and parameters match
- `manage_indexer` - Actions and parameters match (with status truncation feature)
- `health_check` - Simple health check as expected
- `create_datasource` - Parameters match
- `create_skillset` - Parameters match
- `index_status` - Parameters match
- `validate_index_schema` - Parameters match

#### Cache Tools (`cache.py`)
✅ **Aligned:**
- `cache_stats` - No parameters, simple stats
- `cache_clear` - Scope and pattern parameters match

#### Feedback Tools (`feedback.py`)
✅ **Aligned:**
- `submit_feedback` - Parameters match
- `track_search_click` - Parameters match
- `track_search_outcome` - Parameters match

## Key Discrepancies Found

### 1. Missing Documentation in CLAUDE.md
The following tools are implemented but not documented in CLAUDE.md:
- `index_repository` - Local repository indexing via CLI
- `index_changed_files` - Incremental file indexing
- `backup_index_schema` - Schema backup functionality
- `clear_repository_documents` - Repository-specific document clearing
- `rebuild_index` - Full index rebuild (distinct from `index_rebuild`)

### 2. Parameter Documentation Issues

#### `search_code` Tool
**Documentation states:** Various parameters for search control
**Implementation has:** Additional parameters not fully documented:
- `snippet_lines` - Smart truncation algorithm (documented in docstring but not in CLAUDE.md)
- `detail_level` - Output format control (full/compact/ultra)
- `dependency_mode` - Auto mode for dependency resolution
- `exact_terms` - List of exact terms to match
- `disable_cache` - Cache bypass option
- `include_timings` - Performance timing inclusion

#### `cache_clear` Tool
**Documentation states:** Scope parameter for clearing
**Implementation:** Validates scope as one of {"all", "search", "embeddings", "results"}
**Issue:** Documentation validation differs from implementation (checks for "all" or "pattern" in line 41)

### 3. Admin Mode Requirements
Several tools require `MCP_ADMIN_MODE=true` but this is not consistently documented:
- Azure management tools have inline checks for `Config.ADMIN_MODE`
- Some tools use `@require_admin_mode` decorator
- Documentation should clarify which operations require admin mode

### 4. Confirmation Requirements
Tools with `@require_confirmation` decorator need explicit documentation:
- `index_rebuild` - Documented
- `github_index_repo` - Documented
- `rebuild_index` - Not mentioned in CLAUDE.md

### 5. Component Dependencies
Tools check for component availability but documentation doesn't specify:
- Which components must be initialized for each tool
- Fallback behavior when components are unavailable
- Async component startup requirements

## Recommendations

### 1. Update CLAUDE.md
Add missing tools to the MCP Tools Available section:
```markdown
### Additional Azure Management Tools
- `index_repository`: Index local repository into Azure Search
- `index_changed_files`: Index specific changed files
- `backup_index_schema`: Backup current index schema
- `clear_repository_documents`: Clear documents from specific repository
- `rebuild_index`: Complete index drop and rebuild (requires confirm=true)
```

### 2. Document Parameter Details
Expand parameter documentation for `search_code`:
- Add `snippet_lines` behavior explanation
- Document `detail_level` options and their impact
- Clarify `dependency_mode` options

### 3. Fix Cache Validation
Align cache_clear validation in `cache.py:41` with actual valid scopes.

### 4. Admin Mode Matrix
Create a table showing which tools require admin mode:
| Tool | Admin Required | Confirmation Required |
|------|---------------|----------------------|
| manage_index (create/delete) | ✅ | ❌ |
| manage_documents (modify) | ✅ | ❌ |
| index_rebuild | ✅ | ✅ |
| rebuild_index | ✅ | ✅ |

### 5. Component Requirements
Document which server components each tool requires:
- search_* tools → enhanced_search
- generate_code → code_gen
- cache_* → cache_manager
- feedback_* → feedback_collector

### 6. Error Message Alignment
Standardize error messages across tools for consistency.

## Conclusion
The MCP tools implementation is largely well-aligned with documentation, but there are opportunities to improve documentation completeness and accuracy. The main issues are missing documentation for several Azure management tools and incomplete parameter documentation for complex tools like `search_code`.
# Search Code Tool Evaluation Report
**Date:** 2025-08-10  
**Tool:** mcprag search_code MCP tool

## Executive Summary

The search_code tool evaluation reveals critical issues that need immediate attention. While the tool is functional, several P1 and P2 issues significantly impact its effectiveness.

## Test Results Summary

### ❌ Critical Issues (P1)

1. **Repository Filtering Broken**
   - **Test:** RF-01 - Filter to mcprag repository
   - **Input:** `query="FastMCP server implementation", repository="mcprag"`
   - **Expected:** Results only from mcprag repository
   - **Actual:** Results from "venv/lib" repository instead
   - **Impact:** Users cannot filter searches to specific repositories
   - **Severity:** P1 - Blocking basic functionality

2. **Enhanced Mode Relevance Scores Very Low**
   - **Test:** Comparing BM25 vs Enhanced mode
   - **BM25 Score:** 29.75 for top result
   - **Enhanced Score:** 0.0164 for same result (~1800x lower)
   - **Impact:** Enhanced mode ranking is essentially broken
   - **Severity:** P1 - Major feature not working

3. **Content Extraction Failure in Enhanced Mode**
   - **Test:** All enhanced mode queries
   - **Issue:** All results show "No content" and empty headlines
   - **Impact:** Users cannot see code snippets or context
   - **Severity:** P1 - Critical data missing

### ⚠️ Medium Issues (P2)

1. **Repository Field Inconsistency**
   - Some results show `repository: "mcprag"` while file path shows `repo: "venv/lib"`
   - Confusing and inconsistent data structure

2. **Missing Metadata in Enhanced Mode**
   - `function_name`, `class_name`, `start_line`, `end_line` all null
   - Line numbers array contains null values instead of actual lines

3. **Highlights Object Empty**
   - Even with matching terms, highlights object is always empty
   - Reduces ability to show context to users

## Performance Metrics

| Mode | Avg Response Time | Score Range |
|------|-------------------|-------------|
| BM25 | 95ms | 24.82 - 29.75 |
| Enhanced | 148-429ms | 0.016 - 0.016 |

- Enhanced mode is 1.5-4.5x slower than BM25
- Enhanced mode scores are uniformly low (essentially broken)

## Feature Testing Results

### Working Features ✅
- Basic search functionality
- BM25 mode returns reasonable results and scores
- Query parameter accepted and processed
- Max results parameter respected
- Detail level parameter accepted

### Broken Features ❌
- Repository filtering (P1)
- Enhanced mode scoring (P1)
- Content extraction in enhanced mode (P1)
- Code highlights (P2)
- Line number extraction (P2)
- Function/class context extraction (P2)

## Root Cause Analysis

1. **Repository Filtering:** The repository parameter is being ignored or improperly processed in the Azure Search query construction.

2. **Enhanced Mode Issues:** The enhanced ranking system appears to have:
   - Broken normalization causing extremely low scores
   - Failed content extraction from search results
   - Missing metadata population

3. **Data Pipeline Issues:** Results suggest a disconnect between:
   - What Azure Search returns
   - How the enhanced_rag pipeline processes it
   - What gets returned to the user

## Recommendations

### Immediate Actions (This Sprint)
1. **Fix Repository Filtering**
   - Debug the Azure Search query construction
   - Ensure repository field is properly indexed and filterable
   - Add integration tests for repository filtering

2. **Fix Enhanced Mode Scoring**
   - Review score normalization in `enhanced_rag/ranking/contextual_ranker_improved.py`
   - Ensure BM25 scores are properly preserved or scaled
   - Add unit tests for score calculation

3. **Fix Content Extraction**
   - Debug content extraction in result processing
   - Ensure highlights and snippets are properly extracted
   - Fix line number extraction

### Short-term Actions (Next Sprint)
1. Add comprehensive integration tests
2. Implement monitoring for score distributions
3. Add fallback to BM25 when enhanced mode fails
4. Improve error handling and logging

### Long-term Actions
1. Refactor the enhanced ranking system for reliability
2. Implement A/B testing framework
3. Add performance benchmarks to CI/CD
4. Create automated regression test suite

## Test Coverage Gaps

Current automated tests are failing due to import issues. Need to:
1. Fix the test runner to properly import MCP tools
2. Add integration tests that use the actual MCP server
3. Create unit tests for individual components
4. Add performance regression tests

## Conclusion

The search_code tool has significant issues that severely impact its usability. The three P1 issues (repository filtering, enhanced scoring, content extraction) should be addressed immediately as they block core functionality. The tool should potentially default to BM25 mode until enhanced mode issues are resolved.

**Overall Assessment:** 🔴 **Critical** - Tool is partially functional but major features are broken

## Appendix: Test Commands Used

```python
# Test repository filtering
await search_code(query="FastMCP server implementation", repository="mcprag", max_results=3)

# Compare BM25 vs Enhanced
await search_code(query="register_tools", bm25_only=True, max_results=3)
await search_code(query="register_tools", bm25_only=False, max_results=3)

# Test content extraction
await search_code(query="server class", max_results=5, detail_level="full")
```
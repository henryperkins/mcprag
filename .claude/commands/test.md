# Test MCP and Search Functionality

Run tests specific to the MCP server and Azure Search integration.

## Purpose

This command helps you test the MCP server, search functionality, and Azure integration components.

## Usage

```
/test
```

## Quick Test Commands

### Run All Tests
```bash
# Run pytest suite
pytest

# With coverage report
pytest --cov=mcprag --cov=enhanced_rag

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

### Test Categories

#### MCP Protocol Tests
```bash
# Core MCP protocol
pytest tests/test_mcp_protocol.py

# MCP tools functionality
pytest tests/test_mcp_tools.py
pytest tests/test_mcp_tools_core.py
pytest tests/test_mcp_tools_enhanced.py

# Direct MCP testing
pytest tests/test_mcp_direct.py
```

#### Search Tests
```bash
# Basic search functionality
pytest tests/test_basic_search.py
pytest tests/test_single_search.py

# Advanced search features
pytest tests/test_exact_terms_enhancement.py
pytest tests/test_timing_enhancement.py
pytest tests/test_caching_enhancement.py

# Search directly
pytest tests/test_search_directly.py
```

#### Azure Integration Tests
```bash
# Azure ranking
pytest tests/test_azure_ranking_enhancement.py

# Indexing operations
pytest tests/test_reindex.py
pytest tests/test_complete_indexing.py
pytest tests/test_index_single.py

# Vector search
pytest tests/test_vector_search.py
pytest tests/test_text_vector_search.py
```

#### Code Analysis Tests
```bash
# Code chunking
pytest tests/test_code_chunker.py
pytest tests/test_improved_chunking.py

# Pattern recognition
pytest tests/test_pattern_registry.py

# AST analysis
pytest enhanced_rag/code_understanding/test_ast_analyzer.py
```

### Integration Test Suite
```bash
# Full integration test
pytest tests/test_pipeline_integration.py

# Test with real Azure connection
pytest tests/test_integrated_generation_flow.py

# Repository filter test
pytest tests/test_repository_filter.py
```

## Test Framework

### Run Comprehensive Test Matrix
```bash
# Execute full test matrix
python test_framework/mcp_test_runner.py

# View test results
cat test_framework/mcp_test_results.json

# Check test report
cat test_framework/MCP_COMPREHENSIVE_TEST_REPORT.md
```

### Performance Testing
```bash
# Test search performance
python tests/test_timing_enhancement.py

# Cache performance
python tests/test_caching_enhancement.py

# Indexing performance
time python -m enhanced_rag.azure_integration.cli local-repo --repo-path . --repo-name test
```

## Debug Failing Tests

### Verbose Test Output
```bash
# Show print statements
pytest -s tests/test_mcp_search.py

# Debug specific test
pytest -vv tests/test_mcp_tools.py::test_search_code

# With breakpoint
pytest --pdb tests/test_single_search.py
```

### Check Test Dependencies
```bash
# Verify Azure connection
python -c "from azure.search.documents import SearchClient; print('Azure SDK OK')"

# Check enhanced_rag imports
python -c "from enhanced_rag.pipeline import RAGPipeline; print('Pipeline OK')"

# Verify MCP tools
python -c "from mcprag.mcp.tools import get_all_tools; print(len(get_all_tools()))"
```

## Test Data Setup

### Create Test Index
```bash
# Create test index
ACS_INDEX_NAME=test-index python index/create_enhanced_index.py

# Index test data
python -m enhanced_rag.azure_integration.cli local-repo \
  --repo-path example-repo \
  --repo-name test-repo
```

### Clean Up Test Data
```bash
# Remove test documents
python -m enhanced_rag.azure_integration.cli reindex \
  --method clear \
  --filter "repository eq 'test-repo'"
```

## Best Practices

1. **Run tests before commits** - Use pre-commit hooks
2. **Test in isolation** - Use test indices
3. **Mock external services** - For unit tests
4. **Check coverage** - Aim for >80%
5. **Test edge cases** - Empty results, errors, timeouts
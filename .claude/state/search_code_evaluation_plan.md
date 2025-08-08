# Search Code Tool Evaluation Plan

## Overview
This document outlines a comprehensive evaluation framework for testing the `search_code` MCP tool to ensure quality, performance, and reliability across different scenarios and parameters.

## Evaluation Framework

### 1. Test Categories

#### A. Core Functionality Tests
- **Basic Search**: Verify tool responds correctly to simple queries
- **Parameter Validation**: Test input validation and error handling
- **Response Structure**: Verify JSON schema consistency
- **Performance**: Measure response times under various loads

#### B. Search Quality Tests
- **Relevance Scoring**: Evaluate result ranking accuracy
- **Content Extraction**: Verify code snippets are complete and accurate
- **Repository Filtering**: Test isolation of search scope
- **Language Detection**: Verify correct language classification

#### C. Advanced Feature Tests
- **Intent Classification**: Test IMPLEMENT, DEBUG, UNDERSTAND, TEST, REFACTOR intents
- **Search Modes**: BM25-only vs enhanced semantic search
- **Output Formats**: Full, compact, ultra detail levels
- **Dependency Analysis**: Include/exclude dependency tracking

#### D. Edge Case & Error Tests
- **Invalid Inputs**: Empty queries, malformed parameters
- **Boundary Conditions**: Max results, very long queries
- **Repository Edge Cases**: Non-existent repos, permission issues
- **Performance Limits**: Large result sets, complex queries

### 2. Test Scenarios Matrix

#### Repository Filtering Tests
| Test | Repository | Query | Expected Result |
|------|------------|-------|----------------|
| RF-01 | `mcprag` | "FastMCP server" | Only mcprag/* files |
| RF-02 | `enhanced_rag` | "ranking algorithm" | Only enhanced_rag/* files |
| RF-03 | `tests` | "test integration" | Only tests/* files |
| RF-04 | `nonexistent` | "any query" | Empty results or error |
| RF-05 | `""` (empty) | "search term" | All repositories |

#### Search Quality Tests
| Test | Query | Intent | Expected Top Result |
|------|-------|---------|-------------------|
| SQ-01 | "MCPServer class definition" | UNDERSTAND | mcprag/server.py class |
| SQ-02 | "register_tools implementation" | IMPLEMENT | mcprag/mcp/tools/__init__.py |
| SQ-03 | "Azure Search configuration" | DEBUG | Config files or error handling |
| SQ-04 | "ranking algorithm test" | TEST | Test files with ranking tests |
| SQ-05 | "refactor tool registration" | REFACTOR | Tool registration patterns |

#### Parameter Combination Tests
| Test | Parameters | Expected Behavior |
|------|------------|------------------|
| PC-01 | `bm25_only=true` | Higher relevance scores (>1.0) |
| PC-02 | `exact_terms=["keyword"]` | Results containing exact keyword |
| PC-03 | `detail_level=compact, snippet_lines=3` | Truncated content with 3 lines |
| PC-04 | `include_dependencies=true` | Additional context in results |
| PC-05 | `highlight_code=true` | Highlighted search terms in results |

#### Performance Tests
| Test | Scenario | Success Criteria |
|------|----------|-----------------|
| PF-01 | Simple query, 10 results | Response < 200ms |
| PF-02 | Complex query, 50 results | Response < 500ms |
| PF-03 | Repository-filtered search | Response < 300ms |
| PF-04 | BM25-only vs Enhanced mode | Enhanced ≤ 2x BM25 time |
| PF-05 | Concurrent queries (5x) | All complete < 1000ms |

### 3. Success Metrics

#### Functional Metrics
- **Response Rate**: 100% of valid queries return responses
- **Error Rate**: <1% unexpected errors for valid inputs
- **Schema Compliance**: 100% responses match expected JSON schema
- **Parameter Handling**: 100% of documented parameters work as specified

#### Quality Metrics
- **Repository Filtering Accuracy**: 95% of results from correct repository
- **Relevance Score Consistency**: BM25 mode shows scores >1.0, Enhanced mode >0.01
- **Content Completeness**: <5% results with empty/missing content
- **Language Detection**: 95% accuracy for supported languages

#### Performance Metrics
- **Response Time**: 95th percentile <500ms for standard queries
- **Throughput**: Handle 10 concurrent queries without degradation
- **Memory Stability**: No memory leaks during extended testing
- **Cache Effectiveness**: Cache hits improve response time by >50%

### 4. Test Data Requirements

#### Code Repositories
- **Primary**: mcprag project (current working directory)
- **Secondary**: enhanced_rag, tests subdirectories
- **Dependencies**: venv/lib (for negative testing)
- **Synthetic**: Create small test repos with known content

#### Query Types
- **Simple Keywords**: "server", "class", "function"
- **Code Patterns**: "async def", "class MyClass", "import json"
- **Natural Language**: "how to configure Azure Search"
- **Technical Terms**: "FastMCP", "Azure AI Search", "RAG pipeline"

#### Expected Results Database
- Maintain golden dataset of query → expected results mappings
- Include file paths, relevance scores, content snippets
- Update after each major index change

### 5. Automated Testing Framework

#### Test Runner Script
```python
# Pseudo-code structure
class SearchCodeEvaluator:
    def __init__(self):
        self.test_cases = load_test_scenarios()
        self.metrics = MetricsCollector()
    
    async def run_all_tests(self):
        results = {}
        for category in ['functional', 'quality', 'performance', 'edge_cases']:
            results[category] = await self.run_category_tests(category)
        return self.generate_report(results)
    
    async def run_repository_filtering_tests(self):
        # Test RF-01 through RF-05
        pass
    
    async def run_search_quality_tests(self):
        # Test SQ-01 through SQ-05
        pass
```

#### Continuous Monitoring
- **Daily Regression Tests**: Run core functionality suite
- **Weekly Full Suite**: Complete evaluation including performance
- **Pre-deployment Gate**: All tests must pass before releases
- **Performance Monitoring**: Track metrics trends over time

### 6. Evaluation Procedures

#### Pre-Test Setup
1. Verify index health with `health_check` tool
2. Clear cache to ensure fresh results
3. Validate test data repository state
4. Record baseline performance metrics

#### Test Execution
1. **Systematic Testing**: Run tests in defined order
2. **Result Capture**: Store all responses for analysis
3. **Error Documentation**: Log all failures with context
4. **Performance Monitoring**: Track timing and resource usage

#### Post-Test Analysis
1. **Result Validation**: Compare against expected outcomes
2. **Regression Detection**: Flag changes from previous runs
3. **Performance Analysis**: Identify bottlenecks or improvements
4. **Report Generation**: Automated test reports with recommendations

### 7. Issue Classification

#### Severity Levels
- **P0 - Critical**: Tool completely non-functional
- **P1 - High**: Major feature broken (e.g., repository filtering)
- **P2 - Medium**: Quality degradation (e.g., poor relevance scores)
- **P3 - Low**: Minor issues (e.g., formatting problems)

#### Issue Categories
- **Functional**: Feature not working as designed
- **Performance**: Response times or throughput issues
- **Quality**: Poor search results or ranking
- **Usability**: Confusing behavior or error messages

### 8. Test Environment Specifications

#### Hardware Requirements
- **CPU**: Multi-core for concurrent testing
- **Memory**: 8GB+ for index and cache testing
- **Storage**: SSD for fast I/O during tests
- **Network**: Stable connection for Azure Search

#### Software Requirements
- **Python 3.12+**: For test runner compatibility
- **Azure Search Access**: Valid credentials and index
- **MCP Server**: Running mcprag server instance
- **Test Dependencies**: pytest, asyncio, performance profiling tools

### 9. Reporting and Documentation

#### Test Report Format
```
# Search Code Tool Test Report
## Date: {timestamp}
## Test Suite Version: {version}
## Environment: {environment_details}

### Executive Summary
- Tests Run: {total_tests}
- Passed: {passed_count} ({pass_rate}%)
- Failed: {failed_count}
- Performance: {avg_response_time}ms avg

### Detailed Results
[Category-by-category breakdown]

### Issues Found
[P0/P1/P2/P3 issues with reproduction steps]

### Recommendations
[Action items for improvements]
```

#### Trend Analysis
- Track metrics over time
- Identify performance regressions
- Monitor search quality changes
- Document correlation with code changes

### 10. Maintenance and Updates

#### Test Suite Maintenance
- **Quarterly Review**: Update test scenarios based on usage patterns
- **Index Changes**: Adapt tests when search index is modified
- **Feature Updates**: Add tests for new search_code parameters
- **Performance Baselines**: Adjust expectations as system evolves

#### Documentation Updates
- Keep evaluation plan current with tool evolution
- Document new test scenarios and edge cases
- Maintain troubleshooting guides for common issues
- Share learnings with development team

## Implementation Timeline

### Phase 1: Foundation (Week 1-2)
- Create basic test runner framework
- Implement core functionality tests
- Set up automated reporting

### Phase 2: Quality Testing (Week 3-4)
- Develop search quality evaluation methods
- Create golden dataset for result validation
- Implement repository filtering tests

### Phase 3: Advanced Features (Week 5-6)
- Add intent classification testing
- Implement performance benchmarking
- Create edge case and error scenarios

### Phase 4: Integration (Week 7-8)
- Integrate with CI/CD pipeline
- Set up continuous monitoring
- Create alerting for regressions

This evaluation plan provides a comprehensive framework for systematically testing and maintaining the quality of the search_code tool across all its features and use cases.
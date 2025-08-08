# Search Code Tool Evaluation Procedures Guide

## Quick Start

### Running the Evaluation Suite
```bash
# Navigate to project directory
cd /home/azureuser/mcprag

# Run the full evaluation suite
python .claude/state/search_evaluation_runner.py

# Run with specific scenarios file
python .claude/state/search_evaluation_runner.py --scenarios custom_scenarios.json

# Generate report only (for existing results)
python .claude/state/search_evaluation_runner.py --report-only
```

### Prerequisites
- MCP RAG server running and accessible
- Azure Search service healthy and indexed
- Python 3.12+ with required dependencies
- Test scenarios file present (`.claude/state/search_code_test_scenarios.json`)

## Evaluation Workflow

### Phase 1: Pre-Evaluation Setup ✅

#### 1.1 Environment Check
```bash
# Verify MCP server is responsive
python -c "import asyncio; from mcprag.mcp.tools.search import search_code; print('✅ MCP tools accessible')"

# Check Azure Search health
python -m mcprag health_check

# Verify index status
python -m mcprag index_status
```

#### 1.2 Baseline Metrics Collection
```python
# Example baseline collection
baseline_queries = [
    "server implementation",
    "register_tools function", 
    "Azure Search config",
    "ranking algorithm",
    "error handling"
]

# Run each query and record:
# - Response times
# - Result counts
# - Relevance scores
# - Content quality
```

#### 1.3 Test Data Validation
- Ensure test scenarios file is current
- Validate expected results against actual codebase state
- Update golden dataset if codebase has changed significantly

### Phase 2: Test Execution 🚀

#### 2.1 Automated Test Runner
The evaluation runs tests in this order:
1. **Edge Cases** - Input validation and error handling
2. **Parameter Combinations** - Feature interaction testing
3. **Repository Filtering** - Scope isolation testing
4. **Search Quality** - Relevance and accuracy testing
5. **Performance Tests** - Response time and throughput
6. **Regression Tests** - Stability and consistency

#### 2.2 Manual Verification Steps
For critical failures, manually verify:

```bash
# Test repository filtering manually
python -c "
import asyncio
from mcprag.mcp.tools.search import search_code

async def test():
    result = await search_code(query='server', repository='mcprag', max_results=5)
    print(f'Results: {len(result[\"data\"][\"items\"])}')
    for item in result['data']['items']:
        print(f'  {item[\"repository\"]}: {item[\"file\"]}')

asyncio.run(test())
"

# Test BM25 vs Enhanced modes
python -c "
import asyncio, time
from mcprag.mcp.tools.search import search_code

async def compare_modes():
    query = 'register_tools'
    
    # BM25 mode
    start = time.time()
    bm25_result = await search_code(query=query, bm25_only=True, max_results=3)
    bm25_time = (time.time() - start) * 1000
    
    # Enhanced mode  
    start = time.time()
    enhanced_result = await search_code(query=query, bm25_only=False, max_results=3)
    enhanced_time = (time.time() - start) * 1000
    
    print(f'BM25: {bm25_time:.1f}ms, relevance: {bm25_result[\"data\"][\"items\"][0][\"relevance\"]:.3f}')
    print(f'Enhanced: {enhanced_time:.1f}ms, relevance: {enhanced_result[\"data\"][\"items\"][0][\"relevance\"]:.3f}')

asyncio.run(compare_modes())
"
```

### Phase 3: Result Analysis 📊

#### 3.1 Automated Report Generation
The test runner generates:
- **Summary Report**: Pass/fail rates, performance metrics
- **Detailed JSON**: Complete test results for analysis
- **Issue Classification**: P0-P3 severity levels
- **Recommendations**: Actionable next steps

#### 3.2 Manual Analysis Steps

**Performance Analysis:**
```python
# Analyze response time patterns
import json
with open('search_code_evaluation_report_YYYYMMDD_HHMMSS.json') as f:
    report = json.load(f)

# Check for performance regressions
perf = report['performance_summary']
print(f"P95 Response Time: {perf['p95_response_time_ms']:.1f}ms")
print(f"Average: {perf['avg_response_time_ms']:.1f}ms")

# Identify slow queries
slow_tests = [r for r in report['results'] if r['response_time_ms'] > 500]
print(f"Slow queries ({len(slow_tests)}): {[t['test_id'] for t in slow_tests]}")
```

**Quality Analysis:**
```python
# Analyze search quality patterns
quality_issues = [i for i in report['issues'] if i['category'] == 'search_quality']
repo_issues = [i for i in report['issues'] if i['category'] == 'repository_filtering']

print(f"Quality Issues: {len(quality_issues)}")
print(f"Repository Filtering Issues: {len(repo_issues)}")

# Check relevance score distribution
relevance_scores = []
for result in report['results']:
    if result['actual_results'] and result['actual_results'].get('data'):
        items = result['actual_results']['data'].get('items', [])
        for item in items:
            relevance_scores.append(item.get('relevance', 0))

print(f"Relevance Score Range: {min(relevance_scores):.3f} - {max(relevance_scores):.3f}")
```

#### 3.3 Trend Analysis
```python
# Compare with historical reports
import glob
import json
from datetime import datetime

report_files = sorted(glob.glob('search_code_evaluation_report_*.json'))
trends = []

for file in report_files[-5:]:  # Last 5 reports
    with open(file) as f:
        report = json.load(f)
    trends.append({
        'date': report['timestamp'],
        'pass_rate': report['passed_tests'] / report['total_tests'],
        'avg_time': report['performance_summary']['avg_response_time_ms'],
        'p95_time': report['performance_summary']['p95_response_time_ms']
    })

# Identify trends
for i in range(1, len(trends)):
    prev, curr = trends[i-1], trends[i]
    print(f"Pass Rate: {prev['pass_rate']:.2%} → {curr['pass_rate']:.2%}")
    print(f"Avg Time: {prev['avg_time']:.1f}ms → {curr['avg_time']:.1f}ms")
```

### Phase 4: Issue Triage and Resolution 🔧

#### 4.1 Issue Classification

**P0 - Critical (Fix Immediately)**
- Tool completely non-functional
- All tests failing with errors
- Security vulnerabilities

**P1 - High (Fix This Sprint)**
- Repository filtering broken
- Major performance regression (>2x slower)
- Search returning no results for known queries

**P2 - Medium (Fix Next Sprint)**  
- Poor relevance scores
- Missing content in results
- Non-critical feature not working

**P3 - Low (Fix When Possible)**
- Edge case failures
- Minor performance issues
- Documentation/formatting problems

#### 4.2 Common Issues and Resolutions

**Repository Filtering Not Working:**
```python
# Debug repository filtering
async def debug_repo_filter():
    # Test different repository values
    repos = ['mcprag', 'enhanced_rag', 'tests', 'nonexistent']
    
    for repo in repos:
        result = await search_code(query='test', repository=repo, max_results=3)
        items = result.get('data', {}).get('items', [])
        actual_repos = set(item.get('repository', '') for item in items)
        print(f"Requested: {repo}, Got repositories: {actual_repos}")

asyncio.run(debug_repo_filter())
```

**Low Relevance Scores:**
```python
# Compare BM25 vs Enhanced scoring
async def debug_scoring():
    query = "register_tools function"
    
    # BM25 mode
    bm25 = await search_code(query=query, bm25_only=True, max_results=5)
    enhanced = await search_code(query=query, bm25_only=False, max_results=5)
    
    print("BM25 Scores:", [item['relevance'] for item in bm25['data']['items']])
    print("Enhanced Scores:", [item['relevance'] for item in enhanced['data']['items']])
    
    # Check if enhanced mode is working
    if all(score < 0.1 for score in enhanced['data']['items']):
        print("🚨 Enhanced mode may have scoring issues")

asyncio.run(debug_scoring())
```

**Poor Content Extraction:**
```python
# Analyze empty content issues
async def debug_content():
    result = await search_code(query='server class', max_results=10)
    items = result.get('data', {}).get('items', [])
    
    empty_content = [item for item in items if not item.get('content', '').strip()]
    print(f"Empty content results: {len(empty_content)}/{len(items)}")
    
    for item in empty_content[:3]:
        print(f"  {item['file']} - {item.get('headlines', 'No headline')}")

asyncio.run(debug_content())
```

### Phase 5: Continuous Monitoring 📈

#### 5.1 Automated Monitoring Setup
```bash
# Set up cron job for daily regression tests
echo "0 2 * * * cd /home/azureuser/mcprag && python .claude/state/search_evaluation_runner.py --quick" | crontab -

# Weekly full evaluation
echo "0 1 * * 0 cd /home/azureuser/mcprag && python .claude/state/search_evaluation_runner.py --full" | crontab -
```

#### 5.2 Alert Thresholds
Set up monitoring alerts for:
- Pass rate drops below 85%
- P95 response time exceeds 1000ms
- More than 3 P1 issues detected
- Repository filtering accuracy below 90%

#### 5.3 Performance Baselines
Update expected performance baselines quarterly:

```python
# Calculate new baselines from recent successful runs
recent_reports = load_recent_reports(days=30)
successful_runs = [r for r in recent_reports if r['passed_tests'] / r['total_tests'] > 0.9]

new_baselines = {
    'avg_response_time_ms': percentile([r['performance_summary']['avg_response_time_ms'] for r in successful_runs], 80),
    'p95_response_time_ms': percentile([r['performance_summary']['p95_response_time_ms'] for r in successful_runs], 80),
    'min_pass_rate': min(r['passed_tests'] / r['total_tests'] for r in successful_runs)
}

print("Recommended new baselines:", new_baselines)
```

## Integration with Development Workflow

### Pre-Commit Testing
```bash
# Run quick smoke tests before commits
python .claude/state/search_evaluation_runner.py --smoke-test --max-time=30

# Gate commits on critical test failures
if [ $? -ne 0 ]; then
    echo "❌ Critical search tool tests failing - fix before commit"
    exit 1
fi
```

### CI/CD Integration
```yaml
# Example GitHub Actions integration
- name: Run Search Tool Evaluation  
  run: |
    python .claude/state/search_evaluation_runner.py --ci-mode
    
- name: Upload Test Results
  uses: actions/upload-artifact@v3
  with:
    name: search-evaluation-results
    path: search_code_evaluation_report_*.json
```

### Release Validation
```bash
# Pre-release evaluation with full test suite
python .claude/state/search_evaluation_runner.py --release-gate

# Require 95%+ pass rate for production deployments
if [ $(jq '.passed_tests / .total_tests' latest_report.json) < 0.95 ]; then
    echo "❌ Insufficient test pass rate for release"
    exit 1
fi
```

## Troubleshooting Guide

### Common Evaluation Failures

**1. MCP Tool Import Errors**
```bash
# Check MCP server is running
python -c "from mcprag.server import create_server; print('✅ Server module OK')"

# Verify tool registration
python -c "from mcprag.mcp.tools import register_tools; print('✅ Tools module OK')"
```

**2. Azure Search Connection Issues**
```bash
# Test Azure connectivity
python -c "from mcprag.config import Config; print(f'Endpoint: {Config.ACS_ENDPOINT}')"

# Verify credentials
python -m mcprag health_check
```

**3. Test Scenarios File Issues**
```python
# Validate JSON structure
import json
with open('.claude/state/search_code_test_scenarios.json') as f:
    scenarios = json.load(f)
    
# Check required fields
required_sections = ['test_scenarios', 'validation_rules', 'test_execution_order']
missing = [s for s in required_sections if s not in scenarios]
if missing:
    print(f"❌ Missing sections: {missing}")
else:
    print("✅ Scenarios file valid")
```

### Performance Debugging

**Slow Test Execution:**
```python
# Profile individual test performance
import cProfile
import pstats

pr = cProfile.Profile()
pr.enable()

# Run specific slow test
result = await search_code(query='complex query with many terms', max_results=50)

pr.disable()
stats = pstats.Stats(pr)
stats.sort_stats('cumulative')
stats.print_stats(10)
```

**Memory Issues:**
```python
# Monitor memory usage during tests
import psutil
import os

process = psutil.Process(os.getpid())
memory_before = process.memory_info().rss / 1024 / 1024  # MB

# Run evaluation
await evaluator.run_all_tests()

memory_after = process.memory_info().rss / 1024 / 1024  # MB
print(f"Memory usage: {memory_before:.1f}MB → {memory_after:.1f}MB (Δ{memory_after-memory_before:.1f}MB)")
```

## Maintenance Schedule

### Daily (Automated)
- Run smoke tests on core functionality
- Check for new P0/P1 issues
- Verify performance within baseline ranges

### Weekly (Semi-Automated)  
- Full evaluation suite execution
- Trend analysis vs previous week
- Update test scenarios for new features

### Monthly (Manual)
- Review and update golden dataset
- Analyze test coverage gaps
- Update performance baselines
- Stakeholder report generation

### Quarterly (Manual)
- Comprehensive evaluation framework review
- Test scenario validation and updates
- Integration with new development practices
- Tool evolution planning

This evaluation framework ensures systematic, repeatable testing of the search_code tool with actionable insights for continuous improvement.
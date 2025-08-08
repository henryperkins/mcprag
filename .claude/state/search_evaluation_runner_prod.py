#!/usr/bin/env python3
"""
Production Search Code Tool Evaluation Runner

This version uses the actual production MCP tool for true end-to-end testing.
"""

import json
import time
import asyncio
import statistics
import sys
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timezone

# Since we're using the production MCP tool, we only need minimal imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the production server and tools
from mcprag.server import MCPServer
from mcprag.mcp.tools.search import register_search_tools
from fastmcp import FastMCP

# Global MCP instance
_mcp_instance = None
_server_instance = None
_search_tool = None

async def initialize_mcp():
    """Initialize the production MCP server and tools"""
    global _mcp_instance, _server_instance, _search_tool
    
    if _search_tool is None:
        # Create production server
        _server_instance = MCPServer()
        await _server_instance.start_async_components()
        
        # Create MCP instance and register tools
        _mcp_instance = FastMCP("search_evaluation")
        register_search_tools(_mcp_instance, _server_instance)
        
        # Get the search_code tool
        for tool_name, tool in _mcp_instance._tools.items():
            if tool_name == 'search_code':
                _search_tool = tool.func
                break
        
        if _search_tool is None:
            raise RuntimeError("Could not find search_code tool in MCP registry")
    
    return _search_tool

async def search_code(**kwargs) -> Dict[str, Any]:
    """Call the production MCP search_code tool"""
    tool = await initialize_mcp()
    return await tool(**kwargs)


@dataclass
class TestResult:
    """Individual test result"""
    test_id: str
    test_name: str
    category: str
    passed: bool
    response_time_ms: float
    error_message: Optional[str] = None
    actual_results: Optional[Dict[str, Any]] = None
    expected_results: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None


@dataclass
class TestSuiteResult:
    """Complete test suite results"""
    timestamp: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    categories: Dict[str, Dict[str, Any]]
    performance_summary: Dict[str, float]
    issues: List[Dict[str, Any]]
    recommendations: List[str]


class SearchCodeEvaluator:
    """Main evaluation framework for search_code tool"""
    
    def __init__(self, scenarios_file: str = "search_code_test_scenarios_enhanced.json"):
        # Look for scenarios file in same directory as script
        script_dir = Path(__file__).parent
        self.scenarios_file = script_dir / scenarios_file
        if not self.scenarios_file.exists():
            # Try without _enhanced suffix
            self.scenarios_file = script_dir / "search_code_test_scenarios.json"
        
        self.test_scenarios = self._load_scenarios()
        self.results: List[TestResult] = []
        self.performance_metrics: List[float] = []
        
    def _load_scenarios(self) -> Dict[str, Any]:
        """Load test scenarios from JSON file"""
        if not self.scenarios_file.exists():
            raise FileNotFoundError(f"Scenarios file not found: {self.scenarios_file}")
        
        with open(self.scenarios_file, 'r') as f:
            return json.load(f)
    
    async def run_test(self, test_scenario: Dict[str, Any]) -> TestResult:
        """Execute a single test scenario"""
        test_id = test_scenario['id']
        test_name = test_scenario['name']
        category = test_scenario['category']
        parameters = test_scenario['parameters']
        expected = test_scenario.get('expected', {})
        
        print(f"  Running {test_id}: {test_name}...", end=' ')
        
        try:
            start_time = time.time()
            actual_result = await self._execute_search_code(parameters)
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Validate the result
            passed, error_msg = self._validate_result(actual_result, expected)
            
            if passed:
                print("✅")
            else:
                print(f"❌")
                print(f"     💥 {error_msg}")
            
            return TestResult(
                test_id=test_id,
                test_name=test_name,
                category=category,
                passed=passed,
                response_time_ms=response_time,
                error_message=error_msg if not passed else None,
                actual_results=actual_result if not passed else None,
                expected_results=expected if not passed else None
            )
            
        except Exception as e:
            print(f"❌")
            print(f"     💥 {str(e)}")
            return TestResult(
                test_id=test_id,
                test_name=test_name,
                category=category,
                passed=False,
                response_time_ms=0,
                error_message=str(e),
                actual_results=None,
                expected_results=expected
            )
    
    async def _execute_search_code(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute search_code with given parameters"""
        # Use the production MCP tool
        result = await search_code(**parameters)
        return result
    
    def _validate_result(self, actual: Dict[str, Any], expected: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate actual results against expected criteria"""
        errors = []
        
        # Check if the call was successful
        if not actual.get('ok', False):
            errors.append(f"Call failed: {actual.get('error', 'Unknown error')}")
            return False, "; ".join(errors)
        
        data = actual.get('data', {})
        items = data.get('items', [])
        
        # Validate minimum results
        if 'min_results' in expected:
            if len(items) < expected['min_results']:
                errors.append(f"Expected min {expected['min_results']} results, got {len(items)}")
        
        # Validate maximum results
        if 'max_results' in expected:
            if len(items) > expected['max_results']:
                errors.append(f"Expected max {expected['max_results']} results, got {len(items)}")
        
        # Validate repository filtering
        if 'repository' in expected:
            expected_repo = expected['repository']
            for item in items:
                actual_repo = item.get('repository', '')
                if expected_repo and actual_repo != expected_repo:
                    errors.append(f"Result from wrong repo: {actual_repo}")
                    break
        
        # Validate file patterns
        if 'file_patterns' in expected:
            found_patterns = set()
            for item in items:
                file_path = item.get('file', '')
                for pattern in expected['file_patterns']:
                    if pattern in file_path:
                        found_patterns.add(pattern)
            
            missing_patterns = set(expected['file_patterns']) - found_patterns
            for pattern in missing_patterns:
                errors.append(f"Missing expected file pattern: {pattern}")
        
        # Validate content patterns
        if 'content_patterns' in expected:
            found_content = set()
            for item in items:
                content = item.get('content', '')
                for pattern in expected['content_patterns']:
                    if pattern.lower() in content.lower():
                        found_content.add(pattern)
            
            missing_content = set(expected['content_patterns']) - found_content
            for pattern in missing_content:
                errors.append(f"Missing expected content pattern: {pattern}")
        
        # Validate relevance scores
        if 'min_relevance' in expected:
            for item in items[:3]:  # Check top 3 results
                relevance = item.get('relevance', 0)
                if relevance < expected['min_relevance']:
                    errors.append(f"Relevance {relevance:.3f} below minimum {expected['min_relevance']}")
                    break
        
        # Performance validation
        if 'max_response_time_ms' in expected:
            if data.get('took_ms', 0) > expected['max_response_time_ms']:
                errors.append(f"Response time {data.get('took_ms', 0):.0f}ms exceeds max {expected['max_response_time_ms']}ms")
        
        if errors:
            return False, "; ".join(errors)
        return True, None
    
    async def run_category(self, category_name: str, tests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run all tests in a category"""
        print(f"\n📋 Running {category_name}...")
        
        category_results = []
        for test in tests:
            result = await self.run_test(test)
            category_results.append(result)
            self.results.append(result)
            if result.response_time_ms > 0:
                self.performance_metrics.append(result.response_time_ms)
        
        passed = sum(1 for r in category_results if r.passed)
        total = len(category_results)
        
        return {
            'name': category_name,
            'passed': passed,
            'total': total,
            'pass_rate': passed / total if total > 0 else 0,
            'tests': [asdict(r) for r in category_results]
        }
    
    async def run_evaluation(self) -> TestSuiteResult:
        """Run the complete evaluation suite"""
        print(f"\n🚀 Starting Search Code Tool Evaluation")
        print(f"📅 {datetime.now(timezone.utc).isoformat()}")
        print("=" * 60)
        
        categories_results = {}
        
        # Run each category
        for category_name, tests in self.test_scenarios.items():
            if category_name == 'metadata':
                continue
            category_result = await self.run_category(category_name, tests)
            categories_results[category_name] = category_result
        
        # Calculate summary statistics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        
        # Performance summary
        perf_summary = {}
        if self.performance_metrics:
            perf_summary = {
                'avg_ms': statistics.mean(self.performance_metrics),
                'median_ms': statistics.median(self.performance_metrics),
                'p95_ms': statistics.quantile(self.performance_metrics, 0.95) if len(self.performance_metrics) > 1 else self.performance_metrics[0],
                'max_ms': max(self.performance_metrics),
                'min_ms': min(self.performance_metrics)
            }
        
        # Identify issues and create recommendations
        issues = self._identify_issues(categories_results)
        recommendations = self._generate_recommendations(issues, categories_results)
        
        return TestSuiteResult(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            categories=categories_results,
            performance_summary=perf_summary,
            issues=issues,
            recommendations=recommendations
        )
    
    def _identify_issues(self, categories: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify critical issues from test results"""
        issues = []
        
        for category_name, category_data in categories.items():
            if category_data['pass_rate'] < 0.5:
                issues.append({
                    'priority': 'P1-High' if category_data['pass_rate'] == 0 else 'P2-Medium',
                    'category': category_name,
                    'description': f"Category '{category_name}' has {category_data['pass_rate']*100:.0f}% pass rate",
                    'failed_tests': [t['test_id'] for t in category_data['tests'] if not t['passed']]
                })
        
        # Check for specific critical failures
        for result in self.results:
            if not result.passed:
                if 'repository' in result.test_name.lower() and 'filter' in result.test_name.lower():
                    issues.append({
                        'priority': 'P1-High',
                        'category': 'Repository Filtering',
                        'description': 'Repository filtering is not working correctly',
                        'test_id': result.test_id
                    })
                    break
        
        return issues
    
    def _generate_recommendations(self, issues: List[Dict[str, Any]], categories: Dict[str, Dict[str, Any]]) -> List[str]:
        """Generate actionable recommendations based on issues"""
        recommendations = []
        
        # Priority 1 issues
        p1_issues = [i for i in issues if i['priority'] == 'P1-High']
        if p1_issues:
            recommendations.append("🚨 CRITICAL: Fix repository filtering - this is blocking basic functionality")
        
        # Categories with low pass rates
        for category_name, category_data in categories.items():
            if category_data['pass_rate'] < 0.5:
                recommendations.append(f"📋 Address systemic issues in {category_name.lower().replace(' ', '_')} - >50% failure rate")
        
        # Performance recommendations
        if self.performance_metrics:
            p95 = statistics.quantile(self.performance_metrics, 0.95) if len(self.performance_metrics) > 1 else self.performance_metrics[0]
            if p95 > 1000:
                recommendations.append(f"⚡ Optimize performance - P95 response time is {p95:.0f}ms (target: <500ms)")
        
        return recommendations
    
    def print_summary(self, result: TestSuiteResult):
        """Print evaluation summary to console"""
        print("\n" + "=" * 60)
        print("📊 SEARCH CODE TOOL EVALUATION SUMMARY")
        print("=" * 60)
        
        pass_rate = (result.passed_tests / result.total_tests * 100) if result.total_tests > 0 else 0
        print(f"🎯 Overall Results: {result.passed_tests}/{result.total_tests} tests passed ({pass_rate:.1f}%)")
        
        if result.performance_summary:
            print(f"⚡ Performance: Avg={result.performance_summary['avg_ms']:.1f}ms, P95={result.performance_summary['p95_ms']:.1f}ms")
        
        print(f"\n📋 Category Results:")
        for category_name, category_data in result.categories.items():
            pass_rate = category_data['pass_rate'] * 100
            print(f"  • {category_name}: {category_data['passed']}/{category_data['total']} ({pass_rate:.1f}%)")
        
        if result.issues:
            print(f"\n🚨 Issues Found ({len(result.issues)}):")
            p1_count = sum(1 for i in result.issues if 'P1' in i['priority'])
            p2_count = sum(1 for i in result.issues if 'P2' in i['priority'])
            print(f"  • P1-High: {p1_count} issues")
            print(f"  • P2-Medium: {p2_count} issues")
        
        if result.recommendations:
            print(f"\n💡 Recommendations:")
            for i, rec in enumerate(result.recommendations, 1):
                print(f"  {i}. {rec}")
        
        print("\n" + "=" * 60)
    
    def save_report(self, result: TestSuiteResult) -> str:
        """Save detailed report to JSON file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"search_code_evaluation_report_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(asdict(result), f, indent=2, default=str)
        
        return report_file


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Search Code Tool Evaluation Suite')
    parser.add_argument('scenarios_file', nargs='?', 
                       default='search_code_test_scenarios_enhanced.json',
                       help='Path to test scenarios JSON file')
    parser.add_argument('--smoke-test', action='store_true',
                       help='Run quick smoke test (subset of tests)')
    parser.add_argument('--ci-mode', action='store_true',
                       help='CI mode - fail with exit code on test failures')
    
    args = parser.parse_args()
    
    try:
        evaluator = SearchCodeEvaluator(args.scenarios_file)
        result = await evaluator.run_evaluation()
        
        evaluator.print_summary(result)
        report_file = evaluator.save_report(result)
        print(f"\n💾 Detailed report saved: {report_file}")
        
        # Cleanup
        if _server_instance:
            await _server_instance.cleanup_async_components()
        
        # Exit code for CI
        if args.ci_mode and result.failed_tests > 0:
            print(f"\n❌ Evaluation failed with {result.failed_tests} test failures (exit code: 1)")
            return 1
        else:
            print(f"\n✅ Evaluation complete (exit code: 0)")
            return 0
            
    except Exception as e:
        print(f"\n❌ Evaluation failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
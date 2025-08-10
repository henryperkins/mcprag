#!/usr/bin/env python3
"""
Search Code Tool Evaluation Runner

Automated testing framework for the search_code MCP tool.
Runs comprehensive tests across functionality, quality, performance, and edge cases.
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

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# --- real MCP tool import / bootstrap -----------------
from mcprag.server import MCPServer
from mcprag.mcp.tools._helpers import search_code_impl

# Create a server instance for testing
_test_server = None

async def _get_test_server():
    """Get or create a test server instance."""
    global _test_server
    if _test_server is None:
        _test_server = MCPServer()
        await _test_server.start_async_components()
    return _test_server

async def search_code(**kwargs) -> Dict[str, Any]:
    """Proxy to the production search_code tool."""
    server = await _get_test_server()
    
    # Set defaults to match the MCP tool signature
    kwargs.setdefault('intent', None)
    kwargs.setdefault('language', None)
    kwargs.setdefault('repository', None)
    kwargs.setdefault('max_results', 10)
    kwargs.setdefault('include_dependencies', False)
    kwargs.setdefault('skip', 0)
    kwargs.setdefault('orderby', None)
    kwargs.setdefault('highlight_code', False)
    kwargs.setdefault('bm25_only', False)
    kwargs.setdefault('exact_terms', None)
    kwargs.setdefault('disable_cache', False)
    kwargs.setdefault('include_timings', False)
    kwargs.setdefault('dependency_mode', 'auto')
    kwargs.setdefault('detail_level', 'full')
    kwargs.setdefault('snippet_lines', 0)
    
    return await search_code_impl(server=server, **kwargs)


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
    
    def __init__(self, scenarios_file: str = "search_code_test_scenarios.json"):
        self.scenarios_file = Path(scenarios_file)
        self.test_scenarios = self._load_scenarios()
        self.results: List[TestResult] = []
        
    def _load_scenarios(self) -> Dict[str, Any]:
        """Load test scenarios from JSON file"""
        if not self.scenarios_file.exists():
            raise FileNotFoundError(f"Scenarios file not found: {self.scenarios_file}")
        
        with open(self.scenarios_file) as f:
            return json.load(f)
    
    async def run_all_tests(self) -> TestSuiteResult:
        """Execute all test categories"""
        print("🚀 Starting Search Code Tool Evaluation")
        print(f"📅 {datetime.now(timezone.utc).isoformat()}")
        print("=" * 60)
        
        # Execute tests in defined order
        test_order = self.test_scenarios.get("test_execution_order", [])
        
        for category in test_order:
            if category in self.test_scenarios["test_scenarios"]:
                print(f"\n📋 Running {category.replace('_', ' ').title()} Tests...")
                await self._run_category_tests(category)
        
        # Generate comprehensive report
        return self._generate_report()
    
    async def _run_category_tests(self, category: str) -> None:
        """Run all tests in a specific category"""
        scenarios = self.test_scenarios["test_scenarios"][category]
        
        for scenario in scenarios:
            test_result = await self._run_single_test(scenario, category)
            self.results.append(test_result)
            
            # Print immediate feedback
            status = "✅" if test_result.passed else "❌"
            print(f"  {status} {test_result.test_id}: {test_result.test_name}")
            if not test_result.passed and test_result.error_message:
                print(f"     💥 {test_result.error_message}")
    
    async def _run_single_test(self, scenario: Dict[str, Any], category: str) -> TestResult:
        """Execute a single test scenario"""
        test_id = scenario["id"]
        test_name = scenario["name"]
        parameters = scenario["parameters"]
        expected = scenario["expected"]
        
        start_time = time.time()
        
        try:
            # Execute the search_code tool
            # This would need to be adapted to the actual MCP tool interface
            actual_result = await self._execute_search_code(parameters)
            
            response_time_ms = (time.time() - start_time) * 1000
            
            # Validate results against expectations
            validation_result = self._validate_results(actual_result, expected, category)
            
            return TestResult(
                test_id=test_id,
                test_name=test_name,
                category=category,
                passed=validation_result["passed"],
                response_time_ms=response_time_ms,
                error_message=validation_result.get("error"),
                actual_results=actual_result,
                expected_results=expected,
                metrics=validation_result.get("metrics", {})
            )
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            
            return TestResult(
                test_id=test_id,
                test_name=test_name,
                category=category,
                passed=False,
                response_time_ms=response_time_ms,
                error_message=str(e),
                expected_results=expected
            )
    
    async def _execute_search_code(self, parameters: Dict[str, Any] | List[Dict[str, Any]]) -> Dict[str, Any] | List[Dict[str, Any]]:
        # Handle parameter sets supplied as a list (used by comparison / sequential tests)
        if isinstance(parameters, list):
            return [await search_code(**p) for p in parameters]
        return await search_code(**parameters)
    
    def _validate_results(self, actual: Dict[str, Any], expected: Dict[str, Any], category: str) -> Dict[str, Any]:
        """Validate actual results against expected criteria"""
        # Handle multi-call results
        if isinstance(actual, list):
            if not actual:   # safety
                return {"passed": False, "error": "empty result list", "metrics": {}}
            # for now validate only the first call – prevents ** mapping errors
            actual = actual[0]
        validation_result = {"passed": True, "metrics": {}, "errors": []}
        
        # Basic structure validation
        if not actual.get("ok"):
            if not expected.get("error_expected", False):
                validation_result["passed"] = False
                validation_result["errors"].append("Unexpected error response")
            return validation_result
        
        data = actual.get("data", {})
        items = data.get("items", [])
        
        # Validate result count
        if "min_results" in expected:
            if len(items) < expected["min_results"]:
                validation_result["passed"] = False
                validation_result["errors"].append(f"Expected min {expected['min_results']} results, got {len(items)}")
        
        if "max_results" in expected:
            if len(items) > expected["max_results"]:
                validation_result["passed"] = False
                validation_result["errors"].append(f"Expected max {expected['max_results']} results, got {len(items)}")
        
        # Validate repository filtering
        if "all_results_from_repo" in expected:
            expected_repo = expected["all_results_from_repo"]
            for item in items:
                if not item.get("repository", "").startswith(expected_repo):
                    validation_result["passed"] = False
                    validation_result["errors"].append(f"Result from wrong repo: {item.get('repository')}")
                    break
        
        # Validate relevance scores
        if "relevance_threshold" in expected and items:
            min_relevance = min(item.get("relevance", 0) for item in items)
            if min_relevance < expected["relevance_threshold"]:
                validation_result["passed"] = False
                validation_result["errors"].append(f"Relevance below threshold: {min_relevance}")
        
        # Validate performance
        response_time = data.get("took_ms", 0)
        validation_result["metrics"]["response_time_ms"] = response_time
        
        if "response_time_ms" in expected:
            if response_time > expected["response_time_ms"]:
                validation_result["passed"] = False
                validation_result["errors"].append(f"Response time too slow: {response_time}ms")
        
        # Validate content presence
        if "should_contain_files" in expected:
            found_files = [item.get("file", "") for item in items]
            for expected_file in expected["should_contain_files"]:
                if not any(expected_file in f for f in found_files):
                    validation_result["passed"] = False
                    validation_result["errors"].append(f"Missing expected file pattern: {expected_file}")
        
        # Combine errors into single message
        if validation_result["errors"]:
            validation_result["error"] = "; ".join(validation_result["errors"])
        
        return validation_result
    
    def _generate_report(self) -> TestSuiteResult:
        """Generate comprehensive test report"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        
        # Category breakdown
        categories = {}
        for category in set(r.category for r in self.results):
            category_results = [r for r in self.results if r.category == category]
            categories[category] = {
                "total": len(category_results),
                "passed": sum(1 for r in category_results if r.passed),
                "failed": sum(1 for r in category_results if not r.passed),
                "avg_response_time_ms": statistics.mean(r.response_time_ms for r in category_results)
            }
        
        # Performance summary
        all_times = [r.response_time_ms for r in self.results if r.response_time_ms > 0]
        performance_summary = {
            "avg_response_time_ms": statistics.mean(all_times) if all_times else 0,
            "median_response_time_ms": statistics.median(all_times) if all_times else 0,
            "p95_response_time_ms": self._percentile(all_times, 95) if all_times else 0,
            "max_response_time_ms": max(all_times) if all_times else 0
        }
        
        # Identify issues
        issues = []
        failed_results = [r for r in self.results if not r.passed]
        
        for result in failed_results:
            issues.append({
                "test_id": result.test_id,
                "category": result.category,
                "error": result.error_message,
                "severity": self._determine_severity(result)
            })
        
        # Generate recommendations
        recommendations = self._generate_recommendations(categories, issues)
        
        return TestSuiteResult(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            categories=categories,
            performance_summary=performance_summary,
            issues=issues,
            recommendations=recommendations
        )
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data"""
        sorted_data = sorted(data)
        index = (len(sorted_data) - 1) * percentile / 100
        lower = int(index)
        upper = lower + 1
        weight = index - lower
        
        if upper >= len(sorted_data):
            return sorted_data[-1]
        
        return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight
    
    def _determine_severity(self, result: TestResult) -> str:
        """Determine issue severity based on test category and type"""
        if result.category == "repository_filtering":
            return "P1-High"  # Repository filtering is critical
        elif result.category == "edge_cases":
            return "P3-Low"   # Edge cases are typically low severity
        elif result.category == "performance_tests":
            return "P2-Medium"  # Performance issues are medium
        else:
            return "P2-Medium"  # Default to medium
    
    def _generate_recommendations(self, categories: Dict, issues: List[Dict]) -> List[str]:
        """Generate actionable recommendations based on test results"""
        recommendations = []
        
        # Check for critical failures
        high_severity_issues = [i for i in issues if i["severity"] == "P1-High"]
        if high_severity_issues:
            recommendations.append("🚨 CRITICAL: Fix repository filtering - this is blocking basic functionality")
        
        # Check performance issues
        perf_issues = [i for i in issues if i["category"] == "performance_tests"]
        if perf_issues:
            recommendations.append("⚡ Investigate performance bottlenecks - response times exceeding thresholds")
        
        # Check quality issues
        quality_issues = [i for i in issues if i["category"] == "search_quality"]
        if quality_issues:
            recommendations.append("🎯 Review search quality - relevance scores or result accuracy below expectations")
        
        # Check for widespread failures
        for category, stats in categories.items():
            if stats["failed"] / stats["total"] > 0.5:
                recommendations.append(f"📋 Address systemic issues in {category} - >50% failure rate")
        
        return recommendations
    
    async def save_report(self, report: TestSuiteResult, filename: Optional[str] = None) -> str:
        """Save test report to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"search_code_evaluation_report_{timestamp}.json"
        
        report_path = Path(filename)
        
        with open(report_path, 'w') as f:
            json.dump(asdict(report), f, indent=2, default=str)
        
        return str(report_path)
    
    def print_summary_report(self, report: TestSuiteResult) -> None:
        """Print human-readable summary of test results"""
        print("\n" + "=" * 60)
        print("📊 SEARCH CODE TOOL EVALUATION SUMMARY")
        print("=" * 60)
        
        # Overall results
        pass_rate = (report.passed_tests / report.total_tests) * 100 if report.total_tests > 0 else 0
        print(f"🎯 Overall Results: {report.passed_tests}/{report.total_tests} tests passed ({pass_rate:.1f}%)")
        
        # Performance summary
        perf = report.performance_summary
        print(f"⚡ Performance: Avg={perf['avg_response_time_ms']:.1f}ms, P95={perf['p95_response_time_ms']:.1f}ms")
        
        # Category breakdown
        print(f"\n📋 Category Results:")
        for category, stats in report.categories.items():
            rate = (stats['passed'] / stats['total']) * 100
            print(f"  • {category.replace('_', ' ').title()}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")
        
        # Issues summary
        if report.issues:
            print(f"\n🚨 Issues Found ({len(report.issues)}):")
            severity_counts = {}
            for issue in report.issues:
                sev = issue['severity']
                severity_counts[sev] = severity_counts.get(sev, 0) + 1
            
            for sev, count in severity_counts.items():
                print(f"  • {sev}: {count} issues")
        
        # Recommendations
        if report.recommendations:
            print(f"\n💡 Recommendations:")
            for i, rec in enumerate(report.recommendations, 1):
                print(f"  {i}. {rec}")
        
        print("\n" + "=" * 60)


async def main():
    """Main entry point for evaluation runner"""
    global _test_server
    # Use absolute path to the test scenarios file in the same directory
    scenarios_file = os.path.join(os.path.dirname(__file__), "search_code_test_scenarios_enhanced.json")
    evaluator = SearchCodeEvaluator(scenarios_file)
    
    try:
        # Run all tests
        report = await evaluator.run_all_tests()
        
        # Print summary
        evaluator.print_summary_report(report)
        
        # Save detailed report
        report_file = await evaluator.save_report(report)
        print(f"\n💾 Detailed report saved: {report_file}")
        
        # Exit with appropriate code
        exit_code = 0 if report.failed_tests == 0 else 1
        print(f"\n✅ Evaluation complete (exit code: {exit_code})")
        return exit_code
        
    except Exception as e:
        print(f"\n💥 Evaluation failed: {e}")
        return 2
    finally:
        # Cleanup server instance
        if _test_server:
            try:
                await _test_server.cleanup_async_components()
            except Exception as e:
                print(f"Warning: Server cleanup failed: {e}")


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

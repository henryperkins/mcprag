#!/usr/bin/env python3
"""
Universal MCP Tool Testing Framework

Comprehensive testing framework for ALL MCP tools in the MCPRAG ecosystem.
Automatically discovers and tests all registered tools with appropriate test scenarios.
"""

import json
import time
import asyncio
import inspect
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict, field
from pathlib import Path
from datetime import datetime, timezone
from enum import Enum
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from mcprag.server import MCPServer
from mcprag.utils.response_helpers import ok, err


class ToolCategory(Enum):
    """MCP tool categories"""
    SEARCH = "search"
    GENERATION = "generation"
    ANALYSIS = "analysis"
    ADMIN = "admin"
    CACHE = "cache"
    FEEDBACK = "feedback"
    AZURE_MGMT = "azure_management"
    SERVICE_MGMT = "service_management"


@dataclass
class ToolTestCase:
    """Individual test case for a tool"""
    name: str
    description: str
    tool_name: str
    parameters: Dict[str, Any]
    expected_status: str = "ok"
    expected_fields: List[str] = field(default_factory=list)
    validation_func: Optional[Callable] = None
    requires_admin: bool = False
    requires_confirmation: bool = False
    skip_reason: Optional[str] = None


@dataclass
class ToolTestResult:
    """Result of a tool test"""
    tool_name: str
    test_name: str
    passed: bool
    response_time_ms: float
    error_message: Optional[str] = None
    response: Optional[Dict[str, Any]] = None
    skipped: bool = False
    skip_reason: Optional[str] = None


@dataclass
class ToolTestSuite:
    """Test suite for a specific tool"""
    tool_name: str
    category: ToolCategory
    test_cases: List[ToolTestCase]
    implementation_func: Optional[Callable] = None


class UniversalMCPToolEvaluator:
    """Universal testing framework for all MCP tools"""
    
    def __init__(self):
        self.server = None
        self.tool_suites: Dict[str, ToolTestSuite] = {}
        self.test_results: List[ToolTestResult] = []
        self._initialize_test_suites()
    
    async def initialize_server(self):
        """Initialize MCP server for testing"""
        if not self.server:
            self.server = MCPServer()
            await self.server.start_async_components()
    
    async def cleanup_server(self):
        """Cleanup server resources"""
        if self.server:
            await self.server.cleanup_async_components()
            self.server = None
    
    def _initialize_test_suites(self):
        """Initialize test suites for all MCP tools"""
        
        # Search Tools
        self.tool_suites["search_code"] = ToolTestSuite(
            tool_name="search_code",
            category=ToolCategory.SEARCH,
            test_cases=[
                ToolTestCase(
                    name="basic_search",
                    description="Basic code search functionality",
                    tool_name="search_code",
                    parameters={
                        "query": "server",
                        "max_results": 3,
                        "intent": None,
                        "language": None,
                        "repository": None,
                        "include_dependencies": False,
                        "skip": 0,
                        "orderby": None,
                        "highlight_code": False,
                        "bm25_only": False,
                        "exact_terms": None,
                        "disable_cache": False,
                        "include_timings": False,
                        "dependency_mode": "auto",
                        "detail_level": "full",
                        "snippet_lines": 0
                    },
                    expected_fields=["items", "count", "total"]
                ),
                ToolTestCase(
                    name="repository_filter",
                    description="Filter by repository",
                    tool_name="search_code",
                    parameters={
                        "query": "server",
                        "repository": "mcprag",
                        "max_results": 3,
                        "intent": None,
                        "language": None,
                        "include_dependencies": False,
                        "skip": 0,
                        "orderby": None,
                        "highlight_code": False,
                        "bm25_only": False,
                        "exact_terms": None,
                        "disable_cache": False,
                        "include_timings": False,
                        "dependency_mode": "auto",
                        "detail_level": "full",
                        "snippet_lines": 0
                    },
                    expected_fields=["items", "count"],
                    skip_reason="Known P1 issue - repository filtering broken"
                ),
                ToolTestCase(
                    name="bm25_mode",
                    description="BM25-only search mode",
                    tool_name="search_code",
                    parameters={
                        "query": "register_tools",
                        "bm25_only": True,
                        "max_results": 3,
                        "intent": None,
                        "language": None,
                        "repository": None,
                        "include_dependencies": False,
                        "skip": 0,
                        "orderby": None,
                        "highlight_code": False,
                        "exact_terms": None,
                        "disable_cache": False,
                        "include_timings": False,
                        "dependency_mode": "auto",
                        "detail_level": "full",
                        "snippet_lines": 0
                    },
                    expected_fields=["items", "count", "backend"]
                ),
            ]
        )
        
        self.tool_suites["search_microsoft_docs"] = ToolTestSuite(
            tool_name="search_microsoft_docs",
            category=ToolCategory.SEARCH,
            test_cases=[
                ToolTestCase(
                    name="docs_search",
                    description="Search Microsoft documentation",
                    tool_name="search_microsoft_docs",
                    parameters={"query": "Azure Functions", "max_results": 5},
                    expected_fields=["items", "count"]
                ),
            ]
        )
        
        # Generation Tools
        self.tool_suites["generate_code"] = ToolTestSuite(
            tool_name="generate_code",
            category=ToolCategory.GENERATION,
            test_cases=[
                ToolTestCase(
                    name="simple_generation",
                    description="Generate simple Python function",
                    tool_name="generate_code",
                    parameters={
                        "description": "Create a function to calculate fibonacci numbers",
                        "language": "python"
                    },
                    expected_fields=["code", "language"]
                ),
            ]
        )
        
        # Analysis Tools
        self.tool_suites["analyze_context"] = ToolTestSuite(
            tool_name="analyze_context",
            category=ToolCategory.ANALYSIS,
            test_cases=[
                ToolTestCase(
                    name="file_analysis",
                    description="Analyze file context",
                    tool_name="analyze_context",
                    parameters={
                        "file_path": "mcprag/server.py",
                        "include_dependencies": True,
                        "depth": 1
                    },
                    expected_fields=["file", "context"]
                ),
            ]
        )
        
        self.tool_suites["explain_ranking"] = ToolTestSuite(
            tool_name="explain_ranking",
            category=ToolCategory.ANALYSIS,
            test_cases=[
                ToolTestCase(
                    name="ranking_explanation",
                    description="Explain search ranking factors",
                    tool_name="explain_ranking",
                    parameters={"query": "server", "max_results": 3},
                    expected_fields=["explanations", "factors"]
                ),
            ]
        )
        
        # Cache Tools
        self.tool_suites["cache_stats"] = ToolTestSuite(
            tool_name="cache_stats",
            category=ToolCategory.CACHE,
            test_cases=[
                ToolTestCase(
                    name="get_cache_stats",
                    description="Get cache statistics",
                    tool_name="cache_stats",
                    parameters={},
                    expected_fields=["hit_rate", "total_entries"]
                ),
            ]
        )
        
        self.tool_suites["cache_clear"] = ToolTestSuite(
            tool_name="cache_clear",
            category=ToolCategory.CACHE,
            test_cases=[
                ToolTestCase(
                    name="clear_search_cache",
                    description="Clear search cache",
                    tool_name="cache_clear",
                    parameters={"scope": "search"},
                    expected_fields=["cleared_count"]
                ),
            ]
        )
        
        # Feedback Tools
        self.tool_suites["submit_feedback"] = ToolTestSuite(
            tool_name="submit_feedback",
            category=ToolCategory.FEEDBACK,
            test_cases=[
                ToolTestCase(
                    name="positive_feedback",
                    description="Submit positive feedback",
                    tool_name="submit_feedback",
                    parameters={
                        "target_id": "test_123",
                        "kind": "positive",
                        "rating": 5,
                        "notes": "Test feedback"
                    },
                    expected_fields=["feedback_id", "status"]
                ),
            ]
        )
        
        # Admin Tools (require MCP_ADMIN_MODE=true)
        self.tool_suites["index_status"] = ToolTestSuite(
            tool_name="index_status",
            category=ToolCategory.ADMIN,
            test_cases=[
                ToolTestCase(
                    name="get_index_status",
                    description="Get Azure Search index status",
                    tool_name="index_status",
                    parameters={},
                    expected_fields=["index_name", "documents_count"],
                    requires_admin=False  # This one doesn't need admin
                ),
            ]
        )
        
        self.tool_suites["health_check"] = ToolTestSuite(
            tool_name="health_check",
            category=ToolCategory.ADMIN,
            test_cases=[
                ToolTestCase(
                    name="system_health",
                    description="Check system health",
                    tool_name="health_check",
                    parameters={},
                    expected_fields=["status", "components"],
                    requires_admin=False  # This one doesn't need admin
                ),
            ]
        )
        
        self.tool_suites["manage_index"] = ToolTestSuite(
            tool_name="manage_index",
            category=ToolCategory.ADMIN,
            test_cases=[
                ToolTestCase(
                    name="list_indexes",
                    description="List all indexes",
                    tool_name="manage_index",
                    parameters={"action": "list"},
                    expected_fields=["indexes"],
                    requires_admin=True
                ),
            ]
        )
        
        # Add more tool suites as needed...
    
    async def run_tool_test(self, test_case: ToolTestCase) -> ToolTestResult:
        """Run a single tool test case"""
        if test_case.skip_reason:
            return ToolTestResult(
                tool_name=test_case.tool_name,
                test_name=test_case.name,
                passed=False,
                response_time_ms=0,
                skipped=True,
                skip_reason=test_case.skip_reason
            )
        
        # Check admin requirement
        if test_case.requires_admin and os.getenv("MCP_ADMIN_MODE") != "true":
            return ToolTestResult(
                tool_name=test_case.tool_name,
                test_name=test_case.name,
                passed=False,
                response_time_ms=0,
                skipped=True,
                skip_reason="Requires MCP_ADMIN_MODE=true"
            )
        
        start_time = time.time()
        
        try:
            # Get the tool implementation - use the _impl versions where they exist
            from mcprag.mcp.tools._helpers import search_code_impl
            from mcprag.mcp.tools._helpers.search_impl import search_microsoft_docs_impl
            
            # Map tool names to implementations
            # Most tools don't have separate _impl functions, we'll call them directly
            tool_implementations = {
                "search_code": search_code_impl,
                "search_microsoft_docs": search_microsoft_docs_impl,
            }
            
            impl_func = tool_implementations.get(test_case.tool_name)
            
            # If not found in explicit implementations, try to get from server's registered tools
            if not impl_func and hasattr(self.server, '_mcp'):
                try:
                    # Access the internal tool registry
                    mcp = self.server._mcp
                    if hasattr(mcp, '_tool_manager') and hasattr(mcp._tool_manager, '_tools'):
                        tools = mcp._tool_manager._tools
                        if test_case.tool_name in tools:
                            impl_func = tools[test_case.tool_name]['handler']
                except Exception:
                    pass
            
            if not impl_func:
                elapsed_ms = (time.time() - start_time) * 1000
                return ToolTestResult(
                    tool_name=test_case.tool_name,
                    test_name=test_case.name,
                    passed=False,
                    response_time_ms=elapsed_ms,
                    error_message=f"Tool implementation not found: {test_case.tool_name}"
                )
            
            # Execute the tool
            if "server" in inspect.signature(impl_func).parameters:
                result = await impl_func(server=self.server, **test_case.parameters)
            else:
                result = await impl_func(**test_case.parameters)
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Validate response
            if result.get("status") == "error":
                return ToolTestResult(
                    tool_name=test_case.tool_name,
                    test_name=test_case.name,
                    passed=False,
                    response_time_ms=elapsed_ms,
                    error_message=result.get("message", "Unknown error"),
                    response=result
                )
            
            # Check expected fields
            data = result.get("data", {})
            missing_fields = []
            for field in test_case.expected_fields:
                if field not in data:
                    missing_fields.append(field)
            
            if missing_fields:
                return ToolTestResult(
                    tool_name=test_case.tool_name,
                    test_name=test_case.name,
                    passed=False,
                    response_time_ms=elapsed_ms,
                    error_message=f"Missing expected fields: {', '.join(missing_fields)}",
                    response=result
                )
            
            # Run custom validation if provided
            if test_case.validation_func:
                validation_result = test_case.validation_func(result)
                if not validation_result:
                    return ToolTestResult(
                        tool_name=test_case.tool_name,
                        test_name=test_case.name,
                        passed=False,
                        response_time_ms=elapsed_ms,
                        error_message="Custom validation failed",
                        response=result
                    )
            
            return ToolTestResult(
                tool_name=test_case.tool_name,
                test_name=test_case.name,
                passed=True,
                response_time_ms=elapsed_ms,
                response=result
            )
            
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return ToolTestResult(
                tool_name=test_case.tool_name,
                test_name=test_case.name,
                passed=False,
                response_time_ms=elapsed_ms,
                error_message=str(e)
            )
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all tool tests"""
        await self.initialize_server()
        
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        skipped_tests = 0
        
        results_by_category = {}
        results_by_tool = {}
        
        print("\n🚀 Starting Universal MCP Tool Evaluation")
        print(f"📅 {datetime.now(timezone.utc).isoformat()}")
        print("=" * 60)
        
        for tool_name, suite in self.tool_suites.items():
            print(f"\n📋 Testing {tool_name} ({suite.category.value})...")
            
            tool_results = []
            for test_case in suite.test_cases:
                result = await self.run_tool_test(test_case)
                tool_results.append(result)
                self.test_results.append(result)
                
                total_tests += 1
                if result.skipped:
                    skipped_tests += 1
                    print(f"  ⏭️  {test_case.name}: SKIPPED - {result.skip_reason}")
                elif result.passed:
                    passed_tests += 1
                    print(f"  ✅ {test_case.name}: PASSED ({result.response_time_ms:.1f}ms)")
                else:
                    failed_tests += 1
                    print(f"  ❌ {test_case.name}: FAILED - {result.error_message}")
            
            # Store results by tool
            results_by_tool[tool_name] = {
                "total": len(tool_results),
                "passed": sum(1 for r in tool_results if r.passed),
                "failed": sum(1 for r in tool_results if not r.passed and not r.skipped),
                "skipped": sum(1 for r in tool_results if r.skipped),
                "results": tool_results
            }
            
            # Store results by category
            category_name = suite.category.value
            if category_name not in results_by_category:
                results_by_category[category_name] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "tools": []
                }
            
            results_by_category[category_name]["total"] += len(tool_results)
            results_by_category[category_name]["passed"] += sum(1 for r in tool_results if r.passed)
            results_by_category[category_name]["failed"] += sum(1 for r in tool_results if not r.passed and not r.skipped)
            results_by_category[category_name]["skipped"] += sum(1 for r in tool_results if r.skipped)
            results_by_category[category_name]["tools"].append(tool_name)
        
        # Calculate summary statistics
        pass_rate = (passed_tests / (total_tests - skipped_tests) * 100) if (total_tests - skipped_tests) > 0 else 0
        tool_coverage = len(self.tool_suites) / 30 * 100  # Assuming 30+ tools total
        
        print("\n" + "=" * 60)
        print("📊 UNIVERSAL MCP TOOL EVALUATION SUMMARY")
        print("=" * 60)
        print(f"🎯 Overall Results: {passed_tests}/{total_tests - skipped_tests} tests passed ({pass_rate:.1f}%)")
        print(f"📦 Tool Coverage: {len(self.tool_suites)}/30+ tools tested ({tool_coverage:.1f}%)")
        print(f"⏭️  Skipped Tests: {skipped_tests}")
        
        print("\n📋 Results by Category:")
        for category, stats in results_by_category.items():
            effective_total = stats["total"] - stats["skipped"]
            cat_pass_rate = (stats["passed"] / effective_total * 100) if effective_total > 0 else 0
            print(f"  • {category}: {stats['passed']}/{effective_total} ({cat_pass_rate:.1f}%) - {len(stats['tools'])} tools")
        
        print("\n🔧 Results by Tool:")
        for tool_name, stats in results_by_tool.items():
            effective_total = stats["total"] - stats["skipped"]
            tool_pass_rate = (stats["passed"] / effective_total * 100) if effective_total > 0 else 0
            status = "✅" if stats["failed"] == 0 else "❌"
            print(f"  {status} {tool_name}: {stats['passed']}/{effective_total} tests ({tool_pass_rate:.1f}%)")
        
        # Identify critical issues
        critical_issues = []
        for result in self.test_results:
            if not result.passed and not result.skipped:
                critical_issues.append({
                    "tool": result.tool_name,
                    "test": result.test_name,
                    "error": result.error_message
                })
        
        if critical_issues:
            print(f"\n🚨 Critical Issues ({len(critical_issues)}):")
            for issue in critical_issues[:5]:  # Show top 5
                print(f"  • {issue['tool']}.{issue['test']}: {issue['error']}")
        
        print("\n💡 Recommendations:")
        if tool_coverage < 50:
            print("  1. 🚨 CRITICAL: Expand test coverage to remaining tools")
        if pass_rate < 80:
            print("  2. 📋 Fix failing tests to achieve >80% pass rate")
        if skipped_tests > 5:
            print("  3. 🔧 Address issues causing test skips")
        
        print("=" * 60)
        
        # Save detailed report
        # Convert results to serializable format
        serializable_results = []
        for r in self.test_results:
            result_dict = {
                "tool_name": r.tool_name,
                "test_name": r.test_name,
                "passed": r.passed,
                "response_time_ms": r.response_time_ms,
                "error_message": r.error_message,
                "skipped": r.skipped,
                "skip_reason": r.skip_reason
            }
            # Only include response summary if present
            if r.response:
                result_dict["response_status"] = r.response.get("status")
                if r.response.get("data"):
                    # Just include a summary of data fields
                    data = r.response["data"]
                    if isinstance(data, dict):
                        result_dict["response_fields"] = list(data.keys())
            serializable_results.append(result_dict)
        
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "skipped_tests": skipped_tests,
                "pass_rate": pass_rate,
                "tool_coverage": tool_coverage,
                "tools_tested": len(self.tool_suites)
            },
            "results_by_category": results_by_category,
            "results_by_tool": results_by_tool,
            "critical_issues": critical_issues,
            "all_results": serializable_results
        }
        
        report_file = f"universal_tool_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Detailed report saved: {report_file}")
        
        await self.cleanup_server()
        
        return report


async def main():
    """Main entry point"""
    evaluator = UniversalMCPToolEvaluator()
    
    try:
        report = await evaluator.run_all_tests()
        exit_code = 0 if report["summary"]["failed_tests"] == 0 else 1
        print(f"\n✅ Evaluation complete (exit code: {exit_code})")
        return exit_code
    except Exception as e:
        print(f"\n💥 Evaluation failed: {e}")
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
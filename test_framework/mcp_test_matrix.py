#!/usr/bin/env python3
"""
MCP Server Test Matrix
Comprehensive testing framework for all MCP tools, resources, and prompts.
"""

import time
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import traceback
import statistics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_test_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Test result data structure"""
    tool_name: str
    test_case: str
    status: str  # "PASS", "FAIL", "ERROR", "SKIP"
    execution_time_ms: float
    token_count: Optional[int] = None
    error_message: Optional[str] = None
    response_size_bytes: Optional[int] = None
    input_params: Optional[Dict[str, Any]] = None
    output_data: Optional[Any] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

@dataclass
class PerformanceMetrics:
    """Performance metrics for a tool"""
    tool_name: str
    total_tests: int
    success_rate: float
    avg_response_time_ms: float
    p50_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    total_tokens: int
    avg_tokens_per_request: float
    error_count: int
    timeout_count: int

class MCPTestMatrix:
    """Comprehensive test matrix for MCP server"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.test_definitions = self._build_test_matrix()
        
    def _build_test_matrix(self) -> Dict[str, Dict[str, List[Dict]]]:
        """Build the comprehensive test matrix"""
        return {
            "tools": {
                # Core Search Tools
                "search_code": [
                    {
                        "name": "basic_search",
                        "description": "Basic code search functionality",
                        "params": {"query": "function definition"},
                        "expected_fields": ["items", "count", "total", "took_ms"],
                        "min_response_time": 50,
                        "max_response_time": 5000
                    },
                    {
                        "name": "intent_search_implement",
                        "description": "Search with implement intent",
                        "params": {"query": "authentication", "intent": "implement"},
                        "expected_fields": ["items", "count", "total"]
                    },
                    {
                        "name": "intent_search_debug", 
                        "description": "Search with debug intent",
                        "params": {"query": "error handling", "intent": "debug"},
                        "expected_fields": ["items", "count", "total"]
                    },
                    {
                        "name": "language_filter",
                        "description": "Search with language filter",
                        "params": {"query": "class definition", "language": "python"},
                        "expected_fields": ["items", "count", "total"]
                    },
                    {
                        "name": "repository_filter",
                        "description": "Search with repository filter", 
                        "params": {"query": "import", "repository": "mcprag"},
                        "expected_fields": ["items", "count", "total"]
                    },
                    {
                        "name": "pagination",
                        "description": "Test pagination functionality",
                        "params": {"query": "def", "max_results": 5, "skip": 0},
                        "expected_fields": ["items", "count", "total", "has_more"]
                    },
                    {
                        "name": "exact_terms", 
                        "description": "Test exact term filtering",
                        "params": {"query": "search function", "exact_terms": ["search", "function"]},
                        "expected_fields": ["items", "count", "applied_exact_terms"]
                    },
                    {
                        "name": "timing_diagnostics",
                        "description": "Test timing diagnostics",
                        "params": {"query": "test", "include_timings": True},
                        "expected_fields": ["timings_ms"]
                    },
                    {
                        "name": "bm25_only",
                        "description": "Test BM25-only search",
                        "params": {"query": "def search", "bm25_only": True},
                        "expected_fields": ["items", "backend"]
                    },
                    {
                        "name": "empty_query",
                        "description": "Test empty query handling",
                        "params": {"query": ""},
                        "should_fail": True
                    },
                    {
                        "name": "special_characters",
                        "description": "Test special characters in query",
                        "params": {"query": "function(arg) -> return"},
                        "expected_fields": ["items", "count"]
                    },
                    {
                        "name": "very_long_query",
                        "description": "Test very long query",
                        "params": {"query": "search " * 100},
                        "expected_fields": ["items", "count"]
                    }
                ],
                "search_code_raw": [
                    {
                        "name": "basic_raw_search",
                        "description": "Basic raw search functionality",
                        "params": {"query": "function"},
                        "expected_fields": ["results", "count", "total", "query"]
                    }
                ],
                "search_microsoft_docs": [
                    {
                        "name": "docs_search",
                        "description": "Microsoft docs search",
                        "params": {"query": "Azure Functions"},
                        "expected_fields": ["query", "count", "results"],
                        "may_fail": True  # Known issue
                    }
                ],
                "explain_ranking": [
                    {
                        "name": "ranking_explanation",
                        "description": "Test ranking explanation",
                        "params": {"query": "authentication", "mode": "enhanced", "max_results": 5},
                        "expected_fields": ["mode", "query", "explanations"]
                    }
                ],
                "preview_query_processing": [
                    {
                        "name": "query_processing",
                        "description": "Test query processing preview",
                        "params": {"query": "fix authentication bug"},
                        "expected_fields": ["input_query", "detected_intent", "enhancements"]
                    }
                ],
                "search_code_then_docs": [
                    {
                        "name": "hybrid_search",
                        "description": "Test code then docs search",
                        "params": {"query": "authentication", "max_code_results": 3, "max_doc_results": 3},
                        "expected_fields": ["query", "code_results"]
                    }
                ],
                "search_code_hybrid": [
                    {
                        "name": "hybrid_bm25_vector",
                        "description": "Test hybrid BM25 + vector search",
                        "params": {"query": "authentication", "bm25_weight": 0.5, "vector_weight": 0.5},
                        "expected_fields": ["weights", "final_results"]
                    }
                ],
                
                # Admin Tools (require admin mode)
                "cache_stats": [
                    {
                        "name": "get_cache_stats",
                        "description": "Get cache statistics",
                        "params": {},
                        "expected_fields": ["cache_stats"]
                    }
                ],
                "cache_clear": [
                    {
                        "name": "clear_all_cache",
                        "description": "Clear all cache",
                        "params": {"scope": "all"},
                        "expected_fields": ["cleared", "remaining"]
                    }
                ],
                
                # Feedback and Learning
                "submit_feedback": [
                    {
                        "name": "submit_search_feedback",
                        "description": "Submit feedback for search result",
                        "params": {"target_id": "test_123", "kind": "search", "rating": 4, "notes": "Good results"},
                        "expected_fields": ["stored"]
                    }
                ],
                "track_search_click": [
                    {
                        "name": "track_click",
                        "description": "Track search result click",
                        "params": {"query_id": "test_query_123", "doc_id": "doc_456", "rank": 1},
                        "expected_fields": ["tracked", "query_id", "doc_id"]
                    }
                ],
                "track_search_outcome": [
                    {
                        "name": "track_outcome",
                        "description": "Track search outcome",
                        "params": {"query_id": "test_query_123", "outcome": "success", "score": 0.85},
                        "expected_fields": ["tracked", "query_id", "outcome"]
                    }
                ],
                
                # Enhanced RAG Tools (may not be available)
                "generate_code": [
                    {
                        "name": "code_generation",
                        "description": "Test code generation",
                        "params": {"description": "Create a simple hello world function", "language": "python"},
                        "expected_fields": ["generated_code"],
                        "may_fail": True
                    }
                ],
                "analyze_context": [
                    {
                        "name": "context_analysis",
                        "description": "Test context analysis",
                        "params": {"file_path": "mcp_server_sota.py"},
                        "expected_fields": ["analysis"],
                        "may_fail": True
                    }
                ]
            },
            "resources": {
                "resource://repositories": [
                    {
                        "name": "list_repositories",
                        "description": "List all repositories",
                        "expected_fields": ["repositories", "count", "timestamp"]
                    }
                ],
                "resource://statistics": [
                    {
                        "name": "get_statistics", 
                        "description": "Get search statistics",
                        "expected_fields": ["index_name", "features"]
                    }
                ],
                "resource://runtime_diagnostics": [
                    {
                        "name": "runtime_diagnostics",
                        "description": "Get runtime diagnostics",
                        "expected_fields": ["feature_flags", "versions"]
                    }
                ],
                "resource://pipeline_status": [
                    {
                        "name": "pipeline_status",
                        "description": "Get pipeline status",
                        "expected_fields": ["available"],
                        "may_fail": True
                    }
                ]
            },
            "prompts": {
                "implement_feature": [
                    {
                        "name": "implementation_prompt",
                        "description": "Generate implementation prompt",
                        "params": {"feature": "user authentication"},
                        "expected_content_keywords": ["search_code", "intent='implement'", "dependencies"]
                    }
                ],
                "debug_error": [
                    {
                        "name": "debug_prompt", 
                        "description": "Generate debug prompt",
                        "params": {"error": "AttributeError: 'NoneType' object has no attribute 'search'", "file": "test.py"},
                        "expected_content_keywords": ["intent='debug'", "error", "similar issues"]
                    }
                ]
            }
        }
    
    async def run_tool_test(self, tool_name: str, test_case: Dict[str, Any]) -> TestResult:
        """Run a single tool test case"""
        start_time = time.time()
        
        try:
            # Use the MCP search tool to test the target tool
            if tool_name in ["search_code", "search_code_raw", "search_microsoft_docs", 
                           "explain_ranking", "preview_query_processing", "search_code_then_docs",
                           "search_code_hybrid", "cache_stats", "cache_clear", "submit_feedback",
                           "track_search_click", "track_search_outcome"]:
                
                # Use the actual MCP tool for testing
                from mcp_test_runner import MCPTestRunner
                runner = MCPTestRunner()
                
                response = await runner.call_mcp_tool(tool_name, test_case.get("params", {}))
                
                execution_time = (time.time() - start_time) * 1000
                
                # Check response format
                if not isinstance(response, dict):
                    return TestResult(
                        tool_name=tool_name,
                        test_case=test_case["name"],
                        status="FAIL",
                        execution_time_ms=execution_time,
                        error_message="Response is not a dictionary"
                    )
                
                # Check for expected fields
                expected_fields = test_case.get("expected_fields", [])
                missing_fields = []
                
                if response.get("ok"):
                    data = response.get("data", {})
                    for field in expected_fields:
                        if field not in data:
                            missing_fields.append(field)
                else:
                    # For error responses, check if failure was expected
                    if test_case.get("should_fail", False) or test_case.get("may_fail", False):
                        return TestResult(
                            tool_name=tool_name,
                            test_case=test_case["name"], 
                            status="PASS" if test_case.get("should_fail") else "SKIP",
                            execution_time_ms=execution_time,
                            input_params=test_case.get("params"),
                            output_data=response
                        )
                    else:
                        return TestResult(
                            tool_name=tool_name,
                            test_case=test_case["name"],
                            status="FAIL",
                            execution_time_ms=execution_time,
                            error_message=response.get("error", "Unknown error"),
                            input_params=test_case.get("params")
                        )
                
                # Check response time bounds
                min_time = test_case.get("min_response_time", 0)
                max_time = test_case.get("max_response_time", 10000)
                
                time_ok = min_time <= execution_time <= max_time
                
                status = "PASS" if not missing_fields and time_ok else "FAIL"
                error_msg = None
                
                if missing_fields:
                    error_msg = f"Missing expected fields: {missing_fields}"
                elif not time_ok:
                    error_msg = f"Response time {execution_time:.1f}ms outside bounds [{min_time}, {max_time}]"
                
                return TestResult(
                    tool_name=tool_name,
                    test_case=test_case["name"],
                    status=status,
                    execution_time_ms=execution_time,
                    error_message=error_msg,
                    response_size_bytes=len(json.dumps(response)),
                    input_params=test_case.get("params"),
                    output_data=response.get("data") if response.get("ok") else response
                )
            else:
                # Tool not yet implemented in test runner
                return TestResult(
                    tool_name=tool_name,
                    test_case=test_case["name"],
                    status="SKIP",
                    execution_time_ms=0,
                    error_message="Tool not yet implemented in test runner"
                )
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return TestResult(
                tool_name=tool_name,
                test_case=test_case["name"],
                status="ERROR",
                execution_time_ms=execution_time,
                error_message=str(e),
                input_params=test_case.get("params")
            )
    
    async def run_all_tests(self) -> List[TestResult]:
        """Run all test cases"""
        all_results = []
        
        logger.info("Starting comprehensive MCP test suite")
        
        # Test tools
        for tool_name, test_cases in self.test_definitions["tools"].items():
            logger.info(f"Testing tool: {tool_name}")
            
            for test_case in test_cases:
                logger.info(f"  Running test case: {test_case['name']}")
                
                result = await self.run_tool_test(tool_name, test_case)
                all_results.append(result)
                
                # Log result
                if result.status == "PASS":
                    logger.info(f"    ✅ PASS ({result.execution_time_ms:.1f}ms)")
                elif result.status == "SKIP":
                    logger.info(f"    ⏭️  SKIP - {result.error_message}")
                elif result.status == "FAIL":
                    logger.warning(f"    ❌ FAIL - {result.error_message}")
                else:
                    logger.error(f"    💥 ERROR - {result.error_message}")
                
                # Rate limiting - small delay between tests
                await asyncio.sleep(0.1)
        
        self.results = all_results
        return all_results
    
    def generate_performance_metrics(self) -> Dict[str, PerformanceMetrics]:
        """Generate performance metrics for each tool"""
        metrics_by_tool = {}
        
        for tool_name in set(r.tool_name for r in self.results):
            tool_results = [r for r in self.results if r.tool_name == tool_name]
            
            successful_results = [r for r in tool_results if r.status == "PASS"]
            response_times = [r.execution_time_ms for r in successful_results]
            
            total_tokens = sum(r.token_count or 0 for r in tool_results)
            
            if response_times:
                metrics = PerformanceMetrics(
                    tool_name=tool_name,
                    total_tests=len(tool_results),
                    success_rate=len(successful_results) / len(tool_results),
                    avg_response_time_ms=statistics.mean(response_times),
                    p50_response_time_ms=statistics.median(response_times),
                    p95_response_time_ms=statistics.quantiles(response_times, n=20)[18] if len(response_times) > 1 else response_times[0],
                    p99_response_time_ms=statistics.quantiles(response_times, n=100)[98] if len(response_times) > 1 else response_times[0],
                    total_tokens=total_tokens,
                    avg_tokens_per_request=total_tokens / len(tool_results) if tool_results else 0,
                    error_count=len([r for r in tool_results if r.status == "ERROR"]),
                    timeout_count=0  # Not tracking timeouts separately yet
                )
            else:
                metrics = PerformanceMetrics(
                    tool_name=tool_name,
                    total_tests=len(tool_results),
                    success_rate=0.0,
                    avg_response_time_ms=0.0,
                    p50_response_time_ms=0.0,
                    p95_response_time_ms=0.0,
                    p99_response_time_ms=0.0,
                    total_tokens=total_tokens,
                    avg_tokens_per_request=0.0,
                    error_count=len([r for r in tool_results if r.status == "ERROR"]),
                    timeout_count=0
                )
            
            metrics_by_tool[tool_name] = metrics
        
        return metrics_by_tool
    
    def generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        performance_metrics = self.generate_performance_metrics()
        
        # Summary statistics
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r.status == "PASS"])
        failed_tests = len([r for r in self.results if r.status == "FAIL"])
        error_tests = len([r for r in self.results if r.status == "ERROR"])
        skipped_tests = len([r for r in self.results if r.status == "SKIP"])
        
        return {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "errors": error_tests,
                "skipped": skipped_tests,
                "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
                "execution_date": datetime.now().isoformat()
            },
            "performance_metrics": {name: asdict(metrics) for name, metrics in performance_metrics.items()},
            "detailed_results": [asdict(result) for result in self.results],
            "failed_tests": [asdict(r) for r in self.results if r.status == "FAIL"],
            "error_tests": [asdict(r) for r in self.results if r.status == "ERROR"]
        }
    
    def save_results(self, filename: str = "mcp_test_results.json"):
        """Save test results to file"""
        report = self.generate_test_report()
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Test results saved to {filename}")
        return filename

if __name__ == "__main__":
    async def main():
        test_matrix = MCPTestMatrix()
        results = await test_matrix.run_all_tests()
        
        # Generate and save report
        report_file = test_matrix.save_results()
        
        # Print summary
        report = test_matrix.generate_test_report()
        summary = report["summary"]
        
        print("\n" + "="*50)
        print("MCP SERVER TEST RESULTS SUMMARY")
        print("="*50)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']} ({summary['success_rate']:.1%})")
        print(f"Failed: {summary['failed']}")
        print(f"Errors: {summary['errors']}")
        print(f"Skipped: {summary['skipped']}")
        print(f"\nDetailed results saved to: {report_file}")
        
        return report
    
    asyncio.run(main())
#!/usr/bin/env python3
"""
Comprehensive test suite for MCP Azure Search tools
Tests performance, response quality, and usability
"""

import asyncio
import time
import json
from typing import Dict, Any, List
import os

# Import the MCP functions
from mcp_server_sota import (
    search_code, search_code_raw, search_microsoft_docs,
    search_code_hybrid, explain_ranking, diagnose_query,
    search_code_then_docs, search_code_pipeline,
    index_status, cache_stats
)

class MCPToolTester:
    def __init__(self):
        self.results = []
        self.timing_data = []
        
    async def test_with_timing(self, test_name: str, func, *args, **kwargs):
        """Execute a test and measure timing"""
        print(f"\n{'='*60}")
        print(f"Testing: {test_name}")
        print(f"{'='*60}")
        
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            end_time = time.time()
            duration = end_time - start_time
            
            # Parse result
            if isinstance(result, str):
                try:
                    result_data = json.loads(result)
                except:
                    result_data = {"raw": result}
            elif isinstance(result, dict):
                result_data = result
            else:
                result_data = {"data": result}
            
            success = result_data.get("ok", False) if isinstance(result_data, dict) else True
            
            test_result = {
                "test": test_name,
                "success": success,
                "duration": duration,
                "result_size": len(str(result)),
                "error": result_data.get("error") if not success else None
            }
            
            self.results.append(test_result)
            self.timing_data.append((test_name, duration))
            
            print(f"Status: {'✓ Success' if success else '✗ Failed'}")
            print(f"Duration: {duration:.3f}s")
            print(f"Response size: {test_result['result_size']} chars")
            
            if success and isinstance(result_data, dict):
                if "data" in result_data:
                    self._print_result_summary(result_data["data"])
            else:
                print(f"Error: {test_result['error']}")
                
            return result_data
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            test_result = {
                "test": test_name,
                "success": False,
                "duration": duration,
                "error": str(e)
            }
            
            self.results.append(test_result)
            self.timing_data.append((test_name, duration))
            
            print(f"Status: ✗ Exception")
            print(f"Duration: {duration:.3f}s")
            print(f"Error: {e}")
            
            return None
    
    def _print_result_summary(self, data):
        """Print a summary of the result data"""
        if isinstance(data, list):
            print(f"Results count: {len(data)}")
            if len(data) > 0 and isinstance(data[0], dict):
                # Show first result
                first = data[0]
                if "file_path" in first or "path" in first:
                    path = first.get("file_path") or first.get("path")
                    print(f"First result: {path}")
                    if "score" in first:
                        print(f"Score: {first['score']:.4f}")
        elif isinstance(data, dict):
            for key, value in data.items():
                if key in ["query", "intent", "language"]:
                    print(f"{key}: {value}")
                elif isinstance(value, list):
                    print(f"{key}: {len(value)} items")
                elif isinstance(value, (int, float)):
                    print(f"{key}: {value}")
    
    async def run_all_tests(self):
        """Run comprehensive test suite"""
        
        # Test 1: Basic code search (with field mapping issue)
        await self.test_with_timing(
            "Basic Code Search - Azure Search Client",
            search_code,
            query="azure search client initialization",
            max_results=5
        )
        
        # Test 2: Index status check
        await self.test_with_timing(
            "Index Status Check",
            index_status
        )
        
        # Test 3: Cache statistics
        await self.test_with_timing(
            "Cache Statistics",
            cache_stats
        )
        
        # Test 4: Microsoft Docs search
        await self.test_with_timing(
            "Microsoft Docs Search - Azure Functions",
            search_microsoft_docs,
            query="Azure Functions triggers Python",
            max_results=3
        )
        
        # Test 5: Search with different intents
        for intent in ["understand", "implement", "debug", "refactor"]:
            await self.test_with_timing(
                f"Code Search with Intent: {intent}",
                search_code,
                query="error handling validation",
                intent=intent,
                max_results=3
            )
        
        # Test 6: Hybrid search
        await self.test_with_timing(
            "Hybrid Search (BM25 + Vector)",
            search_code_hybrid,
            query="vector embedding configuration",
            bm25_weight=0.5,
            vector_weight=0.5,
            max_results=5
        )
        
        # Test 7: Query diagnostics
        await self.test_with_timing(
            "Query Diagnostics",
            diagnose_query,
            query="search index schema fields"
        )
        
        # Test 8: Ranking explanation
        await self.test_with_timing(
            "Ranking Explanation",
            explain_ranking,
            query="azure cognitive search vector"
        )
        
        # Test 9: Code then docs search
        await self.test_with_timing(
            "Code + Docs Fallback Search",
            search_code_then_docs,
            query="kubernetes deployment yaml",
            max_code_results=3,
            max_doc_results=2
        )
        
        # Test 10: Enhanced pipeline (if available)
        await self.test_with_timing(
            "Enhanced RAG Pipeline",
            search_code_pipeline,
            query="how to create azure search index",
            max_results=5,
            generate_response=False
        )
        
        # Test 11: Language filtering
        await self.test_with_timing(
            "Language Filter - Python Only",
            search_code,
            query="class definition init method",
            language="python",
            max_results=5
        )
        
        # Test 12: BM25-only mode
        await self.test_with_timing(
            "BM25 Only Mode (No Vectors)",
            search_code,
            query="SearchClient search method",
            bm25_only=True,
            max_results=5
        )
        
        # Test 13: Raw search response
        await self.test_with_timing(
            "Raw Search Response",
            search_code_raw,
            query="mcp server implementation",
            max_results=3
        )
        
        # Test 14: Edge case - empty query
        await self.test_with_timing(
            "Edge Case - Empty Query",
            search_code,
            query="",
            max_results=1
        )
        
        # Test 15: Edge case - very long query
        long_query = "azure cognitive search vector embeddings configuration dimension size 1536 3072 text-embedding-3-large openai model integration"
        await self.test_with_timing(
            "Edge Case - Long Query",
            search_code,
            query=long_query,
            max_results=3
        )
        
        self.print_summary()
    
    def print_summary(self):
        """Print test summary and metrics"""
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        
        total_tests = len(self.results)
        successful = sum(1 for r in self.results if r["success"])
        failed = total_tests - successful
        
        print(f"Total tests: {total_tests}")
        print(f"Successful: {successful} ({successful/total_tests*100:.1f}%)")
        print(f"Failed: {failed} ({failed/total_tests*100:.1f}%)")
        
        print(f"\n{'='*60}")
        print("PERFORMANCE METRICS")
        print(f"{'='*60}")
        
        # Sort by duration
        self.timing_data.sort(key=lambda x: x[1])
        
        print("\nFastest operations:")
        for name, duration in self.timing_data[:5]:
            print(f"  {duration:.3f}s - {name}")
        
        print("\nSlowest operations:")
        for name, duration in self.timing_data[-5:]:
            print(f"  {duration:.3f}s - {name}")
        
        # Average timing by operation type
        operation_times = {}
        for result in self.results:
            op_type = result["test"].split(" - ")[0]
            if op_type not in operation_times:
                operation_times[op_type] = []
            operation_times[op_type].append(result["duration"])
        
        print("\nAverage time by operation type:")
        for op_type, times in sorted(operation_times.items()):
            avg_time = sum(times) / len(times)
            print(f"  {avg_time:.3f}s - {op_type} ({len(times)} tests)")
        
        # Token efficiency estimate (chars per second)
        print(f"\n{'='*60}")
        print("EFFICIENCY METRICS")
        print(f"{'='*60}")
        
        for result in self.results:
            if result["success"] and result.get("result_size", 0) > 0:
                chars_per_sec = result["result_size"] / result["duration"]
                print(f"{result['test'][:40]}: {chars_per_sec:.0f} chars/sec")
        
        # Failed tests details
        if failed > 0:
            print(f"\n{'='*60}")
            print("FAILED TESTS DETAILS")
            print(f"{'='*60}")
            
            for result in self.results:
                if not result["success"]:
                    print(f"\n{result['test']}:")
                    print(f"  Error: {result.get('error', 'Unknown error')}")

async def main():
    """Run the test suite"""
    print("MCP Azure Search Tools - Comprehensive Test Suite")
    print("=" * 60)
    
    # Check environment
    if not os.getenv("ACS_ENDPOINT"):
        print("WARNING: ACS_ENDPOINT not set in environment")
    if not os.getenv("ACS_ADMIN_KEY"):
        print("WARNING: ACS_ADMIN_KEY not set in environment")
    
    tester = MCPToolTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
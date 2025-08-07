#!/usr/bin/env python3
"""Test script for the enhanced MCP framework."""

import asyncio
import time
from mcprag.mcp.enhanced_wrapper import enhance_mcp_tool, global_mcp_registry
from mcprag.mcp.utils import RateLimitConfig, RateLimitError, ValidationError


# Example MCP tool implementations for testing
@enhance_mcp_tool(
    tool_name="search_code",
    rate_limit_config=RateLimitConfig(max_requests=5, window_seconds=10),
    enable_validation=True,
    enable_sanitization=True,
    enable_metrics=True
)
async def search_code(query: str, max_results: int = 10, language: str = None):
    """Mock search_code tool for testing."""
    await asyncio.sleep(0.1)  # Simulate processing time
    return {
        "results": [
            {"file": f"test_{i}.py", "line": i, "content": f"// {query} result {i}"}
            for i in range(min(max_results or 10, 3))
        ],
        "query": query,
        "language": language
    }


@enhance_mcp_tool(
    tool_name="analyze_context", 
    rate_limit_config=RateLimitConfig(max_requests=10, window_seconds=60),
    enable_validation=True
)
async def analyze_context(file_path: str, depth: int = 2, include_dependencies: bool = True):
    """Mock analyze_context tool for testing."""
    await asyncio.sleep(0.2)  # Simulate processing time
    return {
        "file_path": file_path,
        "depth": depth,
        "dependencies": ["dep1", "dep2"] if include_dependencies else [],
        "analysis": f"Analysis of {file_path} at depth {depth}"
    }


async def test_basic_functionality():
    """Test basic tool functionality."""
    print("=== Testing Basic Functionality ===")
    
    # Test search_code (use keyword arguments for validation)
    result = await search_code(query="test query", max_results=2)
    print(f"✅ search_code result: {len(result['results'])} results")
    
    # Test analyze_context (use keyword arguments for validation)
    result = await analyze_context(file_path="/path/to/file.py", depth=3)
    print(f"✅ analyze_context result: {result['analysis']}")


async def test_input_validation():
    """Test input validation."""
    print("\n=== Testing Input Validation ===")
    
    try:
        # Test with invalid query (empty string)
        await search_code(query="", max_results=5)
        print("❌ Should have failed validation for empty query")
    except ValidationError as e:
        print(f"✅ Validation correctly rejected empty query: {e}")
    
    try:
        # Test with invalid max_results (too high)
        await search_code(query="test", max_results=1000)
        print("❌ Should have failed validation for max_results > 100")
    except ValidationError as e:
        print(f"✅ Validation correctly rejected max_results > 100: {e}")
    
    try:
        # Test with invalid language (contains numbers)
        await search_code(query="test", language="python123")
        print("❌ Should have failed validation for invalid language")
    except ValidationError as e:
        print(f"✅ Validation correctly rejected invalid language: {e}")


async def test_rate_limiting():
    """Test rate limiting."""
    print("\n=== Testing Rate Limiting ===")
    
    # Make rapid requests to trigger rate limiting
    successful_requests = 0
    rate_limited_requests = 0
    
    for i in range(8):  # Try 8 requests (limit is 5)
        try:
            await search_code(query=f"query {i}")
            successful_requests += 1
            print(f"✅ Request {i+1} succeeded")
        except RateLimitError as e:
            rate_limited_requests += 1
            print(f"🚫 Request {i+1} rate limited: {e}")
    
    print(f"Results: {successful_requests} successful, {rate_limited_requests} rate limited")
    
    if rate_limited_requests > 0:
        print("✅ Rate limiting working correctly")
    else:
        print("❌ Rate limiting may not be working")


async def test_input_sanitization():
    """Test input sanitization."""
    print("\n=== Testing Input Sanitization ===")
    
    # Test with potentially dangerous input (use analyze_context to avoid rate limit)
    dangerous_path = "<script>alert('xss')</script>/path/to/malicious.js"
    result = await analyze_context(file_path=dangerous_path)
    
    # Check if the dangerous content was sanitized
    if "<script>" not in str(result):
        print("✅ Input sanitization working - script tags removed")
    else:
        print("❌ Input sanitization may not be working")


def test_metrics():
    """Test metrics collection."""
    print("\n=== Testing Metrics Collection ===")
    
    # Get metrics for search_code tool
    metrics = global_mcp_registry.get_tool_metrics("search_code")
    
    if metrics:
        print(f"✅ Metrics collected:")
        print(f"  - Total calls: {metrics['total_calls']}")
        print(f"  - Successful calls: {metrics['successful_calls']}")
        print(f"  - Failed calls: {metrics['failed_calls']}")
        print(f"  - Rate limited calls: {metrics['rate_limited_calls']}")
        print(f"  - Success rate: {metrics['success_rate']:.1f}%")
        print(f"  - Average response time: {metrics['average_response_time_ms']:.1f}ms")
    else:
        print("❌ No metrics collected")


def test_registry():
    """Test tool registry functionality."""
    print("\n=== Testing Tool Registry ===")
    
    # List all registered tools
    tools = global_mcp_registry.list_tools()
    print(f"✅ Registered tools: {list(tools.keys())}")
    
    # Check tool configurations
    for tool_name, config in tools.items():
        print(f"  - {tool_name}:")
        print(f"    Rate limiting: {config['rate_limit_enabled']}")
        print(f"    Validation: {config['validation_enabled']}")
        print(f"    Sanitization: {config['sanitization_enabled']}")
        print(f"    Metrics: {config['metrics_enabled']}")
    
    # Get all metrics
    all_metrics = global_mcp_registry.get_all_metrics()
    print(f"✅ Collected metrics for {len(all_metrics)} tools")


async def main():
    """Run all tests."""
    print("🧪 Testing Enhanced MCP Framework\n")
    
    try:
        await test_basic_functionality()
        await test_input_validation()
        await test_rate_limiting()
        await test_input_sanitization()
        test_metrics()
        test_registry()
        
        print("\n🎉 All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
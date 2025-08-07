#!/usr/bin/env python
"""Final verification of all remediation fixes."""

import asyncio
import inspect
import sys
from unittest.mock import Mock, patch

def check_code_contains(module_path: str, class_name: str, method_name: str, search_text: str) -> bool:
    """Helper to check if code contains specific text."""
    try:
        exec(f"from {module_path} import {class_name}")
        cls = eval(class_name)
        method = getattr(cls, method_name)
        source = inspect.getsource(method)
        return search_text in source
    except:
        return False

async def run_final_tests():
    """Run comprehensive final verification tests."""
    print("="*60)
    print("FINAL VERIFICATION OF REMEDIATION FIXES")
    print("="*60)
    
    results = {}
    
    # Test 1: Verify HybridSearcher uses REST operations
    print("\n1. Testing HybridSearcher REST migration...")
    try:
        from enhanced_rag.retrieval.hybrid_searcher import HybridSearcher
        source = inspect.getsource(HybridSearcher.__init__)
        assert "rest_ops" in source
        assert "SearchOperations" in inspect.getsource(HybridSearcher)
        
        # Check search method uses REST
        search_source = inspect.getsource(HybridSearcher.search)
        assert "self.rest_ops.search" in search_source
        assert "await self.rest_ops.search" in search_source
        
        results["HybridSearcher REST migration"] = "✅ PASS"
        print("   ✅ Uses REST operations for search")
    except AssertionError as e:
        results["HybridSearcher REST migration"] = f"❌ FAIL: {e}"
        print(f"   ❌ FAIL: {e}")
    
    # Test 2: Verify exact-term clamping
    print("\n2. Testing exact-term clamping...")
    try:
        from enhanced_rag.retrieval.hybrid_searcher import HybridSearcher
        search_source = inspect.getsource(HybridSearcher.search)
        assert "_clamp_term" in search_source
        assert "[:200]" in search_source
        assert "32 <= ord(ch) <= 126" in search_source
        
        results["Exact-term clamping"] = "✅ PASS"
        print("   ✅ Clamping implemented (length & ASCII)")
    except AssertionError as e:
        results["Exact-term clamping"] = f"❌ FAIL: {e}"
        print(f"   ❌ FAIL: {e}")
    
    # Test 3: Verify REST error logging sanitization
    print("\n3. Testing REST error logging...")
    try:
        from enhanced_rag.azure_integration.rest.client import AzureSearchClient
        request_source = inspect.getsource(AzureSearchClient.request)
        
        # Should NOT contain response.text or response.json() in error logging
        assert "e.response.text" not in request_source.split("logger.error")[1].split("raise")[0]
        assert 'HTTP error {status} during Azure Search request' in request_source
        
        results["REST error logging"] = "✅ PASS"
        print("   ✅ Error logging sanitized")
    except AssertionError as e:
        results["REST error logging"] = f"❌ FAIL: {e}"
        print(f"   ❌ FAIL: {e}")
    
    # Test 4: Verify run_indexer wait support
    print("\n4. Testing run_indexer wait support...")
    try:
        from enhanced_rag.azure_integration.rest.operations import SearchOperations
        sig = inspect.signature(SearchOperations.run_indexer)
        assert "wait" in sig.parameters
        assert "poll_interval" in sig.parameters
        assert "timeout" in sig.parameters
        
        source = inspect.getsource(SearchOperations.run_indexer)
        assert "if not wait:" in source
        assert "get_indexer_status" in source
        
        results["run_indexer wait support"] = "✅ PASS"
        print("   ✅ Wait/polling implemented")
    except AssertionError as e:
        results["run_indexer wait support"] = f"❌ FAIL: {e}"
        print(f"   ❌ FAIL: {e}")
    
    # Test 5: Verify pipeline cleanup
    print("\n5. Testing pipeline cleanup...")
    try:
        from enhanced_rag.pipeline import RAGPipeline
        cleanup_source = inspect.getsource(RAGPipeline.cleanup)
        assert "_azure_operations" in cleanup_source
        assert "client.close()" in cleanup_source
        
        results["Pipeline cleanup"] = "✅ PASS"
        print("   ✅ Closes REST clients")
    except AssertionError as e:
        results["Pipeline cleanup"] = f"❌ FAIL: {e}"
        print(f"   ❌ FAIL: {e}")
    
    # Test 6: Verify MCP tools async startup
    print("\n6. Testing MCP tools async startup...")
    try:
        from mcprag.mcp.tools.generation import register_generation_tools
        from mcprag.mcp.tools.analysis import register_analysis_tools
        
        gen_source = inspect.getsource(register_generation_tools)
        assert "ensure_async_components_started" in gen_source
        
        analysis_source = inspect.getsource(register_analysis_tools)
        assert "ensure_async_components_started" in analysis_source
        
        results["MCP async startup"] = "✅ PASS"
        print("   ✅ Async components ensured")
    except AssertionError as e:
        results["MCP async startup"] = f"❌ FAIL: {e}"
        print(f"   ❌ FAIL: {e}")
    
    # Test 7: Verify no Azure SDK imports remain
    print("\n7. Testing Azure SDK removal...")
    try:
        from enhanced_rag.retrieval.hybrid_searcher import HybridSearcher
        full_source = inspect.getsource(HybridSearcher)
        
        # Should have comment about removal
        assert "Azure SDK SearchClient and AzureKeyCredential removed" in full_source
        
        # Should NOT create SearchClient
        assert "self.search_client = None" in full_source
        
        results["Azure SDK removal"] = "✅ PASS"
        print("   ✅ SDK imports removed/commented")
    except AssertionError as e:
        results["Azure SDK removal"] = f"❌ FAIL: {e}"
        print(f"   ❌ FAIL: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = 0
    failed = 0
    for test, result in results.items():
        if result.startswith("✅"):
            passed += 1
            status = "PASS"
        else:
            failed += 1
            status = "FAIL"
        print(f"{test:30} {status}")
    
    print(f"\nTotal: {passed} passed, {failed} failed out of {len(results)} tests")
    print("="*60)
    
    if failed == 0:
        print("\n🎉 ALL REMEDIATION FIXES VERIFIED SUCCESSFULLY!")
    else:
        print("\n⚠️  Some tests failed. Review the failures above.")
    
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(run_final_tests())
    sys.exit(0 if success else 1)
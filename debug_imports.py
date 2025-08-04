#!/usr/bin/env python3
"""Debug script to check why enhanced RAG imports are failing"""

import sys
import traceback
import os

print("Testing enhanced_rag imports...")
print(f"Python path: {sys.path}")
print(f"Current directory: {os.getcwd()}")
print("-" * 80)

# Test individual imports
try:
    from enhanced_rag.mcp_integration.enhanced_search_tool import EnhancedSearchTool
    print("✅ EnhancedSearchTool imported successfully")
except Exception as e:
    print(f"❌ EnhancedSearchTool import failed: {e}")
    traceback.print_exc()

try:
    from enhanced_rag.mcp_integration.code_gen_tool import CodeGenerationTool
    print("✅ CodeGenerationTool imported successfully")
except Exception as e:
    print(f"❌ CodeGenerationTool import failed: {e}")
    traceback.print_exc()

try:
    from enhanced_rag.mcp_integration.context_aware_tool import ContextAwareTool
    print("✅ ContextAwareTool imported successfully")
except Exception as e:
    print(f"❌ ContextAwareTool import failed: {e}")
    traceback.print_exc()

# Test pipeline import
try:
    from enhanced_rag.pipeline import RAGPipeline
    print("✅ RAGPipeline imported successfully")
except Exception as e:
    print(f"❌ RAGPipeline import failed: {e}")
    traceback.print_exc()

# Test retrieval imports
try:
    from enhanced_rag.retrieval.hybrid_searcher import HybridSearcher
    print("✅ HybridSearcher imported successfully")
except Exception as e:
    print(f"❌ HybridSearcher import failed: {e}")
    traceback.print_exc()

print("\n" + "-" * 80 + "\n")
print("Testing REST API imports...")

# Test REST API imports - the critical ones for new tools
try:
    from enhanced_rag.azure_integration.rest import AzureSearchClient, SearchOperations
    print("✅ REST API client imports successful")
except Exception as e:
    print(f"❌ REST API client import failed: {e}")
    traceback.print_exc()
    
    # Try individual imports to narrow down the issue
    print("\nTrying individual REST imports:")
    try:
        from enhanced_rag.azure_integration.rest.client import AzureSearchClient
        print("  ✅ AzureSearchClient imported")
    except Exception as e2:
        print(f"  ❌ AzureSearchClient failed: {e2}")
        
    try:
        from enhanced_rag.azure_integration.rest.operations import SearchOperations
        print("  ✅ SearchOperations imported")
    except Exception as e3:
        print(f"  ❌ SearchOperations failed: {e3}")

try:
    from enhanced_rag.azure_integration.automation import (
        IndexAutomation,
        DataAutomation,
        IndexerAutomation,
        HealthMonitor
    )
    print("✅ Automation managers imported successfully")
except Exception as e:
    print(f"❌ Automation managers import failed: {e}")
    traceback.print_exc()

print("\n" + "-" * 80 + "\n")
print("Checking for missing dependencies...")

# Check for common missing dependencies
missing_deps = []
deps_to_check = [
    'tenacity',
    'fastapi',
    'uvicorn',
    'azure.search.documents',
    'dotenv',
    'requests',
    'pydantic',
    'aiofiles',
    'httpx',
    'openai',
    'anyio',
    'slowapi',
    'fastmcp',
    'aiohttp'
]

for dep in deps_to_check:
    try:
        __import__(dep.split('.')[0])
        print(f"✅ {dep} is installed")
    except ImportError:
        print(f"❌ {dep} is NOT installed")
        missing_deps.append(dep)

if missing_deps:
    print(f"\n⚠️  Missing dependencies: {', '.join(missing_deps)}")
    print("\nTo install missing dependencies, run:")
    print("pip install " + " ".join(missing_deps))
else:
    print("\n✅ All dependencies are installed")

print("\n" + "-" * 80 + "\n")
print("Testing MCP server initialization...")

try:
    from mcprag.server import MCPServer
    print("✅ MCPServer imported successfully")
    
    # Try to check which features are available
    from mcprag import server as server_module
    print(f"\nFeature availability:")
    print(f"  ENHANCED_RAG_AVAILABLE: {getattr(server_module, 'ENHANCED_RAG_AVAILABLE', 'N/A')}")
    print(f"  REST_API_SUPPORT: {getattr(server_module, 'REST_API_SUPPORT', 'N/A')}")
    print(f"  AZURE_SDK_AVAILABLE: {getattr(server_module, 'AZURE_SDK_AVAILABLE', 'N/A')}")
    print(f"  PIPELINE_AVAILABLE: {getattr(server_module, 'PIPELINE_AVAILABLE', 'N/A')}")
    print(f"  VECTOR_SUPPORT: {getattr(server_module, 'VECTOR_SUPPORT', 'N/A')}")
    
except Exception as e:
    print(f"❌ MCPServer import failed: {e}")
    traceback.print_exc()

print("\n" + "=" * 80 + "\n")
print("Summary:")
if missing_deps:
    print(f"❌ {len(missing_deps)} dependencies are missing")
    print("   Run: pip install -r requirements.txt")
else:
    print("✅ All dependencies are installed")
    print("   If imports are still failing, check for syntax errors or circular imports")
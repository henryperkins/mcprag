#!/usr/bin/env python3
"""Debug script to check why enhanced RAG imports are failing"""

import sys
import traceback

print("Testing enhanced_rag imports...")

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

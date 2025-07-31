#!/usr/bin/env python3
"""
Basic search example using enhanced RAG pipeline
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from enhanced_rag.mcp_integration.enhanced_search_tool import EnhancedSearchTool
from enhanced_rag.mcp_integration.code_gen_tool import CodeGenerationTool
from enhanced_rag.mcp_integration.context_aware_tool import ContextAwareTool


async def demo_enhanced_search():
    """Demonstrate enhanced search capabilities"""
    
    # Configuration
    config = {
        "azure_endpoint": os.getenv("ACS_ENDPOINT"),
        "azure_key": os.getenv("ACS_ADMIN_KEY"),
        "index_name": "codebase-mcp-sota",
        "enable_caching": True
    }
    
    # Initialize tools
    search_tool = EnhancedSearchTool(config)
    code_gen_tool = CodeGenerationTool(config)
    context_tool = ContextAwareTool(config)
    
    print("=" * 60)
    print("Enhanced RAG Pipeline Demo")
    print("=" * 60)
    
    # Example 1: Basic search
    print("\n1. Basic Search Example")
    print("-" * 30)
    query = "implement async function with error handling"
    result = await search_tool.search(
        query=query,
        max_results=5,
        generate_response=True
    )
    
    if result.get('success'):
        print(f"Query: {query}")
        print(f"Found {len(result.get('results', []))} results")
        if result.get('response'):
            print(f"\nGenerated Response:\n{result['response'][:500]}...")
    
    # Example 2: Context-aware search
    print("\n\n2. Context-Aware Search Example")
    print("-" * 30)
    current_file = "/path/to/current/file.py"
    result = await search_tool.search(
        query="how to implement caching",
        current_file=current_file,
        intent="implement",
        generate_response=True
    )
    
    if result.get('success'):
        print(f"Search with context from: {current_file}")
        print(f"Intent: implement")
        print(f"Found {len(result.get('results', []))} results")
    
    # Example 3: Code generation
    print("\n\n3. Code Generation Example")
    print("-" * 30)
    code_result = await code_gen_tool.generate_code(
        description="async function to fetch data from API with retry logic",
        language="python",
        include_tests=True
    )
    
    if code_result.get('success'):
        print("Generated Code:")
        print(code_result.get('code', 'No code generated'))
        if code_result.get('test_code'):
            print("\nGenerated Tests:")
            print(code_result['test_code'])
    
    # Example 4: Context analysis
    print("\n\n4. Context Analysis Example")
    print("-" * 30)
    context_result = await context_tool.analyze_context(
        file_path=__file__,
        include_dependencies=True,
        depth=2
    )
    
    if not context_result.get('error'):
        print(f"File: {context_result.get('file')}")
        print(f"Language: {context_result.get('language')}")
        print(f"Module: {context_result.get('module')}")
        print(f"Summary: {context_result.get('summary')}")
    
    # Example 5: Improvement suggestions
    print("\n\n5. Improvement Suggestions Example")
    print("-" * 30)
    suggestions = await context_tool.suggest_improvements(
        file_path=__file__,
        focus="readability",
        include_examples=False
    )
    
    if suggestions.get('total_suggestions', 0) > 0:
        print(f"Found {suggestions['total_suggestions']} improvement suggestions:")
        for suggestion in suggestions.get('suggestions', []):
            print(f"- {suggestion['type']}: {suggestion['description']}")


async def demo_advanced_features():
    """Demonstrate advanced RAG features"""
    
    config = {
        "azure_endpoint": os.getenv("ACS_ENDPOINT"),
        "azure_key": os.getenv("ACS_ADMIN_KEY"),
        "index_name": "codebase-mcp-sota"
    }
    
    search_tool = EnhancedSearchTool(config)
    
    print("\n\n" + "=" * 60)
    print("Advanced Features Demo")
    print("=" * 60)
    
    # Multi-stage search with dependency resolution
    print("\n1. Multi-Stage Search with Dependencies")
    print("-" * 30)
    
    result = await search_tool.search(
        query="database connection pooling implementation",
        intent="implement",
        include_dependencies=True,
        max_results=10
    )
    
    if result.get('success'):
        print(f"Primary results: {len(result.get('results', []))}")
        for r in result.get('results', [])[:3]:
            print(f"- {r.get('file_path')}: {r.get('function_name', 'N/A')}")
            if r.get('dependencies'):
                print(f"  Dependencies: {', '.join(r['dependencies'][:3])}")


if __name__ == "__main__":
    # Check environment
    if not os.getenv("ACS_ENDPOINT") or not os.getenv("ACS_ADMIN_KEY"):
        print("Error: Missing Azure Search credentials in environment")
        print("Please set ACS_ENDPOINT and ACS_ADMIN_KEY")
        sys.exit(1)
    
    # Run demos
    asyncio.run(demo_enhanced_search())
    asyncio.run(demo_advanced_features())
    
    print("\n\nDemo completed successfully!")
    print("The enhanced RAG pipeline provides:")
    print("- Context-aware search")
    print("- Multi-stage retrieval")
    print("- Code generation")
    print("- Improvement suggestions")
    print("- Dependency resolution")
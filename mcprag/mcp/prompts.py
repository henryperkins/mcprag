"""
MCP prompt templates.

Provides pre-configured prompts for common search scenarios.
"""

from typing import Any, Optional


def register_prompts(mcp: Any) -> None:
    """Register all MCP prompts."""

    @mcp.prompt()
    async def implement_feature(feature: str) -> str:
        """Generate implementation plan for a feature."""
        return f"""I need to implement: {feature}

Please use search_code with:
1. intent='implement' to find similar implementations
2. include_dependencies=true to get required functions
3. Search for relevant utilities and patterns

Then provide a step-by-step implementation plan with code examples."""

    @mcp.prompt()
    async def debug_error(error: str, file: Optional[str] = None) -> str:
        """Generate debugging assistance."""
        context = f" in {file}" if file else ""
        return f"""I'm getting this error{context}: {error}

Please use search_code with:
1. intent='debug' to find error handling patterns
2. Search for the specific error message
3. Look for similar issues in test files

Help me understand and fix this error."""

    @mcp.prompt()
    async def understand_codebase(topic: str) -> str:
        """Generate codebase understanding assistance."""
        return f"""I want to understand: {topic}

Please use search_code with:
1. intent='understand' to find documentation and examples
2. Search for key concepts and terminology
3. Look for README files and documentation

Provide a clear explanation with relevant code examples."""

    @mcp.prompt()
    async def refactor_code(description: str) -> str:
        """Generate refactoring suggestions."""
        return f"""I want to refactor: {description}

Please use search_code with:
1. intent='refactor' to find design patterns
2. Search for best practices and examples
3. Look for similar refactoring cases

Suggest improvements with before/after code examples."""

    @mcp.prompt()
    async def find_dependencies(function_name: str) -> str:
        """Find all dependencies of a function."""
        return f"""Find all dependencies for function: {function_name}

Please use search_code with:
1. query='def {function_name}' to find the function
2. include_dependencies=true
3. dependency_mode='graph' for visual representation

Show the complete dependency tree."""

    @mcp.prompt()
    async def search_with_context(query: str, context_file: str) -> str:
        """Search with specific file context."""
        return f"""Search for: {query}
Context file: {context_file}

Please:
1. First use analyze_context on the context file
2. Then use search_code with the query and context
3. Generate a contextual response

Provide results that best match the current context."""

    @mcp.prompt()
    async def compare_implementations(concept: str) -> str:
        """Compare different implementations of a concept."""
        return f"""Compare implementations of: {concept}

Please:
1. Use search_code to find multiple implementations
2. Use explain_ranking to understand why each was ranked
3. Compare and contrast the approaches

Highlight the pros and cons of each implementation."""

    @mcp.prompt()
    async def learn_from_tests(component: str) -> str:
        """Learn how to use a component from its tests."""
        return f"""Learn how to use: {component}

Please search_code with:
1. query='test_{component}' or '{component}_test'
2. Look in test directories
3. Find usage examples

Extract practical usage patterns from the test cases."""

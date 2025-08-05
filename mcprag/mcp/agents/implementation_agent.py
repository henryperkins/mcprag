"""
Implementation Agent for MCPRag

Specialist agent for code generation and implementation tasks.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ImplementationAgent:
    """
    Specialist agent for code implementation and generation.
    
    Responsibilities:
    - Creating new code implementations
    - Generating examples and templates
    - Providing implementation patterns
    - Suggesting dependencies and imports
    """
    
    SYSTEM_PROMPT = """You are a specialized implementation agent for the MCPRag system.
Your role is to help users create new code implementations based on examples and patterns.

You excel at:
- Understanding implementation requirements
- Finding relevant examples and patterns
- Generating code templates
- Identifying required dependencies
- Following language-specific best practices

You have access to:
- Code generation tools
- Pattern matching capabilities
- Dependency analysis
- Example repositories

When implementing:
1. Understand the requirements fully
2. Find similar implementations for reference
3. Generate clean, well-documented code
4. Include necessary imports and dependencies
5. Provide usage examples and tests
"""

    def __init__(self, server):
        """Initialize implementation agent with server reference"""
        self.server = server
        self.code_gen = server.code_gen if hasattr(server, 'code_gen') else None
        self.pipeline = server.pipeline if hasattr(server, 'pipeline') else None
        
    async def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute implementation request.
        
        Args:
            request: Request from routing agent
                
        Returns:
            Implementation with code, examples, and dependencies
        """
        query = request.get("query", "")
        intent = request.get("intent")
        routing_context = request.get("routing_context", {})
        objective = request.get("agent_objective", "")
        
        logger.info(f"ImplementationAgent executing: {objective}")
        
        try:
            # 1. Search for similar implementations
            examples = await self._find_examples(query, routing_context)
            
            # 2. Generate implementation
            implementation = await self._generate_implementation(
                query, examples, routing_context
            )
            
            # 3. Identify dependencies
            dependencies = self._extract_dependencies(implementation, examples)
            
            # 4. Create usage example
            usage_example = self._create_usage_example(implementation, query)
            
            # 5. Suggest tests
            test_suggestions = self._suggest_tests(implementation, query)
            
            return {
                "success": True,
                "agent": "implementation_agent",
                "objective": objective,
                "implementation": implementation,
                "dependencies": dependencies,
                "usage_example": usage_example,
                "test_suggestions": test_suggestions,
                "reference_examples": examples[:3] if examples else [],
                "implementation_notes": self._generate_notes(query, routing_context)
            }
            
        except Exception as e:
            logger.error(f"Implementation failed: {e}")
            return {
                "success": False,
                "agent": "implementation_agent",
                "error": str(e),
                "suggestions": self._get_implementation_suggestions(query)
            }
    
    async def _find_examples(
        self, 
        query: str, 
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Find similar implementations for reference"""
        if not self.server.enhanced_search:
            return []
            
        # Search for examples with implementation intent
        try:
            result = await self.server.enhanced_search.search(
                query=f"{query} example implementation",
                intent="implement",
                max_results=5,
                include_dependencies=True
            )
            
            examples = []
            if result.get("results"):
                for r in result["results"]:
                    examples.append({
                        "file": r.get("file"),
                        "content": r.get("content"),
                        "relevance": r.get("relevance"),
                        "language": r.get("language", "unknown")
                    })
                    
            return examples
            
        except Exception as e:
            logger.warning(f"Example search failed: {e}")
            return []
    
    async def _generate_implementation(
        self,
        query: str,
        examples: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate implementation based on requirements and examples"""
        # Determine language from context or examples
        language = self._detect_language(context, examples)
        
        # Extract patterns from examples
        patterns = self._extract_patterns(examples)
        
        # Generate implementation structure
        implementation = {
            "language": language,
            "code": self._generate_code_template(query, language, patterns),
            "structure": self._generate_structure(query, language),
            "patterns_used": patterns
        }
        
        # Use code generation tool if available
        if self.code_gen:
            try:
                generated = await self.code_gen.generate(
                    description=query,
                    language=language,
                    context_file=context.get("current_file"),
                    include_tests=True
                )
                
                if generated.get("success"):
                    implementation["code"] = generated.get("code", implementation["code"])
                    implementation["enhanced"] = True
                    
            except Exception as e:
                logger.warning(f"Code generation enhancement failed: {e}")
                
        return implementation
    
    def _detect_language(
        self, 
        context: Dict[str, Any], 
        examples: List[Dict[str, Any]]
    ) -> str:
        """Detect programming language from context or examples"""
        # Check current file
        if context.get("current_file"):
            ext = context["current_file"].split(".")[-1]
            lang_map = {
                "py": "python",
                "js": "javascript", 
                "ts": "typescript",
                "java": "java",
                "go": "go",
                "rs": "rust"
            }
            if ext in lang_map:
                return lang_map[ext]
                
        # Check examples
        if examples:
            for ex in examples:
                if ex.get("language"):
                    return ex["language"]
                    
        return "python"  # Default
    
    def _extract_patterns(self, examples: List[Dict[str, Any]]) -> List[str]:
        """Extract common patterns from examples"""
        patterns = []
        
        if not examples:
            return patterns
            
        # Look for common patterns
        pattern_checks = {
            "error_handling": ["try", "except", "catch", "error"],
            "async": ["async", "await", "promise", "future"],
            "class_based": ["class", "self", "this", "constructor"],
            "functional": ["map", "filter", "reduce", "lambda"],
            "validation": ["validate", "check", "assert", "require"]
        }
        
        for example in examples:
            content = example.get("content", "").lower()
            for pattern_name, keywords in pattern_checks.items():
                if any(keyword in content for keyword in keywords):
                    if pattern_name not in patterns:
                        patterns.append(pattern_name)
                        
        return patterns
    
    def _generate_code_template(
        self,
        query: str,
        language: str,
        patterns: List[str]
    ) -> str:
        """Generate basic code template"""
        templates = {
            "python": self._python_template,
            "javascript": self._javascript_template,
            "typescript": self._typescript_template,
            "java": self._java_template,
            "go": self._go_template
        }
        
        template_func = templates.get(language, self._generic_template)
        return template_func(query, patterns)
    
    def _python_template(self, query: str, patterns: List[str]) -> str:
        """Generate Python template"""
        template = f'''"""
{query}

Generated by MCPRag Implementation Agent
"""

'''
        
        if "async" in patterns:
            template += "import asyncio\n"
        if "error_handling" in patterns:
            template += "from typing import Optional, Union\n"
            
        template += "\n\n"
        
        if "class_based" in patterns:
            template += f'''class Implementation:
    """Implementation for: {query}"""
    
    def __init__(self):
        """Initialize the implementation"""
        pass
    
    def execute(self, *args, **kwargs):
        """Main execution method"""
        # TODO: Implement based on requirements
        raise NotImplementedError("Implementation needed")
'''
        else:
            template += f'''def implement_{query.replace(" ", "_").lower()}(*args, **kwargs):
    """
    Implementation for: {query}
    
    Args:
        *args: Variable arguments
        **kwargs: Keyword arguments
        
    Returns:
        Implementation result
    """
    # TODO: Implement based on requirements
    raise NotImplementedError("Implementation needed")
'''
        
        if "error_handling" in patterns:
            template += '''

def safe_execute(*args, **kwargs):
    """Execute with error handling"""
    try:
        return implement_function(*args, **kwargs)
    except Exception as e:
        # Handle error appropriately
        raise
'''
        
        return template
    
    def _javascript_template(self, query: str, patterns: List[str]) -> str:
        """Generate JavaScript template"""
        template = f'''/**
 * {query}
 * 
 * Generated by MCPRag Implementation Agent
 */

'''
        
        if "class_based" in patterns:
            template += f'''class Implementation {{
    constructor() {{
        // Initialize
    }}
    
    execute(...args) {{
        // TODO: Implement based on requirements
        throw new Error("Implementation needed");
    }}
}}
'''
        elif "async" in patterns:
            template += f'''async function implement{query.replace(" ", "").title()}(...args) {{
    // TODO: Implement based on requirements
    throw new Error("Implementation needed");
}}
'''
        else:
            template += f'''function implement{query.replace(" ", "").title()}(...args) {{
    // TODO: Implement based on requirements  
    throw new Error("Implementation needed");
}}
'''
        
        return template
    
    def _typescript_template(self, query: str, patterns: List[str]) -> str:
        """Generate TypeScript template"""
        # Similar to JavaScript but with types
        return self._javascript_template(query, patterns).replace(
            "(...args)", 
            "(...args: any[])"
        )
    
    def _java_template(self, query: str, patterns: List[str]) -> str:
        """Generate Java template"""
        class_name = query.replace(" ", "").title() + "Implementation"
        return f'''/**
 * {query}
 * 
 * Generated by MCPRag Implementation Agent
 */
public class {class_name} {{
    
    public {class_name}() {{
        // Initialize
    }}
    
    public Object execute(Object... args) {{
        // TODO: Implement based on requirements
        throw new UnsupportedOperationException("Implementation needed");
    }}
}}
'''
    
    def _go_template(self, query: str, patterns: List[str]) -> str:
        """Generate Go template"""
        func_name = query.replace(" ", "").title()
        return f'''// {query}
// 
// Generated by MCPRag Implementation Agent

package implementation

import (
    "fmt"
    "errors"
)

// {func_name} implements: {query}
func {func_name}(args ...interface{{}}) (interface{{}}, error) {{
    // TODO: Implement based on requirements
    return nil, errors.New("implementation needed")
}}
'''
    
    def _generic_template(self, query: str, patterns: List[str]) -> str:
        """Generic template for unknown languages"""
        return f'''// {query}
// 
// Generated by MCPRag Implementation Agent
// 
// TODO: Implement based on requirements
// Language: Unknown - Please specify programming language
'''
    
    def _generate_structure(self, query: str, language: str) -> Dict[str, Any]:
        """Generate implementation structure"""
        return {
            "main_components": self._identify_components(query),
            "suggested_files": self._suggest_file_structure(query, language),
            "interfaces": self._suggest_interfaces(query, language)
        }
    
    def _identify_components(self, query: str) -> List[str]:
        """Identify main components from query"""
        components = []
        
        # Common component keywords
        component_keywords = {
            "api": ["endpoint", "route", "controller"],
            "database": ["model", "repository", "schema"],
            "service": ["business logic", "processing"],
            "utils": ["helpers", "utilities"],
            "config": ["configuration", "settings"]
        }
        
        query_lower = query.lower()
        for component, keywords in component_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                components.append(component)
                
        return components if components else ["main"]
    
    def _suggest_file_structure(self, query: str, language: str) -> List[str]:
        """Suggest file structure for implementation"""
        base_name = query.replace(" ", "_").lower()
        
        extensions = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "java": ".java",
            "go": ".go"
        }
        
        ext = extensions.get(language, ".txt")
        
        files = [f"{base_name}{ext}"]
        
        # Add test file
        if language == "python":
            files.append(f"test_{base_name}.py")
        elif language in ["javascript", "typescript"]:
            files.append(f"{base_name}.test{ext}")
        elif language == "java":
            files.append(f"{base_name.title()}Test.java")
        elif language == "go":
            files.append(f"{base_name}_test.go")
            
        return files
    
    def _suggest_interfaces(self, query: str, language: str) -> List[Dict[str, Any]]:
        """Suggest interfaces/contracts for implementation"""
        interfaces = []
        
        # Only for languages that support interfaces
        if language in ["typescript", "java", "go"]:
            interfaces.append({
                "name": f"{query.replace(' ', '').title()}Interface",
                "methods": ["execute", "validate", "process"],
                "purpose": "Define contract for implementation"
            })
            
        return interfaces
    
    def _extract_dependencies(
        self,
        implementation: Dict[str, Any],
        examples: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """Extract required dependencies"""
        dependencies = {
            "imports": [],
            "packages": [],
            "suggested": []
        }
        
        language = implementation.get("language", "python")
        
        # Extract from examples
        for example in examples:
            content = example.get("content", "")
            
            if language == "python":
                # Find import statements
                import_lines = [line for line in content.split("\n") 
                              if line.strip().startswith(("import ", "from "))]
                dependencies["imports"].extend(import_lines[:5])
                
            elif language in ["javascript", "typescript"]:
                # Find require/import statements
                import_lines = [line for line in content.split("\n")
                              if "import" in line or "require" in line]
                dependencies["imports"].extend(import_lines[:5])
                
        # Deduplicate
        dependencies["imports"] = list(set(dependencies["imports"]))
        
        # Suggest common packages based on patterns
        patterns = implementation.get("patterns_used", [])
        if "async" in patterns:
            if language == "python":
                dependencies["suggested"].append("asyncio")
            elif language == "javascript":
                dependencies["suggested"].append("async/await support")
                
        return dependencies
    
    def _create_usage_example(
        self,
        implementation: Dict[str, Any],
        query: str
    ) -> str:
        """Create usage example for the implementation"""
        language = implementation.get("language", "python")
        
        if language == "python":
            return f'''# Usage example for: {query}

# Import the implementation
from implementation import implement_function

# Basic usage
result = implement_function(param1="value1", param2="value2")
print(result)

# With error handling
try:
    result = implement_function(data)
except Exception as e:
    print(f"Error: {{e}}")
'''
        
        elif language in ["javascript", "typescript"]:
            return f'''// Usage example for: {query}

// Import the implementation
const {{ implement }} = require('./implementation');

// Basic usage
const result = implement('value1', 'value2');
console.log(result);

// With error handling
try {{
    const result = implement(data);
    console.log(result);
}} catch (error) {{
    console.error('Error:', error);
}}
'''
        
        else:
            return f"// Usage example for: {query}\n// TODO: Add usage example"
    
    def _suggest_tests(
        self,
        implementation: Dict[str, Any],
        query: str
    ) -> List[Dict[str, str]]:
        """Suggest test cases for the implementation"""
        suggestions = []
        
        # Basic test cases
        suggestions.append({
            "name": "test_basic_functionality",
            "description": "Test basic functionality with valid inputs",
            "priority": "high"
        })
        
        suggestions.append({
            "name": "test_edge_cases",
            "description": "Test edge cases and boundary conditions",
            "priority": "high"
        })
        
        suggestions.append({
            "name": "test_error_handling",
            "description": "Test error handling with invalid inputs",
            "priority": "medium"
        })
        
        # Pattern-specific tests
        patterns = implementation.get("patterns_used", [])
        
        if "async" in patterns:
            suggestions.append({
                "name": "test_async_behavior",
                "description": "Test asynchronous execution and timing",
                "priority": "medium"
            })
            
        if "validation" in patterns:
            suggestions.append({
                "name": "test_validation_rules",
                "description": "Test all validation rules thoroughly",
                "priority": "high"
            })
            
        return suggestions
    
    def _generate_notes(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> List[str]:
        """Generate implementation notes and tips"""
        notes = []
        
        # General notes
        notes.append("Review examples for best practices and patterns")
        notes.append("Consider error handling and edge cases")
        notes.append("Add appropriate logging for debugging")
        
        # Context-specific notes
        if context.get("complexity") == "high":
            notes.append("Consider breaking into smaller components")
            notes.append("Add comprehensive documentation")
            
        if context.get("has_error_context"):
            notes.append("Include specific error handling for known issues")
            
        return notes
    
    def _get_implementation_suggestions(self, query: str) -> List[str]:
        """Get suggestions when implementation fails"""
        return [
            "Break down the requirement into smaller parts",
            "Search for similar implementations first",
            "Specify the programming language explicitly",
            "Provide more context about the use case",
            f"Try searching for: '{query} example code'"
        ]
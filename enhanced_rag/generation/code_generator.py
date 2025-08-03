"""
Code generation engine that learns from retrieved examples
"""

import logging
import re
import ast
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
from dataclasses import dataclass

from ..core.models import SearchResult
from .style_matcher import StyleMatcher
from .template_manager import TemplateManager

logger = logging.getLogger(__name__)


@dataclass
class GenerationContext:
    """Context for code generation"""
    language: str
    description: str
    retrieved_examples: List[SearchResult]
    style_guide: Optional[str] = None
    context_file: Optional[str] = None
    include_tests: bool = False
    target_framework: Optional[str] = None
    imports_context: Optional[List[str]] = None


class CodeGenerator:
    """
    Generates code by learning patterns from retrieved examples
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize code generator"""
        self.config = config or {}

        # Sub-components
        self.style_matcher = StyleMatcher(config)
        self.template_manager = TemplateManager(config)

        # Language-specific generators
        self.language_generators = {
            'python': self._generate_python,
            'javascript': self._generate_javascript,
            'typescript': self._generate_typescript,
            'java': self._generate_java,
            'go': self._generate_go,
            'rust': self._generate_rust,
            'cpp': self._generate_cpp,
        }

        # Pattern extraction rules
        self.pattern_rules = self._initialize_pattern_rules()

    def _initialize_pattern_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize language-specific pattern extraction rules"""
        return {
            'python': {
                'function_pattern': r'def\s+(\w+)\s*\([^)]*\).*?:',
                'class_pattern': r'class\s+(\w+).*?:',
                'import_pattern': r'^(?:from\s+[\w\.]+\s+)?import\s+.*$',
                'decorator_pattern': r'@\w+(?:\([^)]*\))?',
                'docstring_pattern': r'"""[\s\S]*?"""',
                'type_hint_pattern': r'->\s*[\w\[\],\s]+(?=:)',
            },
            'javascript': {
                'function_pattern': r'(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=]+)\s*=>)',
                'class_pattern': r'class\s+(\w+)(?:\s+extends\s+\w+)?',
                'import_pattern': r'^import\s+.*?from\s+[\'"].*?[\'"]',
                'export_pattern': r'^export\s+(?:default\s+)?(?:function|class|const|let|var)',
                'jsdoc_pattern': r'/\*\*[\s\S]*?\*/',
            },
            'typescript': {
                'function_pattern': r'(?:function\s+(\w+)|const\s+(\w+)\s*:\s*[^=]+\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=]+)\s*=>)',
                'interface_pattern': r'interface\s+(\w+)(?:<[^>]+>)?',
                'type_pattern': r'type\s+(\w+)\s*=',
                'class_pattern': r'class\s+(\w+)(?:<[^>]+>)?(?:\s+(?:extends|implements)\s+[^{]+)?',
                'import_pattern': r'^import\s+.*?from\s+[\'"].*?[\'"]',
            }
        }

    async def generate(self, context: GenerationContext) -> Dict[str, Any]:
        """
        Generate code based on context and retrieved examples

        Args:
            context: Generation context with examples and requirements

        Returns:
            Dict with generated code and metadata
        """
        try:
            # Extract patterns from examples
            patterns = await self._extract_patterns(context)

            # Match coding style
            style_info = await self.style_matcher.analyze_style(
                context.retrieved_examples,
                context.language
            )

            # Get appropriate template
            template = await self.template_manager.get_template(
                context.description,
                context.language,
                patterns
            )

            # Generate code using language-specific generator
            generator = self.language_generators.get(
                context.language.lower(),
                self._generate_generic
            )

            generated_code = await generator(context, patterns, style_info, template)

            # Post-process generated code
            final_code = await self._post_process(
                generated_code,
                context,
                style_info
            )

            # Generate tests if requested
            test_code = None
            if context.include_tests:
                test_code = await self._generate_tests(
                    final_code,
                    context,
                    patterns
                )

            return {
                'success': True,
                'code': final_code,
                'test_code': test_code,
                'patterns_used': list(patterns.keys()),
                'style_info': style_info,
                'template_used': template.get('name') if template else None,
                'confidence': self._calculate_confidence(patterns, style_info)
            }

        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': None
            }

    async def _extract_patterns(
        self,
        context: GenerationContext
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Extract reusable patterns from retrieved examples"""
        patterns = defaultdict(list)

        rules = self.pattern_rules.get(context.language.lower(), {})

        for example in context.retrieved_examples[:10]:  # Top 10 examples
            code = example.code_snippet

            # Extract function patterns
            if 'function_pattern' in rules:
                for match in re.finditer(rules['function_pattern'], code, re.MULTILINE):
                    patterns['functions'].append({
                        'name': match.group(1) or match.group(2) if match.lastindex > 1 else match.group(1),
                        'signature': match.group(0),
                        'source': example.file_path,
                        'score': example.score
                    })

            # Extract class patterns
            if 'class_pattern' in rules:
                for match in re.finditer(rules['class_pattern'], code, re.MULTILINE):
                    patterns['classes'].append({
                        'name': match.group(1),
                        'signature': match.group(0),
                        'source': example.file_path,
                        'score': example.score
                    })

            # Extract import patterns
            if 'import_pattern' in rules:
                for match in re.finditer(rules['import_pattern'], code, re.MULTILINE):
                    patterns['imports'].append({
                        'statement': match.group(0),
                        'source': example.file_path,
                        'score': example.score
                    })

            # Extract structural patterns (loops, conditions, etc.)
            patterns['structures'].extend(
                self._extract_structural_patterns(code, context.language)
            )

        return dict(patterns)

    def _extract_structural_patterns(
        self,
        code: str,
        language: str
    ) -> List[Dict[str, Any]]:
        """Extract structural patterns like loops, conditions, error handling"""
        structures = []

        # Common patterns across languages
        patterns = {
            'error_handling': [
                r'try\s*{.*?}\s*catch',  # JS/Java style
                r'try:.*?except',  # Python
                r'if\s+err\s*!=\s*nil',  # Go
                r'match.*?Ok\(.*?\)|Err\(',  # Rust
            ],
            'async_patterns': [
                r'async\s+def',  # Python
                r'async\s+function',  # JS
                r'await\s+',  # General await
                r'\.then\(',  # Promise chains
            ],
            'validation': [
                r'if\s+not\s+\w+:',  # Python validation
                r'if\s*\(!.*?\)',  # JS/Java validation
                r'assert\s+',  # Assertions
                r'require\(',  # Require patterns
            ],
            'iteration': [
                r'for\s+.*?\s+in\s+',  # Python/JS for-in
                r'\.map\(',  # Functional map
                r'\.filter\(',  # Functional filter
                r'\.reduce\(',  # Functional reduce
            ]
        }

        for pattern_type, regexes in patterns.items():
            for regex in regexes:
                if re.search(regex, code, re.IGNORECASE | re.DOTALL):
                    structures.append({
                        'type': pattern_type,
                        'pattern': regex,
                        'language': language
                    })
                    break  # One match per pattern type

        return structures

    async def _generate_python(
        self,
        context: GenerationContext,
        patterns: Dict[str, List[Dict[str, Any]]],
        style_info: Dict[str, Any],
        template: Optional[Dict[str, Any]]
    ) -> str:
        """Generate Python code"""
        # Start with imports
        imports = self._generate_imports(patterns.get('imports', []), 'python')

        # Generate main structure
        if any('class' in context.description.lower() for _ in [1]):
            # Generate class-based code
            code = self._generate_python_class(context, patterns, style_info)
        else:
            # Generate function-based code
            code = self._generate_python_function(context, patterns, style_info)

        # Combine imports and code
        result = []
        if imports:
            result.append(imports)
            result.append('')  # Blank line

        result.append(code)

        return '\n'.join(result)

    def _generate_python_class(
        self,
        context: GenerationContext,
        patterns: Dict[str, List[Dict[str, Any]]],
        style_info: Dict[str, Any]
    ) -> str:
        """Generate Python class structure"""
        # Extract common class patterns
        class_examples = patterns.get('classes', [])

        # Determine class name from description
        class_name = self._extract_class_name(context.description)

        # Generate class structure
        lines = []

        # Class definition
        lines.append(f"class {class_name}:")

        # Docstring
        lines.append(f'    """')
        lines.append(f'    {context.description}')
        lines.append(f'    """')
        lines.append('')

        # Constructor
        lines.append('    def __init__(self):')
        lines.append('        """Initialize the component"""')
        lines.append('        # TODO: Initialize attributes')
        lines.append('        pass')
        lines.append('')

        # Main method based on description
        method_name = self._extract_method_name(context.description)
        lines.append(f'    def {method_name}(self):')
        lines.append(f'        """')
        lines.append(f'        {context.description}')
        lines.append(f'        """')
        lines.append('        # TODO: Implement logic')
        lines.append('        raise NotImplementedError("Method not yet implemented")')

        return '\n'.join(lines)

    def _generate_python_function(
        self,
        context: GenerationContext,
        patterns: Dict[str, List[Dict[str, Any]]],
        style_info: Dict[str, Any]
    ) -> str:
        """Generate Python function"""
        # Extract function name
        func_name = self._extract_function_name(context.description)

        # Determine parameters from description
        params = self._extract_parameters(context.description)

        # Generate function
        lines = []

        # Function signature
        if params:
            lines.append(f"def {func_name}({', '.join(params)}):")
        else:
            lines.append(f"def {func_name}():")

        # Docstring
        lines.append(f'    """')
        lines.append(f'    {context.description}')
        if params:
            lines.append('')
            lines.append('    Args:')
            for param in params:
                lines.append(f'        {param}: TODO: Add description')
        lines.append('')
        lines.append('    Returns:')
        lines.append('        TODO: Add return description')
        lines.append('    """')

        # Implementation
        lines.append('    # TODO: Implement function logic')

        # Add common patterns based on description
        if 'validate' in context.description.lower():
            lines.append('    if not all([]):  # Add validation conditions')
            lines.append('        raise ValueError("Invalid input")')
            lines.append('')

        if 'async' in context.description.lower():
            # Make it async
            lines[0] = f"async {lines[0]}"
            lines.append('    # TODO: Add async operations')
            lines.append('    await asyncio.sleep(0)  # Placeholder')

        lines.append('    raise NotImplementedError("Function not yet implemented")')

        return '\n'.join(lines)

    async def _generate_javascript(
        self,
        context: GenerationContext,
        patterns: Dict[str, List[Dict[str, Any]]],
        style_info: Dict[str, Any],
        template: Optional[Dict[str, Any]]
    ) -> str:
        """Generate JavaScript code"""
        # Similar to Python but with JS syntax
        func_name = self._extract_function_name(context.description)
        params = self._extract_parameters(context.description)

        lines = []

        # Generate function
        is_async = 'async' in context.description.lower()

        if is_async:
            lines.append(f"async function {func_name}({', '.join(params)}) {{")
        else:
            lines.append(f"function {func_name}({', '.join(params)}) {{")

        # JSDoc comment
        lines.insert(0, "/**")
        lines.insert(1, f" * {context.description}")
        if params:
            for param in params:
                lines.insert(len(lines) - 1, f" * @param {{*}} {param} - TODO: Add description")
        lines.insert(len(lines) - 1, " * @returns {{}} TODO: Add return type")
        lines.insert(len(lines) - 1, " */")

        # Implementation
        lines.append("  // TODO: Implement function logic")

        if 'validate' in context.description.lower():
            lines.append("  if (!/* validation condition */) {")
            lines.append('    throw new Error("Invalid input");')
            lines.append("  }")
            lines.append("")

        lines.append('  throw new Error("Not implemented");')
        lines.append("}")

        return '\n'.join(lines)

    async def _generate_typescript(
        self,
        context: GenerationContext,
        patterns: Dict[str, List[Dict[str, Any]]],
        style_info: Dict[str, Any],
        template: Optional[Dict[str, Any]]
    ) -> str:
        """Generate TypeScript code"""
        # Similar to JavaScript but with types
        func_name = self._extract_function_name(context.description)
        params = self._extract_parameters(context.description)

        lines = []

        # Add interfaces if needed
        if 'interface' in context.description.lower() or 'type' in context.description.lower():
            lines.append("interface Result {")
            lines.append("  // TODO: Define interface properties")
            lines.append("  success: boolean;")
            lines.append("  data?: any;")
            lines.append("}")
            lines.append("")

        # Generate function with types
        is_async = 'async' in context.description.lower()
        return_type = "Promise<Result>" if is_async else "Result"

        typed_params = [f"{p}: any" for p in params]  # Default to any

        if is_async:
            lines.append(f"async function {func_name}({', '.join(typed_params)}): {return_type} {{")
        else:
            lines.append(f"function {func_name}({', '.join(typed_params)}): {return_type} {{")

        # Implementation
        lines.append("  // TODO: Implement function logic")
        lines.append('  throw new Error("Not implemented");')
        lines.append("}")

        return '\n'.join(lines)

    async def _generate_java(
        self,
        context: GenerationContext,
        patterns: Dict[str, List[Dict[str, Any]]],
        style_info: Dict[str, Any],
        template: Optional[Dict[str, Any]]
    ) -> str:
        """Generate Java code"""
        class_name = self._extract_class_name(context.description)
        method_name = self._extract_method_name(context.description)

        lines = []

        # Class definition
        lines.append(f"public class {class_name} {{")
        lines.append("")

        # Main method
        lines.append(f"    public void {method_name}() {{")
        lines.append(f"        // {context.description}")
        lines.append("        // TODO: Implement method logic")
        lines.append('        throw new UnsupportedOperationException("Not implemented");')
        lines.append("    }")
        lines.append("}")

        return '\n'.join(lines)

    async def _generate_go(
        self,
        context: GenerationContext,
        patterns: Dict[str, List[Dict[str, Any]]],
        style_info: Dict[str, Any],
        template: Optional[Dict[str, Any]]
    ) -> str:
        """Generate Go code"""
        func_name = self._extract_function_name(context.description)

        lines = []
        lines.append("package main")
        lines.append("")
        lines.append(f"// {func_name} - {context.description}")
        lines.append(f"func {func_name}() error {{")
        lines.append("    // TODO: Implement function logic")
        lines.append('    return fmt.Errorf("not implemented")')
        lines.append("}")

        return '\n'.join(lines)

    async def _generate_rust(
        self,
        context: GenerationContext,
        patterns: Dict[str, List[Dict[str, Any]]],
        style_info: Dict[str, Any],
        template: Optional[Dict[str, Any]]
    ) -> str:
        """Generate Rust code"""
        func_name = self._extract_function_name(context.description, snake_case=True)

        lines = []
        lines.append(f"/// {context.description}")
        lines.append(f"fn {func_name}() -> Result<(), Box<dyn std::error::Error>> {{")
        lines.append("    // TODO: Implement function logic")
        lines.append('    Err("Not implemented".into())')
        lines.append("}")

        return '\n'.join(lines)

    async def _generate_cpp(
        self,
        context: GenerationContext,
        patterns: Dict[str, List[Dict[str, Any]]],
        style_info: Dict[str, Any],
        template: Optional[Dict[str, Any]]
    ) -> str:
        """Generate C++ code"""
        func_name = self._extract_function_name(context.description)

        lines = []
        lines.append("#include <iostream>")
        lines.append("#include <stdexcept>")
        lines.append("")
        lines.append(f"// {context.description}")
        lines.append(f"void {func_name}() {{")
        lines.append("    // TODO: Implement function logic")
        lines.append('    throw std::runtime_error("Not implemented");')
        lines.append("}")

        return '\n'.join(lines)

    async def _generate_generic(
        self,
        context: GenerationContext,
        patterns: Dict[str, List[Dict[str, Any]]],
        style_info: Dict[str, Any],
        template: Optional[Dict[str, Any]]
    ) -> str:
        """Generic code generation for unsupported languages"""
        return f"// TODO: Implement {context.description}\n// Language: {context.language}"

    def _generate_imports(
        self,
        import_examples: List[Dict[str, Any]],
        language: str
    ) -> str:
        """Generate import statements based on examples"""
        if not import_examples:
            return ""

        # Deduplicate and sort imports
        imports = set()
        for example in import_examples:
            imports.add(example['statement'])

        return '\n'.join(sorted(imports))

    async def _post_process(
        self,
        code: str,
        context: GenerationContext,
        style_info: Dict[str, Any]
    ) -> str:
        """Post-process generated code"""
        # Apply style formatting
        code = await self.style_matcher.apply_style(code, style_info)

        # Add context-specific imports
        if context.imports_context:
            existing_imports = self._extract_imports(code, context.language)
            needed_imports = set(context.imports_context) - existing_imports

            if needed_imports:
                import_statements = self._format_imports(
                    needed_imports,
                    context.language
                )
                code = f"{import_statements}\n\n{code}"

        return code

    async def _generate_tests(
        self,
        code: str,
        context: GenerationContext,
        patterns: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """Generate test code for the generated code"""
        if context.language.lower() == 'python':
            return self._generate_python_tests(code, context)
        elif context.language.lower() in ['javascript', 'typescript']:
            return self._generate_javascript_tests(code, context)
        else:
            return f"// TODO: Add tests for {context.language}"

    def _generate_python_tests(
        self,
        code: str,
        context: GenerationContext
    ) -> str:
        """Generate Python unit tests"""
        # Extract function/class names from generated code
        func_names = re.findall(r'def\s+(\w+)', code)
        class_names = re.findall(r'class\s+(\w+)', code)

        lines = []
        lines.append("import pytest")
        lines.append("import unittest")
        lines.append("")

        if func_names:
            for func in func_names:
                if not func.startswith('_'):  # Skip private functions
                    lines.append(f"def test_{func}():")
                    lines.append(f"    \"\"\"Test {func} function\"\"\"")
                    lines.append("    # TODO: Implement test")
                    lines.append("    with pytest.raises(NotImplementedError):")
                    lines.append(f"        {func}()")
                    lines.append("")

        if class_names:
            for cls in class_names:
                lines.append(f"class Test{cls}(unittest.TestCase):")
                lines.append(f"    \"\"\"Test cases for {cls}\"\"\"")
                lines.append("")
                lines.append("    def setUp(self):")
                lines.append(f"        self.instance = {cls}()")
                lines.append("")
                lines.append("    def test_initialization(self):")
                lines.append(f"        \"\"\"Test {cls} initialization\"\"\"")
                lines.append(f"        self.assertIsInstance(self.instance, {cls})")
                lines.append("")

        return '\n'.join(lines)

    def _generate_javascript_tests(
        self,
        code: str,
        context: GenerationContext
    ) -> str:
        """Generate JavaScript/TypeScript tests"""
        func_names = re.findall(r'function\s+(\w+)|const\s+(\w+)\s*=', code)

        lines = []
        lines.append("describe('Generated Code Tests', () => {")

        for match in func_names:
            func = match[0] or match[1]
            if func:
                lines.append(f"  describe('{func}', () => {{")
                lines.append(f"    it('should be implemented', () => {{")
                lines.append(f"      expect(() => {func}()).toThrow('Not implemented');")
                lines.append("    });")
                lines.append("  });")
                lines.append("")

        lines.append("});")

        return '\n'.join(lines)

    def _extract_class_name(self, description: str) -> str:
        """Extract class name from description"""
        # Look for patterns like "create a X class" or "X manager"
        patterns = [
            r'create\s+(?:a\s+)?(\w+)\s+class',
            r'(\w+)\s+(?:class|manager|handler|service)',
            r'class\s+(?:for\s+)?(\w+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                name = match.group(1)
                # Convert to PascalCase
                return ''.join(word.capitalize() for word in name.split('_'))

        # Fallback: use first noun-like word
        words = description.split()
        for word in words:
            if len(word) > 3 and word.isalpha():
                return word.capitalize()

        return "GeneratedClass"

    def _extract_function_name(
        self,
        description: str,
        snake_case: bool = False
    ) -> str:
        """Extract function name from description"""
        # Look for verb patterns
        patterns = [
            r'(?:function\s+)?(?:to\s+)?(\w+)\s+(?:the\s+)?(\w+)',
            r'(\w+)ing\s+(\w+)',
            r'(\w+)\s+(\w+)\s+(?:data|values|items)',
        ]

        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                verb = match.group(1).lower()
                noun = match.group(2).lower() if match.lastindex > 1 else ""

                if snake_case:
                    return f"{verb}_{noun}".strip('_')
                else:
                    # camelCase
                    return verb + noun.capitalize() if noun else verb

        # Fallback
        return "process_data" if snake_case else "processData"

    def _extract_method_name(self, description: str) -> str:
        """Extract method name from description"""
        return self._extract_function_name(description)

    def _extract_parameters(self, description: str) -> List[str]:
        """Extract likely parameters from description"""
        params = []

        # Look for common parameter patterns
        param_patterns = [
            r'(?:given|with|using|from)\s+(?:a\s+)?(\w+)',
            r'(\w+)\s+(?:parameter|argument|input)',
            r'(?:list|array|collection)\s+of\s+(\w+)',
        ]

        for pattern in param_patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            for match in matches:
                param = match.lower()
                if param not in params and len(param) > 2:
                    params.append(param)

        # Common defaults if no params found
        if not params:
            if 'data' in description.lower():
                params.append('data')
            elif 'file' in description.lower():
                params.append('file_path')
            elif 'text' in description.lower() or 'string' in description.lower():
                params.append('text')

        return params[:4]  # Limit to 4 parameters

    def _extract_imports(self, code: str, language: str) -> set:
        """Extract existing imports from code"""
        imports = set()

        if language.lower() == 'python':
            pattern = r'^(?:from\s+([\w\.]+)|import\s+([\w\.]+))'
        elif language.lower() in ['javascript', 'typescript']:
            pattern = r'^import\s+.*?from\s+[\'"]([^\'"]+)[\'"]'
        else:
            return imports

        for match in re.finditer(pattern, code, re.MULTILINE):
            if match.group(1):
                imports.add(match.group(1))
            elif match.lastindex > 1 and match.group(2):
                imports.add(match.group(2))

        return imports

    def _format_imports(
        self,
        imports: set,
        language: str
    ) -> str:
        """Format import statements"""
        if language.lower() == 'python':
            return '\n'.join(f"import {imp}" for imp in sorted(imports))
        elif language.lower() in ['javascript', 'typescript']:
            return '\n'.join(f"import {imp} from '{imp}';" for imp in sorted(imports))
        else:
            return ""

    def _calculate_confidence(
        self,
        patterns: Dict[str, List[Dict[str, Any]]],
        style_info: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for generated code"""
        confidence = 0.5  # Base confidence

        # More patterns = higher confidence
        total_patterns = sum(len(p) for p in patterns.values())
        if total_patterns > 10:
            confidence += 0.2
        elif total_patterns > 5:
            confidence += 0.1

        # Style consistency
        if style_info.get('consistency_score', 0) > 0.8:
            confidence += 0.1

        # Pattern quality (based on source scores)
        if patterns:
            avg_score = sum(
                p['score']
                for plist in patterns.values()
                for p in plist
            ) / max(1, total_patterns)

            if avg_score > 0.8:
                confidence += 0.2
            elif avg_score > 0.6:
                confidence += 0.1

        return min(1.0, confidence)

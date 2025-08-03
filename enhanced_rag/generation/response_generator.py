"""
Response generation module for creating contextual answers
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from ..utils.performance_monitor import PerformanceMonitor
from ..utils.error_handler import with_retry

from ..core.interfaces import Generator
from ..core.models import (
    SearchResult, SearchIntent, GeneratedResponse, CodeContext
)

logger = logging.getLogger(__name__)


class ResponseGenerator(Generator):
    """
    Generates responses based on retrieved results and intent
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[SearchIntent, str]:
        """Load response templates for different intents"""
        return {
            SearchIntent.IMPLEMENT: """
Based on the search results, here's how to implement {query}:

{code_examples}

Key patterns found:
{patterns}

Dependencies needed:
{dependencies}
""",
            SearchIntent.DEBUG: """
For debugging {query}, I found these relevant solutions:

{solutions}

Common issues:
{issues}

Debugging steps:
{steps}
""",
            SearchIntent.UNDERSTAND: """
Here's an explanation of {query}:

{explanation}

Related concepts:
{concepts}

Code structure:
{structure}
""",
            SearchIntent.REFACTOR: """
For refactoring {query}, here are the recommended approaches:

{patterns}

Improvement suggestions:
{improvements}

Best practices found in codebase:
{best_practices}
""",
            SearchIntent.TEST: """
Testing strategies for {query}:

{test_examples}

Test patterns found:
{test_patterns}

Coverage recommendations:
{coverage_recommendations}
""",
            SearchIntent.DOCUMENT: """
Documentation for {query}:

{doc_examples}

Key points to document:
{key_points}

Style guide compliance:
{style_guide}
"""
        }

    async def generate_response(
        self,
        query: str,
        results: List[SearchResult],
        intent: SearchIntent,
        context: Dict[str, Any]
    ) -> GeneratedResponse:
        """
        Generate a response based on search results
        """
        # Extract relevant information from results
        extracted_info = await self._extract_information(results, intent)

        # Select appropriate template
        template = self.templates.get(intent, self.templates[SearchIntent.IMPLEMENT])

        # TOKEN-BUDGET: keep template + filled data under 7k tokens
        monitor = PerformanceMonitor()
        monitor.increment_counter("responses_generated")

        raw_text = self._fill_template(template, query, extracted_info)
        if len(raw_text) > 28000:  # ~7k tokens rough guardrail
            raw_text = raw_text[:28000] + "\n\n[TRUNCATED]"

        response_text = raw_text

        # Create response object with metadata
        response = GeneratedResponse(
            text=response_text,
            sources=results[:5],  # Top 5 sources
            intent=intent,
            confidence=self._calculate_confidence(results),
            metadata={
                'result_count': len(results),
                'extraction_method': 'template',
                'context_used': bool(context)
            }
        )

        return response

    async def _extract_information(
        self,
        results: List[SearchResult],
        intent: SearchIntent
    ) -> Dict[str, Any]:
        """Extract relevant information from search results based on intent"""
        info = {}

        if intent == SearchIntent.IMPLEMENT:
            info = await self._extract_implementation_info(results)
        elif intent == SearchIntent.DEBUG:
            info = await self._extract_debugging_info(results)
        elif intent == SearchIntent.UNDERSTAND:
            info = await self._extract_explanation_info(results)
        elif intent == SearchIntent.REFACTOR:
            info = await self._extract_refactoring_info(results)
        elif intent == SearchIntent.TEST:
            info = await self._extract_testing_info(results)
        elif intent == SearchIntent.DOCUMENT:
            info = await self._extract_documentation_info(results)

        return info

    async def _extract_implementation_info(self, results: List[SearchResult]) -> Dict[str, Any]:
        """Extract information for implementation intent"""
        code_examples = []
        patterns = set()
        dependencies = set()

        for result in results[:5]:  # Top 5 results
            # Extract code examples
            if result.code_snippet:
                example = {
                    'code': result.code_snippet,
                    'file': result.file_path,
                    'function': result.function_name or 'N/A',
                    'score': result.score
                }
                code_examples.append(example)

            # Extract patterns
            if hasattr(result, 'tags'):
                patterns.update(result.tags)

            # Extract dependencies
            if result.dependencies:
                dependencies.update(result.dependencies)

        # Format code examples
        formatted_examples = []
        for i, example in enumerate(code_examples[:3]):
            formatted_examples.append(
                f"**Example {i+1}** (from `{example['file']}`):\n```\n{example['code']}\n```"
            )

        return {
            'code_examples': '\n\n'.join(formatted_examples),
            'patterns': '\n'.join(f"- {p}" for p in sorted(patterns)[:5]),
            'dependencies': '\n'.join(f"- {d}" for d in sorted(dependencies)[:5])
        }

    async def _extract_debugging_info(self, results: List[SearchResult]) -> Dict[str, Any]:
        """Extract information for debugging intent"""
        solutions = []
        issues = set()
        steps = []

        for result in results[:5]:
            # Look for error handling patterns
            if 'error' in result.code_snippet.lower() or 'exception' in result.code_snippet.lower():
                solution = {
                    'code': result.code_snippet,
                    'file': result.file_path,
                    'explanation': result.relevance_explanation or ''
                }
                solutions.append(solution)

            # Extract common issues
            if hasattr(result, 'tags'):
                for tag in result.tags:
                    if any(keyword in tag.lower() for keyword in ['error', 'bug', 'issue', 'fix']):
                        issues.add(tag)

        # Generate debugging steps
        if solutions:
            steps = [
                "1. Check error logs and stack traces",
                "2. Verify input validation and edge cases",
                "3. Review similar implementations in the codebase",
                "4. Test with minimal reproducible example",
                "5. Apply fixes from similar resolved issues"
            ]

        # Format solutions
        formatted_solutions = []
        for i, solution in enumerate(solutions[:3]):
            formatted_solutions.append(
                f"**Solution {i+1}** (from `{solution['file']}`):\n```\n{solution['code']}\n```"
            )

        return {
            'solutions': '\n\n'.join(formatted_solutions),
            'issues': '\n'.join(f"- {issue}" for issue in sorted(issues)[:5]),
            'steps': '\n'.join(steps)
        }

    async def _extract_explanation_info(self, results: List[SearchResult]) -> Dict[str, Any]:
        """Extract information for understanding intent"""
        explanations = []
        concepts = set()
        structure_info = []

        for result in results[:5]:
            # Extract explanations
            if result.relevance_explanation:
                explanations.append(result.relevance_explanation)

            # Extract related concepts
            if hasattr(result, 'tags'):
                concepts.update(result.tags)

            # Extract structure information
            if result.function_name or result.class_name:
                structure_info.append({
                    'type': 'class' if result.class_name else 'function',
                    'name': result.class_name or result.function_name,
                    'file': result.file_path
                })

        # Format explanation
        main_explanation = '\n\n'.join(explanations[:3]) if explanations else "Based on the code analysis:"

        # Format structure
        structure_lines = []
        for info in structure_info[:5]:
            structure_lines.append(
                f"- {info['type'].capitalize()}: `{info['name']}` in `{info['file']}`"
            )

        return {
            'explanation': main_explanation,
            'concepts': '\n'.join(f"- {c}" for c in sorted(concepts)[:5]),
            'structure': '\n'.join(structure_lines)
        }

    async def _extract_refactoring_info(self, results: List[SearchResult]) -> Dict[str, Any]:
        """Extract information for refactoring intent"""
        patterns = []
        improvements = []

        for result in results[:3]:
            if result.quality_score and result.quality_score > 0.7:
                patterns.append({
                    'code': result.code_snippet,
                    'file': result.file_path,
                    'quality': result.quality_score
                })

        return {
            'patterns': patterns,
            'improvements': improvements
        }

    async def _extract_testing_info(self, results: List[SearchResult]) -> Dict[str, Any]:
        """Extract information for testing intent"""
        test_examples = []

        for result in results[:3]:
            if 'test' in result.file_path.lower():
                test_examples.append({
                    'code': result.code_snippet,
                    'file': result.file_path
                })

        return {
            'test_examples': test_examples
        }

    async def _extract_documentation_info(self, results: List[SearchResult]) -> Dict[str, Any]:
        """Extract information for documentation intent"""
        doc_examples = []

        for result in results[:3]:
            if result.code_snippet and ('"""' in result.code_snippet or "'''" in result.code_snippet):
                doc_examples.append({
                    'code': result.code_snippet,
                    'file': result.file_path
                })

        return {
            'doc_examples': doc_examples
        }

    def _fill_template(
        self,
        template: str,
        query: str,
        extracted_info: Dict[str, Any]
    ) -> str:
        """Fill template with extracted information"""
        # Start with query
        filled = template.replace('{query}', query)

        # Replace all template variables
        for key, value in extracted_info.items():
            placeholder = f'{{{key}}}'
            if placeholder in filled:
                filled = filled.replace(placeholder, str(value))

        # Remove any unfilled placeholders
        import re
        filled = re.sub(r'\{[^}]+\}', '', filled)

        # Clean up empty sections
        lines = filled.split('\n')
        cleaned_lines = []
        skip_next = False

        for i, line in enumerate(lines):
            if skip_next:
                skip_next = False
                continue

            # Skip empty sections
            if line.endswith(':') and i + 1 < len(lines) and not lines[i + 1].strip():
                skip_next = True
                continue

            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines).strip()

    def _calculate_confidence(self, results: List[SearchResult]) -> float:
        """Calculate confidence score based on search results"""
        if not results:
            return 0.0

        # Base confidence on top results' scores
        top_scores = [r.score for r in results[:5]]
        avg_score = sum(top_scores) / len(top_scores) if top_scores else 0.0

        # Adjust based on result count
        if len(results) >= 10:
            confidence = min(avg_score * 1.2, 1.0)
        elif len(results) >= 5:
            confidence = avg_score
        else:
            confidence = avg_score * 0.8

        return confidence

    async def generate_code(
        self,
        description: str,
        context: CodeContext,
        style_examples: List[SearchResult]
    ) -> str:
        """
        Generate code based on description and context (implementation of abstract method)

        Args:
            description: What code to generate
            context: Code context for generation
            style_examples: Example code snippets for style reference

        Returns:
            Generated code as string
        """
        logger.info(f"Generating code for: {description[:100]}...")

        # Extract language from context
        language = self._detect_language(context.current_file) if context else 'python'

        # Extract style patterns from examples
        style_patterns = []
        if style_examples:
            for example in style_examples[:3]:  # Use top 3 examples
                if example.code_snippet:
                    style_patterns.append(example.code_snippet)

        # Generate code based on language and context
        templates = {
            'python': f'''# Generated code for: {description}
# Context: {context.current_file if context else 'Unknown'}

def generated_function():
    """
    {description}
    """
    # TODO: Implement {description}
    pass
''',
            'javascript': f'''// Generated code for: {description}
// Context: {context.current_file if context else 'Unknown'}

function generatedFunction() {{
    /**
     * {description}
     */
    // TODO: Implement {description}
}}
''',
            'typescript': f'''// Generated code for: {description}
// Context: {context.current_file if context else 'Unknown'}

function generatedFunction(): void {{
    /**
     * {description}
     */
    // TODO: Implement {description}
}}
'''
        }

        # Get base template
        code = templates.get(language.lower(), f"// Generated code for: {description}")

        # If we have style examples, add them as reference comments
        if style_patterns:
            style_comments = []
            for i, pattern in enumerate(style_patterns[:2]):
                style_comments.append(f"// Style reference {i+1}:")
                style_comments.append(f"// {pattern.split(chr(10))[0][:50]}...")
            style_ref = "\n".join(style_comments)
            code = f"{style_ref}\n\n{code}"

        # Add imports if context has them
        if context and context.imports:
            imports_section = "\n".join(context.imports[:5])  # Top 5 imports
            if language == 'python':
                code = f"{imports_section}\n\n{code}"
            else:
                code = f"{imports_section}\n\n{code}"

        return code

    async def adapt_to_style(
        self,
        code: str,
        target_style: Dict[str, Any]
    ) -> str:
        """
        Adapt code to match target style (implementation of abstract method)

        Args:
            code: Code to adapt
            target_style: Target style configuration

        Returns:
            Style-adapted code
        """
        logger.info("Adapting code to target style")

        # Extract style preferences
        indent_size = target_style.get('indent_size', 4)
        use_tabs = target_style.get('use_tabs', False)
        quote_style = target_style.get('quote_style', 'single')  # 'single' or 'double'

        adapted_code = code

        # Apply indentation style
        if use_tabs:
            # Convert spaces to tabs
            lines = adapted_code.split('\n')
            adapted_lines = []
            for line in lines:
                # Count leading spaces
                stripped = line.lstrip(' ')
                space_count = len(line) - len(stripped)
                if space_count > 0:
                    # Convert to tabs (assuming 4 spaces = 1 tab)
                    tab_count = space_count // 4
                    remainder = space_count % 4
                    new_line = '\t' * tab_count + ' ' * remainder + stripped
                    adapted_lines.append(new_line)
                else:
                    adapted_lines.append(line)
            adapted_code = '\n'.join(adapted_lines)
        else:
            # Ensure consistent space indentation
            # This is a simplified implementation
            pass

        # Apply quote style (simplified)
        if quote_style == 'double':
            # Convert single quotes to double quotes (very simplified)
            adapted_code = adapted_code.replace("'", '"')
        elif quote_style == 'single':
            # Convert double quotes to single quotes (very simplified)
            adapted_code = adapted_code.replace('"', "'")

        # Add style metadata as comment
        style_comment = f"# Code adapted to style: indent={indent_size}, tabs={use_tabs}, quotes={quote_style}"
        adapted_code = f"{style_comment}\n{adapted_code}"

        return adapted_code

    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        if not file_path:
            return 'python'

        extension = file_path.split('.')[-1].lower()
        language_map = {
            'py': 'python',
            'js': 'javascript',
            'ts': 'typescript',
            'jsx': 'javascript',
            'tsx': 'typescript',
            'java': 'java',
            'cpp': 'cpp',
            'c': 'c',
            'cs': 'csharp',
            'go': 'go',
            'rs': 'rust',
            'rb': 'ruby',
            'php': 'php'
        }

        return language_map.get(extension, 'python')

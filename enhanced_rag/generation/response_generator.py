"""
Response generation module for creating contextual answers
"""

import logging
from typing import List, Dict, Any, Optional

from ..core.interfaces import Generator
from ..core.models import SearchResult, SearchIntent, GeneratedResponse

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
        
        # Generate response
        response_text = self._fill_template(template, query, extracted_info)
        
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

"""
Code generation MCP tool using enhanced RAG pipeline
"""

import logging
import re
from typing import Dict, Any, Optional, List

from ..pipeline import RAGPipeline, QueryContext
from ..core.models import SearchIntent

logger = logging.getLogger(__name__)


class CodeGenerationTool:
    """
    MCP tool for intelligent code generation using RAG pipeline
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.pipeline = RAGPipeline(config)
        self.config = config
        
    async def generate_code(
        self,
        description: str,
        language: str = "python",
        context_file: Optional[str] = None,
        style_guide: Optional[str] = None,
        include_tests: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate code based on description and context
        
        Args:
            description: What code to generate
            language: Target programming language
            context_file: Current file for context
            style_guide: Specific style guide to follow
            include_tests: Whether to generate tests
            
        Returns:
            Generated code with explanation and references
        """
        try:
            # Build enhanced query
            query = self._build_generation_query(description, language, include_tests)
            
            # Build context
            context = QueryContext(
                current_file=context_file,
                workspace_root=kwargs.get('workspace_root'),
                user_preferences={
                    "language": language,
                    "style_guide": style_guide,
                    "include_tests": include_tests
                }
            )
            
            # Process through pipeline with IMPLEMENT intent
            result = await self.pipeline.process_query(
                query=query,
                context=context,
                intent=SearchIntent.IMPLEMENT,
                max_results=10
            )
            
            if not result.success:
                return {
                    'success': False,
                    'error': result.error or 'Code generation failed'
                }
            
            # Extract generated code from response
            generated_code = self._extract_code_from_response(
                result.response,
                language
            )
            
            # Generate tests if requested
            test_code = None
            if include_tests:
                test_code = await self._generate_tests(
                    generated_code,
                    description,
                    language
                )
            
            return {
                'success': True,
                'code': generated_code,
                'language': language,
                'explanation': self._extract_explanation(result.response),
                'test_code': test_code,
                'references': [
                    {
                        'file': r.file_path,
                        'function': r.function_name,
                        'snippet': r.content[:200] + '...' if len(r.content) > 200 else r.content,
                        'relevance': r.score
                    }
                    for r in result.results[:5]
                ],
                'patterns_used': self._identify_patterns(result.results),
                'dependencies': self._extract_dependencies(generated_code, language)
            }
            
        except Exception as e:
            logger.error(f"Code generation error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _build_generation_query(
        self,
        description: str,
        language: str,
        include_tests: bool
    ) -> str:
        """Build query for code generation"""
        query = f"Generate {language} code: {description}"
        if include_tests:
            query += " with unit tests"
        return query
    
    def _extract_code_from_response(
        self,
        response: str,
        language: str
    ) -> str:
        """Extract code blocks from response"""
        # Look for code blocks with language marker
        pattern = rf'```{language}\n(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            return matches[0].strip()
        
        # Fallback to any code block
        pattern = r'```\n(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            return matches[0].strip()
        
        # If no code blocks, try to extract indented code
        lines = response.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            if line.startswith('    ') or line.startswith('\t'):
                in_code = True
                code_lines.append(line)
            elif in_code and line.strip() == '':
                code_lines.append(line)
            elif in_code:
                break
        
        return '\n'.join(code_lines).strip()
    
    def _extract_explanation(self, response: str) -> str:
        """Extract explanation from response"""
        # Remove code blocks
        explanation = re.sub(r'```[\s\S]*?```', '', response)
        # Clean up
        explanation = '\n'.join(line.strip() for line in explanation.split('\n'))
        return explanation.strip()
    
    async def _generate_tests(
        self,
        code: str,
        description: str,
        language: str
    ) -> Optional[str]:
        """Generate unit tests for the code"""
        test_query = f"Generate unit tests for {language}: {description}"
        
        result = await self.pipeline.process_query(
            query=test_query,
            context=QueryContext(user_preferences={"code": code}),
            intent=SearchIntent.TEST,
            max_results=5
        )
        
        if result.success and result.response:
            return self._extract_code_from_response(result.response, language)
        return None
    
    def _identify_patterns(self, results: List[Any]) -> List[str]:
        """Identify design patterns used in similar code"""
        patterns = set()
        
        pattern_keywords = {
            'singleton': ['singleton', 'instance', '_instance'],
            'factory': ['factory', 'create', 'build'],
            'observer': ['observer', 'listener', 'subscribe'],
            'decorator': ['decorator', 'wrapper', '@'],
            'strategy': ['strategy', 'algorithm', 'policy'],
            'adapter': ['adapter', 'wrapper', 'interface'],
            'template': ['template', 'abstract', 'hook']
        }
        
        for result in results[:10]:
            content_lower = result.content.lower()
            for pattern, keywords in pattern_keywords.items():
                if any(kw in content_lower for kw in keywords):
                    patterns.add(pattern)
        
        return list(patterns)
    
    def _extract_dependencies(self, code: str, language: str) -> List[str]:
        """Extract dependencies from generated code"""
        dependencies = set()
        
        if language == 'python':
            # Extract imports
            import_pattern = r'^(?:from\s+(\S+)|import\s+(\S+))'
            for match in re.finditer(import_pattern, code, re.MULTILINE):
                dep = match.group(1) or match.group(2)
                if dep and not dep.startswith('.'):
                    dependencies.add(dep.split('.')[0])
        
        elif language in ['javascript', 'typescript']:
            # Extract imports/requires
            import_pattern = r'(?:import.*from\s+[\'"](.+?)[\'"]|require\([\'"](.+?)[\'"]\))'
            for match in re.finditer(import_pattern, code):
                dep = match.group(1) or match.group(2)
                if dep and not dep.startswith('.'):
                    dependencies.add(dep)
        
        elif language == 'java':
            # Extract imports
            import_pattern = r'^import\s+(.+?);'
            for match in re.finditer(import_pattern, code, re.MULTILINE):
                dep = match.group(1)
                if dep and not dep.startswith('java.'):
                    dependencies.add(dep.split('.')[0])
        
        return sorted(list(dependencies))
    
    async def refactor_code(
        self,
        code: str,
        refactor_type: str,
        language: str = "python",
        context_file: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Refactor existing code
        
        Args:
            code: Code to refactor
            refactor_type: Type of refactoring (e.g., 'extract_function', 'rename', 'simplify')
            language: Programming language
            context_file: Current file for context
            
        Returns:
            Refactored code with explanation
        """
        query = f"Refactor {language} code - {refactor_type}: {code[:200]}..."
        
        context = QueryContext(
            current_file=context_file,
            user_preferences={
                "original_code": code,
                "refactor_type": refactor_type
            }
        )
        
        result = await self.pipeline.process_query(
            query=query,
            context=context,
            intent=SearchIntent.REFACTOR,
            max_results=5
        )
        
        if not result.success:
            return {
                'success': False,
                'error': result.error or 'Refactoring failed'
            }
        
        refactored_code = self._extract_code_from_response(
            result.response,
            language
        )
        
        return {
            'success': True,
            'original_code': code,
            'refactored_code': refactored_code,
            'explanation': self._extract_explanation(result.response),
            'improvements': self._identify_improvements(code, refactored_code),
            'references': [
                {
                    'file': r.file_path,
                    'pattern': r.function_name,
                    'relevance': r.score
                }
                for r in result.results[:3]
            ]
        }
    
    def _identify_improvements(self, original: str, refactored: str) -> List[str]:
        """Identify improvements made in refactoring"""
        improvements = []
        
        # Line count change
        orig_lines = len(original.strip().split('\n'))
        ref_lines = len(refactored.strip().split('\n'))
        if ref_lines < orig_lines:
            improvements.append(f"Reduced lines from {orig_lines} to {ref_lines}")
        
        # Check for common improvements
        if 'def ' in refactored and 'def ' not in original:
            improvements.append("Extracted functions for better modularity")
        
        if original.count('if ') > refactored.count('if '):
            improvements.append("Simplified conditional logic")
        
        if 'class ' in refactored and 'class ' not in original:
            improvements.append("Introduced class structure")
        
        return improvements
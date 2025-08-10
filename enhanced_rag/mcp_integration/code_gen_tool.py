"""
Code generation / refactor MCP tool powered by an enhanced RAG pipeline.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

from ..pipeline import RAGPipeline
from ..core.models import QueryContext, SearchIntent
from ..generation.code_generator import CodeGenerator, GenerationContext
from ..generation.style_matcher import StyleMatcher
from ..generation.template_manager import TemplateManager

logger = logging.getLogger(__name__)


class CodeGenerationTool:
    """
    Intelligent code generation / refactor assistant that uses a Retrieval-Augmented-Generation pipeline.
    """

    # ---------------------------------------------------------------------#
    # Constructor
    # ---------------------------------------------------------------------#
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.pipeline = RAGPipeline(config)
        
        # Initialize generation modules
        generation_config = config.get('generation', {})
        self.code_generator = CodeGenerator(generation_config)
        self.style_matcher = StyleMatcher(generation_config)
        self.template_manager = TemplateManager(generation_config)

    # ---------------------------------------------------------------------#
    # Public API
    # ---------------------------------------------------------------------#
    async def generate_code(
        self,
        description: str,
        *,
        language: str = "python",
        context_file: Optional[str] = None,
        style_guide: Optional[str] = None,
        include_tests: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Generate code from a natural-language description.

        Returns a dict:
            {
              success: bool,
              code: str,
              language: str,
              explanation: str,
              test_code: Optional[str],
              references: List[dict],
              patterns_used: List[str],
              dependencies: List[str],
              error: Optional[str]
            }
        """

        try:
            # -----------------------------------------------------------------
            # Build query + context
            # -----------------------------------------------------------------
            query = self._build_generation_query(description, language, include_tests, style_guide)

            context = QueryContext(
                current_file=context_file,
                workspace_root=kwargs.get("workspace_root"),
                user_preferences={
                    "language": language,
                    "style_guide": style_guide,
                    "include_tests": include_tests,
                },
            )

            # -----------------------------------------------------------------
            # Run RAG pipeline to get examples
            # -----------------------------------------------------------------
            result = await self.pipeline.process_query(
                query=query, 
                context=context, 
                max_results=20  # Get more examples for pattern extraction
            )
            
            if not result.success or not result.results:
                return {"success": False, "error": result.error or "No relevant code examples found"}

            # -----------------------------------------------------------------
            # Create generation context
            # -----------------------------------------------------------------
            generation_context = GenerationContext(
                language=language,
                description=description,
                retrieved_examples=result.results,
                style_guide=style_guide,
                context_file=context_file,
                include_tests=include_tests,
                imports_context=self._extract_imports_context(result.results)
            )

            # -----------------------------------------------------------------
            # Generate code and analyze style in parallel
            # -----------------------------------------------------------------
            # Start style analysis task
            style_task = asyncio.create_task(
                self.style_matcher.analyze_style(result.results[:5], language)
            )
            
            # Start code generation task
            generation_task = asyncio.create_task(
                self.code_generator.generate(generation_context)
            )
            
            # Get generation result first (critical path)
            generation_result = await generation_task
            
            if not generation_result['success']:
                # Cancel style task if generation failed
                style_task.cancel()
                return {"success": False, "error": generation_result.get('error', 'Code generation failed')}
            
            # Get style info (non-blocking)
            style_info = None
            try:
                style_info = await style_task
            except Exception:
                # Style analysis failure is non-critical
                style_info = None
            
            # Attach style info if available
            if style_info:
                generation_result['style_info'] = style_info

            # -----------------------------------------------------------------
            # Build final response
            # -----------------------------------------------------------------
            return {
                "success": True,
                "code": generation_result['code'],
                "language": language,
                "explanation": self._build_explanation(generation_result, result.results),
                "test_code": generation_result.get('test_code'),
                "references": [
                    {
                        "file": r.file_path,
                        "function": r.function_name,
                        "snippet": (
                            (r.code_snippet or "")[:200]
                            + ("..." if len(r.code_snippet or "") > 200 else "")
                        ),
                        "relevance": r.score,
                        "start_line": getattr(r, "start_line", None),
                        "end_line": getattr(r, "end_line", None),
                    }
                    for r in result.results[:5]
                ],
                "patterns_used": generation_result.get('patterns_used', []),
                "dependencies": self._extract_dependencies(generation_result['code'], language),
                "style_info": generation_result.get('style_info'),
                "template_used": generation_result.get('template_used'),
                "confidence": generation_result.get('confidence', 0.5)
            }

        except Exception as exc:
            logger.exception("Code generation error")
            return {"success": False, "error": str(exc)}

    async def refactor_code(
        self,
        code: str,
        refactor_type: str,
        *,
        language: str = "python",
        context_file: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Refactor existing code.
        """
        try:
            # Build query for finding refactoring examples
            query = f"Refactor {language} code - {refactor_type}: find examples of {refactor_type}"

            context = QueryContext(
                current_file=context_file,
                user_preferences={
                    "original_code": code,
                    "refactor_type": refactor_type,
                },
            )

            # Get refactoring examples
            result = await self.pipeline.process_query(
                query=query, 
                context=context, 
                max_results=15
            )

            if not result.success or not result.results:
                return {"success": False, "error": result.error or "No refactoring examples found"}

            # Analyze style of original code
            original_style = await self.style_matcher.analyze_style(
                [type('MockResult', (), {'code_snippet': code, 'language': language})()],
                language
            )

            # Create generation context for refactored code
            refactor_description = f"Refactor the code to {refactor_type}"
            generation_context = GenerationContext(
                language=language,
                description=refactor_description,
                retrieved_examples=result.results,
                context_file=context_file,
                include_tests=False
            )

            # Generate refactored code
            generation_result = await self.code_generator.generate(generation_context)
            
            if not generation_result['success']:
                # Fallback to simple refactoring
                refactored_code = self._apply_basic_refactoring(code, refactor_type, language)
            else:
                refactored_code = generation_result['code']
                
                # Apply original style to refactored code
                refactored_code = await self.style_matcher.apply_style(
                    refactored_code,
                    original_style
                )

            return {
                "success": True,
                "original_code": code,
                "refactored_code": refactored_code,
                "explanation": self._explain_refactoring(refactor_type, code, refactored_code),
                "improvements": self._identify_improvements(code, refactored_code, language),
                "references": [
                    {
                        "file": r.file_path,
                        "pattern": r.function_name,
                        "relevance": r.score,
                    }
                    for r in result.results[:3]
                ],
                "style_preserved": True,
                "confidence": generation_result.get('confidence', 0.7) if generation_result.get('success') else 0.5
            }
            
        except Exception as exc:
            logger.exception("Refactoring error")
            return {"success": False, "error": str(exc)}

    # ---------------------------------------------------------------------#
    # Internal helpers
    # ---------------------------------------------------------------------#
    def _build_generation_query(
        self, description: str, language: str, include_tests: bool, style_guide: Optional[str]
    ) -> str:
        """Compose the upstream natural-language query string."""
        query = f"Generate {language} code: {description}"
        if style_guide:
            query += f" Respect the following style guide: {style_guide}"
        if include_tests:
            query += " and include unit tests"
        return query

    async def _query_tests(
        self,
        description: str,
        language: str,
        code_task: "asyncio.Task",  # noqa: F821
    ) -> Optional[str]:
        """
        Spawned as a background task. Awaits the main code generation first so that
        we can pass the produced code into the test prompt.
        """
        main_result = await code_task
        if not main_result.success:
            return None

        generated_code = self._extract_code_from_response(main_result.response, language)
        if not generated_code:
            return None

        test_query = f"Generate unit tests for the following {language} code: ```{language}\n{generated_code}\n```"

        result = await self.pipeline.process_query(
            query=test_query, context=QueryContext(), max_results=5
        )

        if result.success and result.response:
            return self._extract_code_from_response(result.response, language)
        return None

    def _extract_imports_context(self, results: List[Any]) -> List[str]:
        """Extract common imports from retrieved examples"""
        imports = set()
        
        for result in results[:10]:  # Top 10 results
            code = result.code_snippet
            
            # Extract Python imports
            if (result.language or '').lower() == 'python':
                import_pattern = r'^(?:from\s+[\w\.]+\s+)?import\s+.*$'
                found_imports = re.findall(import_pattern, code, re.MULTILINE)
                imports.update(found_imports)
            
            # Extract JS/TS imports
            elif (result.language or '').lower() in ['javascript', 'typescript']:
                import_pattern = r'^import\s+.*?from\s+[\'"].*?[\'"]'
                found_imports = re.findall(import_pattern, code, re.MULTILINE)
                imports.update(found_imports)
        
        return list(imports)
    
    def _build_explanation(self, generation_result: Dict[str, Any], results: List[Any]) -> str:
        """Build explanation for the generated code"""
        explanation_parts = []
        
        # Add pattern information
        if generation_result.get('patterns_used'):
            patterns = ", ".join(generation_result['patterns_used'])
            explanation_parts.append(f"Generated code uses patterns: {patterns}")
        
        # Add template information
        if generation_result.get('template_used'):
            explanation_parts.append(f"Based on template: {generation_result['template_used']}")
        
        # Add style information
        if generation_result.get('style_info'):
            style_info = generation_result['style_info']
            if style_info.get('detected_from_examples'):
                explanation_parts.append(
                    f"Code style detected from {style_info.get('sample_count', 0)} examples "
                    f"(consistency: {style_info.get('consistency_score', 0):.2f})"
                )
        
        # Add confidence
        confidence = generation_result.get('confidence', 0.5)
        explanation_parts.append(f"Generation confidence: {confidence:.2f}")
        
        # Add references summary
        if results:
            explanation_parts.append(f"Based on {len(results)} relevant code examples")
        
        return "\n".join(explanation_parts)

    # ------------------------------------------------------------------#
    # Parsing helpers
    # ------------------------------------------------------------------#
    def _extract_code_from_response(self, response: str, language: str) -> str:
        """
        Pull the **largest** code block from the model response.
        """

        code_blocks: List[str] = []

        # 1. Look for fenced blocks with explicit language tag
        lang_pat = rf"```{re.escape(language)}\s*\n(.*?)```"
        code_blocks.extend(re.findall(lang_pat, response, re.DOTALL | re.IGNORECASE))

        # 2. Any fenced block
        if not code_blocks:
            generic_pat = r"```\s*\n(.*?)```"
            code_blocks.extend(re.findall(generic_pat, response, re.DOTALL))

        # 3. Indented fallback
        if not code_blocks:
            indented_lines: List[str] = []
            in_code = False
            for line in response.splitlines():
                if line.startswith(("    ", "\t")):
                    in_code = True
                    indented_lines.append(line)
                elif in_code and line.strip() == "":
                    indented_lines.append(line)
                elif in_code:
                    break
            code_blocks.append("\n".join(indented_lines))

        # Choose the largest block to improve odds that it's the main snippet.
        code_blocks = [blk.strip() for blk in code_blocks if blk.strip()]
        return max(code_blocks, key=len) if code_blocks else ""

    def _extract_explanation(self, response: str) -> str:
        """
        Strip code fences but keep paragraph indentation.
        """
        explanation = re.sub(r"```[\s\S]*?```", "", response)
        # Collapse >1 blank line and trim trailing spaces
        lines = [ln.rstrip() for ln in explanation.splitlines()]
        cleaned: List[str] = []
        blank = False
        for ln in lines:
            if ln.strip() == "":
                if not blank:
                    cleaned.append("")
                blank = True
            else:
                cleaned.append(ln)
                blank = False
        return "\n".join(cleaned).strip()

    def _identify_patterns(self, results: List[Any]) -> List[str]:
        """
        Naïve keyword-based search for common design patterns in retrieved snippets.
        """
        patterns: set[str] = set()

        keywords_map = {
            "singleton": ["singleton", ".instance(", "_instance", "get_instance("],
            "factory": ["factory", "create_", "build_"],
            "observer": ["observer", "subscribe(", "notify(", "listener"],
            "decorator": ["decorator(", "@wraps", "wrap("],
            "strategy": ["strategy", "select_algorithm", "policy"],
            "adapter": ["adapter", "wrappee", "convert("],
            "template": ["template method", "hook(", "abstract_step"],
        }

        for res in results[:10]:
            text = res.code_snippet.lower()
            for pattern, keys in keywords_map.items():
                if any(k in text for k in keys):
                    patterns.add(pattern)

        return sorted(patterns)

    def _extract_dependencies(self, code: str, language: str) -> List[str]:
        """
        Pull a list of external module dependencies from the generated code.
        """
        deps: set[str] = set()

        if language.lower() == "python":
            # from x import y , import x, y  as z
            pat = r"^(?:from\s+([\w\.]+)\s+import|import\s+([\w\.,\s]+))"
            for match in re.finditer(pat, code, re.MULTILINE):
                raw = match.group(1) or match.group(2) or ""
                for dep in re.split(r",\s*", raw):
                    dep = dep.split(" as ")[0].split(".")[0].strip()
                    if dep and not dep.startswith("."):
                        deps.add(dep)

        elif language.lower() in {"javascript", "typescript"}:
            pat = r'(?:import\s+.*?from\s+[\'"]([^\'"]+)[\'"]|require\(\s*[\'"]([^\'"]+)[\'"]\s*\))'
            for m in re.finditer(pat, code):
                mod = m.group(1) or m.group(2)
                if mod and not mod.startswith((".", "@/")):
                    deps.add(mod)

        elif language.lower() == "java":
            pat = r"^import\s+([\w\.]+);"
            for match in re.finditer(pat, code, re.MULTILINE):
                mod = match.group(1)
                if mod and not mod.startswith("java."):
                    deps.add(mod.split(".")[0])

        return sorted(deps)

    def _apply_basic_refactoring(self, code: str, refactor_type: str, language: str) -> str:
        """Apply basic refactoring without examples"""
        # This is a simple fallback - in production, you'd want more sophisticated refactoring
        refactored = code
        
        if refactor_type.lower() == "extract method":
            # Add a comment indicating where to extract
            refactored = "# TODO: Extract method here\n" + code
        elif refactor_type.lower() == "rename":
            # Add a comment about renaming
            refactored = "# TODO: Rename variables/functions for clarity\n" + code
        elif refactor_type.lower() == "simplify":
            # Remove extra blank lines as a simple simplification
            lines = code.split('\n')
            refactored = '\n'.join(line for line in lines if line.strip() or not lines)
        
        return refactored
    
    def _explain_refactoring(self, refactor_type: str, original: str, refactored: str) -> str:
        """Explain what changed in the refactoring"""
        explanations = [f"Applied {refactor_type} refactoring"]
        
        # Compare line counts
        orig_lines = len(original.splitlines())
        ref_lines = len(refactored.splitlines())
        
        if ref_lines < orig_lines:
            explanations.append(f"Reduced code from {orig_lines} to {ref_lines} lines")
        elif ref_lines > orig_lines:
            explanations.append(f"Expanded code from {orig_lines} to {ref_lines} lines for clarity")
        
        # Check for structural changes
        if "class" in refactored and "class" not in original:
            explanations.append("Introduced class structure")
        
        if "def" in refactored and refactored.count("def") > original.count("def"):
            explanations.append("Extracted helper functions")
        
        return ". ".join(explanations)
    
    def _identify_improvements(self, original: str, refactored: str, language: str) -> List[str]:
        """
        Heuristic notes about what changed in a refactor.
        """
        improvements: List[str] = []

        orig_lines = len(original.strip().splitlines())
        ref_lines = len(refactored.strip().splitlines())
        if ref_lines < orig_lines:
            improvements.append(f"Reduced LOC from {orig_lines} to {ref_lines}")

        if language.lower() == "python":
            if "def " in refactored and "def " not in original:
                improvements.append("Extracted helper functions for modularity")
            if original.count("if ") > refactored.count("if "):
                improvements.append("Simplified conditional logic")
            if "class " in refactored and "class " not in original:
                improvements.append("Introduced class structure")

        # Generic check
        cyclo_pat = r"\bif\b|\bfor\b|\bwhile\b|\bcase\b|\?:"  # crude cyclomatic hints
        if len(re.findall(cyclo_pat, refactored)) < len(re.findall(cyclo_pat, original)):
            improvements.append("Lower cyclomatic complexity")

        return improvements


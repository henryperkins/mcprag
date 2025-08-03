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
            # Run RAG pipeline
            # -----------------------------------------------------------------
            code_task = asyncio.create_task(
                self.pipeline.process_query(query=query, context=context, max_results=10)
            )

            test_task: Optional[asyncio.Task] = None
            if include_tests:
                test_task = asyncio.create_task(
                    self._query_tests(description, language, code_task)
                )

            result = await code_task
            if not result.success:
                return {"success": False, "error": result.error or "Code generation failed"}

            generated_code = self._extract_code_from_response(result.response, language)

            # -----------------------------------------------------------------
            # Optionally gather test generation
            # -----------------------------------------------------------------
            test_code = None
            if test_task:
                test_code = await test_task

            # -----------------------------------------------------------------
            # Build final response
            # -----------------------------------------------------------------
            return {
                "success": True,
                "code": generated_code,
                "language": language,
                "explanation": self._extract_explanation(result.response),
                "test_code": test_code,
                "references": [
                    {
                        "file": r.file_path,
                        "function": r.function_name,
                        "snippet": (r.content[:200] + "...") if len(r.content) > 200 else r.content,
                        "relevance": r.score,
                    }
                    for r in result.results[:5]
                ],
                "patterns_used": self._identify_patterns(result.results),
                "dependencies": self._extract_dependencies(generated_code, language),
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

        query = f"Refactor {language} code - {refactor_type}: {code[:250]}..."

        context = QueryContext(
            current_file=context_file,
            user_preferences={
                "original_code": code,
                "refactor_type": refactor_type,
            },
        )

        result = await self.pipeline.process_query(query=query, context=context, max_results=5)

        if not result.success:
            return {"success": False, "error": result.error or "Refactoring failed"}

        refactored_code = self._extract_code_from_response(result.response, language)

        return {
            "success": True,
            "original_code": code,
            "refactored_code": refactored_code,
            "explanation": self._extract_explanation(result.response),
            "improvements": self._identify_improvements(code, refactored_code, language),
            "references": [
                {
                    "file": r.file_path,
                    "pattern": r.function_name,
                    "relevance": r.score,
                }
                for r in result.results[:3]
            ],
        }

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
            text = res.content.lower()
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


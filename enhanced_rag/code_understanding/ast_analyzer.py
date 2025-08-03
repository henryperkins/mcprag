"""
AST Analyzer for code understanding
Provides AST-based analysis for Python and JavaScript/TypeScript files
"""

import ast
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

logger = logging.getLogger(__name__)


class ASTAnalyzer:
    """
    Analyzes code files using Abstract Syntax Trees (AST)
    Supports Python (native) and JavaScript/TypeScript (via Babel)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.parse_js_path = Path(__file__).parent.parent.parent / "parse_js.mjs"

        # Cache for parsed AST results
        self._ast_cache: Dict[str, Dict[str, Any]] = {}

    async def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a code file and extract AST information

        Args:
            file_path: Path to the file to analyze

        Returns:
            Dictionary containing AST analysis results
        """
        file_path = Path(file_path)

        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return self._empty_result()

        # Check cache
        cache_key = str(file_path.absolute())
        if cache_key in self._ast_cache:
            return self._ast_cache[cache_key]

        try:
            if file_path.suffix == '.py':
                result = await self._analyze_python_file(file_path)
            elif file_path.suffix in ['.js', '.jsx', '.ts', '.tsx']:
                result = await self._analyze_javascript_file(file_path)
            else:
                logger.debug(f"Unsupported file type: {file_path.suffix}")
                result = self._empty_result()

            # Cache the result
            self._ast_cache[cache_key] = result
            return result

        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return self._empty_result()

    async def _analyze_python_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze Python file using native AST module"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))

            # Extract information
            imports = self._extract_python_imports(tree)
            functions = self._extract_python_functions(tree, content)
            classes = self._extract_python_classes(tree, content)
            dependencies = self._extract_python_dependencies(tree)

            return {
                'language': 'python',
                'imports': imports,
                'functions': functions,
                'classes': classes,
                'dependencies': dependencies,
                'file_path': str(file_path)
            }

        except Exception as e:
            logger.error(f"Error parsing Python file {file_path}: {e}")
            return self._empty_result()

    async def _analyze_javascript_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze JavaScript/TypeScript file using Babel parser"""
        if not self.parse_js_path.exists():
            logger.warning(f"JavaScript parser not found at {self.parse_js_path}")
            return self._empty_result()

        try:
            # Run the Node.js parser
            result = subprocess.run(
                ['node', str(self.parse_js_path), str(file_path)],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.error(f"JS parser error: {result.stderr}")
                return self._empty_result()

            # Parse the JSON output
            chunks = json.loads(result.stdout)

            # Convert chunks to our format
            functions = []
            classes = []
            imports = []

            for chunk in chunks:
                if chunk['type'] == 'function':
                    functions.append({
                        'name': chunk['name'],
                        'signature': chunk.get('signature', ''),
                        'start_line': chunk['start_line'],
                        'end_line': chunk['end_line'],
                        'is_async': 'async' in chunk.get('signature', ''),
                        'docstring': chunk.get('docstring', '')
                    })
                elif chunk['type'] == 'class':
                    classes.append({
                        'name': chunk['name'],
                        'start_line': chunk['start_line'],
                        'end_line': chunk['end_line'],
                        'methods': []  # Could be enhanced to extract methods
                    })
                elif chunk['type'] == 'import':
                    imports.append(chunk.get('value', ''))

            return {
                'language': 'javascript',
                'imports': imports,
                'functions': functions,
                'classes': classes,
                'dependencies': [],  # Could be enhanced
                'file_path': str(file_path)
            }

        except Exception as e:
            logger.error(f"Error parsing JavaScript file {file_path}: {e}")
            return self._empty_result()

    def _extract_python_imports(self, tree: ast.AST) -> List[str]:
        """Extract import statements from Python AST"""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    if alias.name == '*':
                        imports.append(f"{module}.*")
                    else:
                        imports.append(f"{module}.{alias.name}")

        return imports

    def _extract_python_functions(self, tree: ast.AST, content: str) -> List[Dict[str, Any]]:
        """Extract function definitions from Python AST"""
        functions = []
        lines = content.split('\n')

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Extract signature
                start_line = node.lineno - 1
                end_line = node.end_lineno or start_line

                # Get the function signature
                signature_lines = []
                for i in range(start_line, min(end_line + 1, len(lines))):
                    signature_lines.append(lines[i])
                    if ')' in lines[i]:
                        break

                signature = ' '.join(signature_lines).strip()

                # Extract docstring
                docstring = ast.get_docstring(node) or ''

                functions.append({
                    'name': node.name,
                    'signature': signature,
                    'start_line': node.lineno,
                    'end_line': node.end_lineno,
                    'is_async': isinstance(node, ast.AsyncFunctionDef),
                    'docstring': docstring,
                    'decorators': [d.id for d in node.decorator_list if isinstance(d, ast.Name)]
                })

        return functions

    def _extract_python_classes(self, tree: ast.AST, content: str) -> List[Dict[str, Any]]:
        """Extract class definitions from Python AST"""
        classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = []

                # Extract methods
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.append({
                            'name': item.name,
                            'is_async': isinstance(item, ast.AsyncFunctionDef),
                            'decorators': [d.id for d in item.decorator_list if isinstance(d, ast.Name)]
                        })

                classes.append({
                    'name': node.name,
                    'start_line': node.lineno,
                    'end_line': node.end_lineno,
                    'methods': methods,
                    'bases': [base.id for base in node.bases if isinstance(base, ast.Name)]
                })

        return classes

    def _extract_python_dependencies(self, tree: ast.AST) -> List[str]:
        """Extract function calls that might be dependencies"""
        dependencies = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    dependencies.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        dependencies.add(f"{node.func.value.id}.{node.func.attr}")

        # Filter out built-ins and common functions
        builtins = {'print', 'len', 'range', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple'}
        dependencies = [d for d in dependencies if d not in builtins]

        return sorted(list(dependencies))

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty analysis result"""
        return {
            'language': 'unknown',
            'imports': [],
            'functions': [],
            'classes': [],
            'dependencies': [],
            'file_path': ''
        }

    async def find_symbol_definition(self, file_path: str, symbol_name: str) -> Optional[Dict[str, Any]]:
        """
        Find the definition of a symbol in a file

        Args:
            file_path: Path to the file
            symbol_name: Name of the symbol to find

        Returns:
            Dictionary with symbol information or None if not found
        """
        analysis = await self.analyze_file(file_path)

        # Check functions
        for func in analysis.get('functions', []):
            if func['name'] == symbol_name:
                return {
                    'type': 'function',
                    'definition': func,
                    'file_path': file_path
                }

        # Check classes
        for cls in analysis.get('classes', []):
            if cls['name'] == symbol_name:
                return {
                    'type': 'class',
                    'definition': cls,
                    'file_path': file_path
                }

            # Check class methods
            for method in cls.get('methods', []):
                if method['name'] == symbol_name:
                    return {
                        'type': 'method',
                        'definition': method,
                        'class': cls['name'],
                        'file_path': file_path
                    }

        return None

    async def extract_call_graph(self, file_path: str) -> Dict[str, Set[str]]:
        """
        Extract call graph from a file

        Returns:
            Dictionary mapping function names to sets of called functions
        """
        # This is a simplified implementation
        # A full implementation would track function calls within each function
        analysis = await self.analyze_file(file_path)

        call_graph = {}
        for func in analysis.get('functions', []):
            # For now, use the dependencies as a rough approximation
            call_graph[func['name']] = set(analysis.get('dependencies', []))

        return call_graph

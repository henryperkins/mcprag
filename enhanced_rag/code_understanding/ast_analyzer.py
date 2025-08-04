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


def _safe_unparse(node: Optional[ast.AST]) -> str:
    """Safely unparse AST nodes across Python versions."""
    if node is None:
        return ""
    try:
        # Available in Python 3.9+
        return ast.unparse(node)  # type: ignore[attr-defined]
    except Exception:
        # Fallbacks for common node types
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{_safe_unparse(node.value)}.{node.attr}"
        if isinstance(node, ast.Subscript):
            return f"{_safe_unparse(node.value)}[{_safe_unparse(node.slice)}]"
        if isinstance(node, ast.Tuple):
            return "(" + ", ".join(_safe_unparse(e) for e in node.elts) + ")"
        if isinstance(node, ast.Constant):
            return repr(node.value)
        return type(node).__name__


def _decorator_to_str(dec: ast.expr) -> str:
    """Return a readable decorator representation."""
    if isinstance(dec, ast.Name):
        return dec.id
    if isinstance(dec, ast.Attribute):
        return f"{_safe_unparse(dec)}"
    if isinstance(dec, ast.Call):
        return f"{_safe_unparse(dec.func)}(...)"
    return _safe_unparse(dec)


def _format_function_signature(fn: ast.AST, source: str) -> str:
    """Build a robust signature string for FunctionDef/AsyncFunctionDef."""
    assert isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
    prefix = "async def " if isinstance(fn, ast.AsyncFunctionDef) else "def "
    name = fn.name
    args = fn.args

    def fmt_arg(arg: ast.arg, default: Optional[ast.expr] = None) -> str:
        ann = _safe_unparse(arg.annotation) if getattr(arg, "annotation", None) else ""
        default_str = f"={_safe_unparse(default)}" if default is not None else ""
        if ann:
            return f"{arg.arg}: {ann}{default_str}"
        return f"{arg.arg}{default_str}"

    parts: List[str] = []

    # Positional-only args (3.8+)
    posonly = getattr(args, "posonlyargs", [])
    if posonly:
        defaults = args.defaults[: len(posonly)]
        for i, a in enumerate(posonly):
            parts.append(fmt_arg(a, defaults[i] if i < len(defaults) else None))
        parts.append("/")

    # Regular args
    regular = args.args
    reg_defaults = args.defaults[len(posonly):] if posonly else args.defaults
    num_defaults = len(reg_defaults)
    for i, a in enumerate(regular):
        default = reg_defaults[i - (len(regular) - num_defaults)] if i >= len(regular) - num_defaults else None
        parts.append(fmt_arg(a, default))

    # Vararg
    if args.vararg:
        var_ann = _safe_unparse(args.vararg.annotation) if getattr(args.vararg, "annotation", None) else ""
        parts.append(f"*{args.vararg.arg}" + (f": {var_ann}" if var_ann else ""))
    elif args.kwonlyargs:
        # Indicate start of kw-only section when no *vararg
        parts.append("*")

    # Kwonly args
    for i, a in enumerate(args.kwonlyargs):
        default = args.kw_defaults[i]
        parts.append(fmt_arg(a, default))

    # Kwarg
    if args.kwarg:
        kw_ann = _safe_unparse(args.kwarg.annotation) if getattr(args.kwarg, "annotation", None) else ""
        parts.append(f"**{args.kwarg.arg}" + (f": {kw_ann}" if kw_ann else ""))

    ret = _safe_unparse(getattr(fn, "returns", None))
    ret_str = f" -> {ret}" if ret else ""
    return f"{prefix}{name}(" + ", ".join(parts) + f"){ret_str}"


def _format_class_signature(cls: ast.ClassDef) -> str:
    bases = [_safe_unparse(b) for b in cls.bases] if getattr(cls, "bases", None) else []
    if bases:
        return f"class {cls.name}(" + ", ".join(bases) + ")"
    return f"class {cls.name}"


class ASTAnalyzer:
    """
    Analyzes code files using Abstract Syntax Trees (AST)
    Supports Python (native) and JavaScript/TypeScript (via Babel)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        # Prefer project-root parse_js.mjs; allow override
        parser_override = self.config.get("js_parser_path")
        if parser_override:
            self.parse_js_path = Path(parser_override)
        else:
            self.parse_js_path = Path(__file__).resolve().parents[2] / "parse_js.mjs"

        # Node executable and timeout (configurable)
        self.node_cmd = self.config.get("node_command", "node")
        self.js_timeout = int(self.config.get("js_timeout_seconds", 10))

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
        file_path_path = Path(file_path)

        if not file_path_path.exists():
            logger.warning(f"File not found: {file_path_path}")
            return self._empty_result()

        # Check cache
        cache_key = str(file_path_path.absolute())
        if cache_key in self._ast_cache:
            return self._ast_cache[cache_key]

        try:
            suffix = file_path_path.suffix.lower()
            if suffix in ('.py', '.pyi'):
                result = await self._analyze_python_file(file_path_path)
            elif suffix in ['.js', '.jsx', '.ts', '.tsx']:
                result = await self._analyze_javascript_file(file_path_path)
            else:
                logger.debug(f"Unsupported file type: {file_path_path.suffix}")
                result = self._empty_result()

            # Cache the result
            self._ast_cache[cache_key] = result
            return result

        except Exception as e:
            logger.error(f"Error analyzing file {file_path_path}: {e}")
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
                [self.node_cmd, str(self.parse_js_path), str(file_path)],
                capture_output=True,
                text=True,
                timeout=self.js_timeout
            )

            if result.returncode != 0:
                logger.error(f"JS parser error: {result.stderr}")
                return self._empty_result()

            # Parse the JSON output
            try:
                chunks = json.loads(result.stdout)
            except json.JSONDecodeError as je:
                logger.error(f"JS parser invalid JSON for {file_path}: {je}; raw={result.stdout[:500]}")
                return self._empty_result()

            # Convert chunks to our format defensively
            functions: List[Dict[str, Any]] = []
            classes: List[Dict[str, Any]] = []
            imports: List[str] = []

            for chunk in chunks if isinstance(chunks, list) else []:
                ctype = chunk.get('type')
                if ctype == 'function':
                    sig = chunk.get('signature', '') or ''
                    functions.append({
                        'name': chunk.get('name', ''),
                        'signature': sig,
                        'start_line': chunk.get('start_line', 1),
                        'end_line': chunk.get('end_line', 1),
                        'is_async': 'async' in sig,
                        'docstring': chunk.get('docstring', ''),
                        'decorators': chunk.get('decorators', []),
                    })
                elif ctype == 'class':
                    classes.append({
                        'name': chunk.get('name', ''),
                        'start_line': chunk.get('start_line', 1),
                        'end_line': chunk.get('end_line', 1),
                        'methods': chunk.get('methods', []),
                        'bases': chunk.get('bases', []),
                    })
                elif ctype == 'import':
                    val = chunk.get('value') or chunk.get('module') or ''
                    if val:
                        imports.append(val)

            return {
                'language': 'javascript',
                'imports': list(dict.fromkeys(imports)),
                'functions': functions,
                'classes': classes,
                'dependencies': [],
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
        """Extract function definitions from Python AST with robust signatures and decorators."""
        functions: List[Dict[str, Any]] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                signature = _format_function_signature(node, content)
                docstring = ast.get_docstring(node) or ''
                decorators = [_decorator_to_str(d) for d in getattr(node, "decorator_list", [])]

                functions.append({
                    'name': node.name,
                    'signature': signature,
                    'start_line': getattr(node, "lineno", 1),
                    'end_line': getattr(node, "end_lineno", getattr(node, "lineno", 1)),
                    'is_async': isinstance(node, ast.AsyncFunctionDef),
                    'docstring': docstring,
                    'decorators': decorators
                })

        return functions

    def _extract_python_classes(self, tree: ast.AST, content: str) -> List[Dict[str, Any]]:
        """Extract class definitions from Python AST with method details and bases."""
        classes: List[Dict[str, Any]] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods: List[Dict[str, Any]] = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.append({
                            'name': item.name,
                            'signature': _format_function_signature(item, content),
                            'is_async': isinstance(item, ast.AsyncFunctionDef),
                            'decorators': [_decorator_to_str(d) for d in getattr(item, "decorator_list", [])],
                            'docstring': ast.get_docstring(item) or '',
                            'start_line': getattr(item, "lineno", 1),
                            'end_line': getattr(item, "end_lineno", getattr(item, "lineno", 1)),
                        })

                bases = [_safe_unparse(b) for b in getattr(node, "bases", [])]

                classes.append({
                    'name': node.name,
                    'start_line': getattr(node, "lineno", 1),
                    'end_line': getattr(node, "end_lineno", getattr(node, "lineno", 1)),
                    'methods': methods,
                    'bases': bases,
                    'signature': _format_class_signature(node),
                    'docstring': ast.get_docstring(node) or '',
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

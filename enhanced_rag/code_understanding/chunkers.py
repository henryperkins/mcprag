"""
Code Chunking Utilities
Shared chunking logic for both local and remote indexing
"""

import ast
import json
import subprocess
import logging
from typing import List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class CodeChunker:
    """Smart code chunking for optimal search and retrieval."""
    
    @staticmethod
    def chunk_python_file(content: str, file_path: str) -> List[Dict[str, Any]]:
        """Extract semantic chunks from Python code.
        
        Args:
            content: Python source code
            file_path: Path to the file (for context)
            
        Returns:
            List of chunk dictionaries with metadata
        """
        chunks = []
        try:
            tree = ast.parse(content)
            
            # Build parent mapping
            parent_map = {
                child: parent
                for parent in ast.walk(tree)
                for child in ast.iter_child_nodes(parent)
            }
            
            for node in ast.walk(tree):
                # Skip methods inside classes
                if isinstance(node, ast.FunctionDef) and isinstance(
                    parent_map.get(node), ast.ClassDef
                ):
                    continue
                    
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    # Extract function/class with context
                    start_line = node.lineno - 1
                    end_line = node.end_lineno or start_line + 10
                    
                    chunk_lines = content.splitlines()[start_line:end_line]
                    chunk_code = "\n".join(chunk_lines)
                    
                    # Extract semantic information
                    imports = CodeChunker._extract_imports(tree)
                    calls = CodeChunker._extract_function_calls(node)
                    signature = CodeChunker._get_signature(node)
                    
                    # Create semantic context
                    semantic_context = f"""
{signature} in {file_path}
Uses: {', '.join(imports[:10])}
Calls: {', '.join(calls[:10])}
Purpose: {CodeChunker._extract_docstring(node) or 'Implementation details in code'}
                    """.strip()
                    
                    chunks.append({
                        "content": chunk_code,
                        "semantic_context": semantic_context,
                        "signature": signature,
                        "imports": imports,
                        "dependencies": calls,
                        "chunk_type": (
                            "function" if isinstance(node, ast.FunctionDef) else "class"
                        ),
                        "start_line": start_line + 1,
                        "end_line": end_line,
                        "function_name": node.name if isinstance(node, ast.FunctionDef) else None,
                        "class_name": node.name if isinstance(node, ast.ClassDef) else None,
                        "docstring": CodeChunker._extract_docstring(node)
                    })
                    
        except (SyntaxError, UnicodeDecodeError, ValueError) as e:
            # Fallback for non-parseable code
            logger.warning(f"Could not parse {file_path}: {e}")
            chunks.append({
                "content": content[:5000],
                "semantic_context": f"Code from {file_path}",
                "signature": "",
                "imports": [],
                "dependencies": [],
                "chunk_type": "file",
                "start_line": 1,
                "end_line": len(content.splitlines()),
                "function_name": None,
                "class_name": None,
                "docstring": ""
            })
            
        return chunks
    
    @staticmethod
    def _extract_imports(source_or_tree, language: str = "python") -> List[str]:
        """Extract imports from code."""
        if language.lower() == "python":
            if isinstance(source_or_tree, str):
                try:
                    tree = ast.parse(source_or_tree)
                except SyntaxError:
                    return []
            else:
                tree = source_or_tree
                
            collected = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    collected.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    for alias in node.names:
                        collected.append(f"{node.module}.{alias.name}")
                        
            # De-duplicate while preserving order
            seen = set()
            ordered = []
            for name in collected:
                if name not in seen:
                    seen.add(name)
                    ordered.append(name)
            return ordered
            
        # JavaScript/TypeScript imports (simplified)
        import re
        if isinstance(source_or_tree, str):
            lines = source_or_tree.splitlines()
        else:
            lines = []
            
        collected = []
        import_re = re.compile(
            r"^\s*import\s+(?:type\s+)?(?P<body>.+?)\s+from\s+['\"](?P<mod>[^'\"]+)['\"]"
        )
        bare_import_re = re.compile(r"^\s*import\s+['\"](?P<mod>[^'\"]+)['\"]")  
        require_re = re.compile(r"require\([^'\"]*['\"](?P<mod>[^'\"]+)['\"]\\)")
        
        for line in lines:
            m = import_re.match(line)
            if m:
                collected.append(m.group("mod"))
                continue
            m = bare_import_re.match(line)
            if m:
                collected.append(m.group("mod"))
                continue
            m = require_re.search(line)
            if m:
                collected.append(m.group("mod"))
                
        # De-duplicate
        return list(dict.fromkeys(collected))
    
    @staticmethod
    def _extract_function_calls(node) -> List[str]:
        """Extract function calls from AST node."""
        calls = []
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                func = child.func
                if isinstance(func, ast.Name):
                    calls.append(func.id)
                elif isinstance(func, ast.Attribute):
                    calls.append(func.attr)
                    
        # De-duplicate while preserving order
        seen = set()
        ordered = []
        for c in calls:
            if c not in seen:
                seen.add(c)
                ordered.append(c)
                
        return ordered
    
    @staticmethod
    def _get_signature(node) -> str:
        """Get function/class signature."""
        if isinstance(node, ast.FunctionDef):
            # Extract arguments with type annotations
            args_with_types = []
            for arg in node.args.args:
                if arg.annotation:
                    args_with_types.append(f"{arg.arg}: {ast.unparse(arg.annotation)}")
                else:
                    args_with_types.append(arg.arg)
                    
            # Extract return type annotation
            return_annotation = ""
            if node.returns:
                return_annotation = f" -> {ast.unparse(node.returns)}"
                
            return f"def {node.name}({', '.join(args_with_types)}){return_annotation}"
        elif isinstance(node, ast.ClassDef):
            # Extract base classes
            bases = [ast.unparse(base) for base in node.bases]
            if bases:
                return f"class {node.name}({', '.join(bases)})"
            return f"class {node.name}"
        return ""
    
    @staticmethod
    def _extract_docstring(node) -> str:
        """Extract docstring from node."""
        return ast.get_docstring(node) or ""
    
    @staticmethod
    def _parse_js_ts(path: Path) -> dict:
        """Parse JavaScript/TypeScript files using Babel AST."""
        try:
            res = subprocess.run(
                ["node", "parse_js.mjs", str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0 and res.stdout:
                return json.loads(res.stdout)
        except Exception as e:
            logger.warning(f"Failed to parse {path} with Babel: {e}")
            
        # Fallback to empty metadata
        return {"function_signature": "", "imports_used": [], "calls_functions": []}
    
    @staticmethod
    def chunk_js_ts_file(content: str, file_path: str) -> List[Dict[str, Any]]:
        """Extract semantic chunks from JavaScript/TypeScript code.
        
        Args:
            content: JavaScript/TypeScript source code
            file_path: Path to the file (for context)
            
        Returns:
            List of chunk dictionaries with metadata
        """
        chunks = []
        path = Path(file_path)
        
        # Try to parse with Babel if available
        if path.exists():
            meta = CodeChunker._parse_js_ts(path)
        else:
            # For remote files, we can't use Babel parser
            # Use simple heuristics instead
            meta = CodeChunker._parse_js_ts_heuristic(content)
        
        # Split content into lines
        lines = content.splitlines()
        
        # Extract chunks based on metadata
        ast_chunks = meta.get("chunks", [])
        imports = meta.get("imports_used", [])
        calls = meta.get("calls_functions", [])
        
        if ast_chunks:
            # Process each function/class as a separate chunk
            for ast_chunk in ast_chunks:
                start_line = ast_chunk.get("start_line", 1) - 1
                end_line = ast_chunk.get("end_line", len(lines))
                
                # Extract the actual code
                chunk_lines = lines[start_line:end_line]
                chunk_code = "\n".join(chunk_lines)
                
                # Create semantic context
                semantic_context = f"""
{ast_chunk.get('signature', '')} in {file_path}
Uses: {', '.join(imports[:10])}
Calls: {', '.join(list(calls)[:10])}
Type: {ast_chunk.get('type', 'unknown')}
                """.strip()
                
                chunks.append({
                    "content": chunk_code,
                    "semantic_context": semantic_context,
                    "signature": ast_chunk.get("signature", ""),
                    "imports": imports,
                    "dependencies": list(calls),
                    "chunk_type": ast_chunk.get("type", "function"),
                    "start_line": start_line + 1,
                    "end_line": end_line,
                    "function_name": ast_chunk.get("name") if ast_chunk.get("type") == "function" else None,
                    "class_name": ast_chunk.get("name") if ast_chunk.get("type") == "class" else None,
                    "docstring": ""
                })
        else:
            # Fallback to file-level chunk
            chunk = {
                "content": content[:8000],
                "semantic_context": f"Code from {file_path}",
                "signature": "",
                "imports": imports,
                "dependencies": list(calls),
                "chunk_type": "file",
                "start_line": 1,
                "end_line": len(content.splitlines()),
                "function_name": None,
                "class_name": None,
                "docstring": ""
            }
            chunks.append(chunk)
            
        return chunks
    
    @staticmethod
    def _parse_js_ts_heuristic(content: str) -> dict:
        """Parse JS/TS using simple heuristics when Babel is not available."""
        import re
        
        # Extract imports
        imports = []
        import_patterns = [
            r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]",
            r"import\s+['\"]([^'\"]+)['\"]",
            r"require\(['\"]([^'\"]+)['\"]\\)"
        ]
        
        for pattern in import_patterns:
            imports.extend(re.findall(pattern, content))
        
        # Extract function/class definitions
        chunks = []
        lines = content.splitlines()
        
        # Simple function detection
        func_pattern = re.compile(r"^\s*(function\s+(\w+)|const\s+(\w+)\s*=\s*(?:\([^)]*\)\s*=>|function))")
        class_pattern = re.compile(r"^\s*class\s+(\w+)")
        
        for i, line in enumerate(lines):
            func_match = func_pattern.match(line)
            class_match = class_pattern.match(line)
            
            if func_match:
                name = func_match.group(2) or func_match.group(3)
                if name:
                    # Find the end of the function (simplified)
                    end_line = CodeChunker._find_block_end(lines, i)
                    chunks.append({
                        "name": name,
                        "type": "function",
                        "signature": f"function {name}",
                        "start_line": i + 1,
                        "end_line": end_line + 1
                    })
            elif class_match:
                name = class_match.group(1)
                end_line = CodeChunker._find_block_end(lines, i)
                chunks.append({
                    "name": name,
                    "type": "class",
                    "signature": f"class {name}",
                    "start_line": i + 1,
                    "end_line": end_line + 1
                })
        
        return {
            "imports_used": list(set(imports)),
            "calls_functions": [],  # Simplified - not extracting calls
            "chunks": chunks
        }
    
    @staticmethod
    def _find_block_end(lines: List[str], start: int) -> int:
        """Find the end of a code block (simplified)."""
        brace_count = 0
        in_block = False
        
        for i in range(start, len(lines)):
            line = lines[i]
            brace_count += line.count('{') - line.count('}')
            
            if brace_count > 0:
                in_block = True
            elif in_block and brace_count == 0:
                return i
        
        # If we can't find the end, return a reasonable chunk
        return min(start + 50, len(lines) - 1)
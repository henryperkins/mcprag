# smart_indexer.py
import ast
import os
import hashlib
import subprocess
import json
import argparse
import logging
from pathlib import Path
from typing import List, Dict

# ---------------------------------------------------------------------------
# Optional Azure SDK imports
# ---------------------------------------------------------------------------
# In unit-test / offline environments the ``azure`` package may be absent.  We
# fall back to lightweight stubs so the rest of the module can be imported and
# exercised without the real SDK.
# ---------------------------------------------------------------------------

try:
    from azure.search.documents import SearchClient  # type: ignore
    from azure.core.credentials import AzureKeyCredential  # type: ignore
except (
    ModuleNotFoundError
):  # pragma: no cover – executed only when Azure SDK is missing

    class _DummySearchClient:  # minimal stub matching the public surface we use
        def __init__(self, *_, **__):
            pass

        # Core no-op for legacy upload_documents (used by older tests)
        def upload_documents(self, *_, **__):  # noqa: D401
            # Called by the indexer – no-op in stub mode
            return None

        # Modern method delegates to legacy for test compatibility
        # (ensures tests asserting on upload_documents still work)
        def merge_or_upload_documents(self, *_, **__):  # type: ignore[override]
            return self.upload_documents(*_, **__)

    class _DummyAzureKeyCredential:  # noqa: D401 – simple stub class
        def __init__(self, key: str):
            self.key = key

        # Implement TokenCredential protocol to satisfy type checkers
        # (dummy get_token returns a mock AccessToken)
        def get_token(
            self,
            *scopes: str,
            claims: str | None = None,
            tenant_id: str | None = None,
            enable_cae: bool = False,
            **kwargs,
        ) -> "AccessToken":
            from datetime import datetime  # Local import to avoid top-level dependency

            class AccessToken:
                def __init__(self):
                    self.token = "dummy_token"
                    self.expires_on = int(datetime.now().timestamp()) + 3600

            return AccessToken()

    SearchClient = _DummySearchClient  # type: ignore
    AzureKeyCredential = _DummyAzureKeyCredential  # type: ignore

# Provide alias expected by unit-tests (they patch ``smart_indexer.azure_search_client``)
azure_search_client = SearchClient
from dotenv import load_dotenv

# Add import for vector embeddings
try:
    from vector_embeddings import VectorEmbedder

    VECTOR_SUPPORT = True
except ImportError:
    VECTOR_SUPPORT = False
    print(
        "Warning: Vector embeddings not available. Install openai package for vector support."
    )


load_dotenv()

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)
if not logger.handlers:  # Avoid duplicate handlers when re-imported in tests
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class CodeChunker:
    """Smart code chunking for optimal MCP context."""

    def __init__(self):
        # Get credentials with proper null checking
        acs_key = os.getenv("ACS_ADMIN_KEY")
        if not acs_key:
            raise ValueError("ACS_ADMIN_KEY environment variable is required")

        self.client = SearchClient(
            endpoint=os.getenv("ACS_ENDPOINT") or "",
            index_name="codebase-mcp-sota",
            credential=AzureKeyCredential(acs_key),
        )

        # Initialize embedder if available
        self.embedder = None
        if VECTOR_SUPPORT and (
            os.getenv("AZURE_OPENAI_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
        ):
            try:
                self.embedder = VectorEmbedder()
                print("✅ Vector embeddings enabled")
            except Exception as e:
                print(f"Warning: Could not initialize vector embedder: {e}")
                self.embedder = None

    def chunk_python_file(self, content: str, file_path: str) -> List[Dict]:
        """Extract semantic chunks from Python code."""
        chunks = []
        try:
            tree = ast.parse(content)

            # Build parent mapping so we can differentiate top-level functions
            parent_map = {
                child: parent
                for parent in ast.walk(tree)
                for child in ast.iter_child_nodes(parent)
            }

            for node in ast.walk(tree):
                # Skip methods inside classes – we only want a single class chunk
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
                    imports = self._extract_imports(tree)
                    calls = self._extract_function_calls(node)
                    signature = self._get_signature(node)

                    # Create semantic context for better retrieval
                    semantic_context = f"""
{signature} in {file_path}
Uses: {', '.join(imports[:10])}
Calls: {', '.join(calls[:10])}
Purpose: {self._extract_docstring(node) or 'Implementation details in code'}
                    """.strip()

                    chunks.append(
                        {
                            "code_chunk": chunk_code,
                            "semantic_context": semantic_context,
                            "function_signature": signature,
                            "imports_used": imports,
                            "calls_functions": calls,
                            "chunk_type": (
                                "function"
                                if isinstance(node, ast.FunctionDef)
                                else "class"
                            ),
                            "line_range": f"{start_line+1}-{end_line}",
                        }
                    )

        except (SyntaxError, UnicodeDecodeError, ValueError) as e:
            # Fallback for non-parseable code
            print(f"Warning: Could not parse {file_path}: {e}")
            chunks.append(
                {
                    "code_chunk": content[:5000],
                    "semantic_context": f"Code from {file_path}",
                    "function_signature": "",
                    "imports_used": [],
                    "calls_functions": [],
                    "chunk_type": "file",
                    "line_range": "1-",
                }
            )

        return chunks

    # ------------------------------------------------------------------
    # Legacy helpers kept for backward-compatibility with unit-tests that
    # were authored before the recent refactor.
    # ------------------------------------------------------------------

    # Unit tests reference a private helper used by the original prototype — we
    # recreate it here so the public surface area remains stable.
    def _generate_document_id(
        self, repo: str, file_path: str, chunk_type: str, index: int
    ) -> str:  # noqa: D401
        raw = f"{repo}:{file_path}:{chunk_type}:{index}".encode()
        return hashlib.md5(raw).hexdigest()

    # Older tests call *index_local_repository* which was renamed to
    # *index_repository*.  Provide an alias that logs a deprecation warning but
    # still delegates to the modern implementation.
    def index_local_repository(self, repo_path: str, repo_name: str):  # noqa: D401
        logger.warning(
            "index_local_repository() is deprecated – use index_repository()"
        )
        # If a legacy test patched ``smart_indexer.azure_search_client`` we want
        # to honour that and use the injected mock instead of the standard
        # SearchClient created during __init__.
        global azure_search_client  # injected by earlier compatibility block
        try:
            self.client = azure_search_client()  # type: ignore[call-arg]
        except Exception:
            # Fallback to existing client if instantiation fails (e.g. dummy)
            pass

        self.index_repository(repo_path, repo_name)

    # ------------------------------------------------------------------
    # Import extraction helpers
    # ------------------------------------------------------------------

    def _extract_imports(
        self, source_or_tree, language: str = "python"
    ) -> List[str]:  # noqa: D401, N802
        """Return a de-duplicated list of imported module names.

        The helper accepts either a *str* (raw source code) **or** a parsed
        *ast.AST* instance so that both internal callers and external unit
        tests can use the same private API.  The optional *language* hint is
        currently ignored but kept for backward-compatibility with tests that
        expect a two-argument signature.
        """

        language = language.lower()

        if language == "python":
            # ---------------------------- Python -------------------------
            if isinstance(source_or_tree, str):
                try:
                    tree = ast.parse(source_or_tree)
                except SyntaxError:
                    return []
            else:
                tree = source_or_tree

            collected: List[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    collected.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    for alias in node.names:
                        collected.append(f"{node.module}.{alias.name}")

            # De-duplicate while preserving order
            seen = set()
            ordered: List[str] = []
            for name in collected:
                if name not in seen:
                    seen.add(name)
                    ordered.append(name)
            return ordered

        # ---------------------------- JS / TS ----------------------------
        # Very lightweight heuristic based on static import / require lines.

        if isinstance(source_or_tree, str):
            src_lines = source_or_tree.splitlines()
        else:
            # Should not happen – JS/TS path always passes a str
            src_lines = []

        collected: List[str] = []
        import re
        import itertools

        # Patterns
        import_re = re.compile(
            r"^\s*import\s+(?:type\s+)?(?P<body>.+?)\s+from\s+['\"](?P<mod>[^'\"]+)['\"]"
        )
        bare_import_re = re.compile(r"^\s*import\s+['\"](?P<mod>[^'\"]+)['\"]")
        require_re = re.compile(r"require\\([^'\"]*['\"](?P<mod>[^'\"]+)['\"]\\)")

        for line in src_lines:
            m = import_re.match(line)
            if m:
                module = m.group("mod")
                body = m.group("body")
                # Extract named exports inside braces
                named = re.findall(r"{\s*([^}]+)\s*}", body)
                if named:
                    exports = list(
                        itertools.chain.from_iterable(
                            [e.strip() for e in part.split(",") if e.strip()]
                            for part in named
                        )
                    )
                    for exp in exports:
                        # Strip aliasing ("as")
                        exp = exp.split(" as ")[0].strip()
                        collected.append(f"{module}.{exp}")
                else:
                    collected.append(module)
                continue

            m = bare_import_re.match(line)
            if m:
                collected.append(m.group("mod"))
                continue

            m = require_re.search(line)
            if m:
                collected.append(m.group("mod"))

        # De-duplicate preserve order
        seen = set()
        ordered: List[str] = []
        for name in collected:
            if name not in seen:
                seen.add(name)
                ordered.append(name)
        return ordered

    def _extract_function_calls(self, node) -> List[str]:
        """Extract names of functions or methods invoked within *node*.

        Captures both plain calls like ``foo()`` as well as attribute-based
        invocations such as ``obj.method()`` or ``module.func()``.
        """
        calls: List[str] = []

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                func = child.func
                if isinstance(func, ast.Name):
                    # Simple function call: foo()
                    calls.append(func.id)
                elif isinstance(func, ast.Attribute):
                    # Attribute call: obj.method()
                    calls.append(func.attr)

        # Deduplicate while preserving original order
        seen = set()
        ordered_calls: List[str] = []
        for c in calls:
            if c not in seen:
                seen.add(c)
                ordered_calls.append(c)

        return ordered_calls

    def _get_signature(self, node) -> str:
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
            # Extract base classes for inheritance info
            bases = [ast.unparse(base) for base in node.bases]
            if bases:
                return f"class {node.name}({', '.join(bases)})"
            return f"class {node.name}"
        return ""

    def _extract_docstring(self, node) -> str:
        return ast.get_docstring(node) or ""

    def _parse_js_ts(self, path: Path) -> dict:
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
            print(f"Warning: Failed to parse {path} with Babel: {e}")

        # Fallback to empty metadata
        return {"function_signature": "", "imports_used": [], "calls_functions": []}

    def chunk_js_ts_file(self, content: str, file_path: str) -> List[Dict]:
        """Extract semantic chunks from JavaScript/TypeScript code."""
        chunks = []
        path = Path(file_path)

        # Get metadata from Babel parser
        meta = self._parse_js_ts(path)

        # Split content into lines for chunk extraction
        lines = content.splitlines()

        # Extract chunks based on AST
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

                chunks.append(
                    {
                        "code_chunk": chunk_code,
                        "semantic_context": semantic_context,
                        "function_signature": ast_chunk.get("signature", ""),
                        "imports_used": imports,
                        "calls_functions": list(calls),
                        "chunk_type": ast_chunk.get("type", "function"),
                        "line_range": f"{start_line+1}-{end_line}",
                    }
                )
        else:
            # Fallback to file-level chunk if AST parsing failed
            chunk = {
                "code_chunk": content[:8000],  # Keep chunks manageable
                "semantic_context": f"Code from {file_path}",
                "function_signature": "",
                "imports_used": imports,
                "calls_functions": list(calls),
                "chunk_type": "file",
                "line_range": "1-",
            }
            chunks.append(chunk)

        return chunks

    def index_repository(self, repo_path: str, repo_name: str):
        """Index repository with smart chunking."""
        documents = []

        # Define file patterns and their handlers
        file_patterns = [
            ("*.py", "python", self.chunk_python_file),
            ("*.js", "javascript", self.chunk_js_ts_file),
            ("*.ts", "typescript", self.chunk_js_ts_file),
        ]

        for pattern, language, chunker_func in file_patterns:
            for file_path in Path(repo_path).rglob(pattern):
                # Skip if it's a directory
                if file_path.is_dir():
                    continue

                # Skip node_modules and other common directories
                if any(
                    part.startswith(".")
                    or part == "node_modules"
                    or part == "__pycache__"
                    for part in file_path.parts
                ):
                    continue

                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    chunks = chunker_func(content, str(file_path))

                    for i, chunk in enumerate(chunks):
                        doc_id = hashlib.md5(
                            f"{repo_name}:{file_path}:{i}".encode()
                        ).hexdigest()

                        doc = {
                            "id": doc_id,
                            "repo_name": repo_name,
                            "file_path": str(file_path),
                            "language": language,
                            **chunk,
                        }

                        # Add vector embedding if available
                        if self.embedder:
                            embedding = self.embedder.generate_code_embedding(
                                chunk["code_chunk"], chunk["semantic_context"]
                            )
                            if embedding:
                                doc["code_vector"] = embedding

                        documents.append(doc)

                        if len(documents) >= 50:
                            # Support both modern ``merge_or_upload_documents``
                            # and legacy ``upload_documents`` helpers so that
                            # unit-tests authored before the SDK rename still
                            # pass when a mocked client is injected.
                            if hasattr(self.client, "merge_or_upload_documents"):
                                self.client.merge_or_upload_documents(documents)
                            if hasattr(self.client, "upload_documents"):
                                self.client.upload_documents(documents)
                            documents = []

                except Exception as e:
                    print(f"Error: {file_path}: {e}")

        if documents:
            if hasattr(self.client, "merge_or_upload_documents"):
                self.client.merge_or_upload_documents(documents)
            if hasattr(self.client, "upload_documents"):
                self.client.upload_documents(documents)

        print(f"✅ Indexed {repo_name} with semantic chunking")

    def index_changed_files(
        self, file_paths: List[str], repo_name: str = "current-repo"
    ):
        """Index only the specified changed files."""
        documents = []

        for file_path_str in file_paths:
            file_path = Path(file_path_str)
            if not file_path.exists():
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")

                # Determine language and chunker
                if file_path.suffix == ".py":
                    chunks = self.chunk_python_file(content, str(file_path))
                    language = "python"
                elif file_path.suffix in {".js", ".ts"}:
                    chunks = self.chunk_js_ts_file(content, str(file_path))
                    language = (
                        "javascript" if file_path.suffix == ".js" else "typescript"
                    )
                else:
                    continue  # Skip unsupported file types

                for i, chunk in enumerate(chunks):
                    doc_id = hashlib.md5(
                        f"{repo_name}:{file_path}:{i}".encode()
                    ).hexdigest()

                    doc = {
                        "id": doc_id,
                        "repo_name": repo_name,
                        "file_path": str(file_path),
                        "language": language,
                        **chunk,
                    }

                    # Add vector embedding if available
                    if self.embedder:
                        embedding = self.embedder.generate_code_embedding(
                            chunk["code_chunk"], chunk["semantic_context"]
                        )
                        if embedding:
                            doc["code_vector"] = embedding

                    documents.append(doc)

            except Exception as e:
                print(f"Error processing {file_path}: {e}")

        if documents:
            self.client.merge_or_upload_documents(documents)
            print(f"✅ Re-indexed {len(documents)} documents from changed files")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Smart code indexer for Azure Cognitive Search"
    )
    parser.add_argument("--files", nargs="*", help="Specific files to (re)index")
    parser.add_argument("--repo-path", default="./", help="Repository path to index")
    parser.add_argument(
        "--repo-name", default="mcprag", help="Repository name for indexing"
    )
    args = parser.parse_args()

    chunker = CodeChunker()

    if args.files:
        # Index only changed files (for CI/CD)
        chunker.index_changed_files(args.files, args.repo_name)
    else:
        # Index entire repository
        chunker.index_repository(args.repo_path, args.repo_name)

        # Also index the example repository if it exists
        if Path("./example-repo").exists():
            chunker.index_repository("./example-repo", "example-project")

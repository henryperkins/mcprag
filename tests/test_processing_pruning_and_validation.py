"""
Tests for FileProcessor pruning/ignore handling and CLI validation utilities.
"""

import os
from pathlib import Path
from typing import Set, Optional, List

import pytest

from enhanced_rag.azure_integration.processing import FileProcessor
from enhanced_rag.azure_integration.cli import _validate_repo_name, _repo_root_guard


def _write(p: Path, content: str = "") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_fileprocessor_prunes_excluded_dirs_and_respects_gitignore(tmp_path, monkeypatch):
    # Ensure flags enabled
    monkeypatch.setenv("MCP_RESPECT_GITIGNORE", "true")
    monkeypatch.setenv("MCP_INDEX_DEFAULT_EXCLUDES", "true")

    # Layout
    _write(tmp_path / "src" / "main.py", "def foo():\n    return 1\n")
    _write(tmp_path / "README.md", "# Readme\n")
    _write(tmp_path / "node_modules" / "lib" / "index.js", "console.log('x');\n")
    _write(tmp_path / "build" / "app.py", "print('x')\n")
    _write(tmp_path / ".git" / "config", "[core]\n\trepositoryformatversion = 0\n")
    # .gitignore excludes build/
    _write(tmp_path / ".gitignore", "build/\n")

    fp = FileProcessor()
    docs = fp.process_repository(str(tmp_path), "repo")

    paths = {d["file_path"] for d in docs}
    # Inclusion
    assert any(p.endswith("src/main.py") for p in paths)
    assert any(p.endswith("README.md") for p in paths)
    # Pruned directories
    assert not any("node_modules" in p for p in paths)
    assert not any(p.startswith(".git/") or "/.git/" in p for p in paths)
    # .gitignore exclusion
    assert not any("build/" in p or p.endswith("build/app.py") for p in paths)


def test_validate_repo_name():
    assert _validate_repo_name("mcprag") is None
    assert _validate_repo_name("my_repo-1.2") is None
    assert _validate_repo_name("") is not None
    assert _validate_repo_name("bad/name") is not None
    assert _validate_repo_name("bad\\name") is not None
    assert _validate_repo_name("!" * 3) is not None
    assert _validate_repo_name("a" * 101) is not None


def test_repo_root_guard(tmp_path, monkeypatch):
    base = tmp_path / "venv" / "project"
    base.mkdir(parents=True, exist_ok=True)

    # Default (allow_external false)
    msg = _repo_root_guard(str(base), FileProcessor.DEFAULT_EXCLUDE_DIRS)
    assert isinstance(msg, str) and "excluded directory" in msg

    # Override to allow
    monkeypatch.setenv("MCP_ALLOW_EXTERNAL_ROOTS", "true")
    msg2 = _repo_root_guard(str(base), FileProcessor.DEFAULT_EXCLUDE_DIRS)
    assert msg2 is None
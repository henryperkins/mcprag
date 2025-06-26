#!/usr/bin/env python3
"""
Quick-start launcher for the MCP code-search stack.

It can:
• Provision Azure Cognitive Search and create the index
• Ingest a repository into the index (local path or GitHub)
• Launch the MCP server (port 8001)

Run with **no flags** for an interactive Q & A wizard,
or supply flags to automate in CI.

Examples
--------
python quickstart.py               # interactive workflow
python quickstart.py --no-azure    # assume Azure & index already exist
python quickstart.py --server-only # just start the server
"""
import subprocess
import sys
import os
from pathlib import Path
import argparse


def prompt_input(prompt: str, default: str | None = None) -> str:
    """
    Ask the user for a value, falling back to *default* when
    running non-interactively or the user simply hits Enter.
    """
    # Non-interactive shells (e.g. GitHub Actions) return default automatically
    if not sys.stdin.isatty():
        return default or ""
    suffix = f" [{default}]" if default is not None else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or (default or "")

def run(step: str, script: str, extra_args=None):
    """Run a helper script and abort on failure."""
    print(f"\n🚀 {step}")
    cmd = [sys.executable, script]
    if extra_args:
        cmd.extend(extra_args)
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"❌ {step} failed (exit {exc.returncode}). Aborting.")
        sys.exit(exc.returncode)

def main() -> None:
    ap = argparse.ArgumentParser(description="One-shot bootstrap for MCP RAG stack")
    ap.add_argument("--no-azure", action="store_true",
                    help="Assume Azure resources (.env + index) already exist")
    ap.add_argument("--no-index", action="store_true",
                    help="Skip smart_indexer step")
    ap.add_argument("--server-only", action="store_true",
                    help="Only start the MCP server")
    args = ap.parse_args()

    # 1. Azure resources + .env
    if not args.no_azure and not Path(".env").exists():
        run("Azure bootstrap", "setup/setup_azure.py")

    # 2. Create search index
    if not args.no_azure and not args.server_only:
        run("Creating search index", "create_index.py")

    # 3. Ingest current repository
    # 3. Ingest repository
    if not args.no_index and not args.server_only:
        # Ask which repo path to index (interactive only)
        repo_path = prompt_input("Repository path to index", ".")
        extra_args = ["--repo-path", repo_path] if repo_path != "." else []
        run("Indexing repository", "smart_indexer.py", extra_args)

    # 4. Launch MCP server (blocks)
    print("\n🏁 Launching MCP server on http://localhost:8001 ...")
    os.execv(sys.executable, [sys.executable, "mcp_server_sota.py"])

if __name__ == "__main__":
    main()

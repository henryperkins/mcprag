"""Admin and indexing MCP tools."""
from typing import Optional, Dict, Any, TYPE_CHECKING
import asyncio
from ...utils.response_helpers import ok, err
from .base import check_component, require_admin_mode, require_confirmation

if TYPE_CHECKING:
    from ...server import MCPServer


def register_admin_tools(mcp, server: "MCPServer") -> None:
    """Register admin and indexing MCP tools."""

    @mcp.tool()
    @require_admin_mode
    @require_confirmation
    async def index_rebuild(
        repository: Optional[str] = None, *, confirm: bool = False
    ) -> Dict[str, Any]:
        """Rebuild (re-run) the Azure Search indexer.

        The tool is potentially destructive: it triggers a full crawl
        of the configured data-source and may overwrite existing vector
        data.  Therefore a confirmation step is required.

        Pass `confirm=true` to proceed.
        """
        if not check_component(server.indexer_automation, "Indexer automation"):
            return err("Indexer automation not available")

        # Explicit null check for type checker
        if server.indexer_automation is None:
            return err("Indexer automation component is not initialized")

        # Ensure repository is not None for the API calls
        repo_name = repository or "default"

        try:
            if hasattr(server.indexer_automation, "reset_and_run_indexer"):
                result = await server.indexer_automation.reset_and_run_indexer(
                    repo_name, wait_for_completion=False
                )
            elif hasattr(server.indexer_automation, "ops") and hasattr(server.indexer_automation.ops, "run_indexer"):
                await server.indexer_automation.ops.run_indexer(repo_name)
                result = {"status": "started", "indexer_name": repo_name}
            else:
                return err("Indexer method not found")

            return ok({"repository": repository, "result": result})
        except Exception as e:
            return err(str(e))

    @mcp.tool()
    @require_admin_mode
    @require_confirmation
    async def github_index_repo(
        repo: str,
        branch: Optional[str] = None,
        *,
        mode: str = "full",
        confirm: bool = False,
    ) -> Dict[str, Any]:
        """Index a GitHub repository.

        Requires confirmation. Call once without `confirm` to get the
        prompt, again with `confirm=true` to execute.
        """
        if not check_component(server.remote_indexer, "GitHub indexing"):
            return err("GitHub indexing not available")

        # Explicit null check for type checker
        if server.remote_indexer is None:
            return err("Remote indexer component is not initialized")

        try:
            owner, repo_name = repo.split("/")

            # Ensure branch is not None for the API call
            ref_branch = branch or "main"

            # Run sync method in executor
            loop = asyncio.get_running_loop()

            # Use getattr to safely access the method
            if hasattr(server.remote_indexer, "index_remote_repository"):
                index_method = getattr(server.remote_indexer, "index_remote_repository")
                result = await loop.run_in_executor(
                    None, lambda: index_method(owner, repo_name, ref=ref_branch)
                )
            else:
                return err("Remote indexer method not available")

            return ok({"repo": repo, "branch": branch, "mode": mode, "result": result})
        except Exception as e:
            return err(str(e))
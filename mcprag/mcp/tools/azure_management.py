"""Azure AI Search management MCP tools."""
import sys
import json
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from ...utils.response_helpers import ok, err
from .base import check_component

if TYPE_CHECKING:
    from ...server import MCPServer


def _truncate_indexer_status(status: Dict[str, Any], max_size: int = 20000) -> Dict[str, Any]:
    """Truncate indexer status response to prevent token limit issues."""
    # Convert to JSON to estimate size
    status_json = json.dumps(status, default=str)
    
    # If status is small enough, return as-is
    if len(status_json) <= max_size:
        return status
    
    # Create truncated version keeping most important fields
    truncated = {}
    
    # Always keep these top-level fields
    important_fields = ["name", "status", "lastResult", "limits", "executionHistory"]
    for field in important_fields:
        if field in status:
            truncated[field] = status[field]
    
    # Handle executionHistory specially - keep only recent entries
    if "executionHistory" in status and isinstance(status["executionHistory"], list):
        # Keep only the 5 most recent execution history entries
        truncated["executionHistory"] = status["executionHistory"][:5]
        
        # Further truncate each history entry if needed
        for i, history in enumerate(truncated["executionHistory"]):
            if isinstance(history, dict):
                # Keep important fields from each history entry
                history_truncated = {}
                history_important = ["status", "startTime", "endTime", "itemsProcessed", "itemsFailed", "errorMessage"]
                for field in history_important:
                    if field in history:
                        # Truncate long error messages
                        if field == "errorMessage" and isinstance(history[field], str) and len(history[field]) > 1000:
                            history_truncated[field] = history[field][:1000] + "... [truncated]"
                        else:
                            history_truncated[field] = history[field]
                
                truncated["executionHistory"][i] = history_truncated
    
    # Check final size and add truncation notice
    final_json = json.dumps(truncated, default=str)
    if len(final_json) > max_size:
        # Further truncate execution history if still too large
        if "executionHistory" in truncated:
            truncated["executionHistory"] = truncated["executionHistory"][:2]
            truncated["_truncation_notice"] = "Response truncated due to size limits. Use Azure Portal for full details."
    else:
        truncated["_truncation_notice"] = "Some fields truncated due to size limits."
    
    return truncated


def register_azure_tools(mcp, server: "MCPServer") -> None:
    """Register Azure AI Search management MCP tools."""

    @mcp.tool()
    async def manage_index(
        action: str,
        index_definition: Optional[Dict[str, Any]] = None,
        index_name: Optional[str] = None,
        update_if_different: bool = True,
        backup_documents: bool = False
    ) -> Dict[str, Any]:
        """Manage Azure AI Search indexes.

        Actions:
        - create: Create or update an index (requires index_definition)
        - ensure: Ensure index exists with correct schema (requires index_definition)
        - recreate: Drop and recreate index (requires index_definition)
        - delete: Delete an index (requires index_name)
        - optimize: Get optimization recommendations (requires index_name)
        - validate: Validate index schema (requires index_name)
        - list: List all indexes with stats
        """
        if not check_component(server.index_automation, "Index automation"):
            return err("Index automation not available")

        from ...config import Config
        if not Config.ADMIN_MODE and action in ["create", "recreate", "delete"]:
            return err("Admin mode required for destructive operations")

        try:
            if action == "create" or action == "ensure":
                if not index_definition:
                    return err("index_definition required for create/ensure")
                # Add null check for type checker
                if server.index_automation is None:
                    return err("Index automation component is not initialized")
                result = await server.index_automation.ensure_index_exists(
                    index_definition, update_if_different
                )
                return ok(result)

            elif action == "recreate":
                if not index_definition:
                    return err("index_definition required for recreate")
                # Add null check for type checker
                if server.index_automation is None:
                    return err("Index automation component is not initialized")
                result = await server.index_automation.recreate_index(
                    index_definition, backup_documents
                )
                return ok(result)

            elif action == "delete":
                if not index_name:
                    return err("index_name required for delete")
                # Add null check for type checker
                if server.rest_ops is None:
                    return err("REST operations component is not initialized")
                await server.rest_ops.delete_index(index_name)
                return ok({"deleted": True, "index": index_name})

            elif action == "optimize":
                if not index_name:
                    return err("index_name required for optimize")
                # Add null check for type checker
                if server.index_automation is None:
                    return err("Index automation component is not initialized")
                result = await server.index_automation.optimize_index(index_name)
                return ok(result)

            elif action == "validate":
                if not index_name:
                    return err("index_name required for validate")
                # Add null check for type checker
                if server.index_automation is None:
                    return err("Index automation component is not initialized")
                result = await server.index_automation.validate_index_schema(
                    index_name, index_definition
                )
                return ok(result)

            elif action == "list":
                # Add null check for type checker
                if server.index_automation is None:
                    return err("Index automation component is not initialized")
                result = await server.index_automation.list_indexes_with_stats()
                return ok({"indexes": result})

            else:
                return err(f"Invalid action: {action}")

        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def manage_documents(
        action: str,
        index_name: str,
        documents: Optional[List[Dict[str, Any]]] = None,
        document_keys: Optional[List[str]] = None,
        filter_query: Optional[str] = None,
        batch_size: int = 1000,
        merge: bool = False,
        days_old: Optional[int] = None,
        date_field: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Manage documents in Azure AI Search.

        Actions:
        - upload: Upload documents (requires documents)
        - delete: Delete documents by key (requires document_keys)
        - cleanup: Delete old documents (requires days_old and date_field)
        - count: Get document count
        - verify: Verify document integrity

        Args:
            action: The action to perform
            index_name: Name of the index
            documents: Documents to upload (for upload action)
            document_keys: Document keys to delete (for delete action)
            filter_query: Optional filter query (reserved for future use)
            batch_size: Batch size for operations
            merge: Whether to merge documents on upload
            days_old: Days threshold for cleanup
            date_field: Date field for cleanup
            dry_run: Whether to perform a dry run
        """
        if not check_component(server.data_automation, "Data automation"):
            return err("Data automation not available")

        from ...config import Config
        if not Config.ADMIN_MODE and action in ["upload", "delete", "cleanup"]:
            return err("Admin mode required for document modifications")

        try:
            if action == "upload":
                if not documents:
                    return err("documents required for upload")

                # Convert list to async generator
                async def doc_generator():
                    for doc in documents:
                        yield doc

                # Add null check for type checker
                if server.data_automation is None:
                    return err("Data automation component is not initialized")
                result = await server.data_automation.bulk_upload(
                    index_name, doc_generator(), batch_size, merge
                )
                return ok(result)

            elif action == "delete":
                if not document_keys:
                    return err("document_keys required for delete")
                # Add null check for type checker
                if server.rest_ops is None:
                    return err("REST operations component is not initialized")
                result = await server.rest_ops.delete_documents(index_name, document_keys)
                return ok({"deleted": len(document_keys), "index": index_name})

            elif action == "cleanup":
                if not days_old or not date_field:
                    return err("days_old and date_field required for cleanup")
                # Add null check for type checker
                if server.data_automation is None:
                    return err("Data automation component is not initialized")
                result = await server.data_automation.cleanup_old_documents(
                    index_name, date_field, days_old, batch_size, dry_run
                )
                return ok(result)

            elif action == "count":
                # Add null check for type checker
                if server.rest_ops is None:
                    return err("REST operations component is not initialized")
                count = await server.rest_ops.count_documents(index_name)
                return ok({"count": count, "index": index_name})

            elif action == "verify":
                # Add null check for type checker
                if server.data_automation is None:
                    return err("Data automation component is not initialized")
                result = await server.data_automation.verify_documents(
                    index_name, sample_size=100
                )
                return ok(result)

            else:
                return err(f"Invalid action: {action}")

        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def manage_indexer(
        action: str,
        indexer_name: Optional[str] = None,
        datasource_name: Optional[str] = None,
        target_index: Optional[str] = None,
        schedule: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        wait: bool = False,
    ) -> Dict[str, Any]:
        """Manage Azure AI Search indexers.

        Actions:
        - list: List existing indexers
        - status: Get status of an indexer (requires indexer_name)
        - run: Run an indexer now (requires indexer_name)
        - reset: Reset indexer and run (requires indexer_name)
        - create: Create or update indexer (requires indexer_name, datasource_name,
                  target_index)
        - delete: Delete an indexer (requires indexer_name)
        """
        # Basic component checks
        uses_rest = action in {"list", "status", "delete", "run", "reset"}
        uses_automation = action in {"create"}

        if uses_rest and not check_component(server.rest_ops, "REST operations"):
            return err("REST operations not available")
        if uses_automation and not check_component(server.indexer_automation, "Indexer automation"):
            return err("Indexer automation not available")

        try:
            from ...config import Config

            if action in {"run", "reset", "create", "delete"} and not Config.ADMIN_MODE:
                return err("Admin mode required for indexer modifications")

            if action == "list":
                # Null check for type checker
                if server.rest_ops is None:
                    return err("REST operations component is not initialized")
                idx_list = await server.rest_ops.list_indexers()
                return ok({"indexers": idx_list})

            elif action == "status":
                if not indexer_name:
                    return err("indexer_name required for status")
                if server.rest_ops is None:
                    return err("REST operations component is not initialized")
                st = await server.rest_ops.get_indexer_status(indexer_name)
                
                # Truncate large status responses to prevent token limit issues
                truncated_status = _truncate_indexer_status(st)
                return ok({"indexer": indexer_name, "status": truncated_status})

            elif action == "run":
                if not indexer_name:
                    return err("indexer_name required for run")
                if server.rest_ops is None:
                    return err("REST operations component is not initialized")
                result = await server.rest_ops.run_indexer(indexer_name, wait=wait)
                return ok({"indexer": indexer_name, "run_started": True, "result": result})

            elif action == "reset":
                if not indexer_name:
                    return err("indexer_name required for reset")
                if server.rest_ops is None:
                    return err("REST operations component is not initialized")
                await server.rest_ops.reset_indexer(indexer_name)
                # Optionally run after reset
                run_res = None
                if wait:
                    run_res = await server.rest_ops.run_indexer(indexer_name, wait=wait)
                return ok({"indexer": indexer_name, "reset": True, "run_result": run_res})

            elif action == "create":
                # Create or update indexer definition
                if not indexer_name or not datasource_name or not target_index:
                    return err("indexer_name, datasource_name, and target_index are required for create")
                if server.indexer_automation is None:
                    return err("Indexer automation component is not initialized")
                # Some implementations may not expose 'ensure_indexer_exists' statically.
                # Use getattr with sync/async support and fall back to a generic method if present.
                if server.indexer_automation is None:
                    return err("Indexer automation component is not initialized")
                _ensure_idx = getattr(server.indexer_automation, "ensure_indexer_exists", None)
                if callable(_ensure_idx):
                    maybe_res = _ensure_idx(
                        indexer_name=indexer_name,
                        datasource_name=datasource_name,
                        target_index=target_index,
                        schedule=schedule,
                        parameters=parameters,
                    )
                    if hasattr(maybe_res, "__await__"):
                        result = await maybe_res  # type: ignore[reportUnknownMemberType]
                    else:
                        result = maybe_res
                else:
                    _generic = getattr(server.indexer_automation, "create_or_update_indexer", None)
                    if callable(_generic):
                        maybe_res = _generic(
                            indexer_name=indexer_name,
                            datasource_name=datasource_name,
                            target_index=target_index,
                            schedule=schedule,
                            parameters=parameters,
                        )
                        if hasattr(maybe_res, "__await__"):
                            result = await maybe_res  # type: ignore[reportUnknownMemberType]
                        else:
                            result = maybe_res
                    else:
                        raise AttributeError("Indexer automation lacks ensure_indexer_exists and create_or_update_indexer")
                return ok({"indexer": indexer_name, "created_or_updated": True, "result": result})

            elif action == "delete":
                if not indexer_name:
                    return err("indexer_name required for delete")
                if server.rest_ops is None:
                    return err("REST operations component is not initialized")
                await server.rest_ops.delete_indexer(indexer_name)
                return ok({"deleted": True, "indexer": indexer_name})

            else:
                return err(f"Invalid action: {action}")

        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def health_check() -> Dict[str, Any]:
        """Check health of core search components and dependencies."""
        components = {
            "search_client": server.search_client is not None,
            "enhanced_search": server.enhanced_search is not None,
            "context_aware": server.context_aware is not None,
            "feedback_collector": server.feedback_collector is not None,
            "cache_manager": server.cache_manager is not None,
            "index_automation": server.index_automation is not None,
            "data_automation": server.data_automation is not None,
            "rest_ops": server.rest_ops is not None,
            "indexer_automation": server.indexer_automation is not None,
        }
        overall = all(components.values())
        return ok({"healthy": overall, "components": components})

    @mcp.tool()
    async def create_datasource(
        name: str,
        datasource_type: str,
        connection_info: Dict[str, Any],
        container: Optional[Dict[str, Any]] = None,
        credentials: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        refresh: Optional[Dict[str, Any]] = None,
        test_connection: bool = True,
        update_if_exists: bool = True,
    ) -> Dict[str, Any]:
        """Create or update a data source connection for Azure AI Search."""
        from ...config import Config
        if not Config.ADMIN_MODE:
            return err("Admin mode required to create data sources")

        if not check_component(server.rest_ops, "REST operations"):
            return err("REST operations not available")

        # Explicit null check for type checker
        if server.rest_ops is None:
            return err("REST operations component is not initialized")

        try:
            ds_def = {
                "name": name,
                "type": datasource_type,
                "connection_info": connection_info,
                "container": container,
                "credentials": credentials,
                "description": description,
                "refresh": refresh,
            }
            # Clean None values
            ds_def = {k: v for k, v in ds_def.items() if v is not None}

            # Use getattr to avoid static attribute access issues on SDK-typed proxies.
            if server.rest_ops is None:
                return err("REST operations component is not initialized")
            _create_ds = getattr(server.rest_ops, "create_or_update_datasource", None)
            if callable(_create_ds):
                maybe_res = _create_ds(
                    ds_def, update_if_exists=update_if_exists, test_connection=test_connection
                )
                if hasattr(maybe_res, "__await__"):
                    result = await maybe_res  # type: ignore[reportUnknownMemberType]
                else:
                    result = maybe_res
            else:
                _generic_create = getattr(server.rest_ops, "create_or_update", None)
                if callable(_generic_create):
                    maybe_res = _generic_create(
                        resource_type="datasource",
                        definition=ds_def,
                        update_if_exists=update_if_exists,
                        test_connection=test_connection,
                    )
                    if hasattr(maybe_res, "__await__"):
                        result = await maybe_res  # type: ignore[reportUnknownMemberType]
                    else:
                        result = maybe_res
                else:
                    raise AttributeError(
                        "REST operations component lacks both create_or_update_datasource and create_or_update"
                    )
            return ok({"datasource": name, "result": result})
        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def create_skillset(
        name: str,
        skills: List[Dict[str, Any]],
        cognitive_services_key: Optional[str] = None,
        description: Optional[str] = None,
        knowledge_store: Optional[Dict[str, Any]] = None,
        encryption_key: Optional[Dict[str, Any]] = None,
        update_if_exists: bool = True,
    ) -> Dict[str, Any]:
        """Create or update an Azure Cognitive Search skillset."""
        from ...config import Config
        if not Config.ADMIN_MODE:
            return err("Admin mode required to create skillsets")

        if not check_component(server.rest_ops, "REST operations"):
            return err("REST operations not available")

        # Explicit null check for type checker
        if server.rest_ops is None:
            return err("REST operations component is not initialized")

        try:
            sk_def = {
                "name": name,
                "description": description,
                "skills": skills,
                "cognitive_services_key": cognitive_services_key,
                "knowledge_store": knowledge_store,
                "encryption_key": encryption_key,
            }
            # Clean None values
            sk_def = {k: v for k, v in sk_def.items() if v is not None}

            # Pylance type: SearchOperations in Azure SDK does not expose create_or_update_skillset;
            # our rest_ops abstraction provides a unified method that may be named differently.
            # Prefer a generic create_or_update method for skillsets if available, else fall back.
            # Avoid static type errors on SDK proxy type by using getattr with fallbacks.
            _create_skillset = getattr(server.rest_ops, "create_or_update_skillset", None)
            if callable(_create_skillset):
                maybe_result = _create_skillset(sk_def, update_if_exists=update_if_exists)
                # Support both async and sync implementations.
                if hasattr(maybe_result, "__await__"):
                    result = await maybe_result  # type: ignore[reportUnknownMemberType]
                else:
                    result = maybe_result
            else:
                _generic_create = getattr(server.rest_ops, "create_or_update", None)
                if callable(_generic_create):
                    maybe_result = _generic_create(
                        resource_type="skillset",
                        definition=sk_def,
                        update_if_exists=update_if_exists
                    )
                    if hasattr(maybe_result, "__await__"):
                        result = await maybe_result  # type: ignore[reportUnknownMemberType]
                    else:
                        result = maybe_result
                else:
                    raise AttributeError(
                        "REST operations component lacks both create_or_update_skillset and create_or_update"
                    )
            return ok({"skillset": name, "result": result})
        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def index_status() -> Dict[str, Any]:
        """Get the current status of the Azure Search index."""
        if not check_component(server.index_automation, "Index automation"):
            return err("Index automation not available")

        try:
            from ...config import Config
            index_name = Config.INDEX_NAME
            
            # Get index stats and definition using automation components
            if server.index_automation is None:
                return err("Index automation component is not initialized")
                
            stats = await server.index_automation.ops.get_index_stats(index_name)
            index_def = await server.index_automation.ops.get_index(index_name)
            
            return ok({
                "index_name": index_name,
                "fields": len(index_def.get("fields", [])),
                "documents": stats.get("documentCount", 0),
                "storage_size_mb": round(stats.get("storageSize", 0) / (1024 * 1024), 2),
                "vector_search": bool(index_def.get("vectorSearch")),
                "semantic_search": bool(index_def.get("semanticSearch"))
            })
            
        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def validate_index_schema(
        expected_schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Validate the current index schema."""
        if not check_component(server.index_automation, "Index automation"):
            return err("Index automation not available")

        try:
            from ...config import Config
            index_name = Config.INDEX_NAME
                
            if server.index_automation is None:
                return err("Index automation component is not initialized")
                
            result = await server.index_automation.validate_index_schema(
                index_name, expected_schema
            )
            return ok(result)
            
        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def index_repository(
        repo_path: str = ".",
        repo_name: str = "mcprag",
        patterns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Index a repository into Azure Search using the CLI automation.
        
        Args:
            repo_path: Path to the repository to index (default: current directory)
            repo_name: Name to use for the repository in the search index
            patterns: File patterns to include (e.g., ["*.py", "*.js"])
        """
        try:
            from ...config import Config
            if not Config.ADMIN_MODE:
                return err("Admin mode required for repository indexing")
                
            # Use the CLI automation to index repository
            import subprocess
            import os
            
            # Activate virtual environment and run indexing
            venv_python = sys.executable
            
            cmd = [
                venv_python, "-m", "enhanced_rag.azure_integration.cli",
                "local-repo", "--repo-path", repo_path, "--repo-name", repo_name
            ]
            
            if patterns:
                cmd.extend(["--patterns"] + patterns)
            
            # Set working directory to project root
            cwd = "/home/azureuser/mcprag"
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                cwd=cwd,
                env=dict(os.environ, PYTHONPATH=cwd)
            )
            
            if result.returncode != 0:
                return err(f"Failed to index repository: {result.stderr}")
            
            return ok({
                "indexed": True,
                "repo_path": repo_path,
                "repo_name": repo_name,
                "patterns": patterns,
                "output": result.stdout.strip()
            })
            
        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def index_changed_files(
        files: List[str],
        repo_name: str = "mcprag"
    ) -> Dict[str, Any]:
        """Index specific changed files into Azure Search.
        
        Args:
            files: List of file paths that have changed
            repo_name: Name of the repository in the search index
        """
        try:
            from ...config import Config
            if not Config.ADMIN_MODE:
                return err("Admin mode required for file indexing")
                
            import subprocess
            import os
            
            venv_python = sys.executable
            cwd = "/home/azureuser/mcprag"
            
            cmd = [
                venv_python, "-m", "enhanced_rag.azure_integration.cli",
                "changed-files", "--files"
            ] + files + ["--repo-name", repo_name]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                cwd=cwd,
                env=dict(os.environ, PYTHONPATH=cwd)
            )
            
            if result.returncode != 0:
                return err(f"Failed to index changed files: {result.stderr}")
            
            return ok({
                "indexed": True,
                "files": files,
                "repo_name": repo_name,
                "output": result.stdout.strip()
            })
            
        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def backup_index_schema(
        output_file: str = "schema_backup.json"
    ) -> Dict[str, Any]:
        """Backup the current index schema to a file.
        
        Args:
            output_file: Path where to save the schema backup
        """
        try:
            from ...config import Config
            if not Config.ADMIN_MODE:
                return err("Admin mode required for schema backup")
                
            import subprocess
            import os
            
            venv_python = sys.executable
            cwd = "/home/azureuser/mcprag"
            
            result = subprocess.run([
                venv_python, "-m", "enhanced_rag.azure_integration.cli",
                "reindex", "--method", "backup", "--output", output_file
            ], capture_output=True, text=True, cwd=cwd,
               env=dict(os.environ, PYTHONPATH=cwd))
            
            if result.returncode != 0:
                return err(f"Failed to backup schema: {result.stderr}")
            
            return ok({
                "backed_up": True,
                "output_file": output_file,
                "output": result.stdout.strip()
            })
            
        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def clear_repository_documents(
        repository_filter: str
    ) -> Dict[str, Any]:
        """Clear documents from a specific repository in the index.
        
        Args:
            repository_filter: Filter to match repository documents (e.g., "repository eq 'old-repo'")
        """
        try:
            from ...config import Config
            if not Config.ADMIN_MODE:
                return err("Admin mode required for document clearing")
                
            import subprocess
            import os
            
            venv_python = sys.executable
            cwd = "/home/azureuser/mcprag"
            
            result = subprocess.run([
                venv_python, "-m", "enhanced_rag.azure_integration.cli",
                "reindex", "--method", "clear", "--filter", repository_filter
            ], capture_output=True, text=True, cwd=cwd,
               env=dict(os.environ, PYTHONPATH=cwd))
            
            if result.returncode != 0:
                return err(f"Failed to clear documents: {result.stderr}")
            
            return ok({
                "cleared": True,
                "filter": repository_filter,
                "output": result.stdout.strip()
            })
            
        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def rebuild_index(
        confirm: bool = False
    ) -> Dict[str, Any]:
        """Drop and rebuild the entire index. ⚠️ CAUTION: This deletes all data!
        
        Args:
            confirm: Must be set to True to confirm this destructive operation
        """
        try:
            from ...config import Config
            if not Config.ADMIN_MODE:
                return err("Admin mode required for index rebuild")
                
            if not confirm:
                return err("Must set confirm=True to rebuild index. This operation deletes all data!")
                
            import subprocess
            import os
            
            venv_python = sys.executable
            cwd = "/home/azureuser/mcprag"
            
            result = subprocess.run([
                venv_python, "-m", "enhanced_rag.azure_integration.cli",
                "reindex", "--method", "drop-rebuild"
            ], capture_output=True, text=True, cwd=cwd,
               env=dict(os.environ, PYTHONPATH=cwd))
            
            if result.returncode != 0:
                return err(f"Failed to rebuild index: {result.stderr}")
            
            return ok({
                "rebuilt": True,
                "warning": "All previous data has been deleted",
                "output": result.stdout.strip()
            })
            
        except Exception as e:
            return err(str(e))

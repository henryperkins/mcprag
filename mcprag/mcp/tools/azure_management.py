"""Azure AI Search management MCP tools."""
import sys
import os
import subprocess
import json
from typing import Optional, List, Dict, Any, TYPE_CHECKING, Tuple
from enhanced_rag.core.unified_config import get_config
from ...utils.response_helpers import ok, err
from .base import check_component

if TYPE_CHECKING:
    from ...server import MCPServer


def _run_enhanced_cli(argv: List[str]) -> Tuple[int, str, str]:
    """Run enhanced_rag CLI command with consistent environment.
    
    Args:
        argv: Command arguments (e.g., ["local-repo", "--repo-path", ...])
        
    Returns:
        Tuple of (returncode, stdout, stderr)
    """
    # Prefer project venv Python if available (ensures SDKs like openai are present)
    project_root = "/home/azureuser/mcprag"
    venv_candidate = os.path.join(project_root, "venv", "bin", "python")
    venv_python = venv_candidate if os.path.exists(venv_candidate) else sys.executable
    cmd = [venv_python, "-m", "enhanced_rag.azure_integration.cli"] + argv
    
    # Set working directory to project root
    cwd = project_root
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
        env=dict(os.environ, PYTHONPATH=cwd)
    )
    
    return result.returncode, result.stdout.strip(), result.stderr


def _adapt_index_schema_for_api(index_def: Dict[str, Any], api_version: str) -> Dict[str, Any]:
    """Adapt index schema to match Azure API version expectations.

    - For stable API versions (e.g., 2023-11-01), map 'semanticSearch' -> 'semantic'.
    """
    adapted = dict(index_def)
    api_ver = (api_version or "").lower()
    if "semanticSearch" in adapted and ("2023-" in api_ver or "2024-" in api_ver or "2022-" in api_ver):
        sem = adapted.pop("semanticSearch", None)
        if sem is not None:
            adapted["semantic"] = sem
    return adapted


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

        config = get_config()
        if not config.mcp_admin_mode and action in ["create", "recreate", "delete"]:
            return err("Admin mode required for destructive operations")

        try:
            if action == "create" or action == "ensure":
                if not index_definition:
                    return err("index_definition required for create/ensure")
                # Adapt schema based on configured API version to avoid 400s
                index_definition = _adapt_index_schema_for_api(index_definition, get_config().acs_api_version)
                # Component already checked above
                assert server.index_automation is not None  # for type checker
                result = await server.index_automation.ensure_index_exists(
                    index_definition, update_if_different
                )
                return ok(result)

            elif action == "recreate":
                if not index_definition:
                    return err("index_definition required for recreate")
                # Adapt schema for API version
                index_definition = _adapt_index_schema_for_api(index_definition, get_config().acs_api_version)
                # Component already checked above
                assert server.index_automation is not None  # for type checker
                result = await server.index_automation.recreate_index(
                    index_definition, backup_documents
                )
                return ok(result)

            elif action == "delete":
                if not index_name:
                    return err("index_name required for delete")
                # Component already checked above
                assert server.rest_ops is not None  # for type checker
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

        from enhanced_rag.core.unified_config import UnifiedConfig as Config
        if not get_config().mcp_admin_mode and action in ["upload", "delete", "cleanup"]:
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
            from enhanced_rag.core.unified_config import UnifiedConfig as Config

            if action in {"run", "reset", "create", "delete"} and not get_config().mcp_admin_mode:
                return err("Admin mode required for indexer modifications")

            if action == "list":
                # Component already checked above
                assert server.rest_ops is not None  # for type checker
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
                assert server.rest_ops is not None  # for type checker
                result = await server.rest_ops.run_indexer(indexer_name, wait=wait)
                return ok({"indexer": indexer_name, "run_started": True, "result": result})

            elif action == "reset":
                if not indexer_name:
                    return err("indexer_name required for reset")
                assert server.rest_ops is not None  # for type checker
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
        from enhanced_rag.core.unified_config import UnifiedConfig as Config
        if not get_config().mcp_admin_mode:
            return err("Admin mode required to create data sources")

        if not check_component(server.rest_ops, "REST operations"):
            return err("REST operations not available")

        # Component already checked above
        assert server.rest_ops is not None  # for type checker

        try:
            # Build definition that matches Azure REST API schema
            ds_def = {
                "name": name,
                "type": datasource_type,
                # Azure expects 'credentials.connectionString'
                "credentials": {
                    "connectionString": connection_info.get("connectionString", "")
                },
                # Container definition is required but callers may omit;
                # fall back to an empty dict to satisfy the schema.
                "container": container or {},
            }
            # CosmosDB container mapping
            if datasource_type == "cosmosdb":
                # Ensure collection name provided
                collection = None
                if container and "name" in container:
                    collection = container["name"]
                elif "collectionName" in connection_info:
                    collection = connection_info["collectionName"]
                if not collection:
                    return err("CosmosDB datasource requires a collection name in container or connection_info.collectionName")
                # Rebuild container for CosmosDB (collection name only; query optional)
                ds_def["container"] = {"name": collection}
            
            # Optional fields
            if description is not None:
                ds_def["description"] = description
            # Map legacy refresh argument to the correct API field if provided
            if refresh is not None:
                ds_def["dataChangeDetectionPolicy"] = refresh
            # Allow callers to supply a full credentials object that overrides the simple mapping
            if credentials:
                ds_def["credentials"] = credentials
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
                    # Fall back to dedicated REST op: create_datasource(ds_def)
                    _put_ds = getattr(server.rest_ops, "create_datasource", None)
                    if callable(_put_ds):
                        maybe_res = _put_ds(ds_def)
                        if hasattr(maybe_res, "__await__"):
                            result = await maybe_res  # type: ignore[reportUnknownMemberType]
                        else:
                            result = maybe_res
                    else:
                        raise AttributeError(
                            "REST operations component lacks create_datasource, create_or_update_datasource, and create_or_update"
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
        from enhanced_rag.core.unified_config import UnifiedConfig as Config
        if not get_config().mcp_admin_mode:
            return err("Admin mode required to create skillsets")

        if not check_component(server.rest_ops, "REST operations"):
            return err("REST operations not available")

        # Component already checked above
        assert server.rest_ops is not None  # for type checker

        try:
            # Validate and normalize skills
            normalized_skills: List[Dict[str, Any]] = []
            for skill in skills:
                if "@odata.type" not in skill:
                    return err("Each skill must include '@odata.type'")
                # Ensure mandatory lists exist
                skill.setdefault("inputs", [])
                skill.setdefault("outputs", [])
                # Default context
                skill.setdefault("context", "/document")
                normalized_skills.append(skill)
            # Build skillset definition according to API spec
            sk_def: Dict[str, Any] = {
                "name": name,
                "skills": normalized_skills,
            }
            if description is not None:
                sk_def["description"] = description
            # Determine if any skill requires Cognitive Services (most skills except TextSplit)
            requires_cs = any(
                skill["@odata.type"].startswith("#Microsoft.")
                and "TextSplitSkill" not in skill["@odata.type"]
                for skill in normalized_skills
            )
            if not cognitive_services_key and requires_cs:
                import os
                cognitive_services_key = os.getenv("AZURE_COGNITIVE_SERVICES_KEY")
                if not cognitive_services_key:
                    return err(
                        "Cognitive Services key is required for one or more skills but "
                        "was not provided. Set AZURE_COGNITIVE_SERVICES_KEY env var or "
                        "pass cognitive_services_key parameter."
                    )
            # Cognitive services configuration block
            if cognitive_services_key:
                sk_def["cognitiveServices"] = {
                    "@odata.type": "#Microsoft.Azure.Search.DefaultCognitiveServices",
                    "key": cognitive_services_key,
                }
            else:
                # For skillsets containing only built-in skills that don’t need a key
                sk_def["cognitiveServices"] = {
                    "@odata.type": "#Microsoft.Azure.Search.DefaultCognitiveServices"
                }
            # Optional blocks
            if knowledge_store is not None:
                sk_def["knowledgeStore"] = knowledge_store
            if encryption_key is not None:
                sk_def["encryptionKey"] = encryption_key
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
                    # Fall back to dedicated REST op: create_skillset(sk_def)
                    _put_skillset = getattr(server.rest_ops, "create_skillset", None)
                    if callable(_put_skillset):
                        maybe_result = _put_skillset(sk_def)
                        if hasattr(maybe_result, "__await__"):
                            result = await maybe_result  # type: ignore[reportUnknownMemberType]
                        else:
                            result = maybe_result
                    else:
                        raise AttributeError(
                            "REST operations component lacks create_skillset, create_or_update_skillset, and create_or_update"
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
            from enhanced_rag.core.unified_config import UnifiedConfig as Config
            index_name = get_config().acs_index_name

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
                "semantic_search": bool(index_def.get("semanticSearch") or index_def.get("semantic"))
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
            from enhanced_rag.core.unified_config import UnifiedConfig as Config
            index_name = get_config().acs_index_name

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
        patterns: Optional[List[str]] = None,
        embed_vectors: bool = False
    ) -> Dict[str, Any]:
        """Index a repository into Azure Search using the CLI automation.

        Args:
            repo_path: Path to the repository to index (default: current directory)
            repo_name: Name to use for the repository in the search index
            patterns: File patterns to include (e.g., ["*.py", "*.js"])
        """
        try:
            from enhanced_rag.core.unified_config import UnifiedConfig as Config
            if not get_config().mcp_admin_mode:
                return err("Admin mode required for repository indexing")

            # Use the CLI automation to index repository
            # Build CLI arguments
            argv = ["local-repo", "--repo-path", repo_path, "--repo-name", repo_name]
            if patterns:
                argv.extend(["--patterns"] + patterns)
            if embed_vectors:
                argv.append("--embed-vectors")
            
            # Run CLI command
            returncode, stdout, stderr = _run_enhanced_cli(argv)
            
            if returncode != 0:
                return err(f"Failed to index repository: {stderr}")

            return ok({
                "indexed": True,
                "repo_path": repo_path,
                "repo_name": repo_name,
                "patterns": patterns,
                "embed_vectors": embed_vectors,
                "output": stdout
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
            from enhanced_rag.core.unified_config import UnifiedConfig as Config
            if not get_config().mcp_admin_mode:
                return err("Admin mode required for file indexing")

            # Build CLI arguments
            argv = ["changed-files", "--files"] + files + ["--repo-name", repo_name]
            
            # Run CLI command
            returncode, stdout, stderr = _run_enhanced_cli(argv)
            
            if returncode != 0:
                return err(f"Failed to index changed files: {stderr}")

            return ok({
                "indexed": True,
                "files": files,
                "repo_name": repo_name,
                "output": stdout
            })

        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def backfill_embeddings(
        index_name: Optional[str] = None,
        batch_size: int = 200,
        include_context: bool = True,
        max_docs: Optional[int] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Generate and backfill content_vector for existing documents via CLI.

        Args:
            index_name: Target index (defaults to configured index)
            batch_size: Page size for fetch/embed
            include_context: Include file_path and repository in embedding context
            max_docs: Limit number of documents processed
            dry_run: If True, do not write updates
        """
        try:
            if not get_config().mcp_admin_mode:
                return err("Admin mode required for embedding backfill")

            argv = ["backfill-embeddings"]
            if index_name:
                argv += ["--index", index_name]
            argv += ["--batch-size", str(int(batch_size))]
            if include_context:
                argv.append("--include-context")
            if max_docs is not None:
                argv += ["--max-docs", str(int(max_docs))]
            if dry_run:
                argv.append("--dry-run")

            returncode, stdout, stderr = _run_enhanced_cli(argv)
            if returncode != 0:
                return err(f"Backfill failed: {stderr}")
            return ok({
                "backfill_started": True,
                "index": index_name or get_config().acs_index_name,
                "output": stdout,
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
            from enhanced_rag.core.unified_config import UnifiedConfig as Config
            if not get_config().mcp_admin_mode:
                return err("Admin mode required for schema backup")

            # Build CLI arguments
            argv = ["reindex", "--method", "backup", "--output", output_file]
            
            # Run CLI command
            returncode, stdout, stderr = _run_enhanced_cli(argv)
            
            if returncode != 0:
                return err(f"Failed to backup schema: {stderr}")

            return ok({
                "backed_up": True,
                "output_file": output_file,
                "output": stdout
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
            from enhanced_rag.core.unified_config import UnifiedConfig as Config
            if not get_config().mcp_admin_mode:
                return err("Admin mode required for document clearing")

            # Build CLI arguments
            argv = ["reindex", "--method", "clear", "--filter", repository_filter]
            
            # Run CLI command
            returncode, stdout, stderr = _run_enhanced_cli(argv)
            
            if returncode != 0:
                return err(f"Failed to clear documents: {stderr}")

            return ok({
                "cleared": True,
                "filter": repository_filter,
                "output": stdout
            })

        except Exception as e:
            return err(str(e))

    @mcp.tool()
    async def validate_embeddings(
        index_name: Optional[str] = None,
        sample_size: int = 100,
        expected_dimensions: Optional[int] = None
    ) -> Dict[str, Any]:
        """Validate embedding coverage and dimension correctness.

        Args:
            index_name: Index to validate (defaults to configured index)
            sample_size: Number of documents to sample
            expected_dimensions: Expected vector dimensions (defaults to config)
        """
        if not check_component(server.rest_ops, "REST operations"):
            return err("REST operations not available")

        try:
            from enhanced_rag.azure_integration.automation import EmbeddingAutomation
            cfg = get_config()
            idx = index_name or cfg.acs_index_name
            dims = expected_dimensions or int(cfg.embedding_dimensions)

            # server.rest_ops is a SearchOperations; safe to pass
            emb = EmbeddingAutomation(server.rest_ops)  # type: ignore[arg-type]
            result = await emb.validate_embeddings(idx, sample_size=sample_size, expected_dimensions=dims)
            return ok(result)
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
            from enhanced_rag.core.unified_config import UnifiedConfig as Config
            if not get_config().mcp_admin_mode:
                return err("Admin mode required for index rebuild")

            if not confirm:
                return err("Must set confirm=True to rebuild index. This operation deletes all data!")

            # Build CLI arguments
            argv = ["reindex", "--method", "drop-rebuild"]
            
            # Run CLI command
            returncode, stdout, stderr = _run_enhanced_cli(argv)
            
            if returncode != 0:
                return err(f"Failed to rebuild index: {stderr}")

            return ok({
                "rebuilt": True,
                "warning": "All previous data has been deleted",
                "output": stdout
            })

        except Exception as e:
            return err(str(e))

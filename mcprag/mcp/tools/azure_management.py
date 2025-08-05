"""Azure AI Search management MCP tools."""
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from ...utils.response_helpers import ok, err
from .base import check_component

if TYPE_CHECKING:
    from ...server import MCPServer


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
                return ok({"indexer": indexer_name, "status": st})

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
                if wait or True:
                    run_res = await server.rest_ops.run_indexer(indexer_name, wait=wait)
                return ok({"indexer": indexer_name, "reset": True, "run_result": run_res})

            elif action == "create":
                # Create or update indexer definition
                if not indexer_name or not datasource_name or not target_index:
                    return err("indexer_name, datasource_name, and target_index are required for create")
                if server.indexer_automation is None:
                    return err("Indexer automation component is not initialized")
                result = await server.indexer_automation.ensure_indexer_exists(
                    indexer_name=indexer_name,
                    datasource_name=datasource_name,
                    target_index=target_index,
                    schedule=schedule,
                    parameters=parameters,
                )
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

            result = await server.rest_ops.create_or_update_datasource(
                ds_def, update_if_exists=update_if_exists, test_connection=test_connection
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

            result = await server.rest_ops.create_or_update_skillset(
                sk_def, update_if_exists=update_if_exists
            )
            return ok({"skillset": name, "result": result})
        except Exception as e:
            return err(str(e))

"""Azure Search Service Management Tools for MCP.

This module provides MCP tools for managing Azure Search service-level settings,
including semantic search configuration, using the Azure Management REST API.
"""

import os
import logging
from typing import Dict, Any, Optional
import httpx
from fastmcp import Context

logger = logging.getLogger(__name__)


async def get_management_token() -> Optional[str]:
    """Get Azure Management API access token.
    
    This requires Azure CLI to be installed and authenticated.
    Returns None if token cannot be obtained.
    """
    try:
        import subprocess
        result = subprocess.run(
            ["az", "account", "get-access-token", "--query", "accessToken", "--output", "tsv"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"Failed to get Azure access token: {e}")
        return None


async def get_subscription_info() -> Optional[Dict[str, str]]:
    """Get Azure subscription information.
    
    Returns dict with subscription_id and tenant_id, or None if not available.
    """
    try:
        import subprocess
        import json
        result = subprocess.run(
            ["az", "account", "show"],
            capture_output=True,
            text=True,
            check=True
        )
        account_info = json.loads(result.stdout)
        return {
            "subscription_id": account_info.get("id"),
            "tenant_id": account_info.get("tenantId")
        }
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to get Azure subscription info: {e}")
        return None


def register_service_management_tools(server):
    """Register service management tools with the MCP server."""
    
    def ok(data: Any) -> Dict[str, Any]:
        """Create a successful response."""
        return {"ok": True, "data": data}
    
    def err(message: str) -> Dict[str, Any]:
        """Create an error response."""
        return {"ok": False, "error": message, "code": "error"}
    
    @server.mcp.tool()
    async def configure_semantic_search(
        ctx: Context,
        action: str = "status",
        plan: str = "free",
        resource_group: Optional[str] = None,
        search_service_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Configure semantic search at the Azure Search service level.
        
        This uses the Azure Management REST API to enable/disable semantic search.
        Requires Azure CLI to be installed and authenticated with appropriate permissions.
        
        Args:
            action: Action to perform - "status", "enable", or "disable"
            plan: Semantic search plan - "free", "standard", or "disabled" (only for enable action)
            resource_group: Azure resource group name (uses env var if not provided)
            search_service_name: Search service name (uses env var if not provided)
            
        Returns:
            Status of the operation
            
        Note:
            - Requires Azure CLI authentication: `az login`
            - Requires Owner or Contributor permissions on the search service
            - Free plan: Up to 1000 queries per month
            - Standard plan: Pay-per-query pricing
        """
        try:
            # Get resource group and service name from env vars if not provided
            if not resource_group:
                resource_group = os.getenv("AZURE_RESOURCE_GROUP")
                if not resource_group:
                    return err("Resource group not provided and AZURE_RESOURCE_GROUP env var not set")
            
            if not search_service_name:
                # Try to extract from endpoint
                endpoint = os.getenv("ACS_ENDPOINT", "")
                if endpoint:
                    # Extract service name from https://servicename.search.windows.net
                    import re
                    match = re.match(r"https://([^.]+)\.search\.windows\.net", endpoint)
                    if match:
                        search_service_name = match.group(1)
                
                if not search_service_name:
                    search_service_name = os.getenv("AZURE_SEARCH_SERVICE_NAME")
                    
                if not search_service_name:
                    return err("Search service name not provided and cannot be determined from environment")
            
            # Get Azure credentials
            token = await get_management_token()
            if not token:
                return err("Failed to get Azure access token. Ensure Azure CLI is installed and authenticated (az login)")
            
            sub_info = await get_subscription_info()
            if not sub_info:
                return err("Failed to get Azure subscription info")
            
            subscription_id = sub_info["subscription_id"]
            
            # Build Management API URL
            base_url = "https://management.azure.com"
            service_path = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Search/searchServices/{search_service_name}"
            api_version = "2023-11-01"  # Latest stable version that supports semantic search
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                if action == "status":
                    # Get current service configuration
                    response = await client.get(
                        f"{base_url}{service_path}?api-version={api_version}",
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        service_config = response.json()
                        properties = service_config.get("properties", {})
                        semantic_search = properties.get("semanticSearch", "disabled")
                        
                        return ok({
                            "service_name": search_service_name,
                            "resource_group": resource_group,
                            "semantic_search": semantic_search,
                            "sku": service_config.get("sku", {}).get("name", "unknown"),
                            "location": service_config.get("location", "unknown"),
                            "status": properties.get("status", "unknown"),
                            "provisioning_state": properties.get("provisioningState", "unknown")
                        })
                    else:
                        error_detail = response.text
                        return err(f"Failed to get service status: {response.status_code} - {error_detail}")
                
                elif action == "enable":
                    # Validate plan
                    if plan not in ["free", "standard"]:
                        return err(f"Invalid plan '{plan}'. Must be 'free' or 'standard'")
                    
                    # Update service configuration to enable semantic search
                    body = {
                        "properties": {
                            "semanticSearch": plan
                        }
                    }
                    
                    response = await client.patch(
                        f"{base_url}{service_path}?api-version={api_version}",
                        headers=headers,
                        json=body
                    )
                    
                    if response.status_code in [200, 202]:
                        return ok({
                            "message": f"Semantic search enabled with '{plan}' plan",
                            "service_name": search_service_name,
                            "resource_group": resource_group,
                            "semantic_search": plan
                        })
                    else:
                        error_detail = response.text
                        return err(f"Failed to enable semantic search: {response.status_code} - {error_detail}")
                
                elif action == "disable":
                    # Update service configuration to disable semantic search
                    body = {
                        "properties": {
                            "semanticSearch": "disabled"
                        }
                    }
                    
                    response = await client.patch(
                        f"{base_url}{service_path}?api-version={api_version}",
                        headers=headers,
                        json=body
                    )
                    
                    if response.status_code in [200, 202]:
                        return ok({
                            "message": "Semantic search disabled",
                            "service_name": search_service_name,
                            "resource_group": resource_group,
                            "semantic_search": "disabled"
                        })
                    else:
                        error_detail = response.text
                        return err(f"Failed to disable semantic search: {response.status_code} - {error_detail}")
                
                else:
                    return err(f"Invalid action '{action}'. Must be 'status', 'enable', or 'disable'")
                    
        except Exception as e:
            logger.error(f"Error configuring semantic search: {e}", exc_info=True)
            return err(f"Error configuring semantic search: {str(e)}")
    
    @server.mcp.tool()
    async def get_service_info(
        ctx: Context,
        resource_group: Optional[str] = None,
        search_service_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get detailed information about the Azure Search service.
        
        Args:
            resource_group: Azure resource group name (uses env var if not provided)
            search_service_name: Search service name (uses env var if not provided)
            
        Returns:
            Detailed service information including tier, capacity, and features
        """
        try:
            # Get resource group and service name from env vars if not provided
            if not resource_group:
                resource_group = os.getenv("AZURE_RESOURCE_GROUP")
                if not resource_group:
                    return err("Resource group not provided and AZURE_RESOURCE_GROUP env var not set")
            
            if not search_service_name:
                # Try to extract from endpoint
                endpoint = os.getenv("ACS_ENDPOINT", "")
                if endpoint:
                    import re
                    match = re.match(r"https://([^.]+)\.search\.windows\.net", endpoint)
                    if match:
                        search_service_name = match.group(1)
                
                if not search_service_name:
                    search_service_name = os.getenv("AZURE_SEARCH_SERVICE_NAME")
                    
                if not search_service_name:
                    return err("Search service name not provided and cannot be determined from environment")
            
            # Get Azure credentials
            token = await get_management_token()
            if not token:
                return err("Failed to get Azure access token. Ensure Azure CLI is installed and authenticated")
            
            sub_info = await get_subscription_info()
            if not sub_info:
                return err("Failed to get Azure subscription info")
            
            subscription_id = sub_info["subscription_id"]
            
            # Build Management API URL
            base_url = "https://management.azure.com"
            service_path = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Search/searchServices/{search_service_name}"
            api_version = "2023-11-01"
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{base_url}{service_path}?api-version={api_version}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    service_config = response.json()
                    properties = service_config.get("properties", {})
                    sku = service_config.get("sku", {})
                    
                    return ok({
                        "service_name": search_service_name,
                        "resource_group": resource_group,
                        "subscription_id": subscription_id,
                        "location": service_config.get("location"),
                        "sku": {
                            "name": sku.get("name"),
                            "tier": sku.get("tier")
                        },
                        "status": properties.get("status"),
                        "provisioning_state": properties.get("provisioningState"),
                        "replica_count": properties.get("replicaCount"),
                        "partition_count": properties.get("partitionCount"),
                        "hosting_mode": properties.get("hostingMode"),
                        "public_network_access": properties.get("publicNetworkAccess"),
                        "semantic_search": properties.get("semanticSearch", "disabled"),
                        "disable_local_auth": properties.get("disableLocalAuth", False),
                        "auth_options": properties.get("authOptions"),
                        "encryption_with_cmk": properties.get("encryptionWithCmk"),
                        "network_rule_set": properties.get("networkRuleSet"),
                        "private_endpoint_connections": len(properties.get("privateEndpointConnections", [])),
                        "shared_private_link_resources": len(properties.get("sharedPrivateLinkResources", []))
                    })
                else:
                    error_detail = response.text
                    return err(f"Failed to get service info: {response.status_code} - {error_detail}")
                    
        except Exception as e:
            logger.error(f"Error getting service info: {e}", exc_info=True)
            return err(f"Error getting service info: {str(e)}")
    
    logger.info("Service management tools registered")
---
title: "Azure RBAC Tools for the Azure MCP Server - Azure MCP Server"
source: "https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/azure-rbac"
author:
  - "[[diberry]]"
published:
created: 2025-08-09
description: "Learn how to use Azure MCP Server with Azure RBAC to manage role assignments using natural language prompts. Simplify access control management."
tags:
  - "clippings"
---
## Azure RBAC tools for the Azure MCP Server

Azure RBAC tools in the Azure MCP Server allow you to manage Azure role-based access control using natural language prompts. This allows you to quickly view and manage role assignments without remembering complex syntax, streamlining your Azure access management workflow.

[Azure role-based access control (Azure RBAC)](https://learn.microsoft.com/en-us/azure/role-based-access-control) is the authorization system used to manage access to Azure resources. The way you control access to resources using Azure RBAC is to assign Azure roles. This is a key concept to understand – it's how permissions are enforced. A role assignment consists of three elements: security principal, role definition, and scope.

The Azure MCP Server can list Azure RBAC [role assignments](https://learn.microsoft.com/en-us/azure/role-based-access-control/role-assignments) at a specific scope. This allows you to view who has access to what resources and what permissions they have.

Example prompts include:

- **List assignments**: "Show me all role assignments in my subscription."
- **View scope assignments**: "List role assignments for resource group 'myresourcegroup'"
- **Check access**: "What role assignments exist at the subscription scope?"
- **Query assignments**: "Show me all RBAC assignments for my Azure subscription"
- **Find assignments**: "List all role assignments in scope '/subscriptions/12345678-1234-1234-1234-123456789012'"
- **Resource group scope**: "Show role assignments for resource group 'production-rg' in my subscription"
- **Specific resource scope**: "List role assignments for storage account 'mystorageaccount' in resource group 'storage-rg'"
- **Virtual machine access**: "What role assignments exist for VM 'prod-vm01' in the production resource group?"
- **Database permissions**: "Show me who has access to SQL database 'proddb' in resource group 'database-rg'"

| Parameter | Required | Description |
| --- | --- | --- |
| Subscription | Required | The ID of the Azure subscription containing the resources. |
| Scope | Required | The scope to list role assignments for. Can be a subscription, resource group, or resource. |

- [What are the Azure MCP Server tools?](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/)
- [Get started using Azure MCP Server](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/get-started)
---
title: "Azure MCP Server tools - Azure MCP Server"
source: "https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/#available-tools"
author:
  - "[[diberry]]"
published:
created: 2025-08-09
description: "Learn how to use the Azure MCP Server tools for consuming servers."
tags:
  - "clippings"
---
## What are the Azure MCP Server tools?

The Azure Model Context Protocol (MCP) Server exposes many tools you can use from an existing [client](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/get-started?tabs=one-click,azure-cli&pivots=mcp-github-copilot) to interact with Azure services through natural language prompts. For example, you can use the Azure MCP Server to interact with Azure resources conversationally from GitHub Copilot agent mode in Visual Studio Code or other AI agents with commands like these:

- "Show me all my resource groups"
- "List blobs in my storage container named 'documents'"
- "What's the value of the 'ConnectionString' key in my app configuration?"
- "Query my log analytics workspace for errors in the last hour"
- "Show me all my Cosmos DB databases"

## Available tools

Azure MCP Server provides the following tools for Azure services and Azure-related functionality.

| Tool | Description |
| --- | --- |
| [Azure AI Search](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/ai-search) | Manage Azure AI Search resources, including search services, indexes, and queries. |
| [Azure Bicep schema](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/azure-bicep-schema) | Retrieve Bicep schemas for Azure resources to use in Infrastructure as Code templates. |
| [Azure App Configuration](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/app-configuration) | Manage centralized application settings and feature flags. |
| [Azure best practices](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/azure-best-practices) | Get guidance on Azure Functions development, deployment, and Azure SDK usage. |
| [Azure Cache for Redis](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/azure-cache-for-redis) | Manage Azure Cache for Redis instances, Redis clusters, and access policies. |
| [Azure CLI](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/azure-cli-extension) | Execute Azure CLI commands within the MCP server. |
| [Azure Cosmos DB](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/cosmos-db) | Work with Azure Cosmos DB accounts, databases, containers, and documents. |
| [Azure Data Explorer](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/azure-data-explorer) | Work with Azure Data Explorer clusters, databases, tables, and queries. |
| [Azure Database for PostgreSQL](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/postgresql) | Manage Azure Database for PostgreSQL servers, databases, and tables. |
| [Azure Developer CLI](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/azure-developer-cli) | Execute Azure Developer CLI commands for application development and deployment. |
| [Azure Foundry](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/azure-foundry) | Work with Azure AI Foundry models, deployments, and endpoints. |
| [Azure Grafana](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/azure-grafana) | List Grafana workspaces. |
| [Azure Key Vault](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/key-vault-key) | List and create keys, secrets, certificates in Azure Key Vault. |
| [Azure Kubernetes Service](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/azure-aks) | List Azure Kubernetes Service clusters. |
| [Azure Load Testing](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/azure-load-testing) | Create, run, and see load testing. |
| [Azure Marketplace](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/azure-marketplace) | Discover Azure Marketplace products and offers. |
| [Azure MCP tool](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/azure-mcp-tool) | Discover and manage available Azure MCP Server tools. |
| [Azure Monitor](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/monitor) | Query Azure Monitor logs and metrics. |
| [Azure Native ISV](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/azure-native-isv) | Work with Azure Native ISV services, including Datadog integration for monitoring and observability. |
| [Azure Quick Review CLI](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/azure-compliance-quick-review) | Generate compliance and security reports for Azure resources. |
| [Azure RBAC](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/azure-rbac) | View and manage Azure role-based access control assignments. |
| [Azure Service Bus](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/service-bus) | Work with Azure Service Bus messaging services. |
| [Azure SQL](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/azure-sql) | Work with Azure SQL Database servers, databases, firewall rules, and elastic pools. |
| [Azure Storage](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/storage) | List Azure Storage accounts, containers, blobs, and tables. |
| [Azure Virtual Desktop](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/azure-virtual-desktop) | Manage Azure Virtual Desktop host pools, session hosts, and user sessions. |
| [Resource Groups](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/resource-group) | List Azure resource groups. |
| [Subscription](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/subscription) | List Azure subscriptions. |
| [Terraform best practices for Azure](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/azure-terraform-best-practices) | Get guidance on implementing Terraform for Azure resources. |

## Tool parameters

The Azure MCP Server tools define parameters for the data they need to complete tasks. For example, these parameters might include the subscription ID, an account name, or a resource group.

You might include the data for these parameters in the prompt you use to call a tool, or the previous conversation context might establish the data. If the conversation context provides the data, the Azure MCP Server can use that information without requiring you to repeat it in every prompt. This context creates a more natural conversational experience while still ensuring all necessary data is available for the tools.

The tools reference articles document the parameters specific to each tool. All of the tools also share the following global parameters.

| Parameter | Description |
| --- | --- |
| **Subscription** | [Azure subscription](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/initial-subscriptions) ID or name for target resources. This parameter identifies the Azure subscription that contains the resources you want to manage. You can use either the subscription GUID or the display name. Required for most operations. |
| **Resource group** | The name of the Azure resource group. This is a logical container for Azure resources that helps organize and manage related resources together. Required for most resource-specific operations. |
| **Tenant Id** | [Azure tenant](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/landing-zone/design-area/azure-ad-define) ID for authentication. This parameter specifies the Microsoft Entra ID tenant to authenticate against. Can be either the GUID identifier or the display name of your Entra ID tenant. Optional - uses default tenant if not specified. |
| **Authentication method** | [Authentication method](https://learn.microsoft.com/en-us/entra/identity/authentication/concept-authentication-methods) to use for Azure operations. Options include `credential` (Azure CLI/managed identity), `key` (access key), or `connectionString`. Default is `credential`, which uses Azure CLI authentication or managed identity. |
| **Maximum retries** | Maximum number of retry attempts for failed operations before giving up. Controls how many times the system attempts to retry a failed request. Default is 3 retries. |
| **Retry delay** | Initial delay in seconds between retry attempts. For exponential backoff, this value is used as the base delay that gets multiplied on each retry. Default is 2 seconds. |
| **Retry delay maximum** | Maximum delay in seconds between retries, regardless of the retry strategy. This parameter caps the delay time to prevent excessively long waits. Default is 10 seconds. |
| **Retry mode** | Retry strategy to use when operations fail. `fixed` uses consistent delays between retries, while `exponential` increases the delay between each attempt. Default is `exponential` for better handling of temporary issues. |
| **Retry network timeout** | Network operation timeout in seconds. When operations take longer than this timeout, they are canceled and might be retried if retries are enabled. Default is 100 seconds. |

Example prompts include:

- **Set subscription**: "Use subscription 'my-subscription-id' for all operations"
- **Use tenant ID**: "Authenticate using tenant ID 'my-tenant-id'"
- **Set authentication method**: "Use 'credential' authentication for this session"
- **Configure retries**: "Set maximum retries to 5 with a 3-second delay
- **Set retry mode**: "Use 'fixed' retry mode with a maximum delay of 5 seconds"
- **Set network timeout**: "Set network timeout to 120 seconds for all operations"
- **Configure retry parameters**: "Use exponential retry mode with a maximum of 4 retries and a delay of 2 seconds"
- [What is the Azure MCP Server?](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/overview)
- [Get started using Azure MCP Server](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/get-started)
- [Azure MCP Server repository](https://github.com/Azure/azure-mcp)

**Note:** The author created this article with assistance from AI. [Learn more](https://learn.microsoft.com/principles-for-ai-generated-content)

---

## Additional resources

Training

Module

[Integrate MCP Tools with Azure AI Agents - Training](https://learn.microsoft.com/en-us/training/modules/connect-agent-to-mcp-tools/?source=recommendations)

Enable dynamic tool access for your Azure AI agents. Learn how to connect MCP-hosted tools and integrate them seamlessly into agent workflows.

Certification

[Microsoft Certified: Azure Administrator Associate - Certifications](https://learn.microsoft.com/en-us/credentials/certifications/azure-administrator/?source=recommendations)

Demonstrate key skills to configure, manage, secure, and administer key professional functions in Microsoft Azure.
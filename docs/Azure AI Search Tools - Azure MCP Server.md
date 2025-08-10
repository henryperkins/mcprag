---
title: "Azure AI Search Tools - Azure MCP Server"
source: "https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/ai-search"
author:
  - "[[diberry]]"
published:
created: 2025-08-09
description: "Learn how to use the Azure MCP Server with Azure AI Search."
tags:
  - "clippings"
---
The Azure MCP Server allows you to manage Azure AI Search resources, including search services, indexes, and [queries](https://learn.microsoft.com/en-us/azure/search/query-simple-syntax) with natural language prompts without having to remember specific command syntax.

[Azure AI Search](https://learn.microsoft.com/en-us/azure/search/) (formerly known as Azure Cognitive Search) is a cloud search service that gives developers APIs and tools for building rich search experiences over private, heterogeneous content in web, mobile, and enterprise applications.

## List accounts

The Azure MCP Server can list all AI Search accounts in a subscription. This provides a quick overview of your search services.

Example prompts include:

- **List accounts**: "List all my AI Search services in my subscription."
- **Show accounts**: "What AI Search accounts do I have?"
- **Find accounts**: "I need to see my Azure AI Search resources"
- **Query accounts**: "Show me all my search services"
- **Check accounts**: "AI Search services in subscription abc123"

| Parameter | Required or optional | Description |
| --- | --- | --- |
| **Subscription** | Required | The Azure subscription ID or name. |

## List indexes

The Azure MCP Server can list all indexes in an AI Search service. This helps you view the search indexes available in a specific service.

Example prompts include:

- **List indexes**: "Show me all indexes in my 'mysearchservice' AI Search account."
- **View indexes**: "What indexes do I have in search service 'cognitive-search-prod'?"
- **Find indexes**: "List indexes in my search service 'data-search'"
- **Query indexes**: "Show all indexes in my AI Search account"
- **Check indexes**: "What indexes are available in my 'analytics-search' service?"

| Parameter | Required or optional | Description |
| --- | --- | --- |
| **Subscription** | Required | The Azure subscription ID or name. |
| **Service name** | Required | The name of the AI Search service. |

The Azure MCP Server can retrieve detailed information about a specific [index](https://learn.microsoft.com/en-us/azure/search/search-what-is-an-index) in an AI Search service. This includes the index schema, fields, analyzers, scorers, and other index properties.

Example prompts include:

- **Get index details**: "Show me details of the 'products' index in my 'mysearchservice' service."
- **View index schema**: "What fields are in the 'users' index?"
- **Index structure**: "Describe the schema for 'documents' index in my search service"
- **Check index configuration**: "Show me the configuration of my 'content' index"
- **Index definition**: "What's the definition of my 'catalog' search index?"

| Parameter | Required or optional | Description |
| --- | --- | --- |
| **Subscription** | Required | The Azure subscription ID or name. |
| **Service name** | Required | The name of the AI Search service. |
| **Index name** | Required | The name of the index to describe. |

## Query index

The Azure MCP Server can execute [search queries](https://learn.microsoft.com/en-us/azure/search/query-simple-syntax) against an AI Search index. This powerful feature allows you to find specific content using search terms.

Example prompts include:

- **Simple query**: "Search for 'machine learning' in the 'documents' index"
- **Filter query**: "Find all products with category 'electronics' in my product index"
- **Text search**: "Search my 'content' index for anything mentioning 'climate change'"
- **Query search**: "Look up 'azure functions' in my documentation index"
- **Search request**: "Search for 'security best practices' in my knowledge base index"

| Parameter | Required or optional | Description |
| --- | --- | --- |
| **Subscription** | Required | The Azure subscription ID or name. |
| **Service name** | Required | The name of the AI Search service. |
| **Index name** | Required | The name of the index to query. |
| **Query** | Required | The search query to execute against the index. |

- [What are the Azure MCP Server tools?](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/tools/)
- [Get started using Azure MCP Server](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/get-started)

**Note:** The author created this article with assistance from AI. [Learn more](https://learn.microsoft.com/principles-for-ai-generated-content)
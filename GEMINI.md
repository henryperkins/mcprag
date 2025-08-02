# Gemini Code Search & Retrieval System

## Project Overview

This project is a sophisticated code search and retrieval system designed to provide highly relevant and context-aware results for coding-related queries. It leverages Azure Cognitive Search with advanced features like semantic and vector search, combined with local Abstract Syntax Tree (AST) parsing for intelligent code chunking.

The system is architected around a "Model Context Protocol" (MCP) server, which exposes powerful search capabilities to large language models (LLMs) like Gemini. This allows the LLM to query the codebase with natural language, specifying intents like `implement`, `debug`, `understand`, or `refactor` to get tailored results.

**Key Technologies:**

*   **Backend:** Python, FastAPI, Azure Cognitive Search
*   **Frontend (for JS/TS parsing):** Node.js, Babel
*   **Dependencies:** `azure-search-documents`, `pydantic`, `fastapi`, `uvicorn`, and others listed in `requirements.txt`.
*   **Development:** `pytest` for testing, `flake8` and `mypy` for linting and type checking.

## Building and Running

### 1. Environment Setup

First, set up the necessary Azure resources and environment variables.

```bash
# Login to Azure
az login

# Create a resource group and Azure Cognitive Search service
az group create --name mcprag-rg --location eastus
az search service create --name mcprag-search --resource-group mcprag-rg --sku basic --location eastus

# Get the admin key
az search admin-key show --service-name mcprag-search --resource-group mcprag-rg
```

Next, create a `.env` file from the example and fill in your Azure details:

```bash
cp .env.example .env
```

### 2. Installation

Install the required Python and Node.js dependencies:

```bash
pip install -r requirements.txt
npm install
```

### 3. Create the Search Index

Create the search index in your Azure Cognitive Search service:

```bash
python index/create_enhanced_index.py
```

### 4. Index a Repository

To index a code repository, you'll need to modify and run the `smart_indexer.py` script (not present in the provided file list, but mentioned in the `README.md`).

### 5. Running the Server

Start the MCP server to expose the search functionality:

```bash
python mcp_server_sota.py
```

The server will be available at `http://localhost:8001`.

### 6. Running Tests

To run the test suite:

```bash
pytest
```

## Development Conventions

*   **Code Style:** The code follows PEP 8 style guidelines, enforced by `flake8`.
*   **Typing:** The project uses type hints, checked with `mypy`.
*   **Modularity:** The project is organized into modules for different functionalities (e.g., `enhanced_rag`, `index`, `setup`, `tests`).
*   **Configuration:** Configuration is managed through environment variables (`.env` file) and dedicated configuration files (e.g., `mcp_config.json`).
*   **Testing:** Tests are located in the `tests/` directory and use the `pytest` framework. The tests cover various aspects of the system, including search functionality, indexing, and API endpoints.

## Enhanced RAG Sub-system

The `enhanced_rag` directory contains a highly modular and sophisticated Retrieval-Augmented Generation (RAG) system. This sub-system is responsible for the core logic of code understanding, search, and generation.

### Key Modules:

*   **`azure_integration`:** Manages all interactions with Azure Cognitive Search. This includes building the search index (`EnhancedIndexBuilder`), handling data ingestion with indexers (`IndexerIntegration`), and providing embedding generation capabilities (`AzureOpenAIEmbeddingProvider`). It also defines custom skills for the Azure Search pipeline, such as code analysis and vectorization.
*   **`code_understanding`:** This module is responsible for parsing and understanding code. It uses AST-based analysis (`chunkers.py`) to intelligently chunk code into meaningful segments (functions, classes) rather than arbitrary blocks of text. This is a key feature that enables more precise search results.
*   **`context`:** Provides hierarchical context awareness. The `HierarchicalContextAnalyzer` can analyze code at the file, module, and project levels to provide a rich, multi-layered understanding of the code's environment. This context is used to refine search queries and rank results.
*   **`core`:** Defines the core interfaces, data models (Pydantic models), and configuration for the entire RAG system. This ensures consistency and type safety across the different modules.
*   **`generation`:** Responsible for generating code and natural language responses. It uses the retrieved search results to synthesize answers and code snippets that are relevant to the user's query.
*   **`github_integration`:** Provides tools for indexing remote GitHub repositories without needing a local checkout. It includes a GitHub API client and a remote indexer.
*   **`learning`:** Implements a feedback loop to improve the system's performance over time. The `FeedbackCollector` stores user interactions, and the `UsageAnalyzer` identifies patterns in user behavior to adapt the ranking and retrieval strategies.
*   **`mcp_integration`:** Integrates the RAG pipeline with the MCP server. This module provides the tools that are exposed through the MCP, such as `EnhancedSearchTool` and `CodeGenerationTool`.
*   **`pipeline`:** The `RAGPipeline` class orchestrates all the different components of the system. It coordinates the flow of a query from initial context analysis and enhancement to retrieval, ranking, and final response generation.
*   **`ranking`:** This module is responsible for ranking the search results. The `ContextualRanker` uses a multi-factor scoring system that considers not only text relevance but also semantic similarity, context overlap, and code quality. The `AdaptiveRanker` can learn from user feedback to dynamically adjust the ranking weights.
*   **`retrieval`:** Implements a multi-stage retrieval pipeline. The `MultiStageRetriever` combines different search strategies, including hybrid search (vector + keyword), dependency resolution, and pattern matching, to find the most relevant results.
*   **`semantic`:** This module is responsible for understanding the user's intent and enhancing the search query. The `IntentClassifier` categorizes queries (e.g., `implement`, `debug`), and the `ContextualQueryEnhancer` and `MultiVariantQueryRewriter` rewrite the query to be more effective.
*   **`utils`:** Contains utility functions for caching, error handling, and performance monitoring.
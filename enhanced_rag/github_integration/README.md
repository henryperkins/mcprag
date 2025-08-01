# GitHub Integration Module

This module provides GitHub repository indexing and webhook integration for the Enhanced RAG system.

## Components

### 1. GitHubClient (`api_client.py`)
- REST API wrapper with retry logic and authentication
- Methods for repositories, files, commits, and pull requests
- Automatic rate limit handling

### 2. RemoteIndexer (`remote_indexer.py`)
- Indexes GitHub repositories without local checkout
- Uses GitHub API to fetch file contents
- Integrates with Azure Cognitive Search
- Supports incremental indexing of changed files

### 3. Webhook Server (`webhook_app.py`)
- FastAPI application for GitHub webhooks
- Handles push and pull_request events
- Background processing with thread pool
- Admin endpoints for manual indexing

### 4. CLI Interface (`cli.py`)
- Command-line tools for indexing operations
- Commands: index-repo, index-files, index-pr

## Quick Start

### Running the Webhook Server

```bash
# Using the module directly
python -m enhanced_rag.github_integration.webhook_app

# Or using uvicorn
uvicorn enhanced_rag.github_integration.webhook_app:app --host 0.0.0.0 --port 8080
```

### Using the CLI

```bash
# Index an entire repository
python -m enhanced_rag.github_integration.cli index-repo \
  --owner microsoft --repo vscode --ref main

# Index specific files
python -m enhanced_rag.github_integration.cli index-files \
  --owner microsoft --repo vscode \
  --files src/main.ts src/vs/editor/editor.main.ts

# Index pull request files
python -m enhanced_rag.github_integration.cli index-pr \
  --owner microsoft --repo vscode --pr 12345
```

### Programmatic Usage

```python
from enhanced_rag.github_integration import RemoteIndexer, GitHubClient

# Index a repository
indexer = RemoteIndexer()
result = indexer.index_remote_repository("microsoft", "vscode", "main")
print(f"Indexed {result['chunks_indexed']} chunks")

# Get PR files
pr_files = indexer.get_pull_request_files("microsoft", "vscode", 12345)
print(f"PR changes {len(pr_files)} files")

# Use GitHub API directly
client = GitHubClient()
repo_info = client.get_repository("microsoft", "vscode")
print(f"Stars: {repo_info['stargazers_count']}")
```

## Configuration

### Environment Variables

Required:
- `ACS_ENDPOINT`: Azure Cognitive Search endpoint
- `ACS_ADMIN_KEY`: Azure admin key for indexing

Optional:
- `GITHUB_TOKEN`: For private repositories or higher rate limits
- `GITHUB_WEBHOOK_SECRET`: For webhook signature verification
- `WEBHOOK_ADMIN_TOKEN`: For manual indexing endpoints
- `WEBHOOK_LOG_LEVEL`: Logging level (default: INFO)
- `WEBHOOK_MAX_WORKERS`: Thread pool size (default: 5)
- `WEBHOOK_PORT`: Server port (default: 8080)

### Webhook Setup

1. Create a webhook in your GitHub repository:
   - Payload URL: `https://your-server.com/webhook`
   - Content type: `application/json`
   - Secret: Set a strong secret and add to `GITHUB_WEBHOOK_SECRET`
   - Events: Select "Pushes" and "Pull requests"

2. Start the webhook server with required environment variables

3. Verify webhook is working:
   ```bash
   curl https://your-server.com/health
   ```

## Migration from Legacy Scripts

If you're migrating from the old scripts:
- `github_webhook_handler.py` → Use `webhook_app.py` or migration wrapper
- `github_azure_integration.py` → Use `RemoteIndexer` class
- `connect_github_to_azure.py` → Use CLI or `RemoteIndexer` directly

See `migrate_github_integration.py` for detailed migration examples.

## Architecture

```
GitHub Events → Webhook Server → Background Tasks → RemoteIndexer → Azure Search
                                                          ↓
                                                    GitHubClient
                                                          ↓
                                                    GitHub API
```

The module uses:
- Shared code chunking logic from `enhanced_rag.code_understanding`
- Embedding providers from `enhanced_rag.azure_integration`
- Configuration from `enhanced_rag.core.config`
- Document schema aligned with CANONICAL_SCHEMA.md

## Security Considerations

1. **Webhook Verification**: All webhooks are verified using HMAC-SHA256
2. **Admin Authentication**: Manual endpoints require Bearer token auth
3. **Rate Limiting**: Configurable rate limits on all endpoints
4. **Error Handling**: Sensitive data is never logged

## Performance

- Batch document uploads (default: 50 documents)
- Concurrent file processing with thread pool
- Automatic retry with exponential backoff
- Incremental indexing for changed files only

## Troubleshooting

### Common Issues

1. **Webhook not receiving events**
   - Check GitHub webhook settings and delivery logs
   - Verify `GITHUB_WEBHOOK_SECRET` matches
   - Check server logs for signature verification errors

2. **Indexing failures**
   - Verify Azure Search credentials
   - Check index schema matches expected fields
   - Look for rate limit errors from GitHub API

3. **Missing embeddings**
   - Ensure embedding provider is configured
   - Check OpenAI/Azure OpenAI credentials
   - Verify vector dimensions match index schema

### Debug Mode

Enable debug logging:
```bash
export WEBHOOK_LOG_LEVEL=DEBUG
```

Test webhook signature:
```python
from enhanced_rag.github_integration.webhook_app import verify_webhook_signature
valid = verify_webhook_signature(payload, signature, secret)
```
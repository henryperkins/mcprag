# Environment Setup Guide for Enhanced RAG

## Quick Start

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd mcprag
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.template .env
   # Edit .env with your Azure credentials
   ```

3. **Validate setup**:
   ```bash
   python validate_config.py
   ```

4. **Create Azure Search index**:
   ```bash
   python create_enhanced_index.py
   ```

5. **Index your code**:
   ```bash
   python smart_indexer.py --repo-path ./your-repo --repo-name my-project
   ```

6. **Start MCP server**:
   ```bash
   python mcp_server_sota.py
   ```

## Detailed Setup

### 1. Azure Cognitive Search

You need an Azure Cognitive Search service. Create one in the Azure portal:

1. Go to [Azure Portal](https://portal.azure.com)
2. Create a new "Azure Cognitive Search" resource
3. Choose pricing tier (Free tier works for testing)
4. Once created, get:
   - **Endpoint**: `https://your-service.search.windows.net`
   - **Admin Key**: Found in Settings → Keys

### 2. Azure OpenAI (Optional, for embeddings)

For vector search capabilities:

1. Create an Azure OpenAI resource
2. Deploy `text-embedding-3-large` model
3. Get:
   - **Endpoint**: `https://your-openai.openai.azure.com`
   - **API Key**: Found in Keys and Endpoint

### 3. Environment Variables

Create a `.env` file:

```bash
# Required
ACS_ENDPOINT=https://your-search.search.windows.net
ACS_ADMIN_KEY=your-admin-key-here

# Optional (for embeddings)
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com
AZURE_OPENAI_KEY=your-openai-key-here

# Optional settings
DEBUG=false
LOG_LEVEL=INFO
```

### 4. Python Dependencies

Install all required packages:

```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install azure-search-documents pydantic python-dotenv aiohttp
pip install openai  # Optional, for embeddings
pip install fastapi uvicorn  # Optional, for API mode
```

## Index Creation Script

Create a file `create_enhanced_index.py`:

```python
#!/usr/bin/env python3
import asyncio
from enhanced_rag.azure_integration.enhanced_index_builder import EnhancedIndexBuilder

async def main():
    builder = EnhancedIndexBuilder()
    
    # Create the main index
    index = await builder.create_enhanced_rag_index(
        index_name="codebase-mcp-sota",
        description="Enhanced code search index with AST analysis and vector search",
        enable_vectors=True,
        enable_semantic=True
    )
    
    print(f"✅ Created index: {index.name}")
    
    # Validate schema
    validation = await builder.validate_index_schema(
        "codebase-mcp-sota",
        ["content", "function_name", "repository", "language", "content_vector"]
    )
    
    if validation['valid']:
        print("✅ Schema validation passed")
    else:
        print(f"⚠️  Missing fields: {validation['missing_fields']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Common Issues and Solutions

### 1. Import Errors

**Problem**: `ModuleNotFoundError: No module named 'azure'`  
**Solution**: Install Azure SDK: `pip install azure-search-documents`

**Problem**: `ModuleNotFoundError: No module named 'mcp'`  
**Solution**: MCP SDK is optional. The code will work without it.

### 2. Connection Errors

**Problem**: `Connection refused` or `401 Unauthorized`  
**Solution**: 
- Check your ACS_ENDPOINT includes `https://`
- Verify your ACS_ADMIN_KEY is correct
- Ensure your Azure Search service is running

### 3. Index Creation Errors

**Problem**: `Index already exists`  
**Solution**: Either delete the existing index in Azure portal or use a different name

**Problem**: `Invalid analyzer name`  
**Solution**: The code now uses built-in analyzers. If you still see this, check Azure Search API version.

### 4. Embedding Errors

**Problem**: `Embedding generation failed`  
**Solution**: 
- Embeddings are optional. The system works without them.
- If you want embeddings, ensure Azure OpenAI is configured correctly
- Check that `text-embedding-3-large` model is deployed

## Testing Your Setup

### 1. Test Indexing
```bash
# Create a test file
echo "def hello_world():\n    print('Hello, World!')" > test.py

# Index it
python smart_indexer.py --files test.py --repo-name test-repo
```

### 2. Test Search
```bash
# Start the MCP server
python mcp_server_sota.py

# In another terminal, test with curl
curl -X POST http://localhost:8001/search \
  -H "Content-Type: application/json" \
  -d '{"query": "hello world", "max_results": 5}'
```

### 3. Test with Claude Code
```bash
# Add to Claude Code
claude-code mcp add \
  --name azure-code-search \
  --command "python" \
  --args "/path/to/mcp_server_sota.py"
```

## Production Deployment

### 1. Azure Function Deployment

Deploy custom skills as Azure Functions:

```bash
# Install Azure Functions Core Tools
npm install -g azure-functions-core-tools@4

# Create function app
func init CodeAnalysisSkills --python
cd CodeAnalysisSkills

# Add your skill code
func new --name CodeAnalyzer --template "HTTP trigger"

# Deploy
func azure functionapp publish YourFunctionAppName
```

### 2. Docker Deployment

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV ACS_ENDPOINT=${ACS_ENDPOINT}
ENV ACS_ADMIN_KEY=${ACS_ADMIN_KEY}

CMD ["python", "mcp_server_sota.py", "--api"]
```

### 3. CI/CD Integration

GitHub Actions example:

```yaml
name: Index Changed Files

on:
  push:
    branches: [main]

jobs:
  index:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Index changed files
        env:
          ACS_ENDPOINT: ${{ secrets.ACS_ENDPOINT }}
          ACS_ADMIN_KEY: ${{ secrets.ACS_ADMIN_KEY }}
        run: |
          changed_files=$(git diff --name-only HEAD~1 HEAD | grep -E '\.(py|js|ts)$' || true)
          if [ ! -z "$changed_files" ]; then
            python smart_indexer.py --files $changed_files
          fi
```

## Monitoring and Maintenance

### 1. Monitor Index Size
```python
from azure.search.documents import SearchClient
client = SearchClient(endpoint, "codebase-mcp-sota", credential)
print(f"Documents in index: {client.get_document_count()}")
```

### 2. Clean Up Old Documents
```python
# Remove documents older than 90 days
from datetime import datetime, timedelta
cutoff = (datetime.utcnow() - timedelta(days=90)).isoformat()
client.delete_documents(filter=f"last_modified lt {cutoff}")
```

### 3. Performance Tuning
- Adjust `batch_size` in indexer for faster processing
- Use `partition_count` > 1 for large indexes
- Enable caching in MCP server for frequent queries

## Troubleshooting Checklist

- [ ] Run `python validate_config.py` - all checks pass?
- [ ] Check `.env` file exists and has correct values
- [ ] Verify Azure Search service is running
- [ ] Check index exists: `codebase-mcp-sota`
- [ ] Look at logs: `tail -f *.log`
- [ ] Test with simple query first
- [ ] Check firewall/network settings if connection fails
- [ ] Verify Python version >= 3.8

For more help, check the logs or open an issue with the error message.
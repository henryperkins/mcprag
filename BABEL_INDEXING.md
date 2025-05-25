# Smart Indexer with Babel AST Support

This document describes the enhanced smart indexer that supports JavaScript/TypeScript files using Babel AST parsing and includes GitHub Actions for incremental indexing.

## Features

### 🚀 Multi-Language Support
- **Python**: AST-based parsing for functions, classes, imports, and calls
- **JavaScript/TypeScript**: Babel AST parsing with full syntax support
- **Semantic chunking**: Extracts meaningful code segments with context

### 🔄 Incremental Indexing
- **GitHub Actions**: Automatically re-indexes only changed files
- **Azure merge-or-upload**: Uses `mergeOrUploadDocuments` for efficient updates
- **Path filtering**: Only triggers on code file changes (`.py`, `.js`, `.ts`)

## Setup

### 1. Install Dependencies

```bash
# Python dependencies
pip install -r requirements.txt

# Node.js dependencies  
npm install
```

### 2. Configure Azure Secrets

Add these secrets to your GitHub repository:
- `ACS_ENDPOINT`: Your Azure Cognitive Search endpoint
- `ACS_ADMIN_KEY`: Your Azure Cognitive Search admin key

### 3. Set up Environment Variables

Create a `.env` file:
```env
ACS_ENDPOINT=https://your-search-service.search.windows.net
ACS_ADMIN_KEY=your-admin-key
```

## Usage

### Manual Indexing

```bash
# Index entire repository
python smart_indexer.py --repo-path ./ --repo-name mcprag

# Index specific files (for testing)
python smart_indexer.py --files file1.py file2.js file3.ts
```

### Automatic Indexing

The GitHub Action (`.github/workflows/index-changes.yml`) automatically:
1. Detects changed code files in pushes/PRs
2. Sets up Python and Node.js environments
3. Installs dependencies
4. Re-indexes only the changed files
5. Uses Azure's merge-or-upload for efficient updates

## Architecture

### Babel Parser (`parse_js.mjs`)
- Uses `@babel/parser` with TypeScript, JSX, and modern JS plugins
- Extracts imports, function calls, and function/class signatures
- Returns JSON metadata compatible with Python AST output

### Smart Indexer (`smart_indexer.py`)
- **Multi-language chunking**: Handles Python, JavaScript, and TypeScript
- **Semantic context**: Creates meaningful descriptions for better retrieval
- **Incremental updates**: Uses `merge_or_upload_documents` for efficiency
- **CLI interface**: Supports both full and incremental indexing

### GitHub Action
- **Path filtering**: Uses `dorny/paths-filter` for efficient change detection
- **Multi-runtime**: Sets up both Python and Node.js environments
- **Conditional execution**: Only runs when code files change
- **Secret management**: Securely handles Azure credentials

## File Structure

```
├── smart_indexer.py          # Enhanced indexer with JS/TS support
├── parse_js.mjs              # Babel AST parser for JS/TS
├── package.json              # Node.js dependencies
├── test_indexer.py           # Test script (no Azure required)
├── .github/workflows/
│   └── index-changes.yml     # GitHub Action for incremental indexing
└── example-repo/             # Test files
    ├── api.js               # JavaScript example
    ├── auth.py              # Python example
    └── database.py          # Python example
```

## Testing

Run the test suite without Azure credentials:

```bash
python test_indexer.py
```

This will:
- Test JavaScript/TypeScript parsing with Babel
- Test Python AST parsing
- Mock the Azure client to verify document generation
- Show extracted metadata for each file type

## Benefits

1. **Semantic Understanding**: Extracts meaningful code structure, not just text
2. **Efficient Updates**: Only re-indexes changed files in CI/CD
3. **Multi-Language**: Consistent metadata extraction across Python and JS/TS
4. **Production Ready**: Uses Azure's recommended merge-or-upload pattern
5. **Developer Friendly**: Clear CLI interface and comprehensive testing

## Example Output

### JavaScript File Analysis
```json
{
  "function_signature": "class ApiClient",
  "imports_used": ["axios", "lodash"],
  "calls_functions": ["fetch", "json", "error"]
}
```

### Python File Analysis
```json
{
  "function_signature": "def authenticate(username, password)",
  "imports_used": ["hashlib", "jwt", "datetime"],
  "calls_functions": ["hash", "encode", "timedelta"]
}
```

This enhanced indexer provides the foundation for intelligent code search and retrieval in your MCP RAG system.

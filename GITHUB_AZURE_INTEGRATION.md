# GitHub API + Azure Cognitive Search Integration

This document explains the comprehensive integration between GitHub API and Azure Cognitive Search, providing multiple ways to index repositories and handle real-time updates.

## 🏗️ **Integration Architecture**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   GitHub API    │───▶│  Smart Indexer   │───▶│ Azure Cognitive │
│                 │    │  + Babel AST     │    │     Search      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ GitHub Actions  │    │ Webhook Handler  │    │   MCP Server    │
│ (CI/CD)         │    │ (Real-time)      │    │ (Claude Code)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🔄 **Integration Methods**

### **1. Current File-Based Integration**
- ✅ **Local repository access** via file system
- ✅ **GitHub Actions** for automatic indexing on changes
- ✅ **Path filtering** with `dorny/paths-filter`
- ✅ **Incremental updates** using `mergeOrUploadDocuments`

### **2. NEW: GitHub API Integration**
- 🆕 **Remote repository indexing** without local checkout
- 🆕 **Cross-repository support** for multiple repos
- 🆕 **Pull request indexing** for code review context
- 🆕 **Commit comparison** for precise change detection

### **3. NEW: Real-time Webhook Integration**
- 🆕 **Instant indexing** on push/PR events
- 🆕 **Background processing** for non-blocking updates
- 🆕 **Webhook verification** for security
- 🆕 **Multi-repository management**

## 📋 **Setup Instructions**

### **1. Environment Variables**

Add to your `.env` file:
```env
# Azure Cognitive Search
ACS_ENDPOINT=https://your-search-service.search.windows.net
ACS_ADMIN_KEY=your-admin-key

# GitHub API (for remote indexing)
GITHUB_TOKEN=ghp_your_personal_access_token

# Webhook Handler (optional)
GITHUB_WEBHOOK_SECRET=your-webhook-secret
WEBHOOK_PORT=8080
```

### **2. GitHub Secrets**

Add these secrets to your GitHub repository:
- `ACS_ENDPOINT`: Azure Cognitive Search endpoint
- `ACS_ADMIN_KEY`: Azure admin key
- `GITHUB_TOKEN`: Personal access token (automatically provided)

### **3. GitHub Personal Access Token**

For remote repository access, create a token with these permissions:
- `repo` (Full control of private repositories)
- `public_repo` (Access public repositories)

## 🚀 **Usage Examples**

### **Local Repository Indexing**
```bash
# Index current repository
python smart_indexer.py --repo-path ./ --repo-name mcprag

# Index specific changed files
python smart_indexer.py --files file1.py file2.js --repo-name mcprag
```

### **Remote Repository Indexing**
```bash
# Index entire remote repository
python github_azure_integration.py --owner henryperkins --repo mcprag

# Index specific files from remote repo
python github_azure_integration.py --owner henryperkins --repo mcprag --files smart_indexer.py

# Index pull request files
python github_azure_integration.py --owner henryperkins --repo mcprag --pr 123
```

### **Webhook Handler**
```bash
# Start webhook server
python github_webhook_handler.py

# Manual repository indexing via API
curl -X POST "http://localhost:8080/manual/index-repo?owner=henryperkins&repo=mcprag"

# Check indexed repositories
curl "http://localhost:8080/status/repositories"
```

## 🔧 **Integration Capabilities**

### **GitHub API Features**
- ✅ **Repository metadata** (name, description, language stats)
- ✅ **File content retrieval** with base64 decoding
- ✅ **Commit comparison** for change detection
- ✅ **Pull request file analysis**
- ✅ **Branch-specific indexing**
- ✅ **Recursive directory traversal**

### **Azure Search Features**
- ✅ **Semantic chunking** with AST/Babel parsing
- ✅ **Multi-language support** (Python, JavaScript, TypeScript)
- ✅ **Incremental updates** with merge-or-upload
- ✅ **Rich metadata** (imports, function calls, signatures)
- ✅ **GitHub URL linking** for easy navigation

### **Real-time Processing**
- ✅ **Push event handling** for immediate indexing
- ✅ **Pull request events** for code review context
- ✅ **Background task processing** for performance
- ✅ **Signature verification** for security

## 📊 **Data Flow Examples**

### **Push Event Flow**
```
1. Developer pushes code to GitHub
2. GitHub sends webhook to handler
3. Handler extracts changed files
4. GitHub API fetches file contents
5. Babel/AST parses code semantically
6. Azure Search indexes with merge-or-upload
7. MCP Server provides updated search results
```

### **Pull Request Flow**
```
1. Developer opens/updates PR
2. GitHub webhook triggers handler
3. Handler gets PR file list via API
4. Files are parsed and indexed
5. Code review context available in search
```

## 🔐 **Security Considerations**

### **GitHub Webhook Security**
- ✅ **HMAC signature verification** using webhook secret
- ✅ **Environment variable protection** for secrets
- ✅ **Background task isolation** for processing

### **API Token Security**
- ✅ **Personal Access Token** with minimal required permissions
- ✅ **Repository-scoped access** only
- ✅ **Secure environment variable storage**

## 🎯 **Benefits of GitHub API Integration**

### **1. Remote Repository Support**
- Index repositories without local clones
- Support for private repositories with proper tokens
- Cross-organization repository indexing

### **2. Enhanced Change Detection**
- Precise commit-to-commit file comparison
- Pull request specific file analysis
- Branch-aware indexing

### **3. Real-time Updates**
- Instant indexing on code changes
- Background processing for performance
- Webhook-driven automation

### **4. Scalability**
- Multi-repository management
- Efficient API-based file retrieval
- Parallel processing capabilities

## 📈 **Performance Optimizations**

### **Incremental Indexing**
- Only changed files are re-indexed
- Azure merge-or-upload for efficiency
- Background task processing

### **API Rate Limiting**
- Respects GitHub API rate limits
- Efficient batch processing
- Error handling and retries

### **Caching Strategy**
- File content caching for repeated access
- Metadata caching for repository info
- Smart cache invalidation

## 🔄 **Migration Path**

### **From File-Based to API-Based**
1. Keep existing GitHub Actions for local indexing
2. Add GitHub API integration for remote capabilities
3. Optionally add webhook handler for real-time updates
4. Gradually migrate to API-based approach

### **Hybrid Approach**
- Use local indexing for development repositories
- Use API indexing for external/reference repositories
- Use webhooks for production real-time updates

This comprehensive integration provides maximum flexibility for indexing GitHub repositories into Azure Cognitive Search, supporting both local and remote workflows with real-time capabilities.

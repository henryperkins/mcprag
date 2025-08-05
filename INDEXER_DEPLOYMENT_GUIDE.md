# Azure Search Indexer Deployment Guide

This guide covers the complete deployment of a comprehensive Azure Search indexer pipeline for the mcprag codebase.

## Overview

The indexer configuration consists of three main components:

1. **Data Source** (`azure_indexer_datasource.json`) - Connects to Azure Blob Storage
2. **Skillset** (`azure_indexer_skillset.json`) - Processes and analyzes code content
3. **Indexer** (`azure_indexer_main.json`) - Orchestrates the indexing pipeline

## Prerequisites

### Azure Resources Required

1. **Azure Search Service** - With sufficient capacity for your data
2. **Azure Storage Account** - For source data and caching
3. **Azure Cognitive Services** - Multi-service resource for text processing

### Environment Variables

Set these environment variables before deployment:

```bash
# Azure Search Configuration
export ACS_ENDPOINT="https://your-search-service.search.windows.net"
export ACS_ADMIN_KEY="your-admin-key"
export ACS_API_VERSION="2025-05-01-preview"

# Azure Storage Configuration
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=yourstorageaccount;AccountKey=yourkey;EndpointSuffix=core.windows.net"

# Cognitive Services Configuration
export AZURE_COGNITIVE_SERVICES_KEY="your-cognitive-services-key"
```

### Storage Container Setup

1. Create a container named `codebase` in your Azure Storage Account
2. Create a folder structure: `/mcprag/` 
3. Upload your repository files to this location

## Configuration Files

### 1. Data Source Configuration

**File**: `azure_indexer_datasource.json`

- **Type**: Azure Blob Storage
- **Container**: `codebase`
- **Query Path**: `/mcprag` (filters to mcprag subfolder)
- **Change Detection**: High-water mark policy using `_ts` column
- **Deletion Detection**: Soft delete using `isDeleted` column

### 2. Skillset Configuration

**File**: `azure_indexer_skillset.json`

**Skills included**:

- **Text Splitter**: Chunks code into 4000-character segments with 200-character overlap
- **Language Detection**: Identifies programming languages from content
- **Key Phrase Extraction**: Extracts important coding concepts and patterns

**Cognitive Services**: Requires a valid Cognitive Services key for text processing

### 3. Indexer Configuration

**File**: `azure_indexer_main.json`

**Key Features**:

- **Target Index**: `codebase-mcp-sota` (uses existing schema)
- **Schedule**: Runs every 2 hours (`PT2H`)
- **Batch Size**: 100 documents per batch
- **Error Handling**: Tolerates up to 10 failed items
- **File Filtering**: 
  - **Included**: Code files (.py, .js, .ts, etc.), documentation (.md), config files
  - **Excluded**: Binary files, images, archives, temporary files

**Field Mappings**:
- Maps blob metadata to index fields
- Transforms storage paths using base64 decoding
- Routes skillset outputs to appropriate index fields

## Deployment Process

### Method 1: Automated Deployment (Recommended)

Use the provided deployment script:

```bash
python deploy_indexer.py
```

This script will:
1. Validate all prerequisites
2. Create/update the data source
3. Create/update the skillset
4. Create/update the indexer
5. Start the initial indexing run
6. Display status information

### Method 2: Manual Deployment

If you prefer manual deployment or need to customize the process:

#### Step 1: Create Data Source

```bash
curl -X POST "${ACS_ENDPOINT}/datasources?api-version=${ACS_API_VERSION}" \
  -H "Content-Type: application/json" \
  -H "api-key: ${ACS_ADMIN_KEY}" \
  -d @azure_indexer_datasource.json
```

#### Step 2: Create Skillset

```bash
curl -X POST "${ACS_ENDPOINT}/skillsets?api-version=${ACS_API_VERSION}" \
  -H "Content-Type: application/json" \
  -H "api-key: ${ACS_ADMIN_KEY}" \
  -d @azure_indexer_skillset.json
```

#### Step 3: Create Indexer

```bash 
curl -X POST "${ACS_ENDPOINT}/indexers?api-version=${ACS_API_VERSION}" \
  -H "Content-Type: application/json" \
  -H "api-key: ${ACS_ADMIN_KEY}" \
  -d @azure_indexer_main.json
```

#### Step 4: Start Indexer

```bash
curl -X POST "${ACS_ENDPOINT}/indexers/mcprag-codebase-indexer/run?api-version=${ACS_API_VERSION}" \
  -H "api-key: ${ACS_ADMIN_KEY}"
```

## Monitoring and Maintenance

### Check Indexer Status

```bash
curl -X GET "${ACS_ENDPOINT}/indexers/mcprag-codebase-indexer/status?api-version=${ACS_API_VERSION}" \
  -H "api-key: ${ACS_ADMIN_KEY}"
```

### Monitor Execution History

The status response includes execution history with:
- Start/end times
- Items processed/failed
- Error messages and warnings
- Performance metrics

### Common Issues and Solutions

1. **Authentication Failures**
   - Verify Azure Search admin key
   - Check service endpoint URL
   - Ensure sufficient permissions

2. **Storage Access Issues**
   - Validate storage connection string
   - Verify container exists and is accessible
   - Check blob permissions

3. **Cognitive Services Errors**
   - Confirm Cognitive Services key is valid
   - Check service quotas and limits
   - Verify regional availability

4. **Parsing Errors**
   - Review excluded file extensions
   - Check for unsupported file types
   - Validate file encodings

## Performance Optimization

### Batch Size Tuning

- **Small files**: Increase batch size (200-500)
- **Large files**: Decrease batch size (50-100)
- **Mixed content**: Start with default (100)

### Schedule Optimization

- **Active development**: More frequent (PT1H)
- **Stable repositories**: Less frequent (PT4H, PT24H)
- **Large repositories**: Consider load distribution

### Error Tolerance

Adjust `maxFailedItems` and `maxFailedItemsPerBatch` based on:
- Data quality expectations
- Error tolerance requirements
- Monitoring capabilities

## Advanced Configuration

### Custom Skills Integration

To add custom code analysis skills:

1. Deploy Azure Function with code analysis logic
2. Add Web API skill to skillset
3. Map custom skill outputs to index fields
4. Update field mappings in indexer

### Knowledge Store Integration

For advanced analytics, add knowledge store projections:

```json
"knowledgeStore": {
  "storageConnectionString": "{STORAGE_CONNECTION_STRING}",
  "projections": [
    {
      "tables": [
        {
          "tableName": "codeChunks",
          "source": "/document/chunks/*"
        }
      ]
    }
  ]
}
```

### Vector Search Enhancement

For semantic search capabilities:

1. Add embedding skill to skillset
2. Configure vector field in index schema
3. Update output field mappings
4. Enable vector search in queries

## Troubleshooting

### Debug Mode

Enable detailed logging by setting:

```bash
export ACS_LOG_LEVEL="DEBUG"
```

### Status Monitoring

Check indexer status regularly:

```python
from enhanced_rag.azure_integration import UnifiedConfig, ClientFactory

config = UnifiedConfig.from_env()
ops = ClientFactory.create_operations(config.azure_search)
status = await ops.get_indexer_status("mcprag-codebase-indexer")
print(json.dumps(status, indent=2))
```

### Performance Metrics

Monitor these key metrics:
- Items processed per hour
- Average processing time per item
- Error rates and patterns
- Storage and compute usage

## Next Steps

After successful deployment:

1. **Upload Source Data**: Place repository files in Azure Storage
2. **Monitor Initial Run**: Watch first indexing execution
3. **Validate Results**: Query index to verify document processing
4. **Optimize Performance**: Tune batch sizes and schedules
5. **Add Custom Skills**: Enhance with domain-specific processing

## Support Resources

- **Azure Search Documentation**: https://docs.microsoft.com/azure/search/
- **Skillset Reference**: https://docs.microsoft.com/azure/search/cognitive-search-predefined-skills
- **Indexer API Reference**: https://docs.microsoft.com/rest/api/searchservice/indexer-operations
- **Troubleshooting Guide**: https://docs.microsoft.com/azure/search/search-indexer-troubleshooting

EOF < /dev/null

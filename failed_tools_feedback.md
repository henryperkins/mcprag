# Failed MCP Tools Test Results

## Overview
During testing of mcprag MCP server tools 15-27, three tools failed with identical logging configuration errors. This document provides complete feedback from each failed tool.

## Failed Tools Summary

| Tool # | Tool Name | Error Type | Status |
|--------|-----------|------------|--------|
| 19 | `mcp__mcprag__create_datasource` | LogRecord overwrite error | ❌ Failed |
| 20 | `mcp__mcprag__create_skillset` | LogRecord overwrite error | ❌ Failed |
| 27 | `mcp__mcprag__rebuild_index` | LogRecord overwrite error | ❌ Failed |

## Detailed Error Feedback

### Tool 19: mcp__mcprag__create_datasource

**Test Parameters:**
```json
{
  "name": "test-datasource",
  "datasource_type": "azureblob", 
  "connection_info": {"connectionString": "test"},
  "test_connection": false
}
```

**Error Response:**
```
Error executing tool create_datasource: "Attempt to overwrite 'message' in LogRecord"
```

### Tool 20: mcp__mcprag__create_skillset

**Test Parameters:**
```json
{
  "name": "test-skillset",
  "skills": [
    {
      "@odata.type": "#Microsoft.Skills.Text.SplitSkill",
      "name": "split",
      "description": "Split skill",
      "context": "/document",
      "textSplitMode": "pages",
      "maximumPageLength": 4000,
      "inputs": [
        {
          "name": "text",
          "source": "/document/content"
        }
      ],
      "outputs": [
        {
          "name": "textItems",
          "targetName": "pages"
        }
      ]
    }
  ]
}
```

**Error Response:**
```
Error executing tool create_skillset: "Attempt to overwrite 'message' in LogRecord"
```

### Tool 27: mcp__mcprag__rebuild_index

**Test Parameters:**
```json
{
  "confirm": false
}
```

**Error Response:**
```
Error executing tool rebuild_index: "Attempt to overwrite 'message' in LogRecord"
```

## Root Cause Analysis

The consistent error message "Attempt to overwrite 'message' in LogRecord" across all three failed tools indicates a logging configuration issue in the Python logging system. This typically occurs when:

1. Multiple logging handlers are trying to modify the same LogRecord object
2. A custom logging formatter is attempting to overwrite the built-in 'message' attribute
3. Logging configuration conflicts between different components

## Impact Assessment

- **Severity**: Medium - Core functionality for index management is affected
- **Affected Operations**: 
  - Azure Search datasource creation
  - Skillset creation for cognitive search
  - Index rebuild operations
- **Workaround**: These operations may still be possible through direct Azure portal or REST API calls

## Recommendations

1. **Immediate**: Review logging configuration in the affected tool implementations
2. **Short-term**: Implement proper logging handler isolation 
3. **Long-term**: Add comprehensive error handling and logging tests

## Test Environment

- **Date**: 2025-08-07
- **MCP Server**: mcprag
- **Index**: codebase-mcp-sota (3460 documents, 23.46MB)
- **Working Tools**: 10/13 tools tested successfully
- **Failed Tools**: 3/13 tools with identical logging errors
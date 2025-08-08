Service:

Search Service

API Version:

2025-05-01-preview

## In this article

1. [URI Parameters](#uri-parameters)
2. [Request Header](#request-headers)
3. [Responses](#response)
4. [Examples](#examples)
5. [Definitions](#definitions)

Returns statistics for the given index, including a document count and storage usage.

HTTP

```
GET {endpoint}/indexes('{indexName}')/search.stats?api-version=2025-05-01-preview
```

## URI Parameters

|Name|In|Required|Type|Description|
|---|---|---|---|---|
|endpoint|path|True|string|The endpoint URL of the search service.|
|indexName|path|True|string|The name of the index for which to retrieve statistics.|
|api-version|query|True|string|Client Api Version.|

## Request Header

|Name|Required|Type|Description|
|---|---|---|---|
|x-ms-client-request-id||string (uuid)|The tracking ID sent with the request to help with debugging.|

## Responses

|Name|Type|Description|
|---|---|---|
|200 OK|[GetIndexStatisticsResult](#getindexstatisticsresult)||
|Other Status Codes|[ErrorResponse](#errorresponse)|Error response.|

## Examples

### SearchServiceGetIndexStatistics

#### Sample request

- [HTTP](#tabpanel_1_HTTP)

HTTP

```
GET https://previewexampleservice.search.windows.net/indexes('preview-test')/search.stats?api-version=2025-05-01-preview

```

#### Sample response

JSON

```
{
  "documentCount": 12,
  "storageSize": 123456,
  "vectorIndexSize": 123456
}
```

## Definitions

|Name|Description|
|---|---|
|[ErrorAdditionalInfo](#erroradditionalinfo)|The resource management error additional info.|
|[ErrorDetail](#errordetail)|The error detail.|
|[ErrorResponse](#errorresponse)|Error response|
|[GetIndexStatisticsResult](#getindexstatisticsresult)|Statistics for a given index. Statistics are collected periodically and are not guaranteed to always be up-to-date.|

### ErrorAdditionalInfo

Object

The resource management error additional info.

|Name|Type|Description|
|---|---|---|
|info|object|The additional info.|
|type|string|The additional info type.|

### ErrorDetail

Object

The error detail.

|Name|Type|Description|
|---|---|---|
|additionalInfo|[ErrorAdditionalInfo](#erroradditionalinfo)[]|The error additional info.|
|code|string|The error code.|
|details|[ErrorDetail](#errordetail)[]|The error details.|
|message|string|The error message.|
|target|string|The error target.|

### ErrorResponse

Object

Error response

|Name|Type|Description|
|---|---|---|
|error|[ErrorDetail](#errordetail)|The error object.|

### GetIndexStatisticsResult

Object

Statistics for a given index. Statistics are collected periodically and are not guaranteed to always be up-to-date.

|Name|Type|Description|
|---|---|---|
|documentCount|integer (int64)|The number of documents in the index.|
|storageSize|integer (int64)|The amount of storage in bytes consumed by the index.|
|vectorIndexSize|integer (int64)|The amount of memory in bytes consumed by vectors in the index.|

## MCP Integration

Use the MCP tool "index_status" to retrieve a compact summary for the configured index, which combines the index definition and stats.

- Tool: index_status
- Server REST calls under the hood:
  - GET /indexes('{indexName}')/search.stats?api-version=2025-05-01-preview (alias: GET /indexes/{indexName}/stats)
  - GET /indexes/{indexName}?api-version=2025-05-01-preview

Example MCP response:
```
{
  "ok": true,
  "data": {
    "index_name": "preview-test",
    "fields": 42,
    "documents": 12,
    "storage_size_mb": 0.12,
    "vector_search": true,
    "semantic_search": true
  }
}
```

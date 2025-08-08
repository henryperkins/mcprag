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

Retrieves a summary of statistics for all indexes in the search service.

HTTP

```
GET {endpoint}/indexstats?api-version=2025-05-01-preview
```

## URI Parameters

|Name|In|Required|Type|Description|
|---|---|---|---|---|
|endpoint|path|True|string|The endpoint URL of the search service.|
|api-version|query|True|string|Client Api Version.|

## Request Header

|Name|Required|Type|Description|
|---|---|---|---|
|x-ms-client-request-id||string (uuid)|The tracking ID sent with the request to help with debugging.|

## Responses

|Name|Type|Description|
|---|---|---|
|200 OK|[ListIndexStatsSummary](#listindexstatssummary)|Statistics summary for all indexes.|
|Other Status Codes|[ErrorResponse](#errorresponse)|Error response.|

## Examples

### SearchServiceIndexStatsSummary

#### Sample request

- [HTTP](#tabpanel_1_HTTP)

HTTP

```
GET https://previewexampleservice.search.windows.net/indexstats?api-version=2025-05-01-preview

```

#### Sample response

JSON

```
{
  "value": [
    {
      "name": "preview-test",
      "documentCount": 0,
      "storageSize": 0,
      "vectorIndexSize": 0
    }
  ]
}
```

## Definitions

|Name|Description|
|---|---|
|[ErrorAdditionalInfo](#erroradditionalinfo)|The resource management error additional info.|
|[ErrorDetail](#errordetail)|The error detail.|
|[ErrorResponse](#errorresponse)|Error response|
|[IndexStatisticsSummary](#indexstatisticssummary)|Statistics for a given index. Statistics are collected periodically and are not guaranteed to always be up-to-date.|
|[ListIndexStatsSummary](#listindexstatssummary)|Response from a request to retrieve stats summary of all indexes. If successful, it includes the stats of each index in the service.|

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

### IndexStatisticsSummary

Object

Statistics for a given index. Statistics are collected periodically and are not guaranteed to always be up-to-date.

|Name|Type|Description|
|---|---|---|
|documentCount|integer (int64)|The number of documents in the index.|
|name|string|The name of the index.|
|storageSize|integer (int64)|The amount of storage in bytes consumed by the index.|
|vectorIndexSize|integer (int64)|The amount of memory in bytes consumed by vectors in the index.|

### ListIndexStatsSummary

Object

Response from a request to retrieve stats summary of all indexes. If successful, it includes the stats of each index in the service.

|Name|Type|Description|
|---|---|---|
|value|[IndexStatisticsSummary](#indexstatisticssummary)[]|The Statistics summary of all indexes in the Search service.|

## MCP Integration

To retrieve stats for all indexes via MCP, use the "manage_index" tool with action "list". The server composes this by listing indexes and fetching per-index stats.

- Tool: manage_index(action="list")
- Server REST calls under the hood:
  - GET /indexes?api-version=2025-05-01-preview
  - GET /indexes('{indexName}')/search.stats?api-version=2025-05-01-preview (alias: GET /indexes/{indexName}/stats)

Example MCP response:
```
{
  "ok": true,
  "data": {
    "indexes": [
      {
        "name": "preview-test",
        "documentCount": 0,
        "storageSize": 0,
        "vectorIndexSize": 0
      }
    ]
  }
}
```

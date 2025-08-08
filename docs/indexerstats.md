
## In this article

1. [URI Parameters](#uri-parameters)
2. [Request Header](#request-headers)
3. [Responses](#response)
4. [Examples](#examples)
5. [Definitions](#definitions)

Returns the current status and execution history of an indexer.

```
GET {endpoint}/indexers('{indexerName}')/search.status?api-version=2025-05-01-preview
```

## URI Parameters

|Name|In|Required|Type|Description|
|---|---|---|---|---|
|endpoint|path|True|string|The endpoint URL of the search service.|
|indexerName|path|True|string|The name of the indexer for which to retrieve status.|
|api-version|query|True|string|Client Api Version.|

|Name|Required|Type|Description|
|---|---|---|---|
|x-ms-client-request-id||string (uuid)|The tracking ID sent with the request to help with debugging.|

## Responses

|Name|Type|Description|
|---|---|---|
|200 OK|[SearchIndexerStatus](#searchindexerstatus)||
|Other Status Codes|[ErrorResponse](#errorresponse)|Error response.|

## Examples

### SearchServiceGetIndexerStatus

#### Sample request

- [HTTP](#tabpanel_1_HTTP)

```
GET https://myservice.search.windows.net/indexers('myindexer')/search.status?api-version=2025-05-01-preview
```

#### Sample response

```
{
  "status": "running",
  "lastResult": {
    "status": "success",
    "statusDetail": null,
    "errorMessage": null,
    "startTime": "2014-11-26T03:37:18.853Z",
    "endTime": "2014-11-26T03:37:19.012Z",
    "errors": [],
    "warnings": [],
    "itemsProcessed": 11,
    "itemsFailed": 0,
    "initialTrackingState": null,
    "finalTrackingState": null,
    "mode": "indexingAllDocs"
  },
  "executionHistory": [
    {
      "status": "success",
      "statusDetail": null,
      "errorMessage": null,
      "startTime": "2014-11-26T03:37:18.853Z",
      "endTime": "2014-11-26T03:37:19.012Z",
      "errors": [],
      "warnings": [],
      "itemsProcessed": 11,
      "itemsFailed": 0,
      "initialTrackingState": null,
      "finalTrackingState": null,
      "mode": "indexingAllDocs"
    },
    {
      "status": "transientFailure",
      "statusDetail": null,
      "errorMessage": null,
      "startTime": "2014-11-26T03:28:10.125Z",
      "endTime": "2014-11-26T03:28:12.007Z",
      "errors": [
        {
          "key": "",
          "errorMessage": "Document key cannot be missing or empty.",
          "statusCode": 400,
          "name": null,
          "details": null,
          "documentationLink": null
        },
        {
          "key": "document id 1",
          "errorMessage": "Could not read the value of column 'foo' at index '0'.",
          "statusCode": 400,
          "name": "DocumentExtraction.AzureBlob.MyDataSource",
          "details": "The file could not be parsed.",
          "documentationLink": "https://go.microsoft.com/fwlink/?linkid=2049388"
        }
      ],
      "warnings": [
        {
          "key": "document id",
          "message": "A warning doesn't stop indexing, and is intended to inform you of certain interesting situations, like when a blob indexer truncates the amount of text extracted from a blob.",
          "name": null,
          "details": null,
          "documentationLink": null
        },
        {
          "key": "document id 2",
          "message": "Document was truncated to 50000 characters.",
          "name": "Enrichment.LanguageDetectionSkill.#4",
          "details": "The skill did something that didn't break anything, nonetheless something we didn't expect happened, so it might be worth double checking.",
          "documentationLink": "https://go.microsoft.com/fwlink/?linkid=2099692"
        }
      ],
      "itemsProcessed": 1,
      "itemsFailed": 2,
      "initialTrackingState": null,
      "finalTrackingState": null,
      "mode": "indexingAllDocs"
    }
  ],
  "limits": {
    "maxRunTime": "PT22H",
    "maxDocumentExtractionSize": 256000000,
    "maxDocumentContentCharactersToExtract": 4000000
  },
  "currentState": {
    "mode": "indexingAllDocs",
    "allDocsInitialTrackingState": null,
    "allDocsFinalTrackingState": null,
    "resetDocsInitialTrackingState": null,
    "resetDocsFinalTrackingState": null,
    "resetDocumentKeys": [],
    "resetDatasourceDocumentIds": [],
    "resyncInitialTrackingState": null,
    "resyncFinalTrackingState": null
  }
}
```

## Definitions

|Name|Description|
|---|---|
|[ErrorAdditionalInfo](#erroradditionalinfo)|The resource management error additional info.|
|[ErrorDetail](#errordetail)|The error detail.|
|[ErrorResponse](#errorresponse)|Error response|
|[IndexerCurrentState](#indexercurrentstate)|Represents all of the state that defines and dictates the indexer's current execution.|
|[IndexerExecutionResult](#indexerexecutionresult)|Represents the result of an individual indexer execution.|
|[IndexerExecutionStatus](#indexerexecutionstatus)|Represents the status of an individual indexer execution.|
|[IndexerExecutionStatusDetail](#indexerexecutionstatusdetail)|Details the status of an individual indexer execution.|
|[IndexerStatus](#indexerstatus)|Represents the overall indexer status.|
|[IndexingMode](#indexingmode)|Represents the mode the indexer is executing in.|
|[SearchIndexerError](#searchindexererror)|Represents an item- or document-level indexing error.|
|[SearchIndexerLimits](#searchindexerlimits)||
|[SearchIndexerStatus](#searchindexerstatus)|Represents the current status and execution history of an indexer.|
|[SearchIndexerWarning](#searchindexerwarning)|Represents an item-level warning.|

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

### IndexerCurrentState

Object

Represents all of the state that defines and dictates the indexer's current execution.

|Name|Type|Description|
|---|---|---|
|allDocsFinalTrackingState|string|Change tracking state value when indexing finishes on all documents in the datasource.|
|allDocsInitialTrackingState|string|Change tracking state used when indexing starts on all documents in the datasource.|
|mode|[IndexingMode](#indexingmode)|The mode the indexer is running in.|
|resetDatasourceDocumentIds|string[]|The list of datasource document ids that have been reset. The datasource document id is the unique identifier for the data in the datasource. The indexer will prioritize selectively re-ingesting these ids.|
|resetDocsFinalTrackingState|string|Change tracking state value when indexing finishes on select, reset documents in the datasource.|
|resetDocsInitialTrackingState|string|Change tracking state used when indexing starts on select, reset documents in the datasource.|
|resetDocumentKeys|string[]|The list of document keys that have been reset. The document key is the document's unique identifier for the data in the search index. The indexer will prioritize selectively re-ingesting these keys.|
|resyncFinalTrackingState|string|Change tracking state value when indexing finishes on selective options from the datasource.|
|resyncInitialTrackingState|string|Change tracking state used when indexing starts on selective options from the datasource.|

### IndexerExecutionResult

Object

Represents the result of an individual indexer execution.

|Name|Type|Description|
|---|---|---|
|endTime|string (date-time)|The end time of this indexer execution, if the execution has already completed.|
|errorMessage|string|The error message indicating the top-level error, if any.|
|errors|[SearchIndexerError](#searchindexererror)[]|The item-level indexing errors.|
|finalTrackingState|string|Change tracking state with which an indexer execution finished.|
|initialTrackingState|string|Change tracking state with which an indexer execution started.|
|itemsFailed|integer (int32)|The number of items that failed to be indexed during this indexer execution.|
|itemsProcessed|integer (int32)|The number of items that were processed during this indexer execution. This includes both successfully processed items and items where indexing was attempted but failed.|
|mode|[IndexingMode](#indexingmode)|The mode the indexer is running in.|
|startTime|string (date-time)|The start time of this indexer execution.|
|status|[IndexerExecutionStatus](#indexerexecutionstatus)|The outcome of this indexer execution.|
|statusDetail|[IndexerExecutionStatusDetail](#indexerexecutionstatusdetail)|The outcome of this indexer execution.|
|warnings|[SearchIndexerWarning](#searchindexerwarning)[]|The item-level indexing warnings.|

### IndexerExecutionStatus

Enumeration

Represents the status of an individual indexer execution.

|Value|Description|
|---|---|
|transientFailure|An indexer invocation has failed, but the failure may be transient. Indexer invocations will continue per schedule.|
|success|Indexer execution completed successfully.|
|inProgress|Indexer execution is in progress.|
|reset|Indexer has been reset.|

### IndexerExecutionStatusDetail

Enumeration

Details the status of an individual indexer execution.

|Value|Description|
|---|---|
|resetDocs|Indicates that the reset that occurred was for a call to ResetDocs.|
|resync|Indicates to selectively resync based on option(s) from data source.|

### IndexerStatus

Enumeration

Represents the overall indexer status.

|Value|Description|
|---|---|
|unknown|Indicates that the indexer is in an unknown state.|
|error|Indicates that the indexer experienced an error that cannot be corrected without human intervention.|
|running|Indicates that the indexer is running normally.|

### IndexingMode

Enumeration

Represents the mode the indexer is executing in.

|Value|Description|
|---|---|
|indexingAllDocs|The indexer is indexing all documents in the datasource.|
|indexingResetDocs|The indexer is indexing selective, reset documents in the datasource. The documents being indexed are defined on indexer status.|
|indexingResync|The indexer is resyncing and indexing selective option(s) from the datasource.|

### SearchIndexerError

Object

Represents an item- or document-level indexing error.

|Name|Type|Description|
|---|---|---|
|details|string|Additional, verbose details about the error to assist in debugging the indexer. This may not be always available.|
|documentationLink|string|A link to a troubleshooting guide for these classes of errors. This may not be always available.|
|errorMessage|string|The message describing the error that occurred while processing the item.|
|key|string|The key of the item for which indexing failed.|
|name|string|The name of the source at which the error originated. For example, this could refer to a particular skill in the attached skillset. This may not be always available.|
|statusCode|integer (int32)|The status code indicating why the indexing operation failed. Possible values include: 400 for a malformed input document, 404 for document not found, 409 for a version conflict, 422 when the index is temporarily unavailable, or 503 for when the service is too busy.|

### SearchIndexerLimits

Object

|Name|Type|Description|
|---|---|---|
|maxDocumentContentCharactersToExtract|number (int64)|The maximum number of characters that will be extracted from a document picked up for indexing.|
|maxDocumentExtractionSize|number (int64)|The maximum size of a document, in bytes, which will be considered valid for indexing.|
|maxRunTime|string (duration)|The maximum duration that the indexer is permitted to run for one execution.|

### SearchIndexerStatus

Object

Represents the current status and execution history of an indexer.

|Name|Type|Description|
|---|---|---|
|currentState|[IndexerCurrentState](#indexercurrentstate)|All of the state that defines and dictates the indexer's current execution.|
|executionHistory|[IndexerExecutionResult](#indexerexecutionresult)[]|History of the recent indexer executions, sorted in reverse chronological order.|
|lastResult|[IndexerExecutionResult](#indexerexecutionresult)|The result of the most recent or an in-progress indexer execution.|
|limits|[SearchIndexerLimits](#searchindexerlimits)|The execution limits for the indexer.|
|status|[IndexerStatus](#indexerstatus)|Overall indexer status.|

### SearchIndexerWarning

Object

Represents an item-level warning.

|Name|Type|Description|
|---|---|---|
|details|string|Additional, verbose details about the warning to assist in debugging the indexer. This may not be always available.|
|documentationLink|string|A link to a troubleshooting guide for these classes of warnings. This may not be always available.|
|key|string|The key of the item which generated a warning.|
|message|string|The message describing the warning that occurred while processing the item.|
|name|string|The name of the source at which the warning originated. For example, this could refer to a particular skill in the attached skillset. This may not be always available.|

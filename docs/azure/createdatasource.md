---

#### Share via

---

## In this article

1. [URI Parameters](#uri-parameters)
2. [Request Header](#request-headers)
3. [Request Body](#request-body)
4. [Responses](#response)
5. [Examples](#examples)
6. [Definitions](#definitions)

Creates a new datasource.

```
POST {endpoint}/datasources?api-version=2025-05-01-preview
```

## URI Parameters

|Name|In|Required|Type|Description|
|---|---|---|---|---|
|endpoint|path|True|string|The endpoint URL of the search service.|
|api-version|query|True|string|Client Api Version.|

|Name|Required|Type|Description|
|---|---|---|---|
|x-ms-client-request-id||string (uuid)|The tracking ID sent with the request to help with debugging.|

## Request Body

|Name|Required|Type|Description|
|---|---|---|---|
|container|True|[SearchIndexerDataContainer](#searchindexerdatacontainer)|The data container for the datasource.|
|credentials|True|[DataSourceCredentials](#datasourcecredentials)|Credentials for the datasource.|
|name|True|string|The name of the datasource.|
|type|True|[SearchIndexerDataSourceType](#searchindexerdatasourcetype)|The type of the datasource.|
|@odata.etag||string|The ETag of the data source.|
|dataChangeDetectionPolicy||DataChangeDetectionPolicy:<br><br>- [HighWaterMarkChangeDetectionPolicy](#highwatermarkchangedetectionpolicy)<br>- [SqlIntegratedChangeTrackingPolicy](#sqlintegratedchangetrackingpolicy)|The data change detection policy for the datasource.|
|dataDeletionDetectionPolicy||DataDeletionDetectionPolicy:<br><br>- [SoftDeleteColumnDeletionDetectionPolicy](#softdeletecolumndeletiondetectionpolicy)<br>- [NativeBlobSoftDeleteDeletionDetectionPolicy](#nativeblobsoftdeletedeletiondetectionpolicy)|The data deletion detection policy for the datasource.|
|description||string|The description of the datasource.|
|encryptionKey||[SearchResourceEncryptionKey](#searchresourceencryptionkey)|A description of an encryption key that you create in Azure Key Vault. This key is used to provide an additional level of encryption-at-rest for your datasource definition when you want full assurance that no one, not even Microsoft, can decrypt your data source definition. Once you have encrypted your data source definition, it will always remain encrypted. The search service will ignore attempts to set this property to null. You can change this property as needed if you want to rotate your encryption key; Your datasource definition will be unaffected. Encryption with customer-managed keys is not available for free search services, and is only available for paid services created on or after January 1, 2019.|
|identity||SearchIndexerDataIdentity:<br><br>- [SearchIndexerDataNoneIdentity](#searchindexerdatanoneidentity)<br>- [SearchIndexerDataUserAssignedIdentity](#searchindexerdatauserassignedidentity)|An explicit managed identity to use for this datasource. If not specified and the connection string is a managed identity, the system-assigned managed identity is used. If not specified, the value remains unchanged. If "none" is specified, the value of this property is cleared.|
|indexerPermissionOptions||[IndexerPermissionOption](#indexerpermissionoption)[]|Ingestion options with various types of permission data.|

## Responses

|Name|Type|Description|
|---|---|---|
|201 Created|[SearchIndexerDataSource](#searchindexerdatasource)||
|Other Status Codes|[ErrorResponse](#errorresponse)|Error response.|

## Examples

### SearchServiceCreateDataSource

#### Sample request

- [HTTP](#tabpanel_1_HTTP)

```
POST https://previewexampleservice.search.windows.net/datasources?api-version=2025-05-01-preview


{
  "name": "tempdatasource",
  "description": "My Azure Blob data source.",
  "type": "azureblob",
  "credentials": {
    "connectionString": "DefaultEndpointsProtocol=https;AccountName=myAccountName;AccountKey=myAccountKey;EndpointSuffix=core.windows.net "
  },
  "container": {
    "name": "doc-extraction-skillset",
    "query": "E2E_Dsat"
  },
  "identity": {
    "@odata.type": "#Microsoft.Azure.Search.DataNoneIdentity"
  },
  "dataChangeDetectionPolicy": {
    "highWaterMarkColumnName": "metadata_storage_last_modified",
    "@odata.type": "#Microsoft.Azure.Search.HighWaterMarkChangeDetectionPolicy"
  },
  "dataDeletionDetectionPolicy": {
    "softDeleteColumnName": "isDeleted",
    "softDeleteMarkerValue": "true",
    "@odata.type": "#Microsoft.Azure.Search.SoftDeleteColumnDeletionDetectionPolicy"
  },
  "@odata.etag": "0x1234568AE7E58A1",
  "encryptionKey": {
    "keyVaultKeyName": "myUserManagedEncryptionKey-createdinAzureKeyVault",
    "keyVaultKeyVersion": "myKeyVersion-32charAlphaNumericString",
    "keyVaultUri": "https://myKeyVault.vault.azure.net",
    "accessCredentials": {
      "applicationId": "00000000-0000-0000-0000-000000000000",
      "applicationSecret": "<applicationSecret>"
    }
  }
}

```

#### Sample response

```
{
  "name": "tempdatasource",
  "description": "My Azure Blob data source.",
  "type": "azureblob",
  "indexerPermissionOptions": [],
  "credentials": {
    "connectionString": "DefaultEndpointsProtocol=https;AccountName=myAccountName;AccountKey=myAccountKey;EndpointSuffix=core.windows.net "
  },
  "container": {
    "name": "doc-extraction-skillset",
    "query": "E2E_Dsat"
  },
  "dataChangeDetectionPolicy": {
    "@odata.type": "#Microsoft.Azure.Search.HighWaterMarkChangeDetectionPolicy",
    "highWaterMarkColumnName": "metadata_storage_last_modified"
  },
  "dataDeletionDetectionPolicy": {
    "@odata.type": "#Microsoft.Azure.Search.SoftDeleteColumnDeletionDetectionPolicy",
    "softDeleteColumnName": "isDeleted",
    "softDeleteMarkerValue": "true"
  },
  "encryptionKey": {
    "keyVaultKeyName": "myUserManagedEncryptionKey-createdinAzureKeyVault",
    "keyVaultKeyVersion": "myKeyVersion-32charAlphaNumericString",
    "keyVaultUri": "https://myKeyVault.vault.azure.net",
    "accessCredentials": {
      "applicationId": "00000000-0000-0000-0000-000000000000",
      "applicationSecret": "<applicationSecret>"
    }
  },
  "identity": {
    "@odata.type": "#Microsoft.Azure.Search.DataNoneIdentity"
  }
}
```

## Definitions

|Name|Description|
|---|---|
|[AzureActiveDirectoryApplicationCredentials](#azureactivedirectoryapplicationcredentials)|Credentials of a registered application created for your search service, used for authenticated access to the encryption keys stored in Azure Key Vault.|
|[DataSourceCredentials](#datasourcecredentials)|Represents credentials that can be used to connect to a datasource.|
|[ErrorAdditionalInfo](#erroradditionalinfo)|The resource management error additional info.|
|[ErrorDetail](#errordetail)|The error detail.|
|[ErrorResponse](#errorresponse)|Error response|
|[HighWaterMarkChangeDetectionPolicy](#highwatermarkchangedetectionpolicy)|Defines a data change detection policy that captures changes based on the value of a high water mark column.|
|[IndexerPermissionOption](#indexerpermissionoption)|Options with various types of permission data to index.|
|[NativeBlobSoftDeleteDeletionDetectionPolicy](#nativeblobsoftdeletedeletiondetectionpolicy)|Defines a data deletion detection policy utilizing Azure Blob Storage's native soft delete feature for deletion detection.|
|[SearchIndexerDataContainer](#searchindexerdatacontainer)|Represents information about the entity (such as Azure SQL table or CosmosDB collection) that will be indexed.|
|[SearchIndexerDataNoneIdentity](#searchindexerdatanoneidentity)|Clears the identity property of a datasource.|
|[SearchIndexerDataSource](#searchindexerdatasource)|Represents a datasource definition, which can be used to configure an indexer.|
|[SearchIndexerDataSourceType](#searchindexerdatasourcetype)|Defines the type of a datasource.|
|[SearchIndexerDataUserAssignedIdentity](#searchindexerdatauserassignedidentity)|Specifies the identity for a datasource to use.|
|[SearchResourceEncryptionKey](#searchresourceencryptionkey)|A customer-managed encryption key in Azure Key Vault. Keys that you create and manage can be used to encrypt or decrypt data-at-rest, such as indexes and synonym maps.|
|[SoftDeleteColumnDeletionDetectionPolicy](#softdeletecolumndeletiondetectionpolicy)|Defines a data deletion detection policy that implements a soft-deletion strategy. It determines whether an item should be deleted based on the value of a designated 'soft delete' column.|
|[SqlIntegratedChangeTrackingPolicy](#sqlintegratedchangetrackingpolicy)|Defines a data change detection policy that captures changes using the Integrated Change Tracking feature of Azure SQL Database.|

### AzureActiveDirectoryApplicationCredentials

Object

Credentials of a registered application created for your search service, used for authenticated access to the encryption keys stored in Azure Key Vault.

|Name|Type|Description|
|---|---|---|
|applicationId|string|An AAD Application ID that was granted the required access permissions to the Azure Key Vault that is to be used when encrypting your data at rest. The Application ID should not be confused with the Object ID for your AAD Application.|
|applicationSecret|string|The authentication key of the specified AAD application.|

### DataSourceCredentials

Object

Represents credentials that can be used to connect to a datasource.

|Name|Type|Description|
|---|---|---|
|connectionString|string|The connection string for the datasource. Set to `<unchanged>` (with brackets) if you don't want the connection string updated. Set to `<redacted>` if you want to remove the connection string value from the datasource.|

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

### HighWaterMarkChangeDetectionPolicy

Object

Defines a data change detection policy that captures changes based on the value of a high water mark column.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.HighWaterMarkChangeDetectionPolicy|A URI fragment specifying the type of data change detection policy.|
|highWaterMarkColumnName|string|The name of the high water mark column.|

### IndexerPermissionOption

Enumeration

Options with various types of permission data to index.

|Value|Description|
|---|---|
|userIds|Indexer to ingest ACL userIds from data source to index.|
|groupIds|Indexer to ingest ACL groupIds from data source to index.|
|rbacScope|Indexer to ingest Azure RBAC scope from data source to index.|

### NativeBlobSoftDeleteDeletionDetectionPolicy

Object

Defines a data deletion detection policy utilizing Azure Blob Storage's native soft delete feature for deletion detection.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.NativeBlobSoftDeleteDeletionDetectionPolicy|A URI fragment specifying the type of data deletion detection policy.|

### SearchIndexerDataContainer

Object

Represents information about the entity (such as Azure SQL table or CosmosDB collection) that will be indexed.

|Name|Type|Description|
|---|---|---|
|name|string|The name of the table or view (for Azure SQL data source) or collection (for CosmosDB data source) that will be indexed.|
|query|string|A query that is applied to this data container. The syntax and meaning of this parameter is datasource-specific. Not supported by Azure SQL datasources.|

### SearchIndexerDataNoneIdentity

Object

Clears the identity property of a datasource.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.DataNoneIdentity|A URI fragment specifying the type of identity.|

### SearchIndexerDataSource

Object

Represents a datasource definition, which can be used to configure an indexer.

|Name|Type|Description|
|---|---|---|
|@odata.etag|string|The ETag of the data source.|
|container|[SearchIndexerDataContainer](#searchindexerdatacontainer)|The data container for the datasource.|
|credentials|[DataSourceCredentials](#datasourcecredentials)|Credentials for the datasource.|
|dataChangeDetectionPolicy|DataChangeDetectionPolicy:<br><br>- [HighWaterMarkChangeDetectionPolicy](#highwatermarkchangedetectionpolicy)<br>- [SqlIntegratedChangeTrackingPolicy](#sqlintegratedchangetrackingpolicy)|The data change detection policy for the datasource.|
|dataDeletionDetectionPolicy|DataDeletionDetectionPolicy:<br><br>- [NativeBlobSoftDeleteDeletionDetectionPolicy](#nativeblobsoftdeletedeletiondetectionpolicy)<br>- [SoftDeleteColumnDeletionDetectionPolicy](#softdeletecolumndeletiondetectionpolicy)|The data deletion detection policy for the datasource.|
|description|string|The description of the datasource.|
|encryptionKey|[SearchResourceEncryptionKey](#searchresourceencryptionkey)|A description of an encryption key that you create in Azure Key Vault. This key is used to provide an additional level of encryption-at-rest for your datasource definition when you want full assurance that no one, not even Microsoft, can decrypt your data source definition. Once you have encrypted your data source definition, it will always remain encrypted. The search service will ignore attempts to set this property to null. You can change this property as needed if you want to rotate your encryption key; Your datasource definition will be unaffected. Encryption with customer-managed keys is not available for free search services, and is only available for paid services created on or after January 1, 2019.|
|identity|SearchIndexerDataIdentity:<br><br>- [SearchIndexerDataNoneIdentity](#searchindexerdatanoneidentity)<br>- [SearchIndexerDataUserAssignedIdentity](#searchindexerdatauserassignedidentity)|An explicit managed identity to use for this datasource. If not specified and the connection string is a managed identity, the system-assigned managed identity is used. If not specified, the value remains unchanged. If "none" is specified, the value of this property is cleared.|
|indexerPermissionOptions|[IndexerPermissionOption](#indexerpermissionoption)[]|Ingestion options with various types of permission data.|
|name|string|The name of the datasource.|
|type|[SearchIndexerDataSourceType](#searchindexerdatasourcetype)|The type of the datasource.|

### SearchIndexerDataSourceType

Enumeration

Defines the type of a datasource.

|Value|Description|
|---|---|
|azuresql|Indicates an Azure SQL datasource.|
|cosmosdb|Indicates a CosmosDB datasource.|
|azureblob|Indicates an Azure Blob datasource.|
|azuretable|Indicates an Azure Table datasource.|
|mysql|Indicates a MySql datasource.|
|adlsgen2|Indicates an ADLS Gen2 datasource.|
|onelake|Indicates a Microsoft Fabric OneLake datasource.|

### SearchIndexerDataUserAssignedIdentity

Object

Specifies the identity for a datasource to use.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.DataUserAssignedIdentity|A URI fragment specifying the type of identity.|
|userAssignedIdentity|string|The fully qualified Azure resource Id of a user assigned managed identity typically in the form "/subscriptions/12345678-1234-1234-1234-1234567890ab/resourceGroups/rg/providers/Microsoft.ManagedIdentity/userAssignedIdentities/myId" that should have been assigned to the search service.|

### SearchResourceEncryptionKey

Object

A customer-managed encryption key in Azure Key Vault. Keys that you create and manage can be used to encrypt or decrypt data-at-rest, such as indexes and synonym maps.

|Name|Type|Description|
|---|---|---|
|accessCredentials|[AzureActiveDirectoryApplicationCredentials](#azureactivedirectoryapplicationcredentials)|Optional Azure Active Directory credentials used for accessing your Azure Key Vault. Not required if using managed identity instead.|
|identity|SearchIndexerDataIdentity:<br><br>- [SearchIndexerDataNoneIdentity](#searchindexerdatanoneidentity)<br>- [SearchIndexerDataUserAssignedIdentity](#searchindexerdatauserassignedidentity)|An explicit managed identity to use for this encryption key. If not specified and the access credentials property is null, the system-assigned managed identity is used. On update to the resource, if the explicit identity is unspecified, it remains unchanged. If "none" is specified, the value of this property is cleared.|
|keyVaultKeyName|string|The name of your Azure Key Vault key to be used to encrypt your data at rest.|
|keyVaultKeyVersion|string|The version of your Azure Key Vault key to be used to encrypt your data at rest.|
|keyVaultUri|string|The URI of your Azure Key Vault, also referred to as DNS name, that contains the key to be used to encrypt your data at rest. An example URI might be `https://my-keyvault-name.vault.azure.net`.|

### SoftDeleteColumnDeletionDetectionPolicy

Object

Defines a data deletion detection policy that implements a soft-deletion strategy. It determines whether an item should be deleted based on the value of a designated 'soft delete' column.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.SoftDeleteColumnDeletionDetectionPolicy|A URI fragment specifying the type of data deletion detection policy.|
|softDeleteColumnName|string|The name of the column to use for soft-deletion detection.|
|softDeleteMarkerValue|string|The marker value that identifies an item as deleted.|

### SqlIntegratedChangeTrackingPolicy

Object

Defines a data change detection policy that captures changes using the Integrated Change Tracking feature of Azure SQL Database.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.SqlIntegratedChangeTrackingPolicy|A URI fragment specifying the type of data change detection policy.|
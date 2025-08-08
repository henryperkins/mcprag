
Learn how to create and configure an Azure AI Search service using the [Management REST APIs](https://learn.microsoft.com/en-us/rest/api/searchmanagement/). Only the Management REST APIs are guaranteed to provide early access to [preview features](https://learn.microsoft.com/en-us/rest/api/searchmanagement/management-api-versions).

The Management REST API is available in stable and preview versions. Be sure to set a preview API version if you're accessing preview features.

All of the Management REST APIs have examples. If a task isn't covered in this article, see the [API reference](https://learn.microsoft.com/en-us/rest/api/searchmanagement/) instead.

## Prerequisites

- An Azure account with an active subscription. [Create an account for free](https://azure.microsoft.com/free/?WT.mc_id=A261C142F).
- [Visual Studio Code](https://code.visualstudio.com/download) with a [REST client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client).
- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) to get an access token, as described in the following steps. You must be an owner or administrator in your Azure subscription.
	Management REST API calls are authenticated through Microsoft Entra ID. You must provide an access token on the request and permissions to create and configure a resource. In addition to the Azure CLI, you can use [Azure PowerShell to create an access token](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/manage-resources-rest).
	1. Open a command shell for Azure CLI.
	2. Sign in to your Azure subscription. If you have multiple tenants or subscriptions, make sure you select the correct one.
		```
		az login
		```
	3. Get the tenant ID and subscription ID.
		```
		az account show
		```
	4. Get an access token.
		```
		az account get-access-token --query accessToken --output tsv
		```
		You should have a tenant ID, subscription ID, and bearer token. You'll paste these values into the `.rest` or `.http` file that you create in the next step.

If you're not familiar with the REST client for Visual Studio Code, this section includes setup so that you can complete the tasks in this article.

1. Start Visual Studio Code and select the **Extensions** tile.
2. Search for the REST client and select **Install**.
	![Screenshot of the install command.](https://learn.microsoft.com/en-us/azure/search/media/search-get-started-rest/rest-client-install.png)
	Screenshot of the install command.
3. Open or create new file named with either a `.rest` or `.http` file extension.
4. Provide variables for the values you retrieved in the previous step.
	```
	@tenant-id = PUT-YOUR-TENANT-ID-HERE
	@subscription-id = PUT-YOUR-SUBSCRIPTION-ID-HERE
	@token = PUT-YOUR-TOKEN-HERE
	```
5. Verify the session is operational by listing search services in your subscription.
	```
	### List search services
	 GET https://management.azure.com/subscriptions/{{subscription-id}}/providers/Microsoft.Search/searchServices?api-version=2025-05-01  HTTP/1.1
	      Content-type: application/json
	      Authorization: Bearer {{token}}
	```
6. Select **Send request**. A response should appear in an adjacent pane. If you have existing search services, they're listed. Otherwise, the list is empty, but as long as the HTTP code is 200 OK, you're ready for the next steps.
	```
	HTTP/1.1 200 OK
	Cache-Control: no-cache
	Pragma: no-cache
	Content-Length: 22068
	Content-Type: application/json; charset=utf-8
	Expires: -1
	x-ms-ratelimit-remaining-subscription-reads: 11999
	x-ms-request-id: f47d3562-a409-49d2-b9cd-6a108e07304c
	x-ms-correlation-request-id: f47d3562-a409-49d2-b9cd-6a108e07304c
	x-ms-routing-request-id: WESTUS2:20240314T012052Z:f47d3562-a409-49d2-b9cd-6a108e07304c
	Strict-Transport-Security: max-age=31536000; includeSubDomains
	X-Content-Type-Options: nosniff
	X-Cache: CONFIG_NOCACHE
	X-MSEdge-Ref: Ref A: 12401F1160FE4A3A8BB54D99D1FDEE4E Ref B: CO6AA3150217011 Ref C: 2024-03-14T01:20:52Z
	Date: Thu, 14 Mar 2024 01:20:52 GMT
	Connection: close
	{
	  "value": [ . . . ]
	}
	```

Creates or updates a search service under the current subscription. This example uses variables for the search service name and region, which haven't been defined yet. Either provide the names directly or add new variables to the collection.

```
### Create a search service (provide an existing resource group)
@resource-group = PUT-YOUR-RESOURCE-GROUP-NAME-HERE
@search-service = PUT-YOUR-SEARCH-SERVICE-NAME-HERE

PUT https://management.azure.com/subscriptions/{{subscription-id}}/resourceGroups/{{resource-group}}/providers/Microsoft.Search/searchServices/{{search-service}}?api-version=2025-05-01  HTTP/1.1
     Content-type: application/json
     Authorization: Bearer {{token}}

    {
        "location": "North Central US",
        "sku": {
            "name": "basic"
        },
        "properties": {
            "replicaCount": 1,
            "partitionCount": 1,
            "hostingMode": "default"
        }
      }
```

Some Azure AI Search capabilities are only available to new services. To avoid service recreation and bring these capabilities to an existing service, you might be able to [upgrade your service](https://learn.microsoft.com/en-us/azure/search/search-how-to-upgrade).

```
### Upgrade a search service
@resource-group = PUT-YOUR-RESOURCE-GROUP-NAME-HERE
@search-service = PUT-YOUR-SEARCH-SERVICE-NAME-HERE

POST https://management.azure.com/subscriptions/{{subscription-id}}/resourceGroups/{{resource-group}}/providers/Microsoft.Search/searchServices/{{search-service}}/upgrade?api-version=2025-05-01  HTTP/1.1
     Content-type: application/json
     Authorization: Bearer {{token}}
```

If you need more or less capacity, you can [switch to a different pricing tier](https://learn.microsoft.com/en-us/azure/search/search-capacity-planning#change-your-pricing-tier). Currently, you can only switch between Basic and Standard (S1, S2, and S3) tiers. Use the `sku` property to specify the new tier.

```
### Change pricing tiers
@resource-group = PUT-YOUR-RESOURCE-GROUP-NAME-HERE
@search-service = PUT-YOUR-SEARCH-SERVICE-NAME-HERE

PATCH https://management.azure.com/subscriptions/{{subscription-id}}/resourceGroups/{{resource-group}}/providers/Microsoft.Search/searchServices/{{search-service}}?api-version=2025-05-01  HTTP/1.1
     Content-type: application/json
     Authorization: Bearer {{token}}

    {
        "sku": {
            "name": "standard2"
        }
    }
```

To create an [S3HD](https://learn.microsoft.com/en-us/azure/search/search-sku-tier#tier-descriptions) service, use a combination of `sku` and `hostingMode` properties. Set `sku` to `standard3` and "hostingMode" to `HighDensity`.

```
### Create an S3HD service
@resource-group = PUT-YOUR-RESOURCE-GROUP-NAME-HERE
@search-service = PUT-YOUR-SEARCH-SERVICE-NAME-HERE

PUT https://management.azure.com/subscriptions/{{subscription-id}}/resourceGroups/{{resource-group}}/providers/Microsoft.Search/searchServices/{{search-service}}?api-version=2025-05-01  HTTP/1.1
     Content-type: application/json
     Authorization: Bearer {{token}}

    {
        "location": "{{region}}",
        "sku": {
          "name": "standard3"
        },
        "properties": {
          "replicaCount": 1,
          "partitionCount": 1,
          "hostingMode": "HighDensity"
        }
    }
```

**Applies to:** Search Index Data Contributor, Search Index Data Reader, Search Service Contributor

Configure your search service to recognize an **authorization** header on data requests that provide an OAuth2 access token.

To use role-based access control for data plane operations, set `authOptions` to `aadOrApiKey` and then send the request.

To use role-based access control exclusively, [turn off API key authentication](https://learn.microsoft.com/en-us/azure/search/search-security-enable-roles#disable-api-key-authentication) by following up with a second request, this time setting `disableLocalAuth` to true.

```
### Configure role-based access
@resource-group = PUT-YOUR-RESOURCE-GROUP-NAME-HERE
@search-service = PUT-YOUR-SEARCH-SERVICE-NAME-HERE

PATCH https://management.azure.com/subscriptions/{{subscription-id}}/resourcegroups/{{resource-group}}/providers/Microsoft.Search/searchServices/{{search-service}}?api-version=2025-05-01  HTTP/1.1
     Content-type: application/json
     Authorization: Bearer {{token}}

    {
        "properties": {
            "disableLocalAuth": false,
            "authOptions": {
                "aadOrApiKey": {
                    "aadAuthFailureMode": "http401WithBearerChallenge"
                }
            }
        }
    }
```

If you're using [customer-managed encryption](https://learn.microsoft.com/en-us/azure/search/search-security-manage-encryption-keys), you can enable "encryptionWithCMK" with "enforcement" set to "Enabled" if you want the search service to report its compliance status.

When you enable this policy, any REST calls that create objects containing sensitive data, such as the connection string within a data source, will fail if an encryption key isn't provided: `"Error creating Data Source: "CannotCreateNonEncryptedResource: The creation of non-encrypted DataSources is not allowed when encryption policy is enforced."`

```
### Enforce a customer-managed key policy
@resource-group = PUT-YOUR-RESOURCE-GROUP-NAME-HERE
@search-service = PUT-YOUR-SEARCH-SERVICE-NAME-HERE

PATCH https://management.azure.com/subscriptions/{{subscription-id}}/resourcegroups/{{resource-group}}/providers/Microsoft.Search/searchServices/{{search-service}}?api-version=2025-05-01  HTTP/1.1
     Content-type: application/json
     Authorization: Bearer {{token}}
     
     {
        "properties": {
            "encryptionWithCmk": {
                "enforcement": "Enabled"
            }
        }
    }
```

[Semantic ranker is enabled](https://learn.microsoft.com/en-us/azure/search/semantic-how-to-enable-disable) by default at the free plan that allows up to 1,000 requests per month at no charge. You can lock down the feature at the service level to prevent usage.

```
### Disable semantic ranker
@resource-group = PUT-YOUR-RESOURCE-GROUP-NAME-HERE
@search-service = PUT-YOUR-SEARCH-SERVICE-NAME-HERE

PATCH https://management.azure.com/subscriptions/{{subscription-id}}/resourcegroups/{{resource-group}}/providers/Microsoft.Search/searchServices/{{search-service}}?api-version=2025-05-01  HTTP/1.1
     Content-type: application/json
     Authorization: Bearer {{token}}
     
     {
        "properties": {
            "semanticSearch": "Disabled"
        }
    }
```

Azure AI Search [writes to external data sources](https://learn.microsoft.com/en-us/azure/search/search-indexer-securing-resources) when updating a knowledge store, saving debug session state, or caching enrichments. The following example disables these workloads at the service level.

```
### Disable external access
@resource-group = PUT-YOUR-RESOURCE-GROUP-NAME-HERE
@search-service = PUT-YOUR-SEARCH-SERVICE-NAME-HERE

PATCH https://management.azure.com/subscriptions/{{subscription-id}}/resourcegroups/{{resource-group}}/providers/Microsoft.Search/searchServices/{{search-service}}?api-version=2025-05-01  HTTP/1.1
     Content-type: application/json
     Authorization: Bearer {{token}}
     
     {
        "properties": {
            "publicNetworkAccess": "Disabled"
        }
    }
```
```
### Delete a search service
@resource-group = PUT-YOUR-RESOURCE-GROUP-NAME-HERE
@search-service = PUT-YOUR-SEARCH-SERVICE-NAME-HERE

DELETE https://management.azure.com/subscriptions/{{subscription-id}}/resourcegroups/{{resource-group}}/providers/Microsoft.Search/searchServices/{{search-service}}?api-version=2025-05-01  HTTP/1.1
     Content-type: application/json
     Authorization: Bearer {{token}}
```
```
### List admin keys
@resource-group = PUT-YOUR-RESOURCE-GROUP-NAME-HERE
@search-service = PUT-YOUR-SEARCH-SERVICE-NAME-HERE

POST https://management.azure.com/subscriptions/{{subscription-id}}/resourcegroups/{{resource-group}}/providers/Microsoft.Search/searchServices/{{search-service}}/listAdminKeys?api-version=2025-05-01  HTTP/1.1
     Content-type: application/json
     Authorization: Bearer {{token}}
```

You can only regenerate one admin API key at a time.

```
### Regnerate admin keys
@resource-group = PUT-YOUR-RESOURCE-GROUP-NAME-HERE
@search-service = PUT-YOUR-SEARCH-SERVICE-NAME-HERE

POST https://management.azure.com/subscriptions/{{subscription-id}}/resourcegroups/{{resource-group}}/providers/Microsoft.Search/searchServices/{{search-service}}/regenerateAdminKey/primary?api-version=2025-05-01  HTTP/1.1
     Content-type: application/json
     Authorization: Bearer {{token}}
```
```
### Create a query key
@resource-group = PUT-YOUR-RESOURCE-GROUP-NAME-HERE
@search-service = PUT-YOUR-SEARCH-SERVICE-NAME-HERE
@query-key = PUT-YOUR-QUERY-KEY-NAME-HERE

POST https://management.azure.com/subscriptions/{{subscription-id}}/resourcegroups/{{resource-group}}/providers/Microsoft.Search/searchServices/{{search-service}}/createQueryKey/{query-key}?api-version=2025-05-01  HTTP/1.1
     Content-type: application/json
     Authorization: Bearer {{token}}
```
```
### List private endpoint connections
@resource-group = PUT-YOUR-RESOURCE-GROUP-NAME-HERE
@search-service = PUT-YOUR-SEARCH-SERVICE-NAME-HERE

GET https://management.azure.com/subscriptions/{{subscription-id}}/resourcegroups/{{resource-group}}/providers/Microsoft.Search/searchServices/{{search-service}}/privateEndpointConnections?api-version=2025-05-01  HTTP/1.1
     Content-type: application/json
     Authorization: Bearer {{token}}
```
```
### List search operations
GET https://management.azure.com/subscriptions/{{subscription-id}}/resourcegroups?api-version=2021-04-01  HTTP/1.1
  Content-type: application/json
  Authorization: Bearer {{token}}
```

After a search service is configured, your next steps include [creating an index](https://learn.microsoft.com/en-us/azure/search/search-how-to-create-search-index) or [querying an index](https://learn.microsoft.com/en-us/azure/search/search-query-overview) using the Azure portal, REST APIs, or an Azure SDK.

- [Create an Azure AI Search index in the Azure portal](https://learn.microsoft.com/en-us/azure/search/search-get-started-portal)
- [Set up an indexer to load data from other services](https://learn.microsoft.com/en-us/azure/search/search-indexer-overview)
- [Query an Azure AI Search index using Search explorer in the Azure portal](https://learn.microsoft.com/en-us/azure/search/search-explorer)
- [How to use Azure AI Search in.NET](https://learn.microsoft.com/en-us/azure/search/search-howto-dotnet-sdk)

---

## Additional resources

Training

Learning path

[Implement knowledge mining with Azure AI Search - Training](https://learn.microsoft.com/en-us/training/paths/implement-knowledge-mining-azure-cognitive-search/?source=recommendations)

Implement knowledge mining with Azure AI Search

Certification

[Microsoft Certified: Azure AI Engineer Associate - Certifications](https://learn.microsoft.com/en-us/credentials/certifications/azure-ai-engineer/?source=recommendations)

Design and implement an Azure AI solution using Azure AI services, Azure AI Search, and Azure Open AI.
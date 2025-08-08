## Enable or disable semantic ranker

Semantic ranker is a premium feature billed by usage. By default, semantic ranker is enabled on a new billable search service and it's configured for the free plan, but anyone with *Contributor* permissions can disable it or change the billing plan. If you don't want anyone to use the feature, you can [disable it service-wide using the management REST API](https://learn.microsoft.com/en-us/azure/search/?tabs=enable-rest#disable-semantic-ranker-using-the-rest-api).

## Check availability

To check if semantic ranker is available in your region, see the [Azure AI Search regions list](https://learn.microsoft.com/en-us/azure/search/search-region-support).

Semantic ranker might not be enabled on older services. Follow these steps to enable [semantic ranker](https://learn.microsoft.com/en-us/azure/search/semantic-search-overview) at the service level. Once enabled, it's available to all indexes. You can't turn it on or off for specific indexes.

- [**Azure portal**](https://learn.microsoft.com/en-us/azure/search/?tabs=enable-rest#tabpanel_1_enable-portal)
- [**REST**](https://learn.microsoft.com/en-us/azure/search/?tabs=enable-rest#tabpanel_1_enable-rest)

To enable semantic ranker, you can use [Services - Create Or Update (REST API)](https://learn.microsoft.com/en-us/rest/api/searchmanagement/services/create-or-update?view=rest-searchmanagement-2025-05-01&tabs=HTTP&preserve-view=true#searchsemanticsearch).

Management REST API calls are authenticated through Microsoft Entra ID. For instructions on how to authenticate, see [Manage your Azure AI Search service with REST APIs](https://learn.microsoft.com/en-us/azure/search/search-manage-rest).

- Management REST API version 2023-11-01 or later provides the configuration property.
- *Owner* or *Contributor* permissions are required to enable or disable features.
```
PATCH https://management.azure.com/subscriptions/{{subscriptionId}}/resourcegroups/{{resource-group}}/providers/Microsoft.Search/searchServices/{{search-service-name}}?api-version=2025-05-01
    {
      "properties": {
        "semanticSearch": "standard"
      }
    }
```

To turn off feature enablement, or for full protection against accidental usage and charges, you can disable semantic ranker by using the [Create or Update Service API](https://learn.microsoft.com/en-us/rest/api/searchmanagement/services/create-or-update#searchsemanticsearch) on your search service. After the feature is disabled, any requests that include the semantic query type are rejected.

Management REST API calls are authenticated through Microsoft Entra ID. For instructions on how to authenticate, see [Manage your Azure AI Search service with REST APIs](https://learn.microsoft.com/en-us/azure/search/search-manage-rest).

```
PATCH https://management.azure.com/subscriptions/{{subscriptionId}}/resourcegroups/{{resource-group}}/providers/Microsoft.Search/searchServices/{{search-service-name}}?api-version=2025-05-01
    {
      "properties": {
        "semanticSearch": "disabled"
      }
    }
```

To re-enable semantic ranker, run the previous request again and set `semanticSearch` to either **Free** (default) or **Standard**.

[Configure semantic ranker](https://learn.microsoft.com/en-us/azure/search/semantic-how-to-configure)

---

## Additional resources

Training

Module

[Perform search reranking with semantic ranking in Azure AI Search - Training](https://learn.microsoft.com/en-us/training/modules/use-semantic-search/?source=recommendations)

Perform search reranking with semantic ranking in Azure AI Search.

Certification

[Microsoft Certified: Azure AI Engineer Associate - Certifications](https://learn.microsoft.com/en-us/credentials/certifications/azure-ai-engineer/?source=recommendations)

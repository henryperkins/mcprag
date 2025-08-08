You can apply semantic ranking to text queries, hybrid queries, and vector queries if your search documents contain string fields and the [vector query has a text representation](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-query#query-with-integrated-vectorization) in the search document.

This article explains how to invoke the semantic ranker on queries. It assumes you're using the most recent stable or preview APIs. For help with older versions, see [Migrate semantic ranking code](https://learn.microsoft.com/en-us/azure/search/semantic-code-migration).

## Prerequisites

- A search service, Basic tier or higher, with [semantic ranker enabled](https://learn.microsoft.com/en-us/azure/search/semantic-how-to-enable-disable).
- An existing search index with a [semantic configuration](https://learn.microsoft.com/en-us/azure/search/semantic-how-to-configure) and rich text content.
- Review [semantic ranking](https://learn.microsoft.com/en-us/azure/search/semantic-search-overview) if you need an introduction to the feature.

You can use any of the following tools and SDKs to build a query that uses semantic ranking:

- [Azure portal](https://portal.azure.com/), using the index designer to add a semantic configuration.
- [Visual Studio Code](https://code.visualstudio.com/download) with a [REST client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client)
- [Azure SDK for.NET](https://www.nuget.org/packages/Azure.Search.Documents)
- [Azure SDK for Python](https://pypi.org/project/azure-search-documents)
- [Azure SDK for Java](https://central.sonatype.com/artifact/com.azure/azure-search-documents)
- [Azure SDK for JavaScript](https://www.npmjs.com/package/@azure/search-documents)

A few query capabilities bypass relevance scoring, which makes them incompatible with semantic ranking. If your query logic includes the following features, you can't semantically rank your results:

- A query with `search=*` or an empty search string, such as pure filter-only query, won't work because there's nothing to measure semantic relevance against and so the search scores are zero. The query must provide terms or phrases that can be evaluated during processing, and that produces search documents that are scored for relevance. Scored results are inputs to the semantic ranker.
- Sorting (orderBy clauses) on specific fields overrides search scores and a semantic score. Given that the semantic score is supposed to provide the ranking, adding an orderby clause results in an HTTP 400 error if you apply semantic ranking over ordered results.

By default, queries don't use semantic ranking. To use semantic ranking, two different parameters can be used. Each parameter supports a different set of scenarios.

Semantic queries, whether specified through `search` plus `queryType`, or through `semanticQuery`, must be plain text and they can't be empty. Empty queries result in no semantic ranking being applied to the results.

| Semantic ranker parameter | [Plain text search](https://learn.microsoft.com/en-us/azure/search/search-query-create) | [Simple text search syntax](https://learn.microsoft.com/en-us/azure/search/query-simple-syntax) | [Full text search syntax](https://learn.microsoft.com/en-us/azure/search/query-lucene-syntax) | [Vector search](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-query) | [Hybrid Search](https://learn.microsoft.com/en-us/azure/search/hybrid-search-how-to-query) | [Semantic answers](https://learn.microsoft.com/en-us/azure/search/semantic-answers) and captions |
| --- | --- | --- | --- | --- | --- | --- |
| `queryType-semantic` <sup>1</sup> | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| `semanticQuery="<your plain text query>"` <sup>2</sup> | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

<sup>1</sup> `queryType=semantic` can't support explicit `simple` or `full` values because the `queryType` parameter is being used for `semantic`. The effective query behaviors are the defaults of the simple parser.

<sup>2</sup> The `semanticQuery` parameter can be used for all query types. However, it isn't supported in the Azure portal [Search Explorer](https://learn.microsoft.com/en-us/azure/search/search-explorer).

Regardless of the parameter chosen, the index should contain text fields with rich semantic content and a [semantic configuration](https://learn.microsoft.com/en-us/azure/search/semantic-how-to-configure).

- [**Azure portal**](https://learn.microsoft.com/en-us/azure/search/?tabs=portal-query#tabpanel_1_portal-query)
- [**REST API**](https://learn.microsoft.com/en-us/azure/search/?tabs=portal-query#tabpanel_1_rest-query)
- [**.NET SDK**](https://learn.microsoft.com/en-us/azure/search/?tabs=portal-query#tabpanel_1_dotnet-query)

[Search explorer](https://learn.microsoft.com/en-us/azure/search/search-explorer) includes options for semantic ranking. Recall that you can't set the `semanticQuery` parameter in the Azure portal.

1. Sign in to the [Azure portal](https://portal.azure.com/).
2. Open a search index and select **Search explorer**.
3. Select **Query options**. If you already defined a semantic configuration, it's selected by default. If you don't have one, [create a semantic configuration](https://learn.microsoft.com/en-us/azure/search/semantic-how-to-configure) for your index.
	![Screenshot showing query options in Search explorer.](https://learn.microsoft.com/en-us/azure/search/media/semantic-search-overview/search-explorer-semantic-query-options-v2.png)
	Screenshot showing query options in Search explorer.
4. Enter a query, such as "historic hotel with good food", and select **Search**.
5. Alternatively, select **JSON view** and paste definitions into the query editor. The Azure portal doesn't support using `semanticQuery`, so setting `queryType` to `"semantic"` is required:
	![Screenshot showing JSON query syntax in the Azure portal.](https://learn.microsoft.com/en-us/azure/search/media/semantic-search-overview/semantic-portal-json-query.png)
	Screenshot showing JSON query syntax in the Azure portal.
	JSON example for setting query type to semantic that you can paste into the view:
	```json
	{
	  "search": "funky or interesting hotel with good food on site",
	  "count": true,
	  "queryType": "semantic",
	  "semanticConfiguration": "my-semantic-config",
	  "captions": "extractive|highlight-true",
	  "answers": "extractive|count-3",
	  "highlightPreTag": "<strong>",
	  "highlightPostTag": "</strong>",
	  "select": "HotelId,HotelName,Description,Category"
	}
	```

Only the top 50 matches from the initial results can be semantically ranked. As with all queries, a response is composed of all fields marked as retrievable, or just those fields listed in the `select` parameter. A response includes the original relevance score, and might also include a count, or batched results, depending on how you formulated the request.

In semantic ranking, the response has more elements: a new [semantically ranked relevance score](https://learn.microsoft.com/en-us/azure/search/semantic-search-overview#how-results-are-scored), an optional caption in plain text and with highlights, and an optional [answer](https://learn.microsoft.com/en-us/azure/search/semantic-answers). If your results don't include these extra elements, then your query might be misconfigured. As a first step towards troubleshooting the problem, check the semantic configuration to ensure it's specified in both the index definition and query.

In a client app, you can structure the search page to include a caption as the description of the match, rather than the entire contents of a specific field. This approach is useful when individual fields are too dense for the search results page.

The response for the above example query (*"interesting hotel with restaurant on site and cozy lobby or shared area"*) returns three answers (`"answers": "extractive|count-e"`). Captions are returned because the "captions" property is set, with plain text and highlighted versions. If an answer can't be determined, it's omitted from the response. For brevity, this example shows just the three answers and the three highest scoring results from the query.

```json
{
  "@odata.count": 29,
  "@search.answers": [
    {
      "key": "24",
      "text": "Chic hotel near the city. High-rise hotel in downtown, within walking distance to theaters, art galleries, restaurants and shops. Visit Seattle Art Museum by day, and then head over to Benaroya Hall to catch the evening's concert performance.",
      "highlights": "Chic hotel near the city. <strong>High-rise hotel in downtown, </strong>within<strong> walking distance to </strong>theaters, art<strong> galleries, restaurants and shops.</strong> Visit Seattle Art Museum by day, and then head over to Benaroya Hall to catch the evening's concert performance.",
      "score": 0.9340000152587891
    },
    {
      "key": "40",
      "text": "Only 8 miles from Downtown. On-site bar/restaurant, Free hot breakfast buffet, Free wireless internet, All non-smoking hotel. Only 15 miles from airport.",
      "highlights": "Only 8 miles from Downtown. <strong>On-site bar/restaurant, Free hot breakfast buffet, Free wireless internet, </strong>All non-smoking<strong> hotel.</strong> Only 15 miles from airport.",
      "score": 0.9210000038146973
    },
    {
      "key": "38",
      "text": "Nature is Home on the beach. Explore the shore by day, and then come home to our shared living space to relax around a stone fireplace, sip something warm, and explore the library by night. Save up to 30 percent. Valid Now through the end of the year. Restrictions and blackouts may apply.",
      "highlights": "Nature is Home on the beach. Explore the shore by day, and then come home to our<strong> shared living space </strong>to relax around a stone fireplace, sip something warm, and explore the library by night. Save up to 30 percent. Valid Now through the end of the year. Restrictions and blackouts may apply.",
      "score": 0.9200000166893005
    }
  ],
  "value": [
    {
      "@search.score": 3.2328331,
      "@search.rerankerScore": 2.575303316116333,
      "@search.captions": [
        {
          "text": "The best of old town hospitality combined with views of the river and cool breezes off the prairie. Our penthouse suites offer views for miles and the rooftop plaza is open to all guests from sunset to 10 p.m. Enjoy a complimentary continental breakfast in the lobby, and free Wi-Fi throughout the hotel.",
          "highlights": "The best of old town hospitality combined with views of the river and cool breezes off the prairie. Our<strong> penthouse </strong>suites offer views for miles and the rooftop<strong> plaza </strong>is open to all guests from sunset to 10 p.m. Enjoy a<strong> complimentary continental breakfast in the lobby, </strong>and free Wi-Fi<strong> throughout </strong>the hotel."
        }
      ],
      "HotelId": "50",
      "HotelName": "Head Wind Resort",
      "Description": "The best of old town hospitality combined with views of the river and cool breezes off the prairie. Our penthouse suites offer views for miles and the rooftop plaza is open to all guests from sunset to 10 p.m. Enjoy a complimentary continental breakfast in the lobby, and free Wi-Fi throughout the hotel.",
      "Category": "Suite"
    },
    {
      "@search.score": 0.632956,
      "@search.rerankerScore": 2.5425150394439697,
      "@search.captions": [
        {
          "text": "Every stay starts with a warm cookie. Amenities like the Counting Sheep sleep experience, our Wake-up glorious breakfast buffet and spacious workout facilities await.",
          "highlights": "Every stay starts with a warm cookie. Amenities like the<strong> Counting Sheep sleep experience, </strong>our<strong> Wake-up glorious breakfast buffet and spacious workout facilities </strong>await."
        }
      ],
      "HotelId": "34",
      "HotelName": "Lakefront Captain Inn",
      "Description": "Every stay starts with a warm cookie. Amenities like the Counting Sheep sleep experience, our Wake-up glorious breakfast buffet and spacious workout facilities await.",
      "Category": "Budget"
    },
    {
      "@search.score": 3.7076726,
      "@search.rerankerScore": 2.4554927349090576,
      "@search.captions": [
        {
          "text": "Chic hotel near the city. High-rise hotel in downtown, within walking distance to theaters, art galleries, restaurants and shops. Visit Seattle Art Museum by day, and then head over to Benaroya Hall to catch the evening's concert performance.",
          "highlights": "Chic hotel near the city. <strong>High-rise hotel in downtown, </strong>within<strong> walking distance to </strong>theaters, art<strong> galleries, restaurants and shops.</strong> Visit Seattle Art Museum by day, and then head over to Benaroya Hall to catch the evening's concert performance."
        }
      ],
      "HotelId": "24",
      "HotelName": "Uptown Chic Hotel",
      "Description": "Chic hotel near the city. High-rise hotel in downtown, within walking distance to theaters, art galleries, restaurants and shops. Visit Seattle Art Museum by day, and then head over to Benaroya Hall to catch the evening's concert performance.",
      "Category": "Suite"
    },
   . . .
  ]
}
```

## Expected workloads

For semantic ranking, you should expect a search service to support up to 10 concurrent queries per replica.

The service throttles semantic ranking requests if volumes are too high. An error message that includes these phrases indicate the service is at capacity for semantic ranking:

```json
Error in search query: Operation returned an invalid status 'Partial Content'\`
@search.semanticPartialResponseReason\`
CapacityOverloaded
```

If you anticipate consistent throughput requirements near, at, or higher than this level, please file a support ticket so that we can provision for your workload.

Semantic ranking can be used in hybrid queries that combine keyword search and vector search into a single request and a unified response.

[Hybrid query with semantic ranker](https://learn.microsoft.com/en-us/azure/search/hybrid-search-how-to-query#example-semantic-hybrid-search)

---

## Additional resources

Training

Module

[Perform search reranking with semantic ranking in Azure AI Search - Training](https://learn.microsoft.com/en-us/training/modules/use-semantic-search/?source=recommendations)

Perform search reranking with semantic ranking in Azure AI Search.

Certification

[Microsoft Certified: Azure AI Engineer Associate - Certifications](https://learn.microsoft.com/en-us/credentials/certifications/azure-ai-engineer/?source=recommendations)

Design and implement an Azure AI solution using Azure AI services, Azure AI Search, and Azure Open AI.
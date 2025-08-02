---
title: "Hybrid query - Azure AI Search"
source: "https://learn.microsoft.com/en-us/azure/search/hybrid-search-how-to-query?tabs=portal"
author:
  - "[[HeidiSteen]]"
published:
created: 2025-07-31
description: "Learn how to build queries for hybrid search."
tags:
  - "clippings"
---
[Hybrid search](https://learn.microsoft.com/en-us/azure/search/hybrid-search-overview) combines text (keyword) and vector queries in a single search request. Both queries execute in parallel. The results are merged and reordered by new search scores, using [Reciprocal Rank Fusion (RRF)](https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking) to return a unified result set. In many cases, [per benchmark tests](https://techcommunity.microsoft.com/t5/ai-azure-ai-services-blog/azure-ai-search-outperforming-vector-search-with-hybrid/ba-p/3929167), hybrid queries with semantic ranking return the most relevant results.

In this article, learn how to:

- Set up a basic hybrid request
- Add parameters and filters
- Improve relevance using semantic ranking or vector weights
- Optimize query behaviors by controlling inputs (`maxTextRecallSize`)

## Prerequisites

- A search index containing `searchable` vector and nonvector fields. We recommend the [Import and vectorize data wizard](https://learn.microsoft.com/en-us/azure/search/search-import-data-portal) to create an index quickly. Otherwise, see [Create an index](https://learn.microsoft.com/en-us/azure/search/search-how-to-create-search-index) and [Add vector fields to a search index](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-create-index).
- (Optional) If you want the [semantic ranker](https://learn.microsoft.com/en-us/azure/search/semantic-search-overview), your search service must be Basic tier or higher, with [semantic ranker enabled](https://learn.microsoft.com/en-us/azure/search/semantic-how-to-enable-disable).
- (Optional) If you want built-in text-to-vector conversion of a query string, [create and assign a vectorizer](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-configure-vectorizer) to vector fields in the search index.
- Search Explorer in the Azure portal (supports both stable and preview API search syntax) has a JSON view that lets you paste in a hybrid request.
- Newer stable or preview packages of the Azure SDKs (see change logs for SDK feature support).
- [Stable REST APIs](https://learn.microsoft.com/en-us/rest/api/searchservice/documents/search-post) or a recent preview API version if you're using preview features like [maxTextRecallSize and countAndFacetMode(preview)](https://learn.microsoft.com/en-us/azure/search/?tabs=portal#set-maxtextrecallsize-and-countandfacetmode).
	For readability, we use REST examples to explain how the APIs work. You can use a REST client like Visual Studio Code with the REST extension to build hybrid queries. You can also use the Azure SDKs. For more information, see [Quickstart: Vector search](https://learn.microsoft.com/en-us/azure/search/search-get-started-vector).

This section explains the basic structure of a hybrid query and how to set one up in either Search Explorer or for execution in a REST client.

Results are returned in plain text, including vectors in fields marked as `retrievable`. Because numeric vectors aren't useful in search results, choose other fields in the index as a proxy for the vector match. For example, if an index has "descriptionVector" and "descriptionText" fields, the query can match on "descriptionVector" but the search result can show "descriptionText". Use the `select` parameter to specify only human-readable fields in the results.

- [**Azure portal**](https://learn.microsoft.com/en-us/azure/search/?tabs=portal#tabpanel_1_portal)
- [**REST**](https://learn.microsoft.com/en-us/azure/search/?tabs=portal#tabpanel_1_hybrid-rest)

1. Sign in to the [Azure portal](https://portal.azure.com/) and find your search service.
2. Under **Search management** > **Indexes**, select an index that has vectors and non-vector content. [Search Explorer](https://learn.microsoft.com/en-us/azure/search/search-explorer) is the first tab.
3. Under **View**, switch to **JSON view** so that you can paste in a vector query.
4. Replace the default query template with a hybrid query. A basic hybrid query has a text query specified in `search`, and a vector query specified under `vectorQueries.vector`. The text query and vector query can be equivalent or divergent, but it's common for them to share the same intent.
	This example is from the [vector quickstart](https://raw.githubusercontent.com/Azure-Samples/azure-search-rest-samples/refs/heads/main/Quickstart-vectors/az-search-quickstart-vectors.rest) that has vector and nonvector content, and several query examples. For brevity, the vector is truncated in this article.
	```json
	{
	    "search": "historic hotel walk to restaurants and shopping",
	    "vectorQueries": [
	        {
	            "vector": [0.01944167, 0.0040178085, -0.007816401 ... <remaining values omitted> ], 
	            "k": 7,
	            "fields": "DescriptionVector",
	            "kind": "vector",
	            "exhaustive": true
	        }
	    ]
	}
	```
5. Select **Search**.
6. Here's another version of the query. This one adds a `count` for the number of matches found, a `select` parameter for choosing specific fields, and a `top` parameter to return the top seven results.
	```json
	{
	     "count": true,
	     "search": "historic hotel walk to restaurants and shopping",
	     "select": "HotelId, HotelName, Category, Tags, Description",
	     "top": 7,
	     "vectorQueries": [
	         {
	             "vector": [0.01944167, 0.0040178085, -0.007816401 ... <remaining values omitted> ], 
	             "k": 7,
	             "fields": "DescriptionVector",
	             "kind": "vector",
	             "exhaustive": true
	         }
	     ]
	 }
	```

A hybrid query can be tuned to control how much of each subquery contributes to the combined results. Setting `maxTextRecallSize` specifies how many BM25-ranked results are passed to the hybrid ranking model.

If you use `maxTextRecallSize`, you might also want to set `CountAndFacetMode`. This parameter determines whether the `count` and `facets` should include all documents that matched the search query, or only those documents retrieved within the `maxTextRecallSize` window. The default value is "countAllResults".

We recommend the latest preview REST API version [2025-05-01-preview](https://learn.microsoft.com/en-us/rest/api/searchservice/documents/search-post?view=rest-searchservice-2025-05-01-preview&preserve-view=true) for setting these options.

1. Use [Search - POST (preview)](https://learn.microsoft.com/en-us/rest/api/searchservice/documents/search-post?view=rest-searchservice-2025-05-01-preview&preserve-view=true) or [Search - GET (preview)](https://learn.microsoft.com/en-us/rest/api/searchservice/documents/search-get?view=rest-searchservice-2025-05-01-preview&preserve-view=true) to specify preview parameters.
2. Add a `hybridSearch` query parameter object to set the maximum number of documents recalled through the BM25-ranked results of a hybrid query. It has two properties:
	- `maxTextRecallSize` specifies the number of BM25-ranked results to provide to the Reciprocal Rank Fusion (RRF) ranker used in hybrid queries. The default is 1,000. The maximum is 10,000.
	- `countAndFacetMode` reports the counts for the BM25-ranked results (and for facets if you're using them). The default is all documents that match the query. Optionally, you can scope "count" to the `maxTextRecallSize`.
3. Set `maxTextRecallSize`:
	- Decrease `maxTextRecallSize` if vector similarity search is generally outperforming the text-side of the hybrid query.
	- Increase `maxTextRecallSize` if you have a large index, and the default isn't capturing a sufficient number of results. With a larger BM25-ranked result set, you can also set `top`, `skip`, and `next` to retrieve portions of those results.

The following REST examples show two use-cases for setting `maxTextRecallSize`.

The first example reduces `maxTextRecallSize` to 100, limiting the text side of the hybrid query to just 100 document. It also sets `countAndFacetMode` to include only those results from `maxTextRecallSize`.

```
POST https://[service-name].search.windows.net/indexes/[index-name]/docs/search?api-version=2024-05-01-Preview 

    { 
      "vectorQueries": [ 
        { 
          "kind": "vector", 
          "vector": [1.0, 2.0, 3.0], 
          "fields": "my_vector_field", 
          "k": 10 
        } 
      ], 
      "search": "hello world", 
      "hybridSearch": { 
        "maxTextRecallSize": 100, 
        "countAndFacetMode": "countRetrievableResults" 
      } 
    }
```

The second example raises `maxTextRecallSize` to 5,000. It also uses top, skip, and next to pull results from large result sets. In this case, the request pulls in BM25-ranked results starting at position 1,500 through 2,000 as the text query contribution to the RRF composite result set.

```
POST https://[service-name].search.windows.net/indexes/[index-name]/docs/search?api-version=2024-05-01-Preview 

    { 
      "vectorQueries": [ 
        { 
          "kind": "vector", 
          "vector": [1.0, 2.0, 3.0], 
          "fields": "my_vector_field", 
          "k": 10 
        } 
      ], 
      "search": "hello world",
      "top": 500,
      "skip": 1500,
      "next": 500,
      "hybridSearch": { 
        "maxTextRecallSize": 5000, 
        "countAndFacetMode": "countRetrievableResults" 
      } 
    }
```

This section has multiple query examples that illustrate hybrid query patterns.

This example adds a filter, which is applied to the `filterable` nonvector fields of the search index.

```
POST https://{{search-service-name}}.search.windows.net/indexes/{{index-name}}/docs/search?api-version=2024-07-01
Content-Type: application/json
api-key: {{admin-api-key}}
{
    "vectorQueries": [
        {
            "vector": [
                -0.009154141,
                0.018708462,
                . . . 
                -0.02178128,
                -0.00086512347
            ],
            "fields": "DescriptionVector",
            "kind": "vector",
            "k": 10
        }
    ],
    "search": "historic hotel walk to restaurants and shopping",
    "vectorFilterMode": "postFilter",
    "filter": "ParkingIncluded",
    "top": "10"
}
```

**Key points:**

- Filters are applied to the content of filterable fields. In this example, the ParkingIncluded field is a boolean and it's marked as `filterable` in the index schema.
- In hybrid queries, filters can be applied before query execution to reduce the query surface, or after query execution to trim results. `"preFilter"` is the default. To use `postFilter`, set the [filter processing mode](https://learn.microsoft.com/en-us/azure/search/vector-search-filters) as shown in this example.
- When you postfilter query results, the number of results might be less than top-n.

Using a [preview API](https://learn.microsoft.com/en-us/rest/api/searchservice/documents/search-post?view=rest-searchservice-2025-05-01-preview&preserve-view=true), you can override a global filter on the search request by applying a secondary filter that targets just the vector subqueries in a hybrid request.

This feature provides fine-grained control by ensuring that filters only influence the vector search results, leaving keyword-based search results unaffected.

The targeted filter fully overrides the global filter, including any filters used for [security trimming](https://learn.microsoft.com/en-us/azure/search/search-security-trimming-for-azure-search) or geospatial search. In cases where global filters are required, such as security trimming, you must explicitly include these filters in both the top-level filter and in each vector-level filter to ensure security and other constraints are consistently enforced.

To apply targeted vector filters:

- Use the [latest preview Search Documents REST API](https://learn.microsoft.com/en-us/rest/api/searchservice/documents/search-post?view=rest-searchservice-2025-05-01-preview&preserve-view=true#request-body) or an Azure SDK beta package that provides the feature.
- Modify a query request, adding a new `vectorQueries.filterOverride` parameter set to an [OData filter expression](https://learn.microsoft.com/en-us/azure/search/search-query-odata-filter).

Here's an example of hybrid query that adds a filter override. The global filter "Rating gt 3" is replaced at run time by the `filterOverride`.

```
POST https://{{search-service-name}}.search.windows.net/indexes/{{index-name}}/docs/search?api-version=2025-05-01=preview

{
    "vectorQueries": [
        {
            "vector": [
                -0.009154141,
                0.018708462,
                . . . 
                -0.02178128,
                -0.00086512347
            ],
            "fields": "DescriptionVector",
            "kind": "vector",
            "exhaustive": true,
            "filterOverride": "Address/City eq 'Seattle'",
            "k": 10
        }
    ],
    "search": "historic hotel walk to restaurants and shopping",
    "select": "HotelName, Description, Address/City, Rating",
    "filter": "Rating gt 3"
    "debug": "vector",
    "top": 10
}
```

Assuming that you [have semantic ranker](https://learn.microsoft.com/en-us/azure/search/semantic-how-to-enable-disable) and your index definition includes a [semantic configuration](https://learn.microsoft.com/en-us/azure/search/semantic-how-to-query-request), you can formulate a query that includes vector search and keyword search, with semantic ranking over the merged result set. Optionally, you can add captions and answers.

Whenever you use semantic ranking with vectors, make sure `k` is set to 50. Semantic ranker uses up to 50 matches as input. Specifying less than 50 deprives the semantic ranking models of necessary inputs.

```
POST https://{{search-service-name}}.search.windows.net/indexes/{{index-name}}/docs/search?api-version=2024-07-01
Content-Type: application/json
api-key: {{admin-api-key}}
{
    "vectorQueries": [
        {
            "vector": [
                -0.009154141,
                0.018708462,
                . . . 
                -0.02178128,
                -0.00086512347
            ],
            "fields": "DescriptionVector",
            "kind": "vector",
            "k": 50
        }
    ],
    "search": "historic hotel walk to restaurants and shopping",
    "select": "HotelName, Description, Tags",
    "queryType": "semantic",
    "semanticConfiguration": "my-semantic-config",
    "captions": "extractive",
    "answers": "extractive",
    "top": "50"
}
```

**Key points:**

- Semantic ranker accepts up to 50 results from the merged response.
- "queryType" and "semanticConfiguration" are required.
- "captions" and "answers" are optional. Values are extracted from verbatim text in the results. An answer is only returned if the results include content having the characteristics of an answer to the query.

Here's the last query in the collection. It's the same semantic hybrid query as the previous example, but with a filter.

```
POST https://{{search-service-name}}.search.windows.net/indexes/{{index-name}}/docs/search?api-version=2024-07-01
Content-Type: application/json
api-key: {{admin-api-key}}
{
    "vectorQueries": [
        {
            "vector": [
                -0.009154141,
                0.018708462,
                . . . 
                -0.02178128,
                -0.00086512347
            ],
            "fields": "DescriptionVector",
            "kind": "vector",
            "k": 50
        }
    ],
    "search": "historic hotel walk to restaurants and shopping",
    "select": "HotelName, Description, Tags",
    "queryType": "semantic",
    "semanticConfiguration": "my-semantic-config",
    "captions": "extractive",
    "answers": "extractive",
    "filter": "ParkingIsIncluded'",
    "vectorFilterMode": "postFilter",
    "top": "50"
}
```

**Key points:**

- The filter mode can affect the number of results available to the semantic reranker. As a best practice, it's smart to give the semantic ranker the maximum number of documents (50). If prefilters or postfilters are too selective, you might be underserving the semantic ranker by giving it fewer than 50 documents to work with.
- Prefiltering is applied before query execution. If prefilter reduces the search area to 100 documents, the vector query executes over the "DescriptionVector" field for those 100 documents, returning the k=50 best matches. Those 50 matching documents then pass to RRF for merged results, and then to semantic ranker.
- Postfilter is applied after query execution. If k=50 returns 50 matches on the vector query side, followed by a post-filter applied to the 50 matches, your results are reduced by the number of documents that meet filter criteria. This leaves you with fewer than 50 documents to pass to semantic ranker. Keep this in mind if you're using semantic ranking. The semantic ranker works best if it has 50 documents as input.

When you're setting up the hybrid query, think about the response structure. The search engine ranks the matching documents and returns the most relevant results. The response is a flattened rowset. Parameters on the query determine which fields are in each row and how many rows are in the response.

Search results are composed of `retrievable` fields from your search index. A result is either:

- All `retrievable` fields (a REST API default).
- Fields explicitly listed in a `select` parameter on the query.

The examples in this article used a `select` statement to specify text (nonvector) fields in the response.

A query might match to any number of documents, as many as all of them if the search criteria are weak (for example "search=\*" for a null query). Because it's seldom practical to return unbounded results, you should specify a maximum for the *overall response*:

- `"top": n` results for keyword-only queries (no vector)
- `"k": n` results for vector-only queries
- `"top": n` results for hybrid queries (with or without semantic) that include a "search" parameter

Both `k` and `top` are optional. Unspecified, the default number of results in a response is 50. You can set `top` and `skip` to [page through more results](https://learn.microsoft.com/en-us/azure/search/search-pagination-page-layout#paging-results) or change the default.

If you're using semantic ranker in 2024-05-01-preview or later, it's a best practice to set `k` and `maxTextRecallSize` to sum to at least 50 total. You can then restrict the results returned to the user with the `top` parameter.

If you're using semantic ranker in previous APIs do the following:

- For keyword-only search (no vectors) set `top` to 50
- For hybrid search set `k` to 50, to ensure that the semantic ranker gets at least 50 results.

### Ranking

Multiple sets are created for hybrid queries, with or without the optional [semantic reranking](https://learn.microsoft.com/en-us/azure/search/semantic-search-overview). Ranking of results is computed by Reciprocal Rank Fusion (RRF).

In this section, compare the responses between single vector search and simple hybrid search for the top result. The different ranking algorithms, HNSW's similarity metric and RRF is this case, produce scores that have different magnitudes. This behavior is by design. RRF scores can appear quite low, even with a high similarity match. Lower scores are a characteristic of the RRF algorithm. In a hybrid query with RRF, more of the reciprocal of the ranked documents are included in the results, given the relatively smaller score of the RRF ranked documents, as opposed to pure vector search.

**Single Vector Search**: @search.score for results ordered by cosine similarity (default vector similarity distance function).

```json
{
    "@search.score": 0.8399121,
    "HotelId": "49",
    "HotelName": "Swirling Currents Hotel",
    "Description": "Spacious rooms, glamorous suites and residences, rooftop pool, walking access to shopping, dining, entertainment and the city center.",
    "Category": "Luxury",
    "Address": {
    "City": "Arlington"
    }
}
```

**Hybrid Search**: @search.score for hybrid results ranked using Reciprocal Rank Fusion.

```json
{
    "@search.score": 0.032786883413791656,
    "HotelId": "49",
    "HotelName": "Swirling Currents Hotel",
    "Description": "Spacious rooms, glamorous suites and residences, rooftop pool, walking access to shopping, dining, entertainment and the city center.",
    "Category": "Luxury",
    "Address": {
    "City": "Arlington"
    }
}
```

We recommend reviewing vector demo code for [Python](https://github.com/Azure/azure-search-vector-samples/tree/main/demo-python), [C#](https://github.com/Azure/azure-search-vector-samples/tree/main/demo-dotnet) or [JavaScript](https://github.com/Azure/azure-search-vector-samples/tree/main/demo-javascript).

---

## Additional resources

Training

Module

[Perform vector search and retrieval in Azure AI Search - Training](https://learn.microsoft.com/en-us/training/modules/improve-search-results-vector-search/?source=recommendations)

Perform vector search and retrieval in Azure AI Search.
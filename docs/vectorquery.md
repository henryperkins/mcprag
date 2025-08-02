---
title: "Create a Vector Query - Azure AI Search"
source: "https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-query?source=recommendations&tabs=query-2024-07-01%2Cbuiltin-portal"
author:
  - "[[haileytap]]"
published:
created: 2025-07-31
description: "Learn how to build queries for vector search."
tags:
  - "clippings"
---
If you have a [vector index](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-create-index) in Azure AI Search, this article explains how to:

This article uses REST for illustration. After you understand the basic workflow, continue with the Azure SDK code samples in the [azure-search-vector-samples](https://github.com/Azure/azure-search-vector-samples) repo, which provides end-to-end solutions that include vector queries.

You can also use [Search Explorer](https://learn.microsoft.com/en-us/azure/search/search-explorer) in the Azure portal.

## Prerequisites

- An [Azure AI Search service](https://learn.microsoft.com/en-us/azure/search/search-create-service-portal) in any region and on any tier.
- A [vector index](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-create-index). Check for a `vectorSearch` section in your index to confirm its presence.
- Optionally, [add a vectorizer](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-configure-vectorizer) to your index for built-in text-to-vector or image-to-vector conversion during queries.
- Visual Studio Code with a [REST client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client) and sample data if you want to run these examples on your own. To get started with the REST client, see [Quickstart: Full-text search using REST](https://learn.microsoft.com/en-us/azure/search/search-get-started-text).

To query a vector field, the query itself must be a vector.

One approach for converting a user's text query string into its vector representation is to call an embedding library or API in your application code. As a best practice, *always use the same embedding models used to generate embeddings in the source documents*. You can find code samples showing [how to generate embeddings](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-generate-embeddings) in the [azure-search-vector-samples](https://github.com/Azure/azure-search-vector-samples) repo.

A second approach is to [use integrated vectorization](https://learn.microsoft.com/en-us/azure/search/?source=recommendations&tabs=query-2024-07-01%2Cbuiltin-portal#query-with-integrated-vectorization), now generally available, to have Azure AI Search handle your query vectorization inputs and outputs.

Here's a REST API example of a query string submitted to a deployment of an Azure OpenAI embedding model:

```
POST https://{{openai-service-name}}.openai.azure.com/openai/deployments/{{openai-deployment-name}}/embeddings?api-version={{openai-api-version}}
Content-Type: application/json
api-key: {{admin-api-key}}
{
    "input": "what azure services support generative AI'"
}
```

The expected response is 202 for a successful call to the deployed model.

The `embedding` field in the body of the response is the vector representation of the query string `input`. For testing purposes, you would copy the value of the `embedding` array into `vectorQueries.vector` in a query request, using the syntax shown in the next several sections.

The actual response to this POST call to the deployed model includes 1,536 embeddings. For readability, this example only shows the first few vectors.

```json
{
    "object": "list",
    "data": [
        {
            "object": "embedding",
            "index": 0,
            "embedding": [
                -0.009171937,
                0.018715322,
                ...
                -0.0016804502
            ]
        }
    ],
    "model": "ada",
    "usage": {
        "prompt_tokens": 7,
        "total_tokens": 7
    }
}
```

In this approach, your application code is responsible for connecting to a model, generating embeddings, and handling the response.

This section shows you the basic structure of a vector query. You can use the Azure portal, REST APIs, or the Azure SDKs to formulate a vector query.

If you're migrating from [**2023-07-01-Preview**](https://learn.microsoft.com/en-us/rest/api/searchservice/index-preview), there are breaking changes. For more information, see [Upgrade to the latest REST API](https://learn.microsoft.com/en-us/azure/search/search-api-migration).

- [**2024-07-01**](https://learn.microsoft.com/en-us/azure/search/?source=recommendations&tabs=query-2024-07-01%2Cbuiltin-portal#tabpanel_1_query-2024-07-01)
- [**2024-05-01-preview**](https://learn.microsoft.com/en-us/azure/search/?source=recommendations&tabs=query-2024-07-01%2Cbuiltin-portal#tabpanel_1_query-2024-05-01-preview)
- [**Azure portal**](https://learn.microsoft.com/en-us/azure/search/?source=recommendations&tabs=query-2024-07-01%2Cbuiltin-portal#tabpanel_1_portal-vector-query)

[**2024-07-01**](https://learn.microsoft.com/en-us/rest/api/searchservice/search-service-api-versions#2024-07-01) is the stable REST API version of [Search POST](https://learn.microsoft.com/en-us/rest/api/searchservice/documents/search-post). This version supports:

- `vectorQueries` is the construct for vector search.
- `vectorQueries.kind` set to `vector` for a vector array or `text` if the input is a string and if you [have a vectorizer](https://learn.microsoft.com/en-us/azure/search/?source=recommendations&tabs=query-2024-07-01%2Cbuiltin-portal#query-with-integrated-vectorization).
- `vectorQueries.vector` is the query (a vector representation of text or an image).
- `vectorQueries.exhaustive` (optional) invokes exhaustive KNN at query time, even if the field is indexed for HNSW.
- `vectorQueries.fields` (optional) targets specific fields for query execution (up to 10 per query).
- `vectorQueries.weight` (optional) specifies the relative weight of each vector query included in search operations. For more information, see [Vector weighting](https://learn.microsoft.com/en-us/azure/search/?source=recommendations&tabs=query-2024-07-01%2Cbuiltin-portal#vector-weighting).
- `vectorQueries.k` is the number of matches to return.

In the following example, the vector is a representation of this string: `"what Azure services support full text search"`. The query targets the `contentVector` field and returns `k` results. The actual vector has 1,536 embeddings, which are trimmed in this example for readability.

```
POST https://{{search-service-name}}.search.windows.net/indexes/{{index-name}}/docs/search?api-version=2024-07-01
Content-Type: application/json
api-key: {{admin-api-key}}
{
    "count": true,
    "select": "title, content, category",
    "vectorQueries": [
        {
            "kind": "vector",
            "vector": [
                -0.009154141,
                0.018708462,
                . . . 
                -0.02178128,
                -0.00086512347
            ],
            "exhaustive": true,
            "fields": "contentVector",
            "weight": 0.5,
            "k": 5
        }
    ]
}
```

In Azure AI Search, query responses consist of all `retrievable` fields by default. However, it's common to limit search results to a subset of `retrievable` fields by listing them in a `select` statement.

In a vector query, carefully consider whether you need to vector fields in a response. Vector fields aren't human readable, so if you're pushing a response to a web page, you should choose nonvector fields that represent the result. For example, if the query executes against `contentVector`, you could return `content` instead.

If you want vector fields in the result, here's an example of the response structure. `contentVector` is a string array of embeddings, which are trimmed in this example for readability. The search score indicates relevance. Other nonvector fields are included for context.

```json
{
    "@odata.count": 3,
    "value": [
        {
            "@search.score": 0.80025613,
            "title": "Azure Search",
            "category": "AI + Machine Learning",
            "contentVector": [
                -0.0018343845,
                0.017952163,
                0.0025753193,
                ...
            ]
        },
        {
            "@search.score": 0.78856903,
            "title": "Azure Application Insights",
            "category": "Management + Governance",
            "contentVector": [
                -0.016821077,
                0.0037742127,
                0.016136652,
                ...
            ]
        },
        {
            "@search.score": 0.78650564,
            "title": "Azure Media Services",
            "category": "Media",
            "contentVector": [
                -0.025449317,
                0.0038463024,
                -0.02488436,
                ...
            ]
        }
    ]
}
```

**Key points:**

- `k` determines how many nearest neighbor results are returned, in this case, three. Vector queries always return `k` results, assuming at least `k` documents exist, even if some documents have poor similarity. This is because the algorithm finds any `k` nearest neighbors to the query vector.
- The [vector search algorithm](https://learn.microsoft.com/en-us/azure/search/vector-search-ranking) determines the `@search.score`.
- Fields in search results are either all `retrievable` fields or fields in a `select` clause. During vector query execution, matching is made on vector data alone. However, a response can include any `retrievable` field in an index. Because there's no facility for decoding a vector field result, the inclusion of nonvector text fields is helpful for their human-readable values.

You can set the `vectorQueries.fields` property to multiple vector fields. The vector query executes against each vector field that you provide in the `fields` list. You can specify up to 10 fields.

When querying multiple vector fields, ensure that each one contains embeddings from the same embedding model. The query should also be generated from the same embedding model.

```
POST https://{{search-service-name}}.search.windows.net/indexes/{{index-name}}/docs/search?api-version=2024-07-01
Content-Type: application/json
api-key: {{admin-api-key}}
{
    "count": true,
    "select": "title, content, category",
    "vectorQueries": [
        {
            "kind": "vector",
            "vector": [
                -0.009154141,
                0.018708462,
                . . . 
                -0.02178128,
                -0.00086512347
            ],
            "exhaustive": true,
            "fields": "contentVector, titleVector",
            "k": 5
        }
    ]
}
```

Multi-query vector search sends multiple queries across multiple vector fields in your search index. This type of query is commonly used with models such as [CLIP](https://openai.com/research/clip) for multimodal search, where the same model can vectorize both text and images.

The following query example looks for similarity in both `myImageVector` and `myTextVector` but sends two respective query embeddings, each executing in parallel. The result of this query is scored using [reciprocal rank fusion](https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking) (RRF).

- `vectorQueries` provides an array of vector queries.
- `vector` contains the image vectors and text vectors in the search index. Each instance is a separate query.
- `fields` specifies which vector field to target.
- `k` is the number of nearest neighbor matches to include in results.
```json
{
    "count": true,
    "select": "title, content, category",
    "vectorQueries": [
        {
            "kind": "vector",
            "vector": [
                -0.009154141,
                0.018708462,
                . . . 
                -0.02178128,
                -0.00086512347
            ],
            "fields": "myimagevector",
            "k": 5
        },
        {
            "kind": "vector"
            "vector": [
                -0.002222222,
                0.018708462,
                -0.013770515,
            . . .
            ],
            "fields": "mytextvector",
            "k": 5
        }
    ]
}
```

Search indexes can't store images. Assuming that your index includes a field for the image file, the search results would include a combination of text and images.

This section shows a vector query that invokes the [integrated vectorization](https://learn.microsoft.com/en-us/azure/search/vector-search-integrated-vectorization) to convert a text or [image query](https://learn.microsoft.com/en-us/azure/search/search-get-started-portal-image-search) into a vector. We recommend the stable [**2024-07-01**](https://learn.microsoft.com/en-us/rest/api/searchservice/documents/search-post) REST API, Search Explorer, or newer Azure SDK packages for this feature.

A prerequisite is a search index that has a [vectorizer configured and assigned](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-configure-vectorizer) to a vector field. The vectorizer provides connection information to an embedding model used at query time.

- [**Azure portal**](https://learn.microsoft.com/en-us/azure/search/?source=recommendations&tabs=query-2024-07-01%2Cbuiltin-portal#tabpanel_2_builtin-portal)
- [**REST API**](https://learn.microsoft.com/en-us/azure/search/?source=recommendations&tabs=query-2024-07-01%2Cbuiltin-portal#tabpanel_2_builtin-2024-07-01)

Search Explorer supports integrated vectorization at query time. If your index contains vector fields and has a vectorizer, you can use the built-in text-to-vector conversion.

1. Sign in to the [Azure portal](https://portal.azure.com/) and [find your search service](https://portal.azure.com/#blade/HubsExtension/BrowseResourceBlade/resourceType/Microsoft.Search%2FsearchServices).
2. From the left menu, select **Search management** > **Indexes**, and then select your index.
3. Select the **Vector profiles** tab to confirm that you have a vectorizer.
	![Screenshot of a vectorizer setting in a search index.](https://learn.microsoft.com/en-us/azure/search/media/vector-search-how-to-query/check-vectorizer.png)
	Screenshot of a vectorizer setting in a search index.
4. Select the **Search explorer** tab. Using the default query view, you can enter a text string into the search bar. The built-in vectorizer converts your string into a vector, performs the search, and returns results.
	Alternatively, you can select **View** > **JSON view** to view or modify the query. If vectors are present, Search Explorer sets up a vector query automatically. You can use the JSON view to select fields for use in the searche and response, add filters, and construct more advanced queries, such as [hybrid queries](https://learn.microsoft.com/en-us/azure/search/hybrid-search-how-to-query). To see a JSON example, select the REST API tab in this section.

A vector query specifies the `k` parameter, which determines how many matches are returned in the results. The search engine always returns `k` number of matches. If `k` is larger than the number of documents in the index, the number of documents determines the upper limit of what can be returned.

If you're familiar with full-text search, you know to expect zero results if the index doesn't contain a term or phrase. However, in vector search, the search operation identifies nearest neighbors and always return `k` results, even if the nearest neighbors aren't that similar. It's possible to get results for nonsensical or off-topic queries, especially if you aren't using prompts to set boundaries. Less relevant results have a worse similarity score, but they're still the "nearest" vectors if there isn't anything closer. Therefore, a response with no meaningful results can still return `k` results, but each result's similarity score would be low.

A [hybrid approach](https://learn.microsoft.com/en-us/azure/search/hybrid-search-overview) that includes full-text search can mitigate this problem. Another solution is to set a minimum threshold on the search score, but only if the query is a pure single vector query. Hybrid queries aren't conducive to minimum thresholds because the RRF ranges are much smaller and more volatile.

Query parameters that affect result count include:

- `"k": n` results for vector-only queries.
- `"top": n` results for hybrid queries that include a `search` parameter.

Both `k` and `top` are optional. When unspecified, the default number of results in a response is 50. You can set `top` and `skip` to [page through more results](https://learn.microsoft.com/en-us/azure/search/search-pagination-page-layout#paging-results) or change the default.

The ranking of results is computed by either:

- The similarity metric.
- RRF if there are multiple sets of search results.

### Similarity metric

The similarity metric specified in the index `vectorSearch` section for a vector-only query. Valid values are `cosine`, `euclidean`, and `dotProduct`.

Azure OpenAI embedding models use cosine similarity, so if you're using Azure OpenAI embedding models, `cosine` is the recommended metric. Other supported ranking metrics include `euclidean` and `dotProduct`.

### RRF

Multiple sets are created if the query targets multiple vector fields, runs multiple vector queries in parallel, or is a hybrid of vector and full-text search, with or without [semantic ranking](https://learn.microsoft.com/en-us/azure/search/semantic-search-overview).

During query execution, a vector query can only target one internal vector index. For [multiple vector fields](https://learn.microsoft.com/en-us/azure/search/?source=recommendations&tabs=query-2024-07-01%2Cbuiltin-portal#multiple-vector-fields) and [multiple vector queries](https://learn.microsoft.com/en-us/azure/search/?source=recommendations&tabs=query-2024-07-01%2Cbuiltin-portal#multiple-vector-queries), the search engine generates multiple queries that target the respective vector indexes of each field. The output is a set of ranked results for each query, which are fused using RRF. For more information, see [Relevance scoring using Reciprocal Rank Fusion](https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking).

## Vector weighting

Add a `weight` query parameter to specify the relative weight of each vector query included in search operations. This value is used when combining the results of multiple ranking lists produced by two or more vector queries in the same request, or from the vector portion of a hybrid query.

The default is 1.0, and the value must be a positive number larger than zero.

Weights are used when calculating the [RRF scores](https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking#weighted-scores) of each document. The calculation is a multiplier of the `weight` value against the rank score of the document within its respective result set.

The following example is a hybrid query with two vector query strings and one text string. Weights are assigned to the vector queries. The first query is 0.5 or half the weight, reducing its importance in the request. The second vector query is twice as important.

```
POST https://[service-name].search.windows.net/indexes/[index-name]/docs/search?api-version=2024-07-01

    { 
      "vectorQueries": [ 
        { 
          "kind": "vector", 
          "vector": [1.0, 2.0, 3.0], 
          "fields": "my_first_vector_field", 
          "k": 10, 
          "weight": 0.5 
        },
        { 
          "kind": "vector", 
          "vector": [4.0, 5.0, 6.0], 
          "fields": "my_second_vector_field", 
          "k": 10, 
          "weight": 2.0
        } 
      ], 
      "search": "hello world" 
    }
```

Vector weighting applies to vectors only. The text query in this example, `"hello world"`, has an implicit neutral weight of 1.0. However, in a hybrid query, you can increase or decrease the importance of text fields by setting [maxTextRecallSize](https://learn.microsoft.com/en-us/azure/search/hybrid-search-how-to-query#set-maxtextrecallsize-and-countandfacetmode).

Because nearest neighbor search always returns the requested `k` neighbors, it's possible to get multiple low-scoring matches as part of meeting the `k` number requirement on search results. To exclude low-scoring search results, you can add a `threshold` query parameter that filters out results based on a minimum score. Filtering occurs before [fusing results](https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking) from different recall sets.

This parameter is in preview. We recommend the [2024-05-01-preview](https://learn.microsoft.com/en-us/rest/api/searchservice/documents/search-post?view=rest-searchservice-2024-05-01-preview&preserve-view=true) REST API version.

In this example, all matches that score below 0.8 are excluded from vector search results, even if the number of results falls below `k`.

```
POST https://[service-name].search.windows.net/indexes/[index-name]/docs/search?api-version=2024-05-01-preview 
    Content-Type: application/json 
    api-key: [admin key] 

    { 
      "vectorQueries": [ 
        { 
          "kind": "vector", 
          "vector": [1.0, 2.0, 3.0], 
          "fields": "my-cosine-field", 
          "threshold": { 
            "kind": "vectorSimilarity", 
            "value": 0.8 
          } 
        }
      ]
    }
```

As a next step, review vector query code examples in [Python](https://github.com/Azure/azure-search-vector-samples/tree/main/demo-python), [C#](https://github.com/Azure/azure-search-vector-samples/tree/main/demo-dotnet) or [JavaScript](https://github.com/Azure/azure-search-vector-samples/tree/main/demo-javascript).
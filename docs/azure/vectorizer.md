In Azure AI Search a *vectorizer* is a component that performs vectorization using a deployed embedding model on Azure OpenAI or Azure AI Vision. It converts text (or images) to vectors during query execution.

It's defined in a [search index](https://learn.microsoft.com/en-us/azure/search/search-what-is-an-index), it applies to searchable vector fields, and it's used at query time to generate an embedding for a text or image query input. If instead you need to vectorize content as part of the indexing process, refer to [integrated vectorization](https://learn.microsoft.com/en-us/azure/search/vector-search-integrated-vectorization). For built-in vectorization during indexing, you can configure an indexer and skillset that calls an embedding model for your raw text or image content.

To add a vectorizer to search index, you can use the index designer in Azure portal, or call the [Create or Update Index](https://learn.microsoft.com/en-us/rest/api/searchservice/indexes/create-or-update) REST API, or use any Azure SDK package that's updated to provide this feature.

Vectorizers are now generally available as long as you use a generally available skill-vectorizer pair. [AzureOpenAIEmbedding vectorizer](https://learn.microsoft.com/en-us/azure/search/vector-search-vectorizer-azure-open-ai) and [AzureOpenAIEmbedding skill](https://learn.microsoft.com/en-us/azure/search/cognitive-search-skill-azure-openai-embedding) are generally available. The custom [Web API vectorizer](https://learn.microsoft.com/en-us/rest/api/searchservice/indexes/create-or-update#webapivectorizer) is also generally available.

[Azure AI Vision vectorizer](https://learn.microsoft.com/en-us/azure/search/vector-search-vectorizer-ai-services-vision), [Azure AI Foundry model catalog vectorizer](https://learn.microsoft.com/en-us/azure/search/vector-search-vectorizer-azure-machine-learning-ai-studio-catalog), and their equivalent skills are still in preview. Your skillset must specify [2024-05-01-preview REST API](https://learn.microsoft.com/en-us/rest/api/searchservice/operation-groups?view=rest-searchservice-2024-05-01-preview&preserve-view=true) to use preview skills and vectorizers.

## Prerequisites

- [An index with searchable vector fields](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-create-index) on Azure AI Search.
- A deployed embedding model (see the next section).
- Permissions to use the embedding model. On Azure OpenAI, the caller must have [Cognitive Services OpenAI User](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/role-based-access-control#azure-openai-roles) permissions. Or, you can provide an API key.
- [Visual Studio Code](https://code.visualstudio.com/download) with a [REST client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client) to send the query and accept a response.

We recommend that you [enable diagnostic logging](https://learn.microsoft.com/en-us/azure/search/search-monitor-enable-logging) on your search service to confirm vector query execution.

The following table lists the embedding models that can be used with a vectorizer. Because you must use the [same embedding model for indexing and queries](https://learn.microsoft.com/en-us/azure/search/vector-search-integrated-vectorization#using-integrated-vectorization-in-queries), vectorizers are paired with skills that generate embeddings during indexing. The table lists the skill associated with a particular vectorizer.

| Vectorizer kind | Model names | Model provider | Associated skill |
| --- | --- | --- | --- |
| [`azureOpenAI`](https://learn.microsoft.com/en-us/azure/search/vector-search-vectorizer-azure-open-ai) | text-embedding-ada-002   text-embedding-3 | Azure OpenAI | [AzureOpenAIEmbedding skill](https://learn.microsoft.com/en-us/azure/search/cognitive-search-skill-azure-openai-embedding) |
| [`aml`](https://learn.microsoft.com/en-us/azure/search/vector-search-vectorizer-azure-machine-learning-ai-studio-catalog) | Facebook-DinoV2-Image-Embeddings   Cohere-embed-v3   Cohere-embed-v4 <sup>1</sup> | [Azure AI Foundry model catalog](https://learn.microsoft.com/en-us/azure/search/vector-search-integrated-vectorization-ai-studio) | [AML skill](https://learn.microsoft.com/en-us/azure/search/cognitive-search-aml-skill) |
| [`aiServicesVision`](https://learn.microsoft.com/en-us/azure/search/vector-search-vectorizer-ai-services-vision) | [Multimodal embeddings 4.0 API](https://learn.microsoft.com/en-us/azure/ai-services/computer-vision/concept-image-retrieval) | Azure AI Vision (through an Azure AI services multi-service account) | [Azure AI Vision multimodal embeddings skill](https://learn.microsoft.com/en-us/azure/search/cognitive-search-skill-vision-vectorize) |
| [`customWebApi`](https://learn.microsoft.com/en-us/azure/search/vector-search-vectorizer-custom-web-api) | Any embedding model | Hosted externally | [Custom Web API skill](https://learn.microsoft.com/en-us/azure/search/cognitive-search-custom-skill-web-api) |

<sup>1</sup> At this time, you can only specify `embed-v-4-0` programmatically through the [AML skill](https://learn.microsoft.com/en-us/azure/search/cognitive-search-aml-skill) or [Azure AI Foundry model catalog vectorizer](https://learn.microsoft.com/en-us/azure/search/vector-search-vectorizer-azure-machine-learning-ai-studio-catalog), not through the Azure portal. However, you can use the portal to manage the skillset or vectorizer afterward.

The [Import and vectorize data wizard](https://learn.microsoft.com/en-us/azure/search/search-get-started-portal-import-vectors) reads files from Azure Blob storage, creates an index with chunked and vectorized fields, and adds a vectorizer. By design, the vectorizer that's created by the wizard is set to the same embedding model used to index the blob content.

1. [Upload sample data files](https://learn.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-portal) to a container on Azure Storage. We used some [small text files from NASA's earth book](https://github.com/Azure-Samples/azure-search-sample-data/tree/main/nasa-e-book/earth-txt-10) to test these instructions on a free search service.
2. Run the [Import and vectorize data wizard](https://learn.microsoft.com/en-us/azure/search/search-get-started-portal-import-vectors), choosing the blob container for the data source.
	![Screenshot of the connect to your data page.](https://learn.microsoft.com/en-us/azure/search/media/vector-search-how-to-configure-vectorizer/connect-to-data.png)
	Screenshot of the connect to your data page.
3. Choose an existing deployment of **text-embedding-ada-002**. This model generates embeddings during indexing and is also used to configure the vectorizer used during queries.
	![Screenshot of the vectorize and enrich data page.](https://learn.microsoft.com/en-us/azure/search/media/vector-search-how-to-configure-vectorizer/vectorize-enrich-data.png)
	Screenshot of the vectorize and enrich data page.
4. After the wizard is finished and all indexer processing is complete, you should have an index with a searchable vector field. The field's JSON definition looks like this:
	```json
	{
	     "name": "vector",
	     "type": "Collection(Edm.Single)",
	     "searchable": true,
	     "retrievable": true,
	     "dimensions": 1536,
	     "vectorSearchProfile": "vector-nasa-ebook-text-profile"
	 }
	```
5. You should also have a vector profile and a vectorizer, similar to the following example:
	```json
	"profiles": [
	   {
	     "name": "vector-nasa-ebook-text-profile",
	     "algorithm": "vector-nasa-ebook-text-algorithm",
	     "vectorizer": "vector-nasa-ebook-text-vectorizer"
	   }
	 ],
	 "vectorizers": [
	   {
	     "name": "vector-nasa-ebook-text-vectorizer",
	     "kind": "azureOpenAI",
	     "azureOpenAIParameters": {
	       "resourceUri": "https://my-fake-azure-openai-resource.openai.azure.com",
	       "deploymentId": "text-embedding-ada-002",
	       "modelName": "text-embedding-ada-002",
	       "apiKey": "0000000000000000000000000000000000000",
	       "authIdentity": null
	     },
	     "customWebApiParameters": null
	   }
	 ]
	```
6. Skip ahead to [test your vectorizer](https://learn.microsoft.com/en-us/azure/search/#test-a-vectorizer) for text-to-vector conversion during query execution.

This section explains the modifications to an index schema for defining a vectorizer manually.

1. Use [Create or Update Index](https://learn.microsoft.com/en-us/rest/api/searchservice/indexes/create-or-update) to add `vectorizers` to a search index.
2. Add the following JSON to your index definition. The vectorizers section provides connection information to a deployed embedding model. This step shows two vectorizer examples so that you can compare an Azure OpenAI embedding model and a custom web API side by side.
	```json
	"vectorizers": [
	    {
	      "name": "my_azure_open_ai_vectorizer",
	      "kind": "azureOpenAI",
	      "azureOpenAIParameters": {
	        "resourceUri": "https://url.openai.azure.com",
	        "deploymentId": "text-embedding-ada-002",
	        "modelName": "text-embedding-ada-002",
	        "apiKey": "mytopsecretkey"
	      }
	    },
	    {
	      "name": "my_custom_vectorizer",
	      "kind": "customWebApi",
	      "customVectorizerParameters": {
	        "uri": "https://my-endpoint",
	        "authResourceId": " ",
	        "authIdentity": " "
	      }
	    }
	  ]
	```
3. In the same index, add a vector profiles section that specifies one of your vectorizers. Vector profiles also require a [vector search algorithm](https://learn.microsoft.com/en-us/azure/search/vector-search-ranking) used to create navigation structures.
	```json
	"profiles": [ 
	    { 
	        "name": "my_vector_profile", 
	        "algorithm": "my_hnsw_algorithm", 
	        "vectorizer":"my_azure_open_ai_vectorizer" 
	    }
	]
	```
4. Assign a vector profile to a vector field. The following example shows a fields collection with the required key field, a title string field, and two vector fields with a vector profile assignment.
	```json
	"fields": [ 
	        { 
	            "name": "ID", 
	            "type": "Edm.String", 
	            "key": true, 
	            "sortable": true, 
	            "analyzer": "keyword" 
	        }, 
	        { 
	            "name": "title", 
	            "type": "Edm.String"
	        }, 
	        { 
	            "name": "vector", 
	            "type": "Collection(Edm.Single)", 
	            "dimensions": 1536, 
	            "vectorSearchProfile": "my_vector_profile", 
	            "searchable": true, 
	            "retrievable": true
	        }, 
	        { 
	            "name": "my-second-vector", 
	            "type": "Collection(Edm.Single)", 
	            "dimensions": 1024, 
	            "vectorSearchProfile": "my_vector_profile", 
	            "searchable": true, 
	            "retrievable": true
	        }
	]
	```

Use a search client to send a query through a vectorizer. This example assumes Visual Studio Code with a REST client and a [sample index](https://learn.microsoft.com/en-us/azure/search/#try-a-vectorizer-with-sample-data).

1. In Visual Studio Code, provide a search endpoint and [search query API key](https://learn.microsoft.com/en-us/azure/search/search-security-api-keys#find-existing-keys):
	```
	@baseUrl: 
	 @queryApiKey: 00000000000000000000000
	```
2. Paste in a [vector query request](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-query).
	```
	### Run a query
	 POST {{baseUrl}}/indexes/vector-nasa-ebook-txt/docs/search?api-version=2024-07-01 HTTP/1.1
	     Content-Type: application/json
	     api-key: {{queryApiKey}}
	     {
	         "count": true,
	         "select": "title,chunk",
	         "vectorQueries": [
	             {
	                 "kind": "text",
	                 "text": "what cloud formations exists in the troposphere",
	                 "fields": "vector",
	                 "k": 3,
	                 "exhaustive": true
	             }
	         ]
	     }
	```
	Key points about the query include:
	- `"kind": "text"` tells the search engine that the input is a text string, and to use the vectorizer associated with the search field.
	- `"text": "what cloud formations exists in the troposphere"` is the text string to vectorize.
	- `"fields": "vector"` is the name of the field to query over. If you use the sample index produced by the wizard, the generated vector field is named `vector`.
3. Send the request. You should get three `k` results, where the first result is the most relevant.

Notice that there are no vectorizer properties to set at query time. The query reads the vectorizer properties, as per the vector profile field assignment in the index.

## Check logs

If you enabled diagnostic logging for your search service, run a Kusto query to confirm query execution on your vector field:

```
OperationEvent
| where TIMESTAMP > ago(30m)
| where Name == "Query.Search" and AdditionalInfo["QueryMetadata"]["Vectors"] has "TextLength"
```

## Best practices

If you're setting up an Azure OpenAI vectorizer, consider the same [best practices](https://learn.microsoft.com/en-us/azure/search/cognitive-search-skill-azure-openai-embedding#best-practices) that we recommend for the Azure OpenAI embedding skill.

## See also

- [Integrated vectorization (preview)](https://learn.microsoft.com/en-us/azure/search/vector-search-integrated-vectorization)

---

## Additional resources

Training

Module

[Perform vector search and retrieval in Azure AI Search - Training](https://learn.microsoft.com/en-us/training/modules/improve-search-results-vector-search/?source=recommendations)

Perform vector search and retrieval in Azure AI Search.

Certification

[Microsoft Certified: Azure AI Engineer Associate - Certifications](https://learn.microsoft.com/en-us/credentials/certifications/azure-ai-engineer/?source=recommendations)

Design and implement an Azure AI solution using Azure AI services, Azure AI Search, and Azure Open AI.
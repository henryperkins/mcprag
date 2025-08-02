---
title: "Integrated Vectorization Using REST APIs - Azure AI Search"
source: "https://learn.microsoft.com/en-us/azure/search/search-how-to-integrated-vectorization?tabs=prepare-data-storage%2Cprepare-model-aoai"
author:
  - "[[haileytap]]"
published:
created: 2025-07-31
description: "Learn how to use skills to automate data chunking and vectorization during indexing and query execution."
tags:
  - "clippings"
---
In this article, you learn how to use a skillset to chunk and vectorize content from a [supported data source](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#supported-data-sources). The skillset calls the [Text Split skill](https://learn.microsoft.com/en-us/azure/search/cognitive-search-skill-textsplit) or [Document Layout skill](https://learn.microsoft.com/en-us/azure/search/cognitive-search-skill-document-intelligence-layout) for chunking and an embedding skill that's attached to a [supported embedding model](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#supported-embedding-models) for chunk vectorization. You also learn how to store the chunked and vectorized content in a [vector index](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-create-index).

This article describes the end-to-end workflow for [integrated vectorization](https://learn.microsoft.com/en-us/azure/search/vector-search-integrated-vectorization) using REST. For portal-based instructions, see [Quickstart: Vectorize text and images in the Azure portal](https://learn.microsoft.com/en-us/azure/search/search-get-started-portal-import-vectors).

## Prerequisites

- An Azure account with an active subscription. [Create an account for free](https://azure.microsoft.com/free/?WT.mc_id=A261C142F).
- An [Azure AI Search service](https://learn.microsoft.com/en-us/azure/search/search-create-service-portal). We recommend the Basic tier or higher.
- A [supported data source](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#supported-data-sources).
- A [supported embedding model](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#supported-embedding-models).
- Completion of [Quickstart: Connect without keys](https://learn.microsoft.com/en-us/azure/search/search-get-started-rbac) and [Configure a system-assigned managed identity](https://learn.microsoft.com/en-us/azure/search/search-howto-managed-identities-data-sources#create-a-system-managed-identity). Although you can use key-based authentication for data plane operations, this article assumes [roles and managed identities](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#role-based-access), which are more secure.
- [Visual Studio Code](https://code.visualstudio.com/download) with a [REST client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client).

Integrated vectorization works with [all supported data sources](https://learn.microsoft.com/en-us/azure/search/search-indexer-overview#supported-data-sources). However, this article focuses on the most commonly used data sources, which are described in the following table.

| Supported data source | Description |
| --- | --- |
| [Azure Blob Storage](https://learn.microsoft.com/en-us/azure/search/search-howto-indexing-azure-blob-storage) | This data source works with blobs and tables. You must use a standard performance (general-purpose v2) account. Access tiers can be hot, cool, or cold. |
| [Azure Data Lake Storage (ADLS) Gen2](https://learn.microsoft.com/en-us/azure/storage/blobs/create-data-lake-storage-account) | This is an Azure Storage account with a hierarchical namespace enabled. To confirm that you have Data Lake Storage, check the **Properties** tab on the **Overview** page.      ![Screenshot of an Azure Data Lake Storage account in the Azure portal.](https://learn.microsoft.com/en-us/azure/search/media/search-how-to-integrated-vectorization/data-lake-storage-account.png)  Screenshot of an Azure Data Lake Storage account in the Azure portal. |

For integrated vectorization, you must use one of the following embedding models on an Azure AI platform. Deployment instructions are provided in a [later section](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#prepare-your-embedding-model).

| Provider | Supported models |
| --- | --- |
| [Azure OpenAI in Azure AI Foundry Models](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/create-resource) <sup>1, 2</sup> | text-embedding-ada-002   text-embedding-3-small   text-embedding-3-large |
| [Azure AI services multi-service resource](https://learn.microsoft.com/en-us/azure/ai-services/multi-service-resource#azure-ai-services-resource-for-azure-ai-search-skills) <sup>3</sup> | For text and images: [Azure AI Vision multimodal](https://learn.microsoft.com/en-us/azure/ai-services/computer-vision/how-to/image-retrieval) <sup>4</sup> |

<sup>1</sup> The endpoint of your Azure OpenAI resource must have a [custom subdomain](https://learn.microsoft.com/en-us/azure/ai-services/cognitive-services-custom-subdomains), such as `https://my-unique-name.openai.azure.com`. If you created your resource in the [Azure portal](https://portal.azure.com/), this subdomain was automatically generated during resource setup.

<sup>2</sup> Azure OpenAI resources (with access to embedding models) that were created in the [Azure AI Foundry portal](https://ai.azure.com/?cid=learnDocs) aren't supported. Only Azure OpenAI resources created in the Azure portal are compatible with the [Azure OpenAI Embedding skill](https://learn.microsoft.com/en-us/azure/search/cognitive-search-skill-azure-openai-embedding).

<sup>3</sup> For billing purposes, you must [attach your Azure AI multi-service resource](https://learn.microsoft.com/en-us/azure/search/cognitive-search-attach-cognitive-services) to the skillset in your Azure AI Search service. Unless you use a [keyless connection (preview)](https://learn.microsoft.com/en-us/azure/search/cognitive-search-attach-cognitive-services#bill-through-a-keyless-connection) to create the skillset, both resources must be in the same region.

<sup>4</sup> The Azure AI Vision multimodal embedding model is available in [select regions](https://learn.microsoft.com/en-us/azure/ai-services/computer-vision/overview-image-analysis#region-availability).

### Role-based access

You can use Microsoft Entra ID with role assignments or key-based authentication with full-access connection strings. For Azure AI Search connections to other resources, we recommend role assignments.

To configure role-based access for integrated vectorization:

1. On your search service, [enable roles](https://learn.microsoft.com/en-us/azure/search/search-security-enable-roles) and [configure a system-assigned managed identity](https://learn.microsoft.com/en-us/azure/search/search-howto-managed-identities-data-sources#create-a-system-managed-identity).
2. On your data source platform and embedding model provider, create role assignments that allow your search service to access data and models. See [Prepare your data](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#prepare-your-data) and [Prepare your embedding model](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#prepare-your-embedding-model).

In this section, you retrieve the endpoint and Microsoft Entra token for your Azure AI Search service. Both values are necessary to establish connections in REST requests.

1. Sign in to the [Azure portal](https://portal.azure.com/) and select your Azure AI Search service.
2. To obtain your search endpoint, copy the URL on the **Overview** page. An example search endpoint is `https://my-service.search.windows.net`.
3. To obtain your Microsoft Entra token, run the following command on your local system. This step requires completion of [Quickstart: Connect without keys](https://learn.microsoft.com/en-us/azure/search/search-get-started-rbac).
	```
	az account get-access-token --scope https://search.azure.com/.default --query accessToken --output tsv
	```

In this section, you prepare your data for integrated vectorization by uploading files to a [supported data source](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#supported-data-sources), assigning roles, and obtaining connection information.

- [Azure Blob Storage](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#tabpanel_1_prepare-data-storage)
- [ADLS Gen2](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#tabpanel_1_prepare-data-adlsgen2)

1. Sign in to the [Azure portal](https://portal.azure.com/) and select your Azure Storage account.
2. From the left pane, select **Data storage** > **Containers**.
3. Create a container or select an existing container, and then upload your files to the container.
4. To assign roles:
	1. From the left pane, select **Access Control (IAM)**.
	2. Select **Add** > **Add role assignment**.
	3. Under **Job function roles**, select **[Storage Blob Data Reader](https://learn.microsoft.com/en-us/azure/search/search-howto-managed-identities-data-sources#assign-a-role)**, and then select **Next**.
	4. Under **Members**, select **Managed identity**, and then select **Select members**.
	5. Select your subscription and the managed identity of your search service.
5. To obtain a connection string:
	1. From the left pane, select **Security + networking** > **Access keys**.
	2. Copy either connection string, which you specify later in [Set variables](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#set-variables).
6. (Optional) Synchronize deletions in your container with deletions in the search index. To configure your indexer for deletion detection:
	1. [Enable soft delete](https://learn.microsoft.com/en-us/azure/storage/blobs/soft-delete-blob-enable?tabs=azure-portal#enable-blob-soft-delete-hierarchical-namespace) on your storage account. If you're using [native soft delete](https://learn.microsoft.com/en-us/azure/search/search-howto-index-changed-deleted-blobs#native-blob-soft-delete), the next step isn't required.
	2. [Add custom metadata](https://learn.microsoft.com/en-us/azure/search/search-howto-index-changed-deleted-blobs#soft-delete-strategy-using-custom-metadata) that an indexer can scan to determine which blobs are marked for deletion. Give your custom property a descriptive name. For example, you can name the property "IsDeleted" and set it to false. Repeat this step for every blob in the container. When you want to delete the blob, change the property to true. For more information, see [Change and delete detection when indexing from Azure Storage](https://learn.microsoft.com/en-us/azure/search/search-howto-index-changed-deleted-blobs).

In this section, you prepare your Azure AI resource for integrated vectorization by assigning roles, obtaining an endpoint, and deploying a [supported embedding model](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#supported-embedding-models).

- [Azure OpenAI](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#tabpanel_2_prepare-model-aoai)
- [Azure AI Vision](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#tabpanel_2_prepare-model-ai-vision)

Azure AI Search supports text-embedding-ada-002, text-embedding-3-small, and text-embedding-3-large. Internally, Azure AI Search calls the [Azure OpenAI Embedding skill](https://learn.microsoft.com/en-us/azure/search/cognitive-search-skill-azure-openai-embedding) to connect to Azure OpenAI.

1. Sign in to the [Azure portal](https://portal.azure.com/) and select your Azure OpenAI resource.
2. To assign roles:
	1. From the left pane, select **Access control (IAM)**.
	2. Select **Add** > **Add role assignment**.
	3. Under **Job function roles**, select **[Cognitive Services OpenAI User](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/role-based-access-control#azure-openai-roles)**, and then select **Next**.
	4. Under **Members**, select **Managed identity**, and then select **Select members**.
	5. Select your subscription and the managed identity of your search service.
3. To obtain an endpoint:
	1. From the left pane, select **Resource Management** > **Keys and Endpoint**.
	2. Copy the endpoint for your Azure OpenAI resource. You specify this URL later in [Set variables](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#set-variables).
4. To deploy an embedding model:
	1. Sign in to the [Azure AI Foundry portal](https://ai.azure.com/?cid=learnDocs) and select your Azure OpenAI resource.
	2. From the left pane, select **Model catalog**.
	3. Deploy a [supported embedding model](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#supported-embedding-models).
	4. Copy the deployment and model names, which you specify later in [Set variables](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#set-variables). The deployment name is the custom name you chose, while the model name is the model you deployed, such as `text-embedding-ada-002`.

## Set variables

In this section, you specify the connection information for your Azure AI Search service, your [supported data source](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#supported-data-sources), and your [supported embedding model](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#supported-embedding-models).

1. In Visual Studio Code, paste the following placeholders into your `.rest` or `.http` file.
	```
	@baseUrl = PUT-YOUR-SEARCH-SERVICE-URL-HERE
	@token = PUT-YOUR-MICROSOFT-ENTRA-TOKEN-HERE
	```
2. Replace `@baseUrl` with the search endpoint and `@token` with the Microsoft Entra token you obtained in [Get connection information for Azure AI Search](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#get-connection-information-for-azure-ai-search).
3. Depending on your data source, add the following variables.
	| Data source | Variables | Enter this information |
	| --- | --- | --- |
	| Azure Blob Storage | `@storageConnectionString` and `@blobContainer` | The connection string and the name of the container you created in [Prepare your data](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#prepare-your-data). |
	| ADLS Gen2 | `@storageConnectionString` and `@blobContainer` | The connection string and the name of the container you created in [Prepare your data](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#prepare-your-data). |
4. Depending on your embedding model provider, add the following variables.
	| Embedding model provider | Variables | Enter this information |
	| --- | --- | --- |
	| Azure OpenAI | `@aoaiEndpoint`, `@aoaiDeploymentName`, and `@aoaiModelName` | The endpoint, deployment name, and model name you obtained in [Prepare your embedding model](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#prepare-your-embedding-model). |
	| Azure AI Vision | `@aiMultiServiceEndpoint` | The endpoint you obtained in [Prepare your embedding model](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#prepare-your-embedding-model). |
5. To verify the variables, send the following request.
	```
	### List existing indexes by name
	GET {{baseUrl}}/indexes?api-version=2024-07-01  HTTP/1.1
	  Content-Type: application/json
	  Authorization: Bearer {{token}}
	```
	A response should appear in an adjacent pane. If you have existing indexes, they're listed. Otherwise, the list is empty. If the HTTP code is `200 OK`, you're ready to proceed.

In this section, you connect to a [supported data source](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#supported-data-sources) for indexer-based indexing. An [indexer](https://learn.microsoft.com/en-us/azure/search/search-indexer-overview) in Azure AI Search requires a data source that specifies the type, credentials, and container.

1. Use [Create Data Source](https://learn.microsoft.com/en-us/rest/api/searchservice/data-sources/create) to define a data source that provides connection information during indexing.
	```
	### Create a data source
	POST {{baseUrl}}/datasources?api-version=2024-07-01  HTTP/1.1
	  Content-Type: application/json
	  Authorization: Bearer {{token}}
	  {
	    "name": "my-data-source",
	    "type": "azureblob",
	    "subtype": null,
	    "credentials": {
	        "connectionString": "{{storageConnectionString}}"
	    },
	    "container": {
	        "name": "{{blobContainer}}",
	        "query": null
	    },
	    "dataChangeDetectionPolicy": null,
	    "dataDeletionDetectionPolicy": null
	  }
	```
2. Set `type` to your data source: `azureblob` or `adlsgen2`.
3. To create the data source, select **Send request**.

In this section, you create a [skillset](https://learn.microsoft.com/en-us/azure/search/cognitive-search-working-with-skillsets) that calls a built-in skill to chunk your content and an embedding skill to create vector representations of the chunks. The skillset is executed during indexing in a [later section](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#create-an-indexer).

Partitioning your content into chunks helps you meet the requirements of your embedding model and prevents data loss due to truncation. For more information about chunking, see [Chunk large documents for vector search solutions](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-chunk-documents).

For built-in data chunking, Azure AI Search offers the [Text Split skill](https://learn.microsoft.com/en-us/azure/search/cognitive-search-skill-textsplit) and [Document Layout skill](https://learn.microsoft.com/en-us/azure/search/cognitive-search-skill-document-intelligence-layout). The Text Split skill breaks text into sentences or pages of a particular length, while the Document Layout skill breaks content based on paragraph boundaries.

1. Use [Create Skillset](https://learn.microsoft.com/en-us/rest/api/searchservice/skillsets/create) to define a skillset.
	```
	### Create a skillset
	POST {{baseUrl}}/skillsets?api-version=2024-07-01  HTTP/1.1
	  Content-Type: application/json
	  Authorization: Bearer {{token}}
	  {
	    "name": "my-skillset",
	    "skills": []
	  }
	```
2. In the `skills` array, call the Text Split skill or Document Layout skill. You can paste one of the following definitions.
	```
	"skills": [
	     {
	       "@odata.type": "#Microsoft.Skills.Text.SplitSkill",
	       "name": "my-text-split-skill",
	       "textSplitMode": "pages",
	       "maximumPageLength": 2000,
	       "pageOverlapLength": 500,
	       "maximumPagesToTake": 0,
	       "unit": "characters",
	       "defaultLanguageCode": "en",
	       "inputs": [
	        {
	          "name": "text",
	          "source": "/document/text",
	          "inputs": []
	        }
	       ],
	       "outputs": [
	        {
	          "name": "textItems"
	        }
	       ]
	     },
	     {
	       "@odata.type": "#Microsoft.Skills.Util.DocumentIntelligenceLayoutSkill",
	       "name": "my-document-layout-skill",
	       "context": "/document",
	       "outputMode": "oneToMany",
	       "markdownHeaderDepth": "h3",
	       "inputs": [
	        {
	          "name": "file_data",
	          "source": "/document/file_data"
	        }
	       ],
	       "outputs": [
	        {
	          "name": "markdown_document"
	        }
	       ]
	     }
	    ]
	```

To vectorize your chunked content, the skillset needs an embedding skill that points to a [supported embedding model](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#supported-embedding-models).

1. After the built-in chunking skill in the `skills` array, call the [Azure OpenAI Embedding skill](https://learn.microsoft.com/en-us/azure/search/cognitive-search-skill-azure-openai-embedding) or [Azure AI Vision skill](https://learn.microsoft.com/en-us/azure/search/cognitive-search-skill-vision-vectorize). You can paste one of the following definitions.
	```
	{
	       "@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill",
	       "resourceUri": "{{aoaiEndpoint}}",
	       "deploymentId": "{{aoaiDeploymentName}}",
	       "modelName": "{{aoaiModelName}}",
	       "dimensions": 1536,
	       "inputs": [
	         {
	           "name": "text",
	           "source": "/document/text"
	         }
	       ],
	       "outputs": [
	         {
	           "name": "embedding"
	         }
	       ]
	     },
	     {
	       "@odata.type": "#Microsoft.Skills.Vision.VectorizeSkill",
	       "context": "/document",
	       "modelVersion": "2023-04-15", 
	       "inputs": [
	         {
	           "name": "url",
	           "source": "/document/metadata_storage_path"
	         },
	         {
	           "name": "queryString",
	           "source": "/document/metadata_storage_sas_token"
	         }
	       ],
	       "outputs": [
	         {
	           "name": "vector"
	         }
	       ]
	     }
	```
2. If you're using the Azure OpenAI Embedding skill, set `dimensions` to the [number of embeddings generated by your embedding model](https://learn.microsoft.com/en-us/azure/search/cognitive-search-skill-azure-openai-embedding#supported-dimensions-by-modelname).
3. If you're using the Azure AI Vision skill, [attach your Azure AI multi-service resource](https://learn.microsoft.com/en-us/azure/search/cognitive-search-attach-cognitive-services) after the `skills` array. This attachment is for billing purposes.
	```
	"skills": [ ... ],
	    "cognitiveServices": {
	      "@odata.type": "#Microsoft.Azure.Search.AIServicesByIdentity",
	      "subdomainUrl": "{{aiMultiServiceEndpoint}}"
	     }
	```
4. To create the skillset, select **Send request**.

In this section, you set up physical data structures on your Azure AI Search service by creating a [vector index](https://learn.microsoft.com/en-us/azure/search/vector-store). The schema of a vector index requires the following:

- Name
- Key field (string)
- One or more vector fields
- Vector configuration

Vector fields store numerical representations of your chunked data. They must be searchable and retrievable, but they can't be filterable, facetable, or sortable. They also can't have analyzers, normalizers, or synonym map assignments.

In addition to vector fields, the sample index in the following steps contains nonvector fields for human-readable content. It's common to include plain-text equivalents of the content you want to vectorize. For more information, see [Create a vector index](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-create-index).

1. Use [Create Index](https://learn.microsoft.com/en-us/rest/api/searchservice/indexes/create) to define the schema of a vector index.
	```
	### Create a vector index
	POST {{baseUrl}}/indexes?api-version=2024-07-01  HTTP/1.1
	  Content-Type: application/json
	  Authorization: Bearer {{token}}
	  {
	    "name": "my-vector-index",
	    "fields": [],
	    "vectorSearch": []
	  }
	```
2. Add a [vector search configuration](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-create-index#add-a-vector-search-configuration) to the `vectorSearch` section.
	```
	"vectorSearch": {
	      "algorithms": [
	        {
	          "name": "hnsw-algorithm",
	          "kind": "hnsw",
	          "hnswParameters": {
	            "m": 4,
	            "efConstruction": 400,
	            "efSearch": 100,
	            "metric": "cosine"
	          }
	        }
	      ],
	      "profiles": [
	        {
	          "name": "vector-profile-hnsw",
	          "algorithm": "hnsw-algorithm",
	        }
	      ]
	    }
	```
	`vectorSearch.algorithms` specifies the algorithm used for indexing and querying vector fields, while `vectorSearch.profiles` links the algorithm configuration to a profile you can assign to vector fields.
3. Depending on your embedding model, update `vectorSearch.algorithms.metric`. [Valid values for distance metrics](https://learn.microsoft.com/en-us/rest/api/searchservice/indexes/create-or-update#vectorsearchalgorithmmetric) are `cosine`, `dotproduct`, `euclidean`, and `hamming`.
4. Add fields to the `fields` arrays. Include a key field for document identification, nonvector fields for human-readable content, and vector fields for embeddings.
	```
	"fields": [
	      {
	        "name": "id",
	        "type": "Edm.String",
	        "key": true,
	        "filterable": true
	      },
	      {
	        "name": "title",
	        "type": "Edm.String",
	         "searchable": true,
	         "filterable": true,
	         "sortable": true,
	         "retrievable": true
	      },
	      {
	        "name": "titleVector",
	        "type": "Collection(Edm.Single)",
	         "searchable": true,
	         "retrievable": false,
	         "stored": true,
	         "dimensions": 1536,
	         "vectorSearchProfile": "vector-profile-hnsw"
	      },
	      {
	        "name": "content",
	        "type": "Edm.String",
	         "searchable": true,
	         "retrievable": true
	      },
	      {
	        "name": "contentVector",
	        "type": "Collection(Edm.Single)",
	         "searchable": true,
	         "retrievable": false,
	         "stored": false,
	         "dimensions": 1536,
	         "vectorSearchProfile": "vector-profile-hnsw"
	      }
	    ]
	```
5. Depending on your embedding skill, set `dimensions` for each vector field to the following value.
	| Embedding skill | Enter this value |
	| --- | --- |
	| Azure OpenAI | The [number of embeddings generated by your embedding model](https://learn.microsoft.com/en-us/azure/search/cognitive-search-skill-azure-openai-embedding#supported-dimensions-by-modelname). |
	| Azure AI Vision | `1024` |

In this section, you enable vectorization at query time by [defining a vectorizer](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-configure-vectorizer) in your index. The vectorizer uses the embedding model that indexes your data to decode a search string or image into a vector for vector search.

1. Add the [Azure OpenAI vectorizer](https://learn.microsoft.com/en-us/azure/search/vector-search-vectorizer-azure-open-ai) or [Azure AI Vision vectorizer](https://learn.microsoft.com/en-us/azure/search/vector-search-vectorizer-ai-services-vision) after `vectorSearch.profiles`. You can paste one of the following definitions.
	```
	"profiles": [ ... ],
	      "vectorizers": [
	        {
	          "name": "my-openai-vectorizer",
	          "kind": "azureOpenAI",
	          "azureOpenAIParameters": {
	            "resourceUri": "{{aoaiEndpoint}}",
	            "deploymentId": "{{aoaiDeploymentName}}",
	            "modelName": "{{aoaiModelName}}"
	          }
	        },
	        {
	          "name": "my-ai-services-vision-vectorizer",
	          "kind": "aiServicesVision",
	          "aiServicesVisionParameters": {
	            "resourceUri": "{{aiMultiServiceEndpoint}}",
	            "modelVersion": "2023-04-15"
	          }
	        }
	      ]
	```
2. Specify your vectorizer in `vectorSearch.profiles`.
	```
	"profiles": [
	        {
	          "name": "vector-profile-hnsw",
	          "algorithm": "hnsw-algorithm",
	          "vectorizer": "my-openai-vectorizer"
	        }
	      ]
	```
3. To create the vector index, select **Send request**.

In this section, you create an [indexer](https://learn.microsoft.com/en-us/azure/search/search-indexer-overview) to drive the entire vectorization pipeline, from data retrieval to skillset execution to indexing. We recommend that you [run the indexer on a schedule](https://learn.microsoft.com/en-us/azure/search/search-howto-schedule-indexers) to process changes or documents that were missed due to throttling.

1. Use [Create Indexer](https://learn.microsoft.com/en-us/rest/api/searchservice/indexers/create) to define an indexer that executes the vectorization pipeline.
	```
	### Create an indexer
	POST {{baseUrl}}/indexers?api-version=2024-07-01  HTTP/1.1
	  Content-Type: application/json
	  Authorization: Bearer {{token}}
	  {
	    "name": "my-indexer",
	    "dataSourceName": "my-data-source",
	    "targetIndexName": "my-vector-index",
	    "skillsetName": "my-skillset",
	    "schedule": {
	      "interval": "PT2H"
	    },
	    "parameters": {
	      "batchSize": null,
	      "maxFailedItems": null,
	      "maxFailedItemsPerBatch": null
	    }
	  }
	```
2. To create the indexer, select **Send request**.

In this section, you verify that your content was successfully indexed by [creating a vector query](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-query). Because you configured a vectorizer in a [previous section](https://learn.microsoft.com/en-us/azure/search/?tabs=prepare-data-storage%2Cprepare-model-aoai#add-a-vectorizer-to-the-index), the search engine can decode plain text or an image into a vector for query execution.

1. Use [Documents - Search Post](https://learn.microsoft.com/en-us/rest/api/searchservice/documents/search-post) to define a query that's vectorized at query time.
	```
	### Run a vector query
	POST {{baseUrl}}/indexes('my-vector-index')/docs/search.post.search?api-version=2024-07-01  HTTP/1.1
	  Content-Type: application/json
	  Authorization: Bearer {{token}}
	  {
	    "count": true,
	    "select": "title, content",
	    "vectorQueries": [
	        {
	          "kind": "text",
	          "text": "a sample text string for integrated vectorization",
	          "fields": "titleVector, contentVector",
	          "k": "3"
	        }
	    ]
	  }
	```
	For queries that invoke integrated vectorization, `kind` must be set to `text`, and `text` must specify a text string. This string is passed to the vectorizer assigned to the vector field. For more information, see [Query with integrated vectorization](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-query#query-with-integrated-vectorization).
2. To run the vector query, select **Send request**.
- [Integrated vectorization in Azure AI Search](https://learn.microsoft.com/en-us/azure/search/vector-search-integrated-vectorization)
- [Quickstart: Vectorize text and images in the Azure portal](https://learn.microsoft.com/en-us/azure/search/search-get-started-portal-import-vectors)
- [Python sample for integrated vectorization](https://github.com/Azure/azure-search-vector-samples/blob/main/demo-python/code/integrated-vectorization/azure-search-integrated-vectorization-sample.ipynb)

---

## Additional resources

Training

Module

[Perform vector search and retrieval in Azure AI Search - Training](https://learn.microsoft.com/en-us/training/modules/improve-search-results-vector-search/?source=recommendations)

Perform vector search and retrieval in Azure AI Search.

Certification

[Microsoft Certified: Azure AI Engineer Associate - Certifications](https://learn.microsoft.com/en-us/credentials/certifications/azure-ai-engineer/?source=recommendations)

Design and implement an Azure AI solution using Azure AI services, Azure AI Search, and Azure Open AI.
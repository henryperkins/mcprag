## Custom Web API vectorizer

The **custom web API** vectorizer allows you to configure your search queries to call out to a Web API endpoint to generate embeddings at query time. The structure of the JSON payload required to be implemented in the provided endpoint is described further down in this document. Your data is processed in the [Geo](https://azure.microsoft.com/explore/global-infrastructure/data-residency/) where your model is deployed.

Vectorizers are used at query time, but specified in index definitions, and referenced on vector fields through a vector profile. The custom web API vectorizer is called `WebApiVectorizer` in the API.

- Use the [**2024-07-01**](https://learn.microsoft.com/en-us/rest/api/searchservice/indexes/create) REST API or an Azure SDK package that's been updated to provide the feature.
- [Configure a vectorizer in a search index](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-configure-vectorizer) provides usage instructions.

## Vectorizer parameters

Parameters are case-sensitive.

| Parameter name | Description |
| --- | --- |
| `uri` | The URI of the Web API to which the JSON payload is sent. Only the **https** URI scheme is allowed. |
| `httpMethod` | The method to use while sending the payload. Allowed methods are `PUT` or `POST` |
| `httpHeaders` | A collection of key-value pairs where the keys represent header names and values represent header values that are sent to your Web API along with the payload. The following headers are prohibited from being in this collection: `Accept`, `Accept-Charset`, `Accept-Encoding`, `Content-Length`, `Content-Type`, `Cookie`, `Host`, `TE`, `Upgrade`, `Via`. |
| `authResourceId` | (Optional) A string that if set, indicates that this vectorizer should use a managed identity on the connection to the function or app hosting the code. This property takes an application (client) ID or app's registration in Microsoft Entra ID, in any of these formats: `api://<appId>`, `<appId>/.default`, `api://<appId>/.default`. This value is used to scope the authentication token retrieved by the indexer, and is sent along with the custom Web API request to the function or app. Setting this property requires that your search service is [configured for managed identity](https://learn.microsoft.com/en-us/azure/search/search-howto-managed-identities-data-sources) and your Azure function app is [configured for a Microsoft Entra sign in](https://learn.microsoft.com/en-us/azure/app-service/configure-authentication-provider-aad). |
| `authIdentity` | (Optional) A user-managed identity used by the search service for connecting to the function or app hosting the code. You can use either a [system or user managed identity](https://learn.microsoft.com/en-us/azure/search/search-howto-managed-identities-data-sources). To use a system managed identity, leave `authIdentity` blank. |
| `timeout` | (Optional) When specified, indicates the timeout for the http client making the API call. It must be formatted as an XSD "dayTimeDuration" value (a restricted subset of an [ISO 8601 duration](https://www.w3.org/TR/xmlschema11-2/#dayTimeDuration) value). For example, `PT60S` for 60 seconds. If not set, a default value of 30 seconds is chosen. The timeout can be set to a maximum of 230 seconds and a minimum of 1 second. |

The Custom Web API vectorizer supports `text`, `imageUrl`, and `imageBinary` vector queries.

## Sample definition

```json
"vectorizers": [
    {
        "name": "my-custom-web-api-vectorizer",
        "kind": "customWebApi",
        "customWebApiParameters": {
            "uri": "https://contoso.embeddings.com",
            "httpMethod": "POST",
            "httpHeaders": {
                "api-key": "0000000000000000000000000000000000000"
            },
            "timeout": "PT60S",
            "authResourceId": null,
            "authIdentity": null
        },
    }
]
```

The required JSON payload structure that is expected for an endpoint when using it with the custom web API vectorizer is the same as that of the custom web API skill, which is discussed in more detail in [the documentation for the skill](https://learn.microsoft.com/en-us/azure/search/cognitive-search-custom-skill-web-api#sample-input-json-structure).

There are the following other considerations to make when implementing a web API endpoint to use with the custom web API vectorizer.

- The vectorizer sends only one record at a time in the `values` array when making a request to the endpoint.
- The vectorizer passes the data to be vectorized in a specific key in the `data` JSON object in the request payload. That key is `text`, `imageUrl`, or `imageBinary`, depending on which type of vector query was requested.
- The vectorizer expects the resulting embedding to be under the `vector` key in the `data` JSON object in the response payload.
- Any errors or warnings returned by the endpoint are ignored by the vectorizer and not obtainable for debugging purposes at query time.
- If an `imageBinary` vector query was requested, the request payload sent to the endpoint is the following:
	```json
	{
	    "values": [
	        {
	            "recordId": "0",
	            "data":
	            {
	                "imageBinary": {
	                    "data": "<base 64 encoded image binary data>"
	                }
	            }
	        }
	    ]
	}
	```

## See also

- [Integrated vectorization](https://learn.microsoft.com/en-us/azure/search/vector-search-integrated-vectorization)
- [How to configure a vectorizer in a search index](https://learn.microsoft.com/en-us/azure/search/vector-search-how-to-configure-vectorizer)
- [Custom Web API skill](https://learn.microsoft.com/en-us/azure/search/cognitive-search-custom-skill-web-api)
- [Hugging Face Embeddings Generator power skill (can be used for a custom web API vectorizer as well)](https://github.com/Azure-Samples/azure-search-power-skills/tree/main/Vector/EmbeddingGenerator)
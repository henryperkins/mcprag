## In this article

1. [URI Parameters](#uri-parameters)
2. [Request Header](#request-headers)
3. [Request Body](#request-body)
4. [Responses](#response)
5. [Examples](#examples)
6. [Definitions](#definitions)

Creates a new search index.

```
POST {endpoint}/indexes?api-version=2024-07-01
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
|fields|True|[SearchField](#searchfield)[]|The fields of the index.|
|name|True|string|The name of the index.|
|@odata.etag||string|The ETag of the index.|
|analyzers||LexicalAnalyzer[]:<br><br>- [CustomAnalyzer](#customanalyzer)[]<br>- [PatternAnalyzer](#patternanalyzer)[]<br>- [LuceneStandardAnalyzer](#lucenestandardanalyzer)[]<br>- [StopAnalyzer](#stopanalyzer)[]|The analyzers for the index.|
|charFilters||CharFilter[]:<br><br>- [MappingCharFilter](#mappingcharfilter)[]<br>- [PatternReplaceCharFilter](#patternreplacecharfilter)[]|The character filters for the index.|
|corsOptions||[CorsOptions](#corsoptions)|Options to control Cross-Origin Resource Sharing (CORS) for the index.|
|defaultScoringProfile||string|The name of the scoring profile to use if none is specified in the query. If this property is not set and no scoring profile is specified in the query, then default scoring (tf-idf) will be used.|
|encryptionKey||[SearchResourceEncryptionKey](#searchresourceencryptionkey)|A description of an encryption key that you create in Azure Key Vault. This key is used to provide an additional level of encryption-at-rest for your data when you want full assurance that no one, not even Microsoft, can decrypt your data. Once you have encrypted your data, it will always remain encrypted. The search service will ignore attempts to set this property to null. You can change this property as needed if you want to rotate your encryption key; Your data will be unaffected. Encryption with customer-managed keys is not available for free search services, and is only available for paid services created on or after January 1, 2019.|
|scoringProfiles||[ScoringProfile](#scoringprofile)[]|The scoring profiles for the index.|
|semantic||[SemanticSettings](#semanticsettings)|Defines parameters for a search index that influence semantic capabilities.|
|similarity||Similarity:<br><br>- [ClassicSimilarity](#classicsimilarity)<br>- [BM25Similarity](#bm25similarity)|The type of similarity algorithm to be used when scoring and ranking the documents matching a search query. The similarity algorithm can only be defined at index creation time and cannot be modified on existing indexes. If null, the ClassicSimilarity algorithm is used.|
|suggesters||[Suggester](#suggester)[]|The suggesters for the index.|
|tokenFilters||TokenFilter[]:<br><br>- [AsciiFoldingTokenFilter](#asciifoldingtokenfilter)[]<br>- [CjkBigramTokenFilter](#cjkbigramtokenfilter)[]<br>- [CommonGramTokenFilter](#commongramtokenfilter)[]<br>- [DictionaryDecompounderTokenFilter](#dictionarydecompoundertokenfilter)[]<br>- [EdgeNGramTokenFilter](#edgengramtokenfilter)[]<br>- [EdgeNGramTokenFilterV2](#edgengramtokenfilterv2)[]<br>- [ElisionTokenFilter](#elisiontokenfilter)[]<br>- [KeepTokenFilter](#keeptokenfilter)[]<br>- [KeywordMarkerTokenFilter](#keywordmarkertokenfilter)[]<br>- [LengthTokenFilter](#lengthtokenfilter)[]<br>- [LimitTokenFilter](#limittokenfilter)[]<br>- [NGramTokenFilter](#ngramtokenfilter)[]<br>- [NGramTokenFilterV2](#ngramtokenfilterv2)[]<br>- [PatternCaptureTokenFilter](#patterncapturetokenfilter)[]<br>- [PatternReplaceTokenFilter](#patternreplacetokenfilter)[]<br>- [PhoneticTokenFilter](#phonetictokenfilter)[]<br>- [ShingleTokenFilter](#shingletokenfilter)[]<br>- [SnowballTokenFilter](#snowballtokenfilter)[]<br>- [StemmerTokenFilter](#stemmertokenfilter)[]<br>- [StemmerOverrideTokenFilter](#stemmeroverridetokenfilter)[]<br>- [StopwordsTokenFilter](#stopwordstokenfilter)[]<br>- [SynonymTokenFilter](#synonymtokenfilter)[]<br>- [TruncateTokenFilter](#truncatetokenfilter)[]<br>- [UniqueTokenFilter](#uniquetokenfilter)[]<br>- [WordDelimiterTokenFilter](#worddelimitertokenfilter)[]|The token filters for the index.|
|tokenizers||LexicalTokenizer[]:<br><br>- [ClassicTokenizer](#classictokenizer)[]<br>- [EdgeNGramTokenizer](#edgengramtokenizer)[]<br>- [KeywordTokenizer](#keywordtokenizer)[]<br>- [KeywordTokenizerV2](#keywordtokenizerv2)[]<br>- [MicrosoftLanguageTokenizer](#microsoftlanguagetokenizer)[]<br>- [MicrosoftLanguageStemmingTokenizer](#microsoftlanguagestemmingtokenizer)[]<br>- [NGramTokenizer](#ngramtokenizer)[]<br>- [PathHierarchyTokenizerV2](#pathhierarchytokenizerv2)[]<br>- [PatternTokenizer](#patterntokenizer)[]<br>- [LuceneStandardTokenizer](#lucenestandardtokenizer)[]<br>- [LuceneStandardTokenizerV2](#lucenestandardtokenizerv2)[]<br>- [UaxUrlEmailTokenizer](#uaxurlemailtokenizer)[]|The tokenizers for the index.|
|vectorSearch||[VectorSearch](#vectorsearch)|Contains configuration options related to vector search.|

## Responses

|Name|Type|Description|
|---|---|---|
|201 Created|[SearchIndex](#searchindex)||
|Other Status Codes|[ErrorResponse](#errorresponse)|Error response.|

## Examples

### SearchServiceCreateIndex

#### Sample request

- [HTTP](#tabpanel_1_HTTP)

```
POST https://myservice.search.windows.net/indexes?api-version=2024-07-01

{
  "name": "hotels",
  "fields": [
    {
      "name": "hotelId",
      "type": "Edm.String",
      "key": true,
      "searchable": false
    },
    {
      "name": "baseRate",
      "type": "Edm.Double"
    },
    {
      "name": "description",
      "type": "Edm.String",
      "filterable": false,
      "sortable": false,
      "facetable": false
    },
    {
      "name": "descriptionEmbedding",
      "type": "Collection(Edm.Single)",
      "searchable": true,
      "filterable": false,
      "retrievable": true,
      "sortable": false,
      "facetable": false,
      "key": false,
      "indexAnalyzer": null,
      "searchAnalyzer": null,
      "analyzer": null,
      "synonymMaps": [],
      "dimensions": 1536,
      "vectorSearchProfile": "myHnswSQProfile"
    },
    {
      "name": "descriptionEmbedding_notstored",
      "type": "Collection(Edm.Single)",
      "searchable": true,
      "filterable": false,
      "retrievable": false,
      "stored": false,
      "sortable": false,
      "facetable": false,
      "key": false,
      "indexAnalyzer": null,
      "searchAnalyzer": null,
      "analyzer": null,
      "synonymMaps": [],
      "dimensions": 1536,
      "vectorSearchProfile": "myHnswSQProfile"
    },
    {
      "name": "descriptionEmbedding_forBQ",
      "type": "Collection(Edm.Single)",
      "searchable": true,
      "filterable": false,
      "retrievable": true,
      "sortable": false,
      "facetable": false,
      "key": false,
      "indexAnalyzer": null,
      "searchAnalyzer": null,
      "analyzer": null,
      "synonymMaps": [],
      "dimensions": 1536,
      "vectorSearchProfile": "myHnswBQProfile"
    },
    {
      "name": "description_fr",
      "type": "Edm.String",
      "filterable": false,
      "sortable": false,
      "facetable": false,
      "analyzer": "fr.lucene"
    },
    {
      "name": "hotelName",
      "type": "Edm.String"
    },
    {
      "name": "nameEmbedding",
      "type": "Collection(Edm.Half)",
      "searchable": true,
      "filterable": false,
      "retrievable": true,
      "sortable": false,
      "facetable": false,
      "key": false,
      "indexAnalyzer": null,
      "searchAnalyzer": null,
      "analyzer": null,
      "synonymMaps": [],
      "dimensions": 1536,
      "vectorSearchProfile": "myHnswProfile"
    },
    {
      "name": "category",
      "type": "Edm.String"
    },
    {
      "name": "tags",
      "type": "Collection(Edm.String)",
      "analyzer": "tagsAnalyzer"
    },
    {
      "name": "parkingIncluded",
      "type": "Edm.Boolean"
    },
    {
      "name": "smokingAllowed",
      "type": "Edm.Boolean"
    },
    {
      "name": "lastRenovationDate",
      "type": "Edm.DateTimeOffset"
    },
    {
      "name": "rating",
      "type": "Edm.Int32"
    },
    {
      "name": "location",
      "type": "Edm.GeographyPoint"
    }
  ],
  "scoringProfiles": [
    {
      "name": "geo",
      "text": {
        "weights": {
          "hotelName": 5
        }
      },
      "functions": [
        {
          "type": "distance",
          "boost": 5,
          "fieldName": "location",
          "interpolation": "logarithmic",
          "distance": {
            "referencePointParameter": "currentLocation",
            "boostingDistance": 10
          }
        }
      ]
    }
  ],
  "defaultScoringProfile": "geo",
  "suggesters": [
    {
      "name": "sg",
      "searchMode": "analyzingInfixMatching",
      "sourceFields": [
        "hotelName"
      ]
    }
  ],
  "analyzers": [
    {
      "name": "tagsAnalyzer",
      "@odata.type": "#Microsoft.Azure.Search.CustomAnalyzer",
      "charFilters": [
        "html_strip"
      ],
      "tokenizer": "standard_v2"
    }
  ],
  "corsOptions": {
    "allowedOrigins": [
      "tempuri.org"
    ],
    "maxAgeInSeconds": 60
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
  "similarity": {
    "@odata.type": "#Microsoft.Azure.Search.BM25Similarity",
    "b": 0.5,
    "k1": 1.3
  },
  "semantic": {
    "configurations": [
      {
        "name": "semanticHotels",
        "prioritizedFields": {
          "titleField": {
            "fieldName": "hotelName"
          },
          "prioritizedContentFields": [
            {
              "fieldName": "description"
            },
            {
              "fieldName": "description_fr"
            }
          ],
          "prioritizedKeywordsFields": [
            {
              "fieldName": "tags"
            },
            {
              "fieldName": "category"
            }
          ]
        }
      }
    ]
  },
  "vectorSearch": {
    "profiles": [
      {
        "name": "myHnswProfile",
        "algorithm": "myHnsw"
      },
      {
        "name": "myHnswSQProfile",
        "algorithm": "myHnsw",
        "compression": "mySQ8"
      },
      {
        "name": "myHnswBQProfile",
        "algorithm": "myHnsw",
        "compression": "myBQ"
      },
      {
        "name": "myAlgorithm",
        "algorithm": "myExhaustive"
      }
    ],
    "algorithms": [
      {
        "name": "myHnsw",
        "kind": "hnsw",
        "hnswParameters": {
          "m": 4,
          "metric": "cosine"
        }
      },
      {
        "name": "myExhaustive",
        "kind": "exhaustiveKnn",
        "exhaustiveKnnParameters": {
          "metric": "cosine"
        }
      }
    ],
    "compressions": [
      {
        "name": "mySQ8",
        "kind": "scalarQuantization",
        "scalarQuantizationParameters": {
          "quantizedDataType": "int8"
        },
        "rerankWithOriginalVectors": true,
        "defaultOversampling": 10
      },
      {
        "name": "myBQ",
        "kind": "binaryQuantization",
        "rerankWithOriginalVectors": true,
        "defaultOversampling": 10
      }
    ]
  }
}

```

#### Sample response

```
{
  "name": "hotels",
  "fields": [
    {
      "name": "hotelId",
      "type": "Edm.String",
      "searchable": false,
      "filterable": true,
      "retrievable": true,
      "sortable": true,
      "facetable": true,
      "key": true,
      "indexAnalyzer": null,
      "searchAnalyzer": null,
      "analyzer": null,
      "dimensions": null,
      "vectorSearchProfile": null,
      "synonymMaps": []
    },
    {
      "name": "baseRate",
      "type": "Edm.Double",
      "searchable": false,
      "filterable": true,
      "retrievable": true,
      "sortable": true,
      "facetable": true,
      "key": false,
      "indexAnalyzer": null,
      "searchAnalyzer": null,
      "analyzer": null,
      "dimensions": null,
      "vectorSearchProfile": null,
      "synonymMaps": []
    },
    {
      "name": "description",
      "type": "Edm.String",
      "searchable": true,
      "filterable": false,
      "retrievable": true,
      "sortable": false,
      "facetable": false,
      "key": false,
      "indexAnalyzer": null,
      "searchAnalyzer": null,
      "analyzer": null,
      "dimensions": null,
      "vectorSearchProfile": null,
      "synonymMaps": []
    },
    {
      "name": "descriptionEmbedding",
      "type": "Collection(Edm.Single)",
      "searchable": true,
      "filterable": false,
      "retrievable": true,
      "sortable": false,
      "facetable": false,
      "key": false,
      "indexAnalyzer": null,
      "searchAnalyzer": null,
      "analyzer": null,
      "dimensions": 1536,
      "vectorSearchProfile": "myHnswSQProfile",
      "synonymMaps": []
    },
    {
      "name": "descriptionEmbedding_notstored",
      "type": "Collection(Edm.Single)",
      "searchable": true,
      "filterable": false,
      "retrievable": false,
      "stored": false,
      "sortable": false,
      "facetable": false,
      "key": false,
      "indexAnalyzer": null,
      "searchAnalyzer": null,
      "analyzer": null,
      "synonymMaps": [],
      "dimensions": 1536,
      "vectorSearchProfile": "myHnswSQProfile"
    },
    {
      "name": "descriptionEmbedding_forBQ",
      "type": "Collection(Edm.Single)",
      "searchable": true,
      "filterable": false,
      "retrievable": true,
      "sortable": false,
      "facetable": false,
      "key": false,
      "indexAnalyzer": null,
      "searchAnalyzer": null,
      "analyzer": null,
      "dimensions": 1536,
      "vectorSearchProfile": "myHnswBQProfile",
      "synonymMaps": []
    },
    {
      "name": "description_fr",
      "type": "Edm.String",
      "searchable": true,
      "filterable": false,
      "retrievable": true,
      "sortable": false,
      "facetable": false,
      "key": false,
      "indexAnalyzer": null,
      "searchAnalyzer": null,
      "analyzer": "fr.lucene",
      "dimensions": null,
      "vectorSearchProfile": null,
      "synonymMaps": []
    },
    {
      "name": "hotelName",
      "type": "Edm.String",
      "searchable": true,
      "filterable": true,
      "retrievable": true,
      "sortable": true,
      "facetable": true,
      "key": false,
      "indexAnalyzer": null,
      "searchAnalyzer": null,
      "analyzer": null,
      "dimensions": null,
      "vectorSearchProfile": null,
      "synonymMaps": []
    },
    {
      "name": "nameEmbedding",
      "type": "Collection(Edm.Half)",
      "searchable": true,
      "filterable": false,
      "retrievable": true,
      "sortable": false,
      "facetable": false,
      "key": false,
      "indexAnalyzer": null,
      "searchAnalyzer": null,
      "analyzer": null,
      "dimensions": 1536,
      "vectorSearchProfile": "myHnswProfile",
      "synonymMaps": []
    },
    {
      "name": "category",
      "type": "Edm.String",
      "searchable": true,
      "filterable": true,
      "retrievable": true,
      "sortable": true,
      "facetable": true,
      "key": false,
      "indexAnalyzer": null,
      "searchAnalyzer": null,
      "analyzer": null,
      "dimensions": null,
      "vectorSearchProfile": null,
      "synonymMaps": []
    },
    {
      "name": "tags",
      "type": "Collection(Edm.String)",
      "searchable": true,
      "filterable": true,
      "retrievable": true,
      "sortable": false,
      "facetable": true,
      "key": false,
      "indexAnalyzer": null,
      "searchAnalyzer": null,
      "analyzer": "tagsAnalyzer",
      "dimensions": null,
      "vectorSearchProfile": null,
      "synonymMaps": []
    },
    {
      "name": "parkingIncluded",
      "type": "Edm.Boolean",
      "searchable": false,
      "filterable": true,
      "retrievable": true,
      "sortable": true,
      "facetable": true,
      "key": false,
      "indexAnalyzer": null,
      "searchAnalyzer": null,
      "analyzer": null,
      "dimensions": null,
      "vectorSearchProfile": null,
      "synonymMaps": []
    },
    {
      "name": "smokingAllowed",
      "type": "Edm.Boolean",
      "searchable": false,
      "filterable": true,
      "retrievable": true,
      "sortable": true,
      "facetable": true,
      "key": false,
      "indexAnalyzer": null,
      "searchAnalyzer": null,
      "analyzer": null,
      "dimensions": null,
      "vectorSearchProfile": null,
      "synonymMaps": []
    },
    {
      "name": "lastRenovationDate",
      "type": "Edm.DateTimeOffset",
      "searchable": false,
      "filterable": true,
      "retrievable": true,
      "sortable": true,
      "facetable": true,
      "key": false,
      "indexAnalyzer": null,
      "searchAnalyzer": null,
      "analyzer": null,
      "dimensions": null,
      "vectorSearchProfile": null,
      "synonymMaps": []
    },
    {
      "name": "rating",
      "type": "Edm.Int32",
      "searchable": false,
      "filterable": true,
      "retrievable": true,
      "sortable": true,
      "facetable": true,
      "key": false,
      "indexAnalyzer": null,
      "searchAnalyzer": null,
      "analyzer": null,
      "dimensions": null,
      "vectorSearchProfile": null,
      "synonymMaps": []
    },
    {
      "name": "location",
      "type": "Edm.GeographyPoint",
      "searchable": false,
      "filterable": true,
      "retrievable": true,
      "sortable": true,
      "facetable": false,
      "key": false,
      "indexAnalyzer": null,
      "searchAnalyzer": null,
      "analyzer": null,
      "dimensions": null,
      "vectorSearchProfile": null,
      "synonymMaps": []
    }
  ],
  "scoringProfiles": [
    {
      "name": "geo",
      "functionAggregation": "sum",
      "text": {
        "weights": {
          "hotelName": 5
        }
      },
      "functions": [
        {
          "fieldName": "location",
          "interpolation": "logarithmic",
          "type": "distance",
          "boost": 5,
          "distance": {
            "referencePointParameter": "currentLocation",
            "boostingDistance": 10
          }
        }
      ]
    }
  ],
  "defaultScoringProfile": "geo",
  "suggesters": [
    {
      "name": "sg",
      "searchMode": "analyzingInfixMatching",
      "sourceFields": [
        "hotelName"
      ]
    }
  ],
  "analyzers": [
    {
      "name": "tagsAnalyzer",
      "@odata.type": "#Microsoft.Azure.Search.CustomAnalyzer",
      "charFilters": [
        "html_strip"
      ],
      "tokenFilters": [],
      "tokenizer": "standard_v2"
    }
  ],
  "tokenizers": [],
  "tokenFilters": [],
  "charFilters": [],
  "corsOptions": {
    "allowedOrigins": [
      "tempuri.org"
    ],
    "maxAgeInSeconds": 60
  },
  "encryptionKey": {
    "keyVaultKeyName": "myUserManagedEncryptionKey-createdinAzureKeyVault",
    "keyVaultKeyVersion": "myKeyVersion-32charAlphaNumericString",
    "keyVaultUri": "https://myKeyVault.vault.azure.net",
    "accessCredentials": {
      "applicationId": "00000000-0000-0000-0000-000000000000",
      "applicationSecret": null
    }
  },
  "similarity": {
    "@odata.type": "#Microsoft.Azure.Search.BM25Similarity",
    "b": 0.5,
    "k1": 1.3
  },
  "semantic": {
    "configurations": [
      {
        "name": "semanticHotels",
        "prioritizedFields": {
          "titleField": {
            "fieldName": "hotelName"
          },
          "prioritizedContentFields": [
            {
              "fieldName": "description"
            },
            {
              "fieldName": "description_fr"
            }
          ],
          "prioritizedKeywordsFields": [
            {
              "fieldName": "tags"
            },
            {
              "fieldName": "category"
            }
          ]
        }
      }
    ]
  },
  "vectorSearch": {
    "algorithms": [
      {
        "name": "myHnsw",
        "kind": "hnsw",
        "hnswParameters": {
          "metric": "cosine",
          "m": 4,
          "efConstruction": 400,
          "efSearch": 500
        }
      },
      {
        "name": "myExhaustive",
        "kind": "exhaustiveKnn",
        "exhaustiveKnnParameters": {
          "metric": "cosine"
        }
      }
    ],
    "profiles": [
      {
        "name": "myHnswProfile",
        "algorithm": "myHnsw"
      },
      {
        "name": "myHnswSQProfile",
        "algorithm": "myHnsw",
        "compression": "mySQ8"
      },
      {
        "name": "myHnswBQProfile",
        "algorithm": "myHnsw",
        "vectorizer": "myOpenAi",
        "compression": "myBQ"
      },
      {
        "name": "myAlgorithm",
        "algorithm": "myExhaustive"
      }
    ],
    "compressions": [
      {
        "name": "mySQ8",
        "kind": "scalarQuantization",
        "scalarQuantizationParameters": {
          "quantizedDataType": "int8"
        },
        "rerankWithOriginalVectors": true,
        "defaultOversampling": 10
      },
      {
        "name": "myBQ",
        "kind": "binaryQuantization",
        "rerankWithOriginalVectors": true,
        "defaultOversampling": 10
      }
    ]
  }
}
```

## Definitions

|Name|Description|
|---|---|
|[AsciiFoldingTokenFilter](#asciifoldingtokenfilter)|Converts alphabetic, numeric, and symbolic Unicode characters which are not in the first 127 ASCII characters (the "Basic Latin" Unicode block) into their ASCII equivalents, if such equivalents exist. This token filter is implemented using Apache Lucene.|
|[AzureActiveDirectoryApplicationCredentials](#azureactivedirectoryapplicationcredentials)|Credentials of a registered application created for your search service, used for authenticated access to the encryption keys stored in Azure Key Vault.|
|[AzureOpenAIEmbeddingSkill](#azureopenaiembeddingskill)|Allows you to generate a vector embedding for a given text input using the Azure OpenAI resource.|
|[AzureOpenAIModelName](#azureopenaimodelname)|The Azure Open AI model name that will be called.|
|[AzureOpenAIParameters](#azureopenaiparameters)|Specifies the parameters for connecting to the Azure OpenAI resource.|
|[AzureOpenAIVectorizer](#azureopenaivectorizer)|Specifies the Azure OpenAI resource used to vectorize a query string.|
|[BinaryQuantizationVectorSearchCompressionConfiguration](#binaryquantizationvectorsearchcompressionconfiguration)|Contains configuration options specific to the binary quantization compression method used during indexing and querying.|
|[BM25Similarity](#bm25similarity)|Ranking function based on the Okapi BM25 similarity algorithm. BM25 is a TF-IDF-like algorithm that includes length normalization (controlled by the 'b' parameter) as well as term frequency saturation (controlled by the 'k1' parameter).|
|[CharFilterName](#charfiltername)|Defines the names of all character filters supported by the search engine.|
|[CjkBigramTokenFilter](#cjkbigramtokenfilter)|Forms bigrams of CJK terms that are generated from the standard tokenizer. This token filter is implemented using Apache Lucene.|
|[CjkBigramTokenFilterScripts](#cjkbigramtokenfilterscripts)|Scripts that can be ignored by CjkBigramTokenFilter.|
|[ClassicSimilarity](#classicsimilarity)|Legacy similarity algorithm which uses the Lucene TFIDFSimilarity implementation of TF-IDF. This variation of TF-IDF introduces static document length normalization as well as coordinating factors that penalize documents that only partially match the searched queries.|
|[ClassicTokenizer](#classictokenizer)|Grammar-based tokenizer that is suitable for processing most European-language documents. This tokenizer is implemented using Apache Lucene.|
|[CommonGramTokenFilter](#commongramtokenfilter)|Construct bigrams for frequently occurring terms while indexing. Single terms are still indexed too, with bigrams overlaid. This token filter is implemented using Apache Lucene.|
|[CorsOptions](#corsoptions)|Defines options to control Cross-Origin Resource Sharing (CORS) for an index.|
|[CustomAnalyzer](#customanalyzer)|Allows you to take control over the process of converting text into indexable/searchable tokens. It's a user-defined configuration consisting of a single predefined tokenizer and one or more filters. The tokenizer is responsible for breaking text into tokens, and the filters for modifying tokens emitted by the tokenizer.|
|[DictionaryDecompounderTokenFilter](#dictionarydecompoundertokenfilter)|Decomposes compound words found in many Germanic languages. This token filter is implemented using Apache Lucene.|
|[DistanceScoringFunction](#distancescoringfunction)|Defines a function that boosts scores based on distance from a geographic location.|
|[DistanceScoringParameters](#distancescoringparameters)|Provides parameter values to a distance scoring function.|
|[EdgeNGramTokenFilter](#edgengramtokenfilter)|Generates n-grams of the given size(s) starting from the front or the back of an input token. This token filter is implemented using Apache Lucene.|
|[EdgeNGramTokenFilterSide](#edgengramtokenfilterside)|Specifies which side of the input an n-gram should be generated from.|
|[EdgeNGramTokenFilterV2](#edgengramtokenfilterv2)|Generates n-grams of the given size(s) starting from the front or the back of an input token. This token filter is implemented using Apache Lucene.|
|[EdgeNGramTokenizer](#edgengramtokenizer)|Tokenizes the input from an edge into n-grams of the given size(s). This tokenizer is implemented using Apache Lucene.|
|[ElisionTokenFilter](#elisiontokenfilter)|Removes elisions. For example, "l'avion" (the plane) will be converted to "avion" (plane). This token filter is implemented using Apache Lucene.|
|[ErrorAdditionalInfo](#erroradditionalinfo)|The resource management error additional info.|
|[ErrorDetail](#errordetail)|The error detail.|
|[ErrorResponse](#errorresponse)|Error response|
|[ExhaustiveKnnParameters](#exhaustiveknnparameters)|Contains the parameters specific to exhaustive KNN algorithm.|
|[ExhaustiveKnnVectorSearchAlgorithmConfiguration](#exhaustiveknnvectorsearchalgorithmconfiguration)|Contains configuration options specific to the exhaustive KNN algorithm used during querying, which will perform brute-force search across the entire vector index.|
|[FreshnessScoringFunction](#freshnessscoringfunction)|Defines a function that boosts scores based on the value of a date-time field.|
|[FreshnessScoringParameters](#freshnessscoringparameters)|Provides parameter values to a freshness scoring function.|
|[HnswParameters](#hnswparameters)|Contains the parameters specific to the HNSW algorithm.|
|[HnswVectorSearchAlgorithmConfiguration](#hnswvectorsearchalgorithmconfiguration)|Contains configuration options specific to the HNSW approximate nearest neighbors algorithm used during indexing and querying. The HNSW algorithm offers a tunable trade-off between search speed and accuracy.|
|[InputFieldMappingEntry](#inputfieldmappingentry)|Input field mapping for a skill.|
|[KeepTokenFilter](#keeptokenfilter)|A token filter that only keeps tokens with text contained in a specified list of words. This token filter is implemented using Apache Lucene.|
|[KeywordMarkerTokenFilter](#keywordmarkertokenfilter)|Marks terms as keywords. This token filter is implemented using Apache Lucene.|
|[KeywordTokenizer](#keywordtokenizer)|Emits the entire input as a single token. This tokenizer is implemented using Apache Lucene.|
|[KeywordTokenizerV2](#keywordtokenizerv2)|Emits the entire input as a single token. This tokenizer is implemented using Apache Lucene.|
|[LengthTokenFilter](#lengthtokenfilter)|Removes words that are too long or too short. This token filter is implemented using Apache Lucene.|
|[LexicalAnalyzerName](#lexicalanalyzername)|Defines the names of all text analyzers supported by the search engine.|
|[LexicalTokenizerName](#lexicaltokenizername)|Defines the names of all tokenizers supported by the search engine.|
|[LimitTokenFilter](#limittokenfilter)|Limits the number of tokens while indexing. This token filter is implemented using Apache Lucene.|
|[LuceneStandardAnalyzer](#lucenestandardanalyzer)|Standard Apache Lucene analyzer; Composed of the standard tokenizer, lowercase filter and stop filter.|
|[LuceneStandardTokenizer](#lucenestandardtokenizer)|Breaks text following the Unicode Text Segmentation rules. This tokenizer is implemented using Apache Lucene.|
|[LuceneStandardTokenizerV2](#lucenestandardtokenizerv2)|Breaks text following the Unicode Text Segmentation rules. This tokenizer is implemented using Apache Lucene.|
|[MagnitudeScoringFunction](#magnitudescoringfunction)|Defines a function that boosts scores based on the magnitude of a numeric field.|
|[MagnitudeScoringParameters](#magnitudescoringparameters)|Provides parameter values to a magnitude scoring function.|
|[MappingCharFilter](#mappingcharfilter)|A character filter that applies mappings defined with the mappings option. Matching is greedy (longest pattern matching at a given point wins). Replacement is allowed to be the empty string. This character filter is implemented using Apache Lucene.|
|[MicrosoftLanguageStemmingTokenizer](#microsoftlanguagestemmingtokenizer)|Divides text using language-specific rules and reduces words to their base forms.|
|[MicrosoftLanguageTokenizer](#microsoftlanguagetokenizer)|Divides text using language-specific rules.|
|[MicrosoftStemmingTokenizerLanguage](#microsoftstemmingtokenizerlanguage)|Lists the languages supported by the Microsoft language stemming tokenizer.|
|[MicrosoftTokenizerLanguage](#microsofttokenizerlanguage)|Lists the languages supported by the Microsoft language tokenizer.|
|[NGramTokenFilter](#ngramtokenfilter)|Generates n-grams of the given size(s). This token filter is implemented using Apache Lucene.|
|[NGramTokenFilterV2](#ngramtokenfilterv2)|Generates n-grams of the given size(s). This token filter is implemented using Apache Lucene.|
|[NGramTokenizer](#ngramtokenizer)|Tokenizes the input into n-grams of the given size(s). This tokenizer is implemented using Apache Lucene.|
|[OutputFieldMappingEntry](#outputfieldmappingentry)|Output field mapping for a skill.|
|[PathHierarchyTokenizerV2](#pathhierarchytokenizerv2)|Tokenizer for path-like hierarchies. This tokenizer is implemented using Apache Lucene.|
|[PatternAnalyzer](#patternanalyzer)|Flexibly separates text into terms via a regular expression pattern. This analyzer is implemented using Apache Lucene.|
|[PatternCaptureTokenFilter](#patterncapturetokenfilter)|Uses Java regexes to emit multiple tokens - one for each capture group in one or more patterns. This token filter is implemented using Apache Lucene.|
|[PatternReplaceCharFilter](#patternreplacecharfilter)|A character filter that replaces characters in the input string. It uses a regular expression to identify character sequences to preserve and a replacement pattern to identify characters to replace. For example, given the input text "aa bb aa bb", pattern "(aa)\s+(bb)", and replacement "$1#$2", the result would be "aa#bb aa#bb". This character filter is implemented using Apache Lucene.|
|[PatternReplaceTokenFilter](#patternreplacetokenfilter)|A character filter that replaces characters in the input string. It uses a regular expression to identify character sequences to preserve and a replacement pattern to identify characters to replace. For example, given the input text "aa bb aa bb", pattern "(aa)\s+(bb)", and replacement "$1#$2", the result would be "aa#bb aa#bb". This token filter is implemented using Apache Lucene.|
|[PatternTokenizer](#patterntokenizer)|Tokenizer that uses regex pattern matching to construct distinct tokens. This tokenizer is implemented using Apache Lucene.|
|[PhoneticEncoder](#phoneticencoder)|Identifies the type of phonetic encoder to use with a PhoneticTokenFilter.|
|[PhoneticTokenFilter](#phonetictokenfilter)|Create tokens for phonetic matches. This token filter is implemented using Apache Lucene.|
|[PrioritizedFields](#prioritizedfields)|Describes the title, content, and keywords fields to be used for semantic ranking, captions, highlights, and answers.|
|[RegexFlags](#regexflags)|Defines flags that can be combined to control how regular expressions are used in the pattern analyzer and pattern tokenizer.|
|[ScalarQuantizationParameters](#scalarquantizationparameters)|Contains the parameters specific to Scalar Quantization.|
|[ScalarQuantizationVectorSearchCompressionConfiguration](#scalarquantizationvectorsearchcompressionconfiguration)|Contains configuration options specific to the scalar quantization compression method used during indexing and querying.|
|[ScoringFunctionAggregation](#scoringfunctionaggregation)|Defines the aggregation function used to combine the results of all the scoring functions in a scoring profile.|
|[ScoringFunctionInterpolation](#scoringfunctioninterpolation)|Defines the function used to interpolate score boosting across a range of documents.|
|[ScoringProfile](#scoringprofile)|Defines parameters for a search index that influence scoring in search queries.|
|[SearchField](#searchfield)|Represents a field in an index definition, which describes the name, data type, and search behavior of a field.|
|[SearchFieldDataType](#searchfielddatatype)|Defines the data type of a field in a search index.|
|[SearchIndex](#searchindex)|Represents a search index definition, which describes the fields and search behavior of an index.|
|[SearchIndexerDataNoneIdentity](#searchindexerdatanoneidentity)|Clears the identity property of a datasource.|
|[SearchIndexerDataUserAssignedIdentity](#searchindexerdatauserassignedidentity)|Specifies the identity for a datasource to use.|
|[SearchResourceEncryptionKey](#searchresourceencryptionkey)|A customer-managed encryption key in Azure Key Vault. Keys that you create and manage can be used to encrypt or decrypt data-at-rest, such as indexes and synonym maps.|
|[SemanticConfiguration](#semanticconfiguration)|Defines a specific configuration to be used in the context of semantic capabilities.|
|[SemanticField](#semanticfield)|A field that is used as part of the semantic configuration.|
|[SemanticSettings](#semanticsettings)|Defines parameters for a search index that influence semantic capabilities.|
|[ShingleTokenFilter](#shingletokenfilter)|Creates combinations of tokens as a single token. This token filter is implemented using Apache Lucene.|
|[SnowballTokenFilter](#snowballtokenfilter)|A filter that stems words using a Snowball-generated stemmer. This token filter is implemented using Apache Lucene.|
|[SnowballTokenFilterLanguage](#snowballtokenfilterlanguage)|The language to use for a Snowball token filter.|
|[StemmerOverrideTokenFilter](#stemmeroverridetokenfilter)|Provides the ability to override other stemming filters with custom dictionary-based stemming. Any dictionary-stemmed terms will be marked as keywords so that they will not be stemmed with stemmers down the chain. Must be placed before any stemming filters. This token filter is implemented using Apache Lucene.|
|[StemmerTokenFilter](#stemmertokenfilter)|Language specific stemming filter. This token filter is implemented using Apache Lucene.|
|[StemmerTokenFilterLanguage](#stemmertokenfilterlanguage)|The language to use for a stemmer token filter.|
|[StopAnalyzer](#stopanalyzer)|Divides text at non-letters; Applies the lowercase and stopword token filters. This analyzer is implemented using Apache Lucene.|
|[StopwordsList](#stopwordslist)|Identifies a predefined list of language-specific stopwords.|
|[StopwordsTokenFilter](#stopwordstokenfilter)|Removes stop words from a token stream. This token filter is implemented using Apache Lucene.|
|[Suggester](#suggester)|Defines how the Suggest API should apply to a group of fields in the index.|
|[SuggesterSearchMode](#suggestersearchmode)|A value indicating the capabilities of the suggester.|
|[SynonymTokenFilter](#synonymtokenfilter)|Matches single or multi-word synonyms in a token stream. This token filter is implemented using Apache Lucene.|
|[TagScoringFunction](#tagscoringfunction)|Defines a function that boosts scores of documents with string values matching a given list of tags.|
|[TagScoringParameters](#tagscoringparameters)|Provides parameter values to a tag scoring function.|
|[TextWeights](#textweights)|Defines weights on index fields for which matches should boost scoring in search queries.|
|[TokenCharacterKind](#tokencharacterkind)|Represents classes of characters on which a token filter can operate.|
|[TokenFilterName](#tokenfiltername)|Defines the names of all token filters supported by the search engine.|
|[TruncateTokenFilter](#truncatetokenfilter)|Truncates the terms to a specific length. This token filter is implemented using Apache Lucene.|
|[UaxUrlEmailTokenizer](#uaxurlemailtokenizer)|Tokenizes urls and emails as one token. This tokenizer is implemented using Apache Lucene.|
|[UniqueTokenFilter](#uniquetokenfilter)|Filters out tokens with same text as the previous token. This token filter is implemented using Apache Lucene.|
|[VectorEncodingFormat](#vectorencodingformat)|The encoding format for interpreting vector field contents.|
|[VectorSearch](#vectorsearch)|Contains configuration options related to vector search.|
|[VectorSearchAlgorithmKind](#vectorsearchalgorithmkind)|The algorithm used for indexing and querying.|
|[VectorSearchAlgorithmMetric](#vectorsearchalgorithmmetric)|The similarity metric to use for vector comparisons. It is recommended to choose the same similarity metric as the embedding model was trained on.|
|[VectorSearchCompressionKind](#vectorsearchcompressionkind)|The compression method used for indexing and querying.|
|[VectorSearchCompressionTargetDataType](#vectorsearchcompressiontargetdatatype)|The quantized data type of compressed vector values.|
|[VectorSearchProfile](#vectorsearchprofile)|Defines a combination of configurations to use with vector search.|
|[VectorSearchVectorizerKind](#vectorsearchvectorizerkind)|The vectorization method to be used during query time.|
|[WebApiParameters](#webapiparameters)|Specifies the properties for connecting to a user-defined vectorizer.|
|[WebApiVectorizer](#webapivectorizer)|Specifies a user-defined vectorizer for generating the vector embedding of a query string. Integration of an external vectorizer is achieved using the custom Web API interface of a skillset.|
|[WordDelimiterTokenFilter](#worddelimitertokenfilter)|Splits words into subwords and performs optional transformations on subword groups. This token filter is implemented using Apache Lucene.|

### AsciiFoldingTokenFilter

Object

Converts alphabetic, numeric, and symbolic Unicode characters which are not in the first 127 ASCII characters (the "Basic Latin" Unicode block) into their ASCII equivalents, if such equivalents exist. This token filter is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.AsciiFoldingTokenFilter||A URI fragment specifying the type of token filter.|
|name|string||The name of the token filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|
|preserveOriginal|boolean|False|A value indicating whether the original token will be kept. Default is false.|

### AzureActiveDirectoryApplicationCredentials

Object

Credentials of a registered application created for your search service, used for authenticated access to the encryption keys stored in Azure Key Vault.

|Name|Type|Description|
|---|---|---|
|applicationId|string|An AAD Application ID that was granted the required access permissions to the Azure Key Vault that is to be used when encrypting your data at rest. The Application ID should not be confused with the Object ID for your AAD Application.|
|applicationSecret|string|The authentication key of the specified AAD application.|

### AzureOpenAIEmbeddingSkill

Object

Allows you to generate a vector embedding for a given text input using the Azure OpenAI resource.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill|A URI fragment specifying the type of skill.|
|apiKey|string|API key of the designated Azure OpenAI resource.|
|authIdentity|SearchIndexerDataIdentity:<br><br>- [SearchIndexerDataNoneIdentity](#searchindexerdatanoneidentity)<br>- [SearchIndexerDataUserAssignedIdentity](#searchindexerdatauserassignedidentity)|The user-assigned managed identity used for outbound connections.|
|context|string|Represents the level at which operations take place, such as the document root or document content (for example, /document or /document/content). The default is /document.|
|deploymentId|string|ID of the Azure OpenAI model deployment on the designated resource.|
|description|string|The description of the skill which describes the inputs, outputs, and usage of the skill.|
|dimensions|integer (int32)|The number of dimensions the resulting output embeddings should have. Only supported in text-embedding-3 and later models.|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]|Inputs of the skills could be a column in the source data set, or the output of an upstream skill.|
|modelName|[AzureOpenAIModelName](#azureopenaimodelname)|The name of the embedding model that is deployed at the provided deploymentId path.|
|name|string|The name of the skill which uniquely identifies it within the skillset. A skill with no name defined will be given a default name of its 1-based index in the skills array, prefixed with the character '#'.|
|outputs|[OutputFieldMappingEntry](#outputfieldmappingentry)[]|The output of a skill is either a field in a search index, or a value that can be consumed as an input by another skill.|
|resourceUri|string (uri)|The resource URI of the Azure OpenAI resource.|

### AzureOpenAIModelName

Enumeration

The Azure Open AI model name that will be called.

|Value|Description|
|---|---|
|text-embedding-ada-002||
|text-embedding-3-large||
|text-embedding-3-small||

### AzureOpenAIParameters

Object

Specifies the parameters for connecting to the Azure OpenAI resource.

|Name|Type|Description|
|---|---|---|
|apiKey|string|API key of the designated Azure OpenAI resource.|
|authIdentity|SearchIndexerDataIdentity:<br><br>- [SearchIndexerDataNoneIdentity](#searchindexerdatanoneidentity)<br>- [SearchIndexerDataUserAssignedIdentity](#searchindexerdatauserassignedidentity)|The user-assigned managed identity used for outbound connections.|
|deploymentId|string|ID of the Azure OpenAI model deployment on the designated resource.|
|modelName|[AzureOpenAIModelName](#azureopenaimodelname)|The name of the embedding model that is deployed at the provided deploymentId path.|
|resourceUri|string (uri)|The resource URI of the Azure OpenAI resource.|

### AzureOpenAIVectorizer

Object

Specifies the Azure OpenAI resource used to vectorize a query string.

|Name|Type|Description|
|---|---|---|
|azureOpenAIParameters|AzureOpenAIParameters:<br><br>[AzureOpenAIEmbeddingSkill](#azureopenaiembeddingskill)|Contains the parameters specific to Azure OpenAI embedding vectorization.|
|kind|string:<br><br>azureOpenAI|The name of the kind of vectorization method being configured for use with vector search.|
|name|string|The name to associate with this particular vectorization method.|

### BinaryQuantizationVectorSearchCompressionConfiguration

Object

Contains configuration options specific to the binary quantization compression method used during indexing and querying.

|Name|Type|Default value|Description|
|---|---|---|---|
|defaultOversampling|number (double)||Default oversampling factor. Oversampling will internally request more documents (specified by this multiplier) in the initial search. This increases the set of results that will be reranked using recomputed similarity scores from full-precision vectors. Minimum value is 1, meaning no oversampling (1x). This parameter can only be set when rerankWithOriginalVectors is true. Higher values improve recall at the expense of latency.|
|kind|string:<br><br>binaryQuantization||The name of the kind of compression method being configured for use with vector search.|
|name|string||The name to associate with this particular configuration.|
|rerankWithOriginalVectors|boolean|True|If set to true, once the ordered set of results calculated using compressed vectors are obtained, they will be reranked again by recalculating the full-precision similarity scores. This will improve recall at the expense of latency.|

### BM25Similarity

Object

Ranking function based on the Okapi BM25 similarity algorithm. BM25 is a TF-IDF-like algorithm that includes length normalization (controlled by the 'b' parameter) as well as term frequency saturation (controlled by the 'k1' parameter).

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.BM25Similarity||
|b|number (double)|This property controls how the length of a document affects the relevance score. By default, a value of 0.75 is used. A value of 0.0 means no length normalization is applied, while a value of 1.0 means the score is fully normalized by the length of the document.|
|k1|number (double)|This property controls the scaling function between the term frequency of each matching terms and the final relevance score of a document-query pair. By default, a value of 1.2 is used. A value of 0.0 means the score does not scale with an increase in term frequency.|

### CharFilterName

Enumeration

Defines the names of all character filters supported by the search engine.

### CjkBigramTokenFilter

Object

Forms bigrams of CJK terms that are generated from the standard tokenizer. This token filter is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.CjkBigramTokenFilter||A URI fragment specifying the type of token filter.|
|ignoreScripts|[CjkBigramTokenFilterScripts](#cjkbigramtokenfilterscripts)[]||The scripts to ignore.|
|name|string||The name of the token filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|
|outputUnigrams|boolean|False|A value indicating whether to output both unigrams and bigrams (if true), or just bigrams (if false). Default is false.|

### CjkBigramTokenFilterScripts

Enumeration

Scripts that can be ignored by CjkBigramTokenFilter.

|Value|Description|
|---|---|
|han|Ignore Han script when forming bigrams of CJK terms.|
|hiragana|Ignore Hiragana script when forming bigrams of CJK terms.|
|katakana|Ignore Katakana script when forming bigrams of CJK terms.|
|hangul|Ignore Hangul script when forming bigrams of CJK terms.|

### ClassicSimilarity

Object

Legacy similarity algorithm which uses the Lucene TFIDFSimilarity implementation of TF-IDF. This variation of TF-IDF introduces static document length normalization as well as coordinating factors that penalize documents that only partially match the searched queries.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.ClassicSimilarity||

### ClassicTokenizer

Object

Grammar-based tokenizer that is suitable for processing most European-language documents. This tokenizer is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.ClassicTokenizer||A URI fragment specifying the type of tokenizer.|
|maxTokenLength|integer (int32)<br><br>maximum: 300|255|The maximum token length. Default is 255. Tokens longer than the maximum length are split. The maximum token length that can be used is 300 characters.|
|name|string||The name of the tokenizer. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|

### CommonGramTokenFilter

Object

Construct bigrams for frequently occurring terms while indexing. Single terms are still indexed too, with bigrams overlaid. This token filter is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.CommonGramTokenFilter||A URI fragment specifying the type of token filter.|
|commonWords|string[]||The set of common words.|
|ignoreCase|boolean|False|A value indicating whether common words matching will be case insensitive. Default is false.|
|name|string||The name of the token filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|
|queryMode|boolean|False|A value that indicates whether the token filter is in query mode. When in query mode, the token filter generates bigrams and then removes common words and single terms followed by a common word. Default is false.|

### CorsOptions

Object

Defines options to control Cross-Origin Resource Sharing (CORS) for an index.

|Name|Type|Description|
|---|---|---|
|allowedOrigins|string[]|The list of origins from which JavaScript code will be granted access to your index. Can contain a list of hosts of the form {protocol}://{fully-qualified-domain-name}[:{port#}], or a single '*' to allow all origins (not recommended).|
|maxAgeInSeconds|integer (int64)|The duration for which browsers should cache CORS preflight responses. Defaults to 5 minutes.|

### CustomAnalyzer

Object

Allows you to take control over the process of converting text into indexable/searchable tokens. It's a user-defined configuration consisting of a single predefined tokenizer and one or more filters. The tokenizer is responsible for breaking text into tokens, and the filters for modifying tokens emitted by the tokenizer.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.CustomAnalyzer|A URI fragment specifying the type of analyzer.|
|charFilters|[CharFilterName](#charfiltername)[]|A list of character filters used to prepare input text before it is processed by the tokenizer. For instance, they can replace certain characters or symbols. The filters are run in the order in which they are listed.|
|name|string|The name of the analyzer. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|
|tokenFilters|[TokenFilterName](#tokenfiltername)[]|A list of token filters used to filter out or modify the tokens generated by a tokenizer. For example, you can specify a lowercase filter that converts all characters to lowercase. The filters are run in the order in which they are listed.|
|tokenizer|[LexicalTokenizerName](#lexicaltokenizername)|The name of the tokenizer to use to divide continuous text into a sequence of tokens, such as breaking a sentence into words.|

### DictionaryDecompounderTokenFilter

Object

Decomposes compound words found in many Germanic languages. This token filter is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.DictionaryDecompounderTokenFilter||A URI fragment specifying the type of token filter.|
|maxSubwordSize|integer (int32)<br><br>maximum: 300|15|The maximum subword size. Only subwords shorter than this are outputted. Default is 15. Maximum is 300.|
|minSubwordSize|integer (int32)<br><br>maximum: 300|2|The minimum subword size. Only subwords longer than this are outputted. Default is 2. Maximum is 300.|
|minWordSize|integer (int32)<br><br>maximum: 300|5|The minimum word size. Only words longer than this get processed. Default is 5. Maximum is 300.|
|name|string||The name of the token filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|
|onlyLongestMatch|boolean|False|A value indicating whether to add only the longest matching subword to the output. Default is false.|
|wordList|string[]||The list of words to match against.|

### DistanceScoringFunction

Object

Defines a function that boosts scores based on distance from a geographic location.

|Name|Type|Description|
|---|---|---|
|boost|number (double)|A multiplier for the raw score. Must be a positive number not equal to 1.0.|
|distance|[DistanceScoringParameters](#distancescoringparameters)|Parameter values for the distance scoring function.|
|fieldName|string|The name of the field used as input to the scoring function.|
|interpolation|[ScoringFunctionInterpolation](#scoringfunctioninterpolation)|A value indicating how boosting will be interpolated across document scores; defaults to "Linear".|
|type|string:<br><br>distance|Indicates the type of function to use. Valid values include magnitude, freshness, distance, and tag. The function type must be lower case.|

### DistanceScoringParameters

Object

Provides parameter values to a distance scoring function.

|Name|Type|Description|
|---|---|---|
|boostingDistance|number (double)|The distance in kilometers from the reference location where the boosting range ends.|
|referencePointParameter|string|The name of the parameter passed in search queries to specify the reference location.|

### EdgeNGramTokenFilter

Object

Generates n-grams of the given size(s) starting from the front or the back of an input token. This token filter is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.EdgeNGramTokenFilter||A URI fragment specifying the type of token filter.|
|maxGram|integer (int32)|2|The maximum n-gram length. Default is 2.|
|minGram|integer (int32)|1|The minimum n-gram length. Default is 1. Must be less than the value of maxGram.|
|name|string||The name of the token filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|
|side|[EdgeNGramTokenFilterSide](#edgengramtokenfilterside)|front|Specifies which side of the input the n-gram should be generated from. Default is "front".|

### EdgeNGramTokenFilterSide

Enumeration

Specifies which side of the input an n-gram should be generated from.

|Value|Description|
|---|---|
|front|Specifies that the n-gram should be generated from the front of the input.|
|back|Specifies that the n-gram should be generated from the back of the input.|

### EdgeNGramTokenFilterV2

Object

Generates n-grams of the given size(s) starting from the front or the back of an input token. This token filter is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.EdgeNGramTokenFilterV2||A URI fragment specifying the type of token filter.|
|maxGram|integer (int32)<br><br>maximum: 300|2|The maximum n-gram length. Default is 2. Maximum is 300.|
|minGram|integer (int32)<br><br>maximum: 300|1|The minimum n-gram length. Default is 1. Maximum is 300. Must be less than the value of maxGram.|
|name|string||The name of the token filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|
|side|[EdgeNGramTokenFilterSide](#edgengramtokenfilterside)|front|Specifies which side of the input the n-gram should be generated from. Default is "front".|

### EdgeNGramTokenizer

Object

Tokenizes the input from an edge into n-grams of the given size(s). This tokenizer is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.EdgeNGramTokenizer||A URI fragment specifying the type of tokenizer.|
|maxGram|integer (int32)<br><br>maximum: 300|2|The maximum n-gram length. Default is 2. Maximum is 300.|
|minGram|integer (int32)<br><br>maximum: 300|1|The minimum n-gram length. Default is 1. Maximum is 300. Must be less than the value of maxGram.|
|name|string||The name of the tokenizer. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|
|tokenChars|[TokenCharacterKind](#tokencharacterkind)[]||Character classes to keep in the tokens.|

### ElisionTokenFilter

Object

Removes elisions. For example, "l'avion" (the plane) will be converted to "avion" (plane). This token filter is implemented using Apache Lucene.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.ElisionTokenFilter|A URI fragment specifying the type of token filter.|
|articles|string[]|The set of articles to remove.|
|name|string|The name of the token filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|

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

### ExhaustiveKnnParameters

Object

Contains the parameters specific to exhaustive KNN algorithm.

|Name|Type|Description|
|---|---|---|
|metric|[VectorSearchAlgorithmMetric](#vectorsearchalgorithmmetric)|The similarity metric to use for vector comparisons.|

### ExhaustiveKnnVectorSearchAlgorithmConfiguration

Object

Contains configuration options specific to the exhaustive KNN algorithm used during querying, which will perform brute-force search across the entire vector index.

|Name|Type|Description|
|---|---|---|
|exhaustiveKnnParameters|[ExhaustiveKnnParameters](#exhaustiveknnparameters)|Contains the parameters specific to exhaustive KNN algorithm.|
|kind|string:<br><br>exhaustiveKnn|The name of the kind of algorithm being configured for use with vector search.|
|name|string|The name to associate with this particular configuration.|

### FreshnessScoringFunction

Object

Defines a function that boosts scores based on the value of a date-time field.

|Name|Type|Description|
|---|---|---|
|boost|number (double)|A multiplier for the raw score. Must be a positive number not equal to 1.0.|
|fieldName|string|The name of the field used as input to the scoring function.|
|freshness|[FreshnessScoringParameters](#freshnessscoringparameters)|Parameter values for the freshness scoring function.|
|interpolation|[ScoringFunctionInterpolation](#scoringfunctioninterpolation)|A value indicating how boosting will be interpolated across document scores; defaults to "Linear".|
|type|string:<br><br>freshness|Indicates the type of function to use. Valid values include magnitude, freshness, distance, and tag. The function type must be lower case.|

### FreshnessScoringParameters

Object

Provides parameter values to a freshness scoring function.

|Name|Type|Description|
|---|---|---|
|boostingDuration|string (duration)|The expiration period after which boosting will stop for a particular document.|

### HnswParameters

Object

Contains the parameters specific to the HNSW algorithm.

|Name|Type|Default value|Description|
|---|---|---|---|
|efConstruction|integer (int32)<br><br>minimum: 100  <br>maximum: 1000|400|The size of the dynamic list containing the nearest neighbors, which is used during index time. Increasing this parameter may improve index quality, at the expense of increased indexing time. At a certain point, increasing this parameter leads to diminishing returns.|
|efSearch|integer (int32)<br><br>minimum: 100  <br>maximum: 1000|500|The size of the dynamic list containing the nearest neighbors, which is used during search time. Increasing this parameter may improve search results, at the expense of slower search. At a certain point, increasing this parameter leads to diminishing returns.|
|m|integer (int32)<br><br>minimum: 4  <br>maximum: 10|4|The number of bi-directional links created for every new element during construction. Increasing this parameter value may improve recall and reduce retrieval times for datasets with high intrinsic dimensionality at the expense of increased memory consumption and longer indexing time.|
|metric|[VectorSearchAlgorithmMetric](#vectorsearchalgorithmmetric)||The similarity metric to use for vector comparisons.|

### HnswVectorSearchAlgorithmConfiguration

Object

Contains configuration options specific to the HNSW approximate nearest neighbors algorithm used during indexing and querying. The HNSW algorithm offers a tunable trade-off between search speed and accuracy.

|Name|Type|Description|
|---|---|---|
|hnswParameters|[HnswParameters](#hnswparameters)|Contains the parameters specific to HNSW algorithm.|
|kind|string:<br><br>hnsw|The name of the kind of algorithm being configured for use with vector search.|
|name|string|The name to associate with this particular configuration.|

### InputFieldMappingEntry

Object

Input field mapping for a skill.

|Name|Type|Description|
|---|---|---|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]|The recursive inputs used when creating a complex type.|
|name|string|The name of the input.|
|source|string|The source of the input.|
|sourceContext|string|The source context used for selecting recursive inputs.|

### KeepTokenFilter

Object

A token filter that only keeps tokens with text contained in a specified list of words. This token filter is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.KeepTokenFilter||A URI fragment specifying the type of token filter.|
|keepWords|string[]||The list of words to keep.|
|keepWordsCase|boolean|False|A value indicating whether to lower case all words first. Default is false.|
|name|string||The name of the token filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|

### KeywordMarkerTokenFilter

Object

Marks terms as keywords. This token filter is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.KeywordMarkerTokenFilter||A URI fragment specifying the type of token filter.|
|ignoreCase|boolean|False|A value indicating whether to ignore case. If true, all words are converted to lower case first. Default is false.|
|keywords|string[]||A list of words to mark as keywords.|
|name|string||The name of the token filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|

### KeywordTokenizer

Object

Emits the entire input as a single token. This tokenizer is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.KeywordTokenizer||A URI fragment specifying the type of tokenizer.|
|bufferSize|integer (int32)|256|The read buffer size in bytes. Default is 256.|
|name|string||The name of the tokenizer. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|

### KeywordTokenizerV2

Object

Emits the entire input as a single token. This tokenizer is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.KeywordTokenizerV2||A URI fragment specifying the type of tokenizer.|
|maxTokenLength|integer (int32)<br><br>maximum: 300|256|The maximum token length. Default is 256. Tokens longer than the maximum length are split. The maximum token length that can be used is 300 characters.|
|name|string||The name of the tokenizer. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|

### LengthTokenFilter

Object

Removes words that are too long or too short. This token filter is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.LengthTokenFilter||A URI fragment specifying the type of token filter.|
|max|integer (int32)<br><br>maximum: 300|300|The maximum length in characters. Default and maximum is 300.|
|min|integer (int32)<br><br>maximum: 300|0|The minimum length in characters. Default is 0. Maximum is 300. Must be less than the value of max.|
|name|string||The name of the token filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|

### LexicalAnalyzerName

Enumeration

Defines the names of all text analyzers supported by the search engine.

|Value|Description|
|---|---|
|ar.microsoft|Microsoft analyzer for Arabic.|
|ar.lucene|Lucene analyzer for Arabic.|
|hy.lucene|Lucene analyzer for Armenian.|
|bn.microsoft|Microsoft analyzer for Bangla.|
|eu.lucene|Lucene analyzer for Basque.|
|bg.microsoft|Microsoft analyzer for Bulgarian.|
|bg.lucene|Lucene analyzer for Bulgarian.|
|ca.microsoft|Microsoft analyzer for Catalan.|
|ca.lucene|Lucene analyzer for Catalan.|
|zh-Hans.microsoft|Microsoft analyzer for Chinese (Simplified).|
|zh-Hans.lucene|Lucene analyzer for Chinese (Simplified).|
|zh-Hant.microsoft|Microsoft analyzer for Chinese (Traditional).|
|zh-Hant.lucene|Lucene analyzer for Chinese (Traditional).|
|hr.microsoft|Microsoft analyzer for Croatian.|
|cs.microsoft|Microsoft analyzer for Czech.|
|cs.lucene|Lucene analyzer for Czech.|
|da.microsoft|Microsoft analyzer for Danish.|
|da.lucene|Lucene analyzer for Danish.|
|nl.microsoft|Microsoft analyzer for Dutch.|
|nl.lucene|Lucene analyzer for Dutch.|
|en.microsoft|Microsoft analyzer for English.|
|en.lucene|Lucene analyzer for English.|
|et.microsoft|Microsoft analyzer for Estonian.|
|fi.microsoft|Microsoft analyzer for Finnish.|
|fi.lucene|Lucene analyzer for Finnish.|
|fr.microsoft|Microsoft analyzer for French.|
|fr.lucene|Lucene analyzer for French.|
|gl.lucene|Lucene analyzer for Galician.|
|de.microsoft|Microsoft analyzer for German.|
|de.lucene|Lucene analyzer for German.|
|el.microsoft|Microsoft analyzer for Greek.|
|el.lucene|Lucene analyzer for Greek.|
|gu.microsoft|Microsoft analyzer for Gujarati.|
|he.microsoft|Microsoft analyzer for Hebrew.|
|hi.microsoft|Microsoft analyzer for Hindi.|
|hi.lucene|Lucene analyzer for Hindi.|
|hu.microsoft|Microsoft analyzer for Hungarian.|
|hu.lucene|Lucene analyzer for Hungarian.|
|is.microsoft|Microsoft analyzer for Icelandic.|
|id.microsoft|Microsoft analyzer for Indonesian (Bahasa).|
|id.lucene|Lucene analyzer for Indonesian.|
|ga.lucene|Lucene analyzer for Irish.|
|it.microsoft|Microsoft analyzer for Italian.|
|it.lucene|Lucene analyzer for Italian.|
|ja.microsoft|Microsoft analyzer for Japanese.|
|ja.lucene|Lucene analyzer for Japanese.|
|kn.microsoft|Microsoft analyzer for Kannada.|
|ko.microsoft|Microsoft analyzer for Korean.|
|ko.lucene|Lucene analyzer for Korean.|
|lv.microsoft|Microsoft analyzer for Latvian.|
|lv.lucene|Lucene analyzer for Latvian.|
|lt.microsoft|Microsoft analyzer for Lithuanian.|
|ml.microsoft|Microsoft analyzer for Malayalam.|
|ms.microsoft|Microsoft analyzer for Malay (Latin).|
|mr.microsoft|Microsoft analyzer for Marathi.|
|nb.microsoft|Microsoft analyzer for Norwegian (Bokmål).|
|no.lucene|Lucene analyzer for Norwegian.|
|fa.lucene|Lucene analyzer for Persian.|
|pl.microsoft|Microsoft analyzer for Polish.|
|pl.lucene|Lucene analyzer for Polish.|
|pt-BR.microsoft|Microsoft analyzer for Portuguese (Brazil).|
|pt-BR.lucene|Lucene analyzer for Portuguese (Brazil).|
|pt-PT.microsoft|Microsoft analyzer for Portuguese (Portugal).|
|pt-PT.lucene|Lucene analyzer for Portuguese (Portugal).|
|pa.microsoft|Microsoft analyzer for Punjabi.|
|ro.microsoft|Microsoft analyzer for Romanian.|
|ro.lucene|Lucene analyzer for Romanian.|
|ru.microsoft|Microsoft analyzer for Russian.|
|ru.lucene|Lucene analyzer for Russian.|
|sr-cyrillic.microsoft|Microsoft analyzer for Serbian (Cyrillic).|
|sr-latin.microsoft|Microsoft analyzer for Serbian (Latin).|
|sk.microsoft|Microsoft analyzer for Slovak.|
|sl.microsoft|Microsoft analyzer for Slovenian.|
|es.microsoft|Microsoft analyzer for Spanish.|
|es.lucene|Lucene analyzer for Spanish.|
|sv.microsoft|Microsoft analyzer for Swedish.|
|sv.lucene|Lucene analyzer for Swedish.|
|ta.microsoft|Microsoft analyzer for Tamil.|
|te.microsoft|Microsoft analyzer for Telugu.|
|th.microsoft|Microsoft analyzer for Thai.|
|th.lucene|Lucene analyzer for Thai.|
|tr.microsoft|Microsoft analyzer for Turkish.|
|tr.lucene|Lucene analyzer for Turkish.|
|uk.microsoft|Microsoft analyzer for Ukrainian.|
|ur.microsoft|Microsoft analyzer for Urdu.|
|vi.microsoft|Microsoft analyzer for Vietnamese.|
|standard.lucene|Standard Lucene analyzer.|
|standardasciifolding.lucene|Standard ASCII Folding Lucene analyzer. See [https://learn.microsoft.com/rest/api/searchservice/Custom-analyzers-in-Azure-Search#Analyzers](https://learn.microsoft.com/en-us/rest/api/searchservice/Custom-analyzers-in-Azure-Search#Analyzers)|
|keyword|Treats the entire content of a field as a single token. This is useful for data like zip codes, ids, and some product names. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/core/KeywordAnalyzer.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/core/KeywordAnalyzer.html)|
|pattern|Flexibly separates text into terms via a regular expression pattern. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/miscellaneous/PatternAnalyzer.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/miscellaneous/PatternAnalyzer.html)|
|simple|Divides text at non-letters and converts them to lower case. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/core/SimpleAnalyzer.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/core/SimpleAnalyzer.html)|
|stop|Divides text at non-letters; Applies the lowercase and stopword token filters. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/core/StopAnalyzer.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/core/StopAnalyzer.html)|
|whitespace|An analyzer that uses the whitespace tokenizer. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/core/WhitespaceAnalyzer.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/core/WhitespaceAnalyzer.html)|

### LexicalTokenizerName

Enumeration

Defines the names of all tokenizers supported by the search engine.

### LimitTokenFilter

Object

Limits the number of tokens while indexing. This token filter is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.LimitTokenFilter||A URI fragment specifying the type of token filter.|
|consumeAllTokens|boolean|False|A value indicating whether all tokens from the input must be consumed even if maxTokenCount is reached. Default is false.|
|maxTokenCount|integer (int32)|1|The maximum number of tokens to produce. Default is 1.|
|name|string||The name of the token filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|

### LuceneStandardAnalyzer

Object

Standard Apache Lucene analyzer; Composed of the standard tokenizer, lowercase filter and stop filter.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.StandardAnalyzer||A URI fragment specifying the type of analyzer.|
|maxTokenLength|integer (int32)<br><br>maximum: 300|255|The maximum token length. Default is 255. Tokens longer than the maximum length are split. The maximum token length that can be used is 300 characters.|
|name|string||The name of the analyzer. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|
|stopwords|string[]||A list of stopwords.|

### LuceneStandardTokenizer

Object

Breaks text following the Unicode Text Segmentation rules. This tokenizer is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.StandardTokenizer||A URI fragment specifying the type of tokenizer.|
|maxTokenLength|integer (int32)|255|The maximum token length. Default is 255. Tokens longer than the maximum length are split.|
|name|string||The name of the tokenizer. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|

### LuceneStandardTokenizerV2

Object

Breaks text following the Unicode Text Segmentation rules. This tokenizer is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.StandardTokenizerV2||A URI fragment specifying the type of tokenizer.|
|maxTokenLength|integer (int32)<br><br>maximum: 300|255|The maximum token length. Default is 255. Tokens longer than the maximum length are split. The maximum token length that can be used is 300 characters.|
|name|string||The name of the tokenizer. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|

### MagnitudeScoringFunction

Object

Defines a function that boosts scores based on the magnitude of a numeric field.

|Name|Type|Description|
|---|---|---|
|boost|number (double)|A multiplier for the raw score. Must be a positive number not equal to 1.0.|
|fieldName|string|The name of the field used as input to the scoring function.|
|interpolation|[ScoringFunctionInterpolation](#scoringfunctioninterpolation)|A value indicating how boosting will be interpolated across document scores; defaults to "Linear".|
|magnitude|[MagnitudeScoringParameters](#magnitudescoringparameters)|Parameter values for the magnitude scoring function.|
|type|string:<br><br>magnitude|Indicates the type of function to use. Valid values include magnitude, freshness, distance, and tag. The function type must be lower case.|

### MagnitudeScoringParameters

Object

Provides parameter values to a magnitude scoring function.

|Name|Type|Description|
|---|---|---|
|boostingRangeEnd|number (double)|The field value at which boosting ends.|
|boostingRangeStart|number (double)|The field value at which boosting starts.|
|constantBoostBeyondRange|boolean|A value indicating whether to apply a constant boost for field values beyond the range end value; default is false.|

### MappingCharFilter

Object

A character filter that applies mappings defined with the mappings option. Matching is greedy (longest pattern matching at a given point wins). Replacement is allowed to be the empty string. This character filter is implemented using Apache Lucene.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.MappingCharFilter|A URI fragment specifying the type of char filter.|
|mappings|string[]|A list of mappings of the following format: "a=>b" (all occurrences of the character "a" will be replaced with character "b").|
|name|string|The name of the char filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|

### MicrosoftLanguageStemmingTokenizer

Object

Divides text using language-specific rules and reduces words to their base forms.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.MicrosoftLanguageStemmingTokenizer||A URI fragment specifying the type of tokenizer.|
|isSearchTokenizer|boolean|False|A value indicating how the tokenizer is used. Set to true if used as the search tokenizer, set to false if used as the indexing tokenizer. Default is false.|
|language|[MicrosoftStemmingTokenizerLanguage](#microsoftstemmingtokenizerlanguage)||The language to use. The default is English.|
|maxTokenLength|integer (int32)<br><br>maximum: 300|255|The maximum token length. Tokens longer than the maximum length are split. Maximum token length that can be used is 300 characters. Tokens longer than 300 characters are first split into tokens of length 300 and then each of those tokens is split based on the max token length set. Default is 255.|
|name|string||The name of the tokenizer. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|

### MicrosoftLanguageTokenizer

Object

Divides text using language-specific rules.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.MicrosoftLanguageTokenizer||A URI fragment specifying the type of tokenizer.|
|isSearchTokenizer|boolean|False|A value indicating how the tokenizer is used. Set to true if used as the search tokenizer, set to false if used as the indexing tokenizer. Default is false.|
|language|[MicrosoftTokenizerLanguage](#microsofttokenizerlanguage)||The language to use. The default is English.|
|maxTokenLength|integer (int32)<br><br>maximum: 300|255|The maximum token length. Tokens longer than the maximum length are split. Maximum token length that can be used is 300 characters. Tokens longer than 300 characters are first split into tokens of length 300 and then each of those tokens is split based on the max token length set. Default is 255.|
|name|string||The name of the tokenizer. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|

### MicrosoftStemmingTokenizerLanguage

Enumeration

Lists the languages supported by the Microsoft language stemming tokenizer.

|Value|Description|
|---|---|
|arabic|Selects the Microsoft stemming tokenizer for Arabic.|
|bangla|Selects the Microsoft stemming tokenizer for Bangla.|
|bulgarian|Selects the Microsoft stemming tokenizer for Bulgarian.|
|catalan|Selects the Microsoft stemming tokenizer for Catalan.|
|croatian|Selects the Microsoft stemming tokenizer for Croatian.|
|czech|Selects the Microsoft stemming tokenizer for Czech.|
|danish|Selects the Microsoft stemming tokenizer for Danish.|
|dutch|Selects the Microsoft stemming tokenizer for Dutch.|
|english|Selects the Microsoft stemming tokenizer for English.|
|estonian|Selects the Microsoft stemming tokenizer for Estonian.|
|finnish|Selects the Microsoft stemming tokenizer for Finnish.|
|french|Selects the Microsoft stemming tokenizer for French.|
|german|Selects the Microsoft stemming tokenizer for German.|
|greek|Selects the Microsoft stemming tokenizer for Greek.|
|gujarati|Selects the Microsoft stemming tokenizer for Gujarati.|
|hebrew|Selects the Microsoft stemming tokenizer for Hebrew.|
|hindi|Selects the Microsoft stemming tokenizer for Hindi.|
|hungarian|Selects the Microsoft stemming tokenizer for Hungarian.|
|icelandic|Selects the Microsoft stemming tokenizer for Icelandic.|
|indonesian|Selects the Microsoft stemming tokenizer for Indonesian.|
|italian|Selects the Microsoft stemming tokenizer for Italian.|
|kannada|Selects the Microsoft stemming tokenizer for Kannada.|
|latvian|Selects the Microsoft stemming tokenizer for Latvian.|
|lithuanian|Selects the Microsoft stemming tokenizer for Lithuanian.|
|malay|Selects the Microsoft stemming tokenizer for Malay.|
|malayalam|Selects the Microsoft stemming tokenizer for Malayalam.|
|marathi|Selects the Microsoft stemming tokenizer for Marathi.|
|norwegianBokmaal|Selects the Microsoft stemming tokenizer for Norwegian (Bokmål).|
|polish|Selects the Microsoft stemming tokenizer for Polish.|
|portuguese|Selects the Microsoft stemming tokenizer for Portuguese.|
|portugueseBrazilian|Selects the Microsoft stemming tokenizer for Portuguese (Brazil).|
|punjabi|Selects the Microsoft stemming tokenizer for Punjabi.|
|romanian|Selects the Microsoft stemming tokenizer for Romanian.|
|russian|Selects the Microsoft stemming tokenizer for Russian.|
|serbianCyrillic|Selects the Microsoft stemming tokenizer for Serbian (Cyrillic).|
|serbianLatin|Selects the Microsoft stemming tokenizer for Serbian (Latin).|
|slovak|Selects the Microsoft stemming tokenizer for Slovak.|
|slovenian|Selects the Microsoft stemming tokenizer for Slovenian.|
|spanish|Selects the Microsoft stemming tokenizer for Spanish.|
|swedish|Selects the Microsoft stemming tokenizer for Swedish.|
|tamil|Selects the Microsoft stemming tokenizer for Tamil.|
|telugu|Selects the Microsoft stemming tokenizer for Telugu.|
|turkish|Selects the Microsoft stemming tokenizer for Turkish.|
|ukrainian|Selects the Microsoft stemming tokenizer for Ukrainian.|
|urdu|Selects the Microsoft stemming tokenizer for Urdu.|

### MicrosoftTokenizerLanguage

Enumeration

Lists the languages supported by the Microsoft language tokenizer.

|Value|Description|
|---|---|
|bangla|Selects the Microsoft tokenizer for Bangla.|
|bulgarian|Selects the Microsoft tokenizer for Bulgarian.|
|catalan|Selects the Microsoft tokenizer for Catalan.|
|chineseSimplified|Selects the Microsoft tokenizer for Chinese (Simplified).|
|chineseTraditional|Selects the Microsoft tokenizer for Chinese (Traditional).|
|croatian|Selects the Microsoft tokenizer for Croatian.|
|czech|Selects the Microsoft tokenizer for Czech.|
|danish|Selects the Microsoft tokenizer for Danish.|
|dutch|Selects the Microsoft tokenizer for Dutch.|
|english|Selects the Microsoft tokenizer for English.|
|french|Selects the Microsoft tokenizer for French.|
|german|Selects the Microsoft tokenizer for German.|
|greek|Selects the Microsoft tokenizer for Greek.|
|gujarati|Selects the Microsoft tokenizer for Gujarati.|
|hindi|Selects the Microsoft tokenizer for Hindi.|
|icelandic|Selects the Microsoft tokenizer for Icelandic.|
|indonesian|Selects the Microsoft tokenizer for Indonesian.|
|italian|Selects the Microsoft tokenizer for Italian.|
|japanese|Selects the Microsoft tokenizer for Japanese.|
|kannada|Selects the Microsoft tokenizer for Kannada.|
|korean|Selects the Microsoft tokenizer for Korean.|
|malay|Selects the Microsoft tokenizer for Malay.|
|malayalam|Selects the Microsoft tokenizer for Malayalam.|
|marathi|Selects the Microsoft tokenizer for Marathi.|
|norwegianBokmaal|Selects the Microsoft tokenizer for Norwegian (Bokmål).|
|polish|Selects the Microsoft tokenizer for Polish.|
|portuguese|Selects the Microsoft tokenizer for Portuguese.|
|portugueseBrazilian|Selects the Microsoft tokenizer for Portuguese (Brazil).|
|punjabi|Selects the Microsoft tokenizer for Punjabi.|
|romanian|Selects the Microsoft tokenizer for Romanian.|
|russian|Selects the Microsoft tokenizer for Russian.|
|serbianCyrillic|Selects the Microsoft tokenizer for Serbian (Cyrillic).|
|serbianLatin|Selects the Microsoft tokenizer for Serbian (Latin).|
|slovenian|Selects the Microsoft tokenizer for Slovenian.|
|spanish|Selects the Microsoft tokenizer for Spanish.|
|swedish|Selects the Microsoft tokenizer for Swedish.|
|tamil|Selects the Microsoft tokenizer for Tamil.|
|telugu|Selects the Microsoft tokenizer for Telugu.|
|thai|Selects the Microsoft tokenizer for Thai.|
|ukrainian|Selects the Microsoft tokenizer for Ukrainian.|
|urdu|Selects the Microsoft tokenizer for Urdu.|
|vietnamese|Selects the Microsoft tokenizer for Vietnamese.|

### NGramTokenFilter

Object

Generates n-grams of the given size(s). This token filter is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.NGramTokenFilter||A URI fragment specifying the type of token filter.|
|maxGram|integer (int32)|2|The maximum n-gram length. Default is 2.|
|minGram|integer (int32)|1|The minimum n-gram length. Default is 1. Must be less than the value of maxGram.|
|name|string||The name of the token filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|

### NGramTokenFilterV2

Object

Generates n-grams of the given size(s). This token filter is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.NGramTokenFilterV2||A URI fragment specifying the type of token filter.|
|maxGram|integer (int32)<br><br>maximum: 300|2|The maximum n-gram length. Default is 2. Maximum is 300.|
|minGram|integer (int32)<br><br>maximum: 300|1|The minimum n-gram length. Default is 1. Maximum is 300. Must be less than the value of maxGram.|
|name|string||The name of the token filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|

### NGramTokenizer

Object

Tokenizes the input into n-grams of the given size(s). This tokenizer is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.NGramTokenizer||A URI fragment specifying the type of tokenizer.|
|maxGram|integer (int32)<br><br>maximum: 300|2|The maximum n-gram length. Default is 2. Maximum is 300.|
|minGram|integer (int32)<br><br>maximum: 300|1|The minimum n-gram length. Default is 1. Maximum is 300. Must be less than the value of maxGram.|
|name|string||The name of the tokenizer. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|
|tokenChars|[TokenCharacterKind](#tokencharacterkind)[]||Character classes to keep in the tokens.|

### OutputFieldMappingEntry

Object

Output field mapping for a skill.

|Name|Type|Description|
|---|---|---|
|name|string|The name of the output defined by the skill.|
|targetName|string|The target name of the output. It is optional and default to name.|

### PathHierarchyTokenizerV2

Object

Tokenizer for path-like hierarchies. This tokenizer is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.PathHierarchyTokenizerV2||A URI fragment specifying the type of tokenizer.|
|delimiter|string (char)|/|The delimiter character to use. Default is "/".|
|maxTokenLength|integer (int32)<br><br>maximum: 300|300|The maximum token length. Default and maximum is 300.|
|name|string||The name of the tokenizer. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|
|replacement|string (char)|/|A value that, if set, replaces the delimiter character. Default is "/".|
|reverse|boolean|False|A value indicating whether to generate tokens in reverse order. Default is false.|
|skip|integer (int32)|0|The number of initial tokens to skip. Default is 0.|

### PatternAnalyzer

Object

Flexibly separates text into terms via a regular expression pattern. This analyzer is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.PatternAnalyzer||A URI fragment specifying the type of analyzer.|
|flags|[RegexFlags](#regexflags)||Regular expression flags.|
|lowercase|boolean|True|A value indicating whether terms should be lower-cased. Default is true.|
|name|string||The name of the analyzer. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|
|pattern|string|\W+|A regular expression pattern to match token separators. Default is an expression that matches one or more non-word characters.|
|stopwords|string[]||A list of stopwords.|

### PatternCaptureTokenFilter

Object

Uses Java regexes to emit multiple tokens - one for each capture group in one or more patterns. This token filter is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.PatternCaptureTokenFilter||A URI fragment specifying the type of token filter.|
|name|string||The name of the token filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|
|patterns|string[]||A list of patterns to match against each token.|
|preserveOriginal|boolean|True|A value indicating whether to return the original token even if one of the patterns matches. Default is true.|

### PatternReplaceCharFilter

Object

A character filter that replaces characters in the input string. It uses a regular expression to identify character sequences to preserve and a replacement pattern to identify characters to replace. For example, given the input text "aa bb aa bb", pattern "(aa)\s+(bb)", and replacement "$1#$2", the result would be "aa#bb aa#bb". This character filter is implemented using Apache Lucene.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.PatternReplaceCharFilter|A URI fragment specifying the type of char filter.|
|name|string|The name of the char filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|
|pattern|string|A regular expression pattern.|
|replacement|string|The replacement text.|

### PatternReplaceTokenFilter

Object

A character filter that replaces characters in the input string. It uses a regular expression to identify character sequences to preserve and a replacement pattern to identify characters to replace. For example, given the input text "aa bb aa bb", pattern "(aa)\s+(bb)", and replacement "$1#$2", the result would be "aa#bb aa#bb". This token filter is implemented using Apache Lucene.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.PatternReplaceTokenFilter|A URI fragment specifying the type of token filter.|
|name|string|The name of the token filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|
|pattern|string|A regular expression pattern.|
|replacement|string|The replacement text.|

### PatternTokenizer

Object

Tokenizer that uses regex pattern matching to construct distinct tokens. This tokenizer is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.PatternTokenizer||A URI fragment specifying the type of tokenizer.|
|flags|[RegexFlags](#regexflags)||Regular expression flags.|
|group|integer (int32)|-1|The zero-based ordinal of the matching group in the regular expression pattern to extract into tokens. Use -1 if you want to use the entire pattern to split the input into tokens, irrespective of matching groups. Default is -1.|
|name|string||The name of the tokenizer. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|
|pattern|string|\W+|A regular expression pattern to match token separators. Default is an expression that matches one or more non-word characters.|

### PhoneticEncoder

Enumeration

Identifies the type of phonetic encoder to use with a PhoneticTokenFilter.

|Value|Description|
|---|---|
|metaphone|Encodes a token into a Metaphone value.|
|doubleMetaphone|Encodes a token into a double metaphone value.|
|soundex|Encodes a token into a Soundex value.|
|refinedSoundex|Encodes a token into a Refined Soundex value.|
|caverphone1|Encodes a token into a Caverphone 1.0 value.|
|caverphone2|Encodes a token into a Caverphone 2.0 value.|
|cologne|Encodes a token into a Cologne Phonetic value.|
|nysiis|Encodes a token into a NYSIIS value.|
|koelnerPhonetik|Encodes a token using the Kölner Phonetik algorithm.|
|haasePhonetik|Encodes a token using the Haase refinement of the Kölner Phonetik algorithm.|
|beiderMorse|Encodes a token into a Beider-Morse value.|

### PhoneticTokenFilter

Object

Create tokens for phonetic matches. This token filter is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.PhoneticTokenFilter||A URI fragment specifying the type of token filter.|
|encoder|[PhoneticEncoder](#phoneticencoder)|metaphone|The phonetic encoder to use. Default is "metaphone".|
|name|string||The name of the token filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|
|replace|boolean|True|A value indicating whether encoded tokens should replace original tokens. If false, encoded tokens are added as synonyms. Default is true.|

### PrioritizedFields

Object

Describes the title, content, and keywords fields to be used for semantic ranking, captions, highlights, and answers.

|Name|Type|Description|
|---|---|---|
|prioritizedContentFields|[SemanticField](#semanticfield)[]|Defines the content fields to be used for semantic ranking, captions, highlights, and answers. For the best result, the selected fields should contain text in natural language form. The order of the fields in the array represents their priority. Fields with lower priority may get truncated if the content is long.|
|prioritizedKeywordsFields|[SemanticField](#semanticfield)[]|Defines the keyword fields to be used for semantic ranking, captions, highlights, and answers. For the best result, the selected fields should contain a list of keywords. The order of the fields in the array represents their priority. Fields with lower priority may get truncated if the content is long.|
|titleField|[SemanticField](#semanticfield)|Defines the title field to be used for semantic ranking, captions, highlights, and answers. If you don't have a title field in your index, leave this blank.|

### RegexFlags

Enumeration

Defines flags that can be combined to control how regular expressions are used in the pattern analyzer and pattern tokenizer.

|Value|Description|
|---|---|
|CANON_EQ|Enables canonical equivalence.|
|CASE_INSENSITIVE|Enables case-insensitive matching.|
|COMMENTS|Permits whitespace and comments in the pattern.|
|DOTALL|Enables dotall mode.|
|LITERAL|Enables literal parsing of the pattern.|
|MULTILINE|Enables multiline mode.|
|UNICODE_CASE|Enables Unicode-aware case folding.|
|UNIX_LINES|Enables Unix lines mode.|

### ScalarQuantizationParameters

Object

Contains the parameters specific to Scalar Quantization.

|Name|Type|Description|
|---|---|---|
|quantizedDataType|[VectorSearchCompressionTargetDataType](#vectorsearchcompressiontargetdatatype)|The quantized data type of compressed vector values.|

### ScalarQuantizationVectorSearchCompressionConfiguration

Object

Contains configuration options specific to the scalar quantization compression method used during indexing and querying.

|Name|Type|Default value|Description|
|---|---|---|---|
|defaultOversampling|number (double)||Default oversampling factor. Oversampling will internally request more documents (specified by this multiplier) in the initial search. This increases the set of results that will be reranked using recomputed similarity scores from full-precision vectors. Minimum value is 1, meaning no oversampling (1x). This parameter can only be set when rerankWithOriginalVectors is true. Higher values improve recall at the expense of latency.|
|kind|string:<br><br>scalarQuantization||The name of the kind of compression method being configured for use with vector search.|
|name|string||The name to associate with this particular configuration.|
|rerankWithOriginalVectors|boolean|True|If set to true, once the ordered set of results calculated using compressed vectors are obtained, they will be reranked again by recalculating the full-precision similarity scores. This will improve recall at the expense of latency.|
|scalarQuantizationParameters|[ScalarQuantizationParameters](#scalarquantizationparameters)||Contains the parameters specific to Scalar Quantization.|

### ScoringFunctionAggregation

Enumeration

Defines the aggregation function used to combine the results of all the scoring functions in a scoring profile.

|Value|Description|
|---|---|
|sum|Boost scores by the sum of all scoring function results.|
|average|Boost scores by the average of all scoring function results.|
|minimum|Boost scores by the minimum of all scoring function results.|
|maximum|Boost scores by the maximum of all scoring function results.|
|firstMatching|Boost scores using the first applicable scoring function in the scoring profile.|

### ScoringFunctionInterpolation

Enumeration

Defines the function used to interpolate score boosting across a range of documents.

|Value|Description|
|---|---|
|linear|Boosts scores by a linearly decreasing amount. This is the default interpolation for scoring functions.|
|constant|Boosts scores by a constant factor.|
|quadratic|Boosts scores by an amount that decreases quadratically. Boosts decrease slowly for higher scores, and more quickly as the scores decrease. This interpolation option is not allowed in tag scoring functions.|
|logarithmic|Boosts scores by an amount that decreases logarithmically. Boosts decrease quickly for higher scores, and more slowly as the scores decrease. This interpolation option is not allowed in tag scoring functions.|

### ScoringProfile

Object

Defines parameters for a search index that influence scoring in search queries.

|Name|Type|Description|
|---|---|---|
|functionAggregation|[ScoringFunctionAggregation](#scoringfunctionaggregation)|A value indicating how the results of individual scoring functions should be combined. Defaults to "Sum". Ignored if there are no scoring functions.|
|functions|ScoringFunction[]:<br><br>- [DistanceScoringFunction](#distancescoringfunction)[]<br>- [FreshnessScoringFunction](#freshnessscoringfunction)[]<br>- [MagnitudeScoringFunction](#magnitudescoringfunction)[]<br>- [TagScoringFunction](#tagscoringfunction)[]|The collection of functions that influence the scoring of documents.|
|name|string|The name of the scoring profile.|
|text|[TextWeights](#textweights)|Parameters that boost scoring based on text matches in certain index fields.|

### SearchField

Object

Represents a field in an index definition, which describes the name, data type, and search behavior of a field.

|Name|Type|Description|
|---|---|---|
|analyzer|[LexicalAnalyzerName](#lexicalanalyzername)|The name of the analyzer to use for the field. This option can be used only with searchable fields and it can't be set together with either searchAnalyzer or indexAnalyzer. Once the analyzer is chosen, it cannot be changed for the field. Must be null for complex fields.|
|dimensions|integer (int32)<br><br>minimum: 2  <br>maximum: 2048|The dimensionality of the vector field.|
|facetable|boolean|A value indicating whether to enable the field to be referenced in facet queries. Typically used in a presentation of search results that includes hit count by category (for example, search for digital cameras and see hits by brand, by megapixels, by price, and so on). This property must be null for complex fields. Fields of type Edm.GeographyPoint or Collection(Edm.GeographyPoint) cannot be facetable. Default is true for all other simple fields.|
|fields|[SearchField](#searchfield)[]|A list of sub-fields if this is a field of type Edm.ComplexType or Collection(Edm.ComplexType). Must be null or empty for simple fields.|
|filterable|boolean|A value indicating whether to enable the field to be referenced in $filter queries. filterable differs from searchable in how strings are handled. Fields of type Edm.String or Collection(Edm.String) that are filterable do not undergo word-breaking, so comparisons are for exact matches only. For example, if you set such a field f to "sunny day", $filter=f eq 'sunny' will find no matches, but $filter=f eq 'sunny day' will. This property must be null for complex fields. Default is true for simple fields and null for complex fields.|
|indexAnalyzer|[LexicalAnalyzerName](#lexicalanalyzername)|The name of the analyzer used at indexing time for the field. This option can be used only with searchable fields. It must be set together with searchAnalyzer and it cannot be set together with the analyzer option. This property cannot be set to the name of a language analyzer; use the analyzer property instead if you need a language analyzer. Once the analyzer is chosen, it cannot be changed for the field. Must be null for complex fields.|
|key|boolean|A value indicating whether the field uniquely identifies documents in the index. Exactly one top-level field in each index must be chosen as the key field and it must be of type Edm.String. Key fields can be used to look up documents directly and update or delete specific documents. Default is false for simple fields and null for complex fields.|
|name|string|The name of the field, which must be unique within the fields collection of the index or parent field.|
|retrievable|boolean|A value indicating whether the field can be returned in a search result. You can disable this option if you want to use a field (for example, margin) as a filter, sorting, or scoring mechanism but do not want the field to be visible to the end user. This property must be true for key fields, and it must be null for complex fields. This property can be changed on existing fields. Enabling this property does not cause any increase in index storage requirements. Default is true for simple fields, false for vector fields, and null for complex fields.|
|searchAnalyzer|[LexicalAnalyzerName](#lexicalanalyzername)|The name of the analyzer used at search time for the field. This option can be used only with searchable fields. It must be set together with indexAnalyzer and it cannot be set together with the analyzer option. This property cannot be set to the name of a language analyzer; use the analyzer property instead if you need a language analyzer. This analyzer can be updated on an existing field. Must be null for complex fields.|
|searchable|boolean|A value indicating whether the field is full-text searchable. This means it will undergo analysis such as word-breaking during indexing. If you set a searchable field to a value like "sunny day", internally it will be split into the individual tokens "sunny" and "day". This enables full-text searches for these terms. Fields of type Edm.String or Collection(Edm.String) are searchable by default. This property must be false for simple fields of other non-string data types, and it must be null for complex fields. Note: searchable fields consume extra space in your index to accommodate additional tokenized versions of the field value for full-text searches. If you want to save space in your index and you don't need a field to be included in searches, set searchable to false.|
|sortable|boolean|A value indicating whether to enable the field to be referenced in $orderby expressions. By default, the search engine sorts results by score, but in many experiences users will want to sort by fields in the documents. A simple field can be sortable only if it is single-valued (it has a single value in the scope of the parent document). Simple collection fields cannot be sortable, since they are multi-valued. Simple sub-fields of complex collections are also multi-valued, and therefore cannot be sortable. This is true whether it's an immediate parent field, or an ancestor field, that's the complex collection. Complex fields cannot be sortable and the sortable property must be null for such fields. The default for sortable is true for single-valued simple fields, false for multi-valued simple fields, and null for complex fields.|
|stored|boolean|An immutable value indicating whether the field will be persisted separately on disk to be returned in a search result. You can disable this option if you don't plan to return the field contents in a search response to save on storage overhead. This can only be set during index creation and only for vector fields. This property cannot be changed for existing fields or set as false for new fields. If this property is set as false, the property 'retrievable' must also be set to false. This property must be true or unset for key fields, for new fields, and for non-vector fields, and it must be null for complex fields. Disabling this property will reduce index storage requirements. The default is true for vector fields.|
|synonymMaps|string[]|A list of the names of synonym maps to associate with this field. This option can be used only with searchable fields. Currently only one synonym map per field is supported. Assigning a synonym map to a field ensures that query terms targeting that field are expanded at query-time using the rules in the synonym map. This attribute can be changed on existing fields. Must be null or an empty collection for complex fields.|
|type|[SearchFieldDataType](#searchfielddatatype)|The data type of the field.|
|vectorEncoding|[VectorEncodingFormat](#vectorencodingformat)|The encoding format to interpret the field contents.|
|vectorSearchProfile|string|The name of the vector search profile that specifies the algorithm and vectorizer to use when searching the vector field.|

### SearchFieldDataType

Enumeration

Defines the data type of a field in a search index.

|Value|Description|
|---|---|
|Edm.String|Indicates that a field contains a string.|
|Edm.Int32|Indicates that a field contains a 32-bit signed integer.|
|Edm.Int64|Indicates that a field contains a 64-bit signed integer.|
|Edm.Double|Indicates that a field contains an IEEE double-precision floating point number.|
|Edm.Boolean|Indicates that a field contains a Boolean value (true or false).|
|Edm.DateTimeOffset|Indicates that a field contains a date/time value, including timezone information.|
|Edm.GeographyPoint|Indicates that a field contains a geo-location in terms of longitude and latitude.|
|Edm.ComplexType|Indicates that a field contains one or more complex objects that in turn have sub-fields of other types.|
|Edm.Single|Indicates that a field contains a single-precision floating point number. This is only valid when used with Collection(Edm.Single).|
|Edm.Half|Indicates that a field contains a half-precision floating point number. This is only valid when used with Collection(Edm.Half).|
|Edm.Int16|Indicates that a field contains a 16-bit signed integer. This is only valid when used with Collection(Edm.Int16).|
|Edm.SByte|Indicates that a field contains a 8-bit signed integer. This is only valid when used with Collection(Edm.SByte).|
|Edm.Byte|Indicates that a field contains a 8-bit unsigned integer. This is only valid when used with Collection(Edm.Byte).|

### SearchIndex

Object

Represents a search index definition, which describes the fields and search behavior of an index.

|Name|Type|Description|
|---|---|---|
|@odata.etag|string|The ETag of the index.|
|analyzers|LexicalAnalyzer[]:<br><br>- [CustomAnalyzer](#customanalyzer)[]<br>- [LuceneStandardAnalyzer](#lucenestandardanalyzer)[]<br>- [PatternAnalyzer](#patternanalyzer)[]<br>- [StopAnalyzer](#stopanalyzer)[]|The analyzers for the index.|
|charFilters|CharFilter[]:<br><br>- [MappingCharFilter](#mappingcharfilter)[]<br>- [PatternReplaceCharFilter](#patternreplacecharfilter)[]|The character filters for the index.|
|corsOptions|[CorsOptions](#corsoptions)|Options to control Cross-Origin Resource Sharing (CORS) for the index.|
|defaultScoringProfile|string|The name of the scoring profile to use if none is specified in the query. If this property is not set and no scoring profile is specified in the query, then default scoring (tf-idf) will be used.|
|encryptionKey|[SearchResourceEncryptionKey](#searchresourceencryptionkey)|A description of an encryption key that you create in Azure Key Vault. This key is used to provide an additional level of encryption-at-rest for your data when you want full assurance that no one, not even Microsoft, can decrypt your data. Once you have encrypted your data, it will always remain encrypted. The search service will ignore attempts to set this property to null. You can change this property as needed if you want to rotate your encryption key; Your data will be unaffected. Encryption with customer-managed keys is not available for free search services, and is only available for paid services created on or after January 1, 2019.|
|fields|[SearchField](#searchfield)[]|The fields of the index.|
|name|string|The name of the index.|
|scoringProfiles|[ScoringProfile](#scoringprofile)[]|The scoring profiles for the index.|
|semantic|[SemanticSettings](#semanticsettings)|Defines parameters for a search index that influence semantic capabilities.|
|similarity|Similarity:<br><br>- [BM25Similarity](#bm25similarity)<br>- [ClassicSimilarity](#classicsimilarity)|The type of similarity algorithm to be used when scoring and ranking the documents matching a search query. The similarity algorithm can only be defined at index creation time and cannot be modified on existing indexes. If null, the ClassicSimilarity algorithm is used.|
|suggesters|[Suggester](#suggester)[]|The suggesters for the index.|
|tokenFilters|TokenFilter[]:<br><br>- [AsciiFoldingTokenFilter](#asciifoldingtokenfilter)[]<br>- [CjkBigramTokenFilter](#cjkbigramtokenfilter)[]<br>- [CommonGramTokenFilter](#commongramtokenfilter)[]<br>- [DictionaryDecompounderTokenFilter](#dictionarydecompoundertokenfilter)[]<br>- [EdgeNGramTokenFilter](#edgengramtokenfilter)[]<br>- [EdgeNGramTokenFilterV2](#edgengramtokenfilterv2)[]<br>- [ElisionTokenFilter](#elisiontokenfilter)[]<br>- [KeepTokenFilter](#keeptokenfilter)[]<br>- [KeywordMarkerTokenFilter](#keywordmarkertokenfilter)[]<br>- [LengthTokenFilter](#lengthtokenfilter)[]<br>- [LimitTokenFilter](#limittokenfilter)[]<br>- [NGramTokenFilter](#ngramtokenfilter)[]<br>- [NGramTokenFilterV2](#ngramtokenfilterv2)[]<br>- [PatternCaptureTokenFilter](#patterncapturetokenfilter)[]<br>- [PatternReplaceTokenFilter](#patternreplacetokenfilter)[]<br>- [PhoneticTokenFilter](#phonetictokenfilter)[]<br>- [ShingleTokenFilter](#shingletokenfilter)[]<br>- [SnowballTokenFilter](#snowballtokenfilter)[]<br>- [StemmerOverrideTokenFilter](#stemmeroverridetokenfilter)[]<br>- [StemmerTokenFilter](#stemmertokenfilter)[]<br>- [StopwordsTokenFilter](#stopwordstokenfilter)[]<br>- [SynonymTokenFilter](#synonymtokenfilter)[]<br>- [TruncateTokenFilter](#truncatetokenfilter)[]<br>- [UniqueTokenFilter](#uniquetokenfilter)[]<br>- [WordDelimiterTokenFilter](#worddelimitertokenfilter)[]|The token filters for the index.|
|tokenizers|LexicalTokenizer[]:<br><br>- [ClassicTokenizer](#classictokenizer)[]<br>- [EdgeNGramTokenizer](#edgengramtokenizer)[]<br>- [KeywordTokenizer](#keywordtokenizer)[]<br>- [KeywordTokenizerV2](#keywordtokenizerv2)[]<br>- [LuceneStandardTokenizer](#lucenestandardtokenizer)[]<br>- [LuceneStandardTokenizerV2](#lucenestandardtokenizerv2)[]<br>- [MicrosoftLanguageStemmingTokenizer](#microsoftlanguagestemmingtokenizer)[]<br>- [MicrosoftLanguageTokenizer](#microsoftlanguagetokenizer)[]<br>- [NGramTokenizer](#ngramtokenizer)[]<br>- [PathHierarchyTokenizerV2](#pathhierarchytokenizerv2)[]<br>- [PatternTokenizer](#patterntokenizer)[]<br>- [UaxUrlEmailTokenizer](#uaxurlemailtokenizer)[]|The tokenizers for the index.|
|vectorSearch|[VectorSearch](#vectorsearch)|Contains configuration options related to vector search.|

### SearchIndexerDataNoneIdentity

Object

Clears the identity property of a datasource.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.DataNoneIdentity|A URI fragment specifying the type of identity.|

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
|keyVaultKeyName|string|The name of your Azure Key Vault key to be used to encrypt your data at rest.|
|keyVaultKeyVersion|string|The version of your Azure Key Vault key to be used to encrypt your data at rest.|
|keyVaultUri|string|The URI of your Azure Key Vault, also referred to as DNS name, that contains the key to be used to encrypt your data at rest. An example URI might be `https://my-keyvault-name.vault.azure.net`.|

### SemanticConfiguration

Object

Defines a specific configuration to be used in the context of semantic capabilities.

|Name|Type|Description|
|---|---|---|
|name|string|The name of the semantic configuration.|
|prioritizedFields|[PrioritizedFields](#prioritizedfields)|Describes the title, content, and keyword fields to be used for semantic ranking, captions, highlights, and answers. At least one of the three sub properties (titleField, prioritizedKeywordsFields and prioritizedContentFields) need to be set.|

### SemanticField

Object

A field that is used as part of the semantic configuration.

|Name|Type|Description|
|---|---|---|
|fieldName|string||

### SemanticSettings

Object

Defines parameters for a search index that influence semantic capabilities.

|Name|Type|Description|
|---|---|---|
|configurations|[SemanticConfiguration](#semanticconfiguration)[]|The semantic configurations for the index.|
|defaultConfiguration|string|Allows you to set the name of a default semantic configuration in your index, making it optional to pass it on as a query parameter every time.|

### ShingleTokenFilter

Object

Creates combinations of tokens as a single token. This token filter is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.ShingleTokenFilter||A URI fragment specifying the type of token filter.|
|filterToken|string|_|The string to insert for each position at which there is no token. Default is an underscore ("_").|
|maxShingleSize|integer (int32)<br><br>minimum: 2|2|The maximum shingle size. Default and minimum value is 2.|
|minShingleSize|integer (int32)<br><br>minimum: 2|2|The minimum shingle size. Default and minimum value is 2. Must be less than the value of maxShingleSize.|
|name|string||The name of the token filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|
|outputUnigrams|boolean|True|A value indicating whether the output stream will contain the input tokens (unigrams) as well as shingles. Default is true.|
|outputUnigramsIfNoShingles|boolean|False|A value indicating whether to output unigrams for those times when no shingles are available. This property takes precedence when outputUnigrams is set to false. Default is false.|
|tokenSeparator|string||The string to use when joining adjacent tokens to form a shingle. Default is a single space (" ").|

### SnowballTokenFilter

Object

A filter that stems words using a Snowball-generated stemmer. This token filter is implemented using Apache Lucene.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.SnowballTokenFilter|A URI fragment specifying the type of token filter.|
|language|[SnowballTokenFilterLanguage](#snowballtokenfilterlanguage)|The language to use.|
|name|string|The name of the token filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|

### SnowballTokenFilterLanguage

Enumeration

The language to use for a Snowball token filter.

|Value|Description|
|---|---|
|armenian|Selects the Lucene Snowball stemming tokenizer for Armenian.|
|basque|Selects the Lucene Snowball stemming tokenizer for Basque.|
|catalan|Selects the Lucene Snowball stemming tokenizer for Catalan.|
|danish|Selects the Lucene Snowball stemming tokenizer for Danish.|
|dutch|Selects the Lucene Snowball stemming tokenizer for Dutch.|
|english|Selects the Lucene Snowball stemming tokenizer for English.|
|finnish|Selects the Lucene Snowball stemming tokenizer for Finnish.|
|french|Selects the Lucene Snowball stemming tokenizer for French.|
|german|Selects the Lucene Snowball stemming tokenizer for German.|
|german2|Selects the Lucene Snowball stemming tokenizer that uses the German variant algorithm.|
|hungarian|Selects the Lucene Snowball stemming tokenizer for Hungarian.|
|italian|Selects the Lucene Snowball stemming tokenizer for Italian.|
|kp|Selects the Lucene Snowball stemming tokenizer for Dutch that uses the Kraaij-Pohlmann stemming algorithm.|
|lovins|Selects the Lucene Snowball stemming tokenizer for English that uses the Lovins stemming algorithm.|
|norwegian|Selects the Lucene Snowball stemming tokenizer for Norwegian.|
|porter|Selects the Lucene Snowball stemming tokenizer for English that uses the Porter stemming algorithm.|
|portuguese|Selects the Lucene Snowball stemming tokenizer for Portuguese.|
|romanian|Selects the Lucene Snowball stemming tokenizer for Romanian.|
|russian|Selects the Lucene Snowball stemming tokenizer for Russian.|
|spanish|Selects the Lucene Snowball stemming tokenizer for Spanish.|
|swedish|Selects the Lucene Snowball stemming tokenizer for Swedish.|
|turkish|Selects the Lucene Snowball stemming tokenizer for Turkish.|

### StemmerOverrideTokenFilter

Object

Provides the ability to override other stemming filters with custom dictionary-based stemming. Any dictionary-stemmed terms will be marked as keywords so that they will not be stemmed with stemmers down the chain. Must be placed before any stemming filters. This token filter is implemented using Apache Lucene.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.StemmerOverrideTokenFilter|A URI fragment specifying the type of token filter.|
|name|string|The name of the token filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|
|rules|string[]|A list of stemming rules in the following format: "word => stem", for example: "ran => run".|

### StemmerTokenFilter

Object

Language specific stemming filter. This token filter is implemented using Apache Lucene.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.StemmerTokenFilter|A URI fragment specifying the type of token filter.|
|language|[StemmerTokenFilterLanguage](#stemmertokenfilterlanguage)|The language to use.|
|name|string|The name of the token filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|

### StemmerTokenFilterLanguage

Enumeration

The language to use for a stemmer token filter.

|Value|Description|
|---|---|
|arabic|Selects the Lucene stemming tokenizer for Arabic.|
|armenian|Selects the Lucene stemming tokenizer for Armenian.|
|basque|Selects the Lucene stemming tokenizer for Basque.|
|brazilian|Selects the Lucene stemming tokenizer for Portuguese (Brazil).|
|bulgarian|Selects the Lucene stemming tokenizer for Bulgarian.|
|catalan|Selects the Lucene stemming tokenizer for Catalan.|
|czech|Selects the Lucene stemming tokenizer for Czech.|
|danish|Selects the Lucene stemming tokenizer for Danish.|
|dutch|Selects the Lucene stemming tokenizer for Dutch.|
|dutchKp|Selects the Lucene stemming tokenizer for Dutch that uses the Kraaij-Pohlmann stemming algorithm.|
|english|Selects the Lucene stemming tokenizer for English.|
|lightEnglish|Selects the Lucene stemming tokenizer for English that does light stemming.|
|minimalEnglish|Selects the Lucene stemming tokenizer for English that does minimal stemming.|
|possessiveEnglish|Selects the Lucene stemming tokenizer for English that removes trailing possessives from words.|
|porter2|Selects the Lucene stemming tokenizer for English that uses the Porter2 stemming algorithm.|
|lovins|Selects the Lucene stemming tokenizer for English that uses the Lovins stemming algorithm.|
|finnish|Selects the Lucene stemming tokenizer for Finnish.|
|lightFinnish|Selects the Lucene stemming tokenizer for Finnish that does light stemming.|
|french|Selects the Lucene stemming tokenizer for French.|
|lightFrench|Selects the Lucene stemming tokenizer for French that does light stemming.|
|minimalFrench|Selects the Lucene stemming tokenizer for French that does minimal stemming.|
|galician|Selects the Lucene stemming tokenizer for Galician.|
|minimalGalician|Selects the Lucene stemming tokenizer for Galician that does minimal stemming.|
|german|Selects the Lucene stemming tokenizer for German.|
|german2|Selects the Lucene stemming tokenizer that uses the German variant algorithm.|
|lightGerman|Selects the Lucene stemming tokenizer for German that does light stemming.|
|minimalGerman|Selects the Lucene stemming tokenizer for German that does minimal stemming.|
|greek|Selects the Lucene stemming tokenizer for Greek.|
|hindi|Selects the Lucene stemming tokenizer for Hindi.|
|hungarian|Selects the Lucene stemming tokenizer for Hungarian.|
|lightHungarian|Selects the Lucene stemming tokenizer for Hungarian that does light stemming.|
|indonesian|Selects the Lucene stemming tokenizer for Indonesian.|
|irish|Selects the Lucene stemming tokenizer for Irish.|
|italian|Selects the Lucene stemming tokenizer for Italian.|
|lightItalian|Selects the Lucene stemming tokenizer for Italian that does light stemming.|
|sorani|Selects the Lucene stemming tokenizer for Sorani.|
|latvian|Selects the Lucene stemming tokenizer for Latvian.|
|norwegian|Selects the Lucene stemming tokenizer for Norwegian (Bokmål).|
|lightNorwegian|Selects the Lucene stemming tokenizer for Norwegian (Bokmål) that does light stemming.|
|minimalNorwegian|Selects the Lucene stemming tokenizer for Norwegian (Bokmål) that does minimal stemming.|
|lightNynorsk|Selects the Lucene stemming tokenizer for Norwegian (Nynorsk) that does light stemming.|
|minimalNynorsk|Selects the Lucene stemming tokenizer for Norwegian (Nynorsk) that does minimal stemming.|
|portuguese|Selects the Lucene stemming tokenizer for Portuguese.|
|lightPortuguese|Selects the Lucene stemming tokenizer for Portuguese that does light stemming.|
|minimalPortuguese|Selects the Lucene stemming tokenizer for Portuguese that does minimal stemming.|
|portugueseRslp|Selects the Lucene stemming tokenizer for Portuguese that uses the RSLP stemming algorithm.|
|romanian|Selects the Lucene stemming tokenizer for Romanian.|
|russian|Selects the Lucene stemming tokenizer for Russian.|
|lightRussian|Selects the Lucene stemming tokenizer for Russian that does light stemming.|
|spanish|Selects the Lucene stemming tokenizer for Spanish.|
|lightSpanish|Selects the Lucene stemming tokenizer for Spanish that does light stemming.|
|swedish|Selects the Lucene stemming tokenizer for Swedish.|
|lightSwedish|Selects the Lucene stemming tokenizer for Swedish that does light stemming.|
|turkish|Selects the Lucene stemming tokenizer for Turkish.|

### StopAnalyzer

Object

Divides text at non-letters; Applies the lowercase and stopword token filters. This analyzer is implemented using Apache Lucene.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.StopAnalyzer|A URI fragment specifying the type of analyzer.|
|name|string|The name of the analyzer. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|
|stopwords|string[]|A list of stopwords.|

### StopwordsList

Enumeration

Identifies a predefined list of language-specific stopwords.

|Value|Description|
|---|---|
|arabic|Selects the stopword list for Arabic.|
|armenian|Selects the stopword list for Armenian.|
|basque|Selects the stopword list for Basque.|
|brazilian|Selects the stopword list for Portuguese (Brazil).|
|bulgarian|Selects the stopword list for Bulgarian.|
|catalan|Selects the stopword list for Catalan.|
|czech|Selects the stopword list for Czech.|
|danish|Selects the stopword list for Danish.|
|dutch|Selects the stopword list for Dutch.|
|english|Selects the stopword list for English.|
|finnish|Selects the stopword list for Finnish.|
|french|Selects the stopword list for French.|
|galician|Selects the stopword list for Galician.|
|german|Selects the stopword list for German.|
|greek|Selects the stopword list for Greek.|
|hindi|Selects the stopword list for Hindi.|
|hungarian|Selects the stopword list for Hungarian.|
|indonesian|Selects the stopword list for Indonesian.|
|irish|Selects the stopword list for Irish.|
|italian|Selects the stopword list for Italian.|
|latvian|Selects the stopword list for Latvian.|
|norwegian|Selects the stopword list for Norwegian.|
|persian|Selects the stopword list for Persian.|
|portuguese|Selects the stopword list for Portuguese.|
|romanian|Selects the stopword list for Romanian.|
|russian|Selects the stopword list for Russian.|
|sorani|Selects the stopword list for Sorani.|
|spanish|Selects the stopword list for Spanish.|
|swedish|Selects the stopword list for Swedish.|
|thai|Selects the stopword list for Thai.|
|turkish|Selects the stopword list for Turkish.|

### StopwordsTokenFilter

Object

Removes stop words from a token stream. This token filter is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.StopwordsTokenFilter||A URI fragment specifying the type of token filter.|
|ignoreCase|boolean|False|A value indicating whether to ignore case. If true, all words are converted to lower case first. Default is false.|
|name|string||The name of the token filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|
|removeTrailing|boolean|True|A value indicating whether to ignore the last search term if it's a stop word. Default is true.|
|stopwords|string[]||The list of stopwords. This property and the stopwords list property cannot both be set.|
|stopwordsList|[StopwordsList](#stopwordslist)|english|A predefined list of stopwords to use. This property and the stopwords property cannot both be set. Default is English.|

### Suggester

Object

Defines how the Suggest API should apply to a group of fields in the index.

|Name|Type|Description|
|---|---|---|
|name|string|The name of the suggester.|
|searchMode|[SuggesterSearchMode](#suggestersearchmode)|A value indicating the capabilities of the suggester.|
|sourceFields|string[]|The list of field names to which the suggester applies. Each field must be searchable.|

### SuggesterSearchMode

Enumeration

A value indicating the capabilities of the suggester.

|Value|Description|
|---|---|
|analyzingInfixMatching|Matches consecutive whole terms and prefixes in a field. For example, for the field 'The fastest brown fox', the queries 'fast' and 'fastest brow' would both match.|

### SynonymTokenFilter

Object

Matches single or multi-word synonyms in a token stream. This token filter is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.SynonymTokenFilter||A URI fragment specifying the type of token filter.|
|expand|boolean|True|A value indicating whether all words in the list of synonyms (if => notation is not used) will map to one another. If true, all words in the list of synonyms (if => notation is not used) will map to one another. The following list: incredible, unbelievable, fabulous, amazing is equivalent to: incredible, unbelievable, fabulous, amazing => incredible, unbelievable, fabulous, amazing. If false, the following list: incredible, unbelievable, fabulous, amazing will be equivalent to: incredible, unbelievable, fabulous, amazing => incredible. Default is true.|
|ignoreCase|boolean|False|A value indicating whether to case-fold input for matching. Default is false.|
|name|string||The name of the token filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|
|synonyms|string[]||A list of synonyms in following one of two formats: 1. incredible, unbelievable, fabulous => amazing - all terms on the left side of => symbol will be replaced with all terms on its right side; 2. incredible, unbelievable, fabulous, amazing - comma separated list of equivalent words. Set the expand option to change how this list is interpreted.|

### TagScoringFunction

Object

Defines a function that boosts scores of documents with string values matching a given list of tags.

|Name|Type|Description|
|---|---|---|
|boost|number (double)|A multiplier for the raw score. Must be a positive number not equal to 1.0.|
|fieldName|string|The name of the field used as input to the scoring function.|
|interpolation|[ScoringFunctionInterpolation](#scoringfunctioninterpolation)|A value indicating how boosting will be interpolated across document scores; defaults to "Linear".|
|tag|[TagScoringParameters](#tagscoringparameters)|Parameter values for the tag scoring function.|
|type|string:<br><br>tag|Indicates the type of function to use. Valid values include magnitude, freshness, distance, and tag. The function type must be lower case.|

### TagScoringParameters

Object

Provides parameter values to a tag scoring function.

|Name|Type|Description|
|---|---|---|
|tagsParameter|string|The name of the parameter passed in search queries to specify the list of tags to compare against the target field.|

### TextWeights

Object

Defines weights on index fields for which matches should boost scoring in search queries.

|Name|Type|Description|
|---|---|---|
|weights|object|The dictionary of per-field weights to boost document scoring. The keys are field names and the values are the weights for each field.|

### TokenCharacterKind

Enumeration

Represents classes of characters on which a token filter can operate.

|Value|Description|
|---|---|
|letter|Keeps letters in tokens.|
|digit|Keeps digits in tokens.|
|whitespace|Keeps whitespace in tokens.|
|punctuation|Keeps punctuation in tokens.|
|symbol|Keeps symbols in tokens.|

### TokenFilterName

Enumeration

Defines the names of all token filters supported by the search engine.

|Value|Description|
|---|---|
|arabic_normalization|A token filter that applies the Arabic normalizer to normalize the orthography. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/ar/ArabicNormalizationFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/ar/ArabicNormalizationFilter.html)|
|apostrophe|Strips all characters after an apostrophe (including the apostrophe itself). See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/tr/ApostropheFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/tr/ApostropheFilter.html)|
|asciifolding|Converts alphabetic, numeric, and symbolic Unicode characters which are not in the first 127 ASCII characters (the "Basic Latin" Unicode block) into their ASCII equivalents, if such equivalents exist. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/miscellaneous/ASCIIFoldingFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/miscellaneous/ASCIIFoldingFilter.html)|
|cjk_bigram|Forms bigrams of CJK terms that are generated from the standard tokenizer. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/cjk/CJKBigramFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/cjk/CJKBigramFilter.html)|
|cjk_width|Normalizes CJK width differences. Folds fullwidth ASCII variants into the equivalent basic Latin, and half-width Katakana variants into the equivalent Kana. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/cjk/CJKWidthFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/cjk/CJKWidthFilter.html)|
|classic|Removes English possessives, and dots from acronyms. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/standard/ClassicFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/standard/ClassicFilter.html)|
|common_grams|Construct bigrams for frequently occurring terms while indexing. Single terms are still indexed too, with bigrams overlaid. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/commongrams/CommonGramsFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/commongrams/CommonGramsFilter.html)|
|edgeNGram_v2|Generates n-grams of the given size(s) starting from the front or the back of an input token. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/ngram/EdgeNGramTokenFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/ngram/EdgeNGramTokenFilter.html)|
|elision|Removes elisions. For example, "l'avion" (the plane) will be converted to "avion" (plane). See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/util/ElisionFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/util/ElisionFilter.html)|
|german_normalization|Normalizes German characters according to the heuristics of the German2 snowball algorithm. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/de/GermanNormalizationFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/de/GermanNormalizationFilter.html)|
|hindi_normalization|Normalizes text in Hindi to remove some differences in spelling variations. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/hi/HindiNormalizationFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/hi/HindiNormalizationFilter.html)|
|indic_normalization|Normalizes the Unicode representation of text in Indian languages. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/in/IndicNormalizationFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/in/IndicNormalizationFilter.html)|
|keyword_repeat|Emits each incoming token twice, once as keyword and once as non-keyword. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/miscellaneous/KeywordRepeatFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/miscellaneous/KeywordRepeatFilter.html)|
|kstem|A high-performance kstem filter for English. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/en/KStemFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/en/KStemFilter.html)|
|length|Removes words that are too long or too short. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/miscellaneous/LengthFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/miscellaneous/LengthFilter.html)|
|limit|Limits the number of tokens while indexing. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/miscellaneous/LimitTokenCountFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/miscellaneous/LimitTokenCountFilter.html)|
|lowercase|Normalizes token text to lower case. See [https://lucene.apache.org/core/6_6_1/analyzers-common/org/apache/lucene/analysis/core/LowerCaseFilter.html](https://lucene.apache.org/core/6_6_1/analyzers-common/org/apache/lucene/analysis/core/LowerCaseFilter.html)|
|nGram_v2|Generates n-grams of the given size(s). See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/ngram/NGramTokenFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/ngram/NGramTokenFilter.html)|
|persian_normalization|Applies normalization for Persian. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/fa/PersianNormalizationFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/fa/PersianNormalizationFilter.html)|
|phonetic|Create tokens for phonetic matches. See [https://lucene.apache.org/core/4_10_3/analyzers-phonetic/org/apache/lucene/analysis/phonetic/package-tree.html](https://lucene.apache.org/core/4_10_3/analyzers-phonetic/org/apache/lucene/analysis/phonetic/package-tree.html)|
|porter_stem|Uses the Porter stemming algorithm to transform the token stream. See [http://tartarus.org/~martin/PorterStemmer](http://tartarus.org/%7Emartin/PorterStemmer)|
|reverse|Reverses the token string. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/reverse/ReverseStringFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/reverse/ReverseStringFilter.html)|
|scandinavian_normalization|Normalizes use of the interchangeable Scandinavian characters. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/miscellaneous/ScandinavianNormalizationFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/miscellaneous/ScandinavianNormalizationFilter.html)|
|scandinavian_folding|Folds Scandinavian characters åÅäæÄÆ->a and öÖøØ->o. It also discriminates against use of double vowels aa, ae, ao, oe and oo, leaving just the first one. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/miscellaneous/ScandinavianFoldingFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/miscellaneous/ScandinavianFoldingFilter.html)|
|shingle|Creates combinations of tokens as a single token. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/shingle/ShingleFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/shingle/ShingleFilter.html)|
|snowball|A filter that stems words using a Snowball-generated stemmer. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/snowball/SnowballFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/snowball/SnowballFilter.html)|
|sorani_normalization|Normalizes the Unicode representation of Sorani text. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/ckb/SoraniNormalizationFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/ckb/SoraniNormalizationFilter.html)|
|stemmer|Language specific stemming filter. See [https://learn.microsoft.com/rest/api/searchservice/Custom-analyzers-in-Azure-Search#TokenFilters](https://learn.microsoft.com/en-us/rest/api/searchservice/Custom-analyzers-in-Azure-Search#TokenFilters)|
|stopwords|Removes stop words from a token stream. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/core/StopFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/core/StopFilter.html)|
|trim|Trims leading and trailing whitespace from tokens. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/miscellaneous/TrimFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/miscellaneous/TrimFilter.html)|
|truncate|Truncates the terms to a specific length. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/miscellaneous/TruncateTokenFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/miscellaneous/TruncateTokenFilter.html)|
|unique|Filters out tokens with same text as the previous token. See [http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/miscellaneous/RemoveDuplicatesTokenFilter.html](http://lucene.apache.org/core/4_10_3/analyzers-common/org/apache/lucene/analysis/miscellaneous/RemoveDuplicatesTokenFilter.html)|
|uppercase|Normalizes token text to upper case. See [https://lucene.apache.org/core/6_6_1/analyzers-common/org/apache/lucene/analysis/core/UpperCaseFilter.html](https://lucene.apache.org/core/6_6_1/analyzers-common/org/apache/lucene/analysis/core/UpperCaseFilter.html)|
|word_delimiter|Splits words into subwords and performs optional transformations on subword groups.|

### TruncateTokenFilter

Object

Truncates the terms to a specific length. This token filter is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.TruncateTokenFilter||A URI fragment specifying the type of token filter.|
|length|integer (int32)<br><br>maximum: 300|300|The length at which terms will be truncated. Default and maximum is 300.|
|name|string||The name of the token filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|

### UaxUrlEmailTokenizer

Object

Tokenizes urls and emails as one token. This tokenizer is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.UaxUrlEmailTokenizer||A URI fragment specifying the type of tokenizer.|
|maxTokenLength|integer (int32)<br><br>maximum: 300|255|The maximum token length. Default is 255. Tokens longer than the maximum length are split. The maximum token length that can be used is 300 characters.|
|name|string||The name of the tokenizer. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|

### UniqueTokenFilter

Object

Filters out tokens with same text as the previous token. This token filter is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.UniqueTokenFilter||A URI fragment specifying the type of token filter.|
|name|string||The name of the token filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|
|onlyOnSamePosition|boolean|False|A value indicating whether to remove duplicates only at the same position. Default is false.|

### VectorEncodingFormat

Enumeration

The encoding format for interpreting vector field contents.

|Value|Description|
|---|---|
|packedBit|Encoding format representing bits packed into a wider data type.|

### VectorSearch

Object

Contains configuration options related to vector search.

|Name|Type|Description|
|---|---|---|
|algorithms|VectorSearchAlgorithmConfiguration[]:<br><br>- [ExhaustiveKnnVectorSearchAlgorithmConfiguration](#exhaustiveknnvectorsearchalgorithmconfiguration)[]<br>- [HnswVectorSearchAlgorithmConfiguration](#hnswvectorsearchalgorithmconfiguration)[]|Contains configuration options specific to the algorithm used during indexing or querying.|
|compressions|VectorSearchCompressionConfiguration[]:<br><br>- [BinaryQuantizationVectorSearchCompressionConfiguration](#binaryquantizationvectorsearchcompressionconfiguration)[]<br>- [ScalarQuantizationVectorSearchCompressionConfiguration](#scalarquantizationvectorsearchcompressionconfiguration)[]|Contains configuration options specific to the compression method used during indexing or querying.|
|profiles|[VectorSearchProfile](#vectorsearchprofile)[]|Defines combinations of configurations to use with vector search.|
|vectorizers|VectorSearchVectorizer[]:<br><br>- [AzureOpenAIVectorizer](#azureopenaivectorizer)[]<br>- [WebApiVectorizer](#webapivectorizer)[]|Contains configuration options on how to vectorize text vector queries.|

### VectorSearchAlgorithmKind

Enumeration

The algorithm used for indexing and querying.

|Value|Description|
|---|---|
|hnsw|HNSW (Hierarchical Navigable Small World), a type of approximate nearest neighbors algorithm.|
|exhaustiveKnn|Exhaustive KNN algorithm which will perform brute-force search.|

### VectorSearchAlgorithmMetric

Enumeration

The similarity metric to use for vector comparisons. It is recommended to choose the same similarity metric as the embedding model was trained on.

|Value|Description|
|---|---|
|cosine|Measures the angle between vectors to quantify their similarity, disregarding magnitude. The smaller the angle, the closer the similarity.|
|euclidean|Computes the straight-line distance between vectors in a multi-dimensional space. The smaller the distance, the closer the similarity.|
|dotProduct|Calculates the sum of element-wise products to gauge alignment and magnitude similarity. The larger and more positive, the closer the similarity.|
|hamming|Only applicable to bit-packed binary data types. Determines dissimilarity by counting differing positions in binary vectors. The fewer differences, the closer the similarity.|

### VectorSearchCompressionKind

Enumeration

The compression method used for indexing and querying.

|Value|Description|
|---|---|
|scalarQuantization|Scalar Quantization, a type of compression method. In scalar quantization, the original vectors values are compressed to a narrower type by discretizing and representing each component of a vector using a reduced set of quantized values, thereby reducing the overall data size.|
|binaryQuantization|Binary Quantization, a type of compression method. In binary quantization, the original vectors values are compressed to the narrower binary type by discretizing and representing each component of a vector using binary values, thereby reducing the overall data size.|

### VectorSearchCompressionTargetDataType

Enumeration

The quantized data type of compressed vector values.

### VectorSearchProfile

Object

Defines a combination of configurations to use with vector search.

|Name|Type|Description|
|---|---|---|
|algorithm|string|The name of the vector search algorithm configuration that specifies the algorithm and optional parameters.|
|compression|string|The name of the compression method configuration that specifies the compression method and optional parameters.|
|name|string|The name to associate with this particular vector search profile.|
|vectorizer|string|The name of the vectorization being configured for use with vector search.|

### VectorSearchVectorizerKind

Enumeration

The vectorization method to be used during query time.

|Value|Description|
|---|---|
|azureOpenAI|Generate embeddings using an Azure OpenAI resource at query time.|
|customWebApi|Generate embeddings using a custom web endpoint at query time.|

### WebApiParameters

Object

Specifies the properties for connecting to a user-defined vectorizer.

|Name|Type|Description|
|---|---|---|
|authIdentity|SearchIndexerDataIdentity:<br><br>- [SearchIndexerDataNoneIdentity](#searchindexerdatanoneidentity)<br>- [SearchIndexerDataUserAssignedIdentity](#searchindexerdatauserassignedidentity)|The user-assigned managed identity used for outbound connections. If an authResourceId is provided and it's not specified, the system-assigned managed identity is used. On updates to the indexer, if the identity is unspecified, the value remains unchanged. If set to "none", the value of this property is cleared.|
|authResourceId|string|Applies to custom endpoints that connect to external code in an Azure function or some other application that provides the transformations. This value should be the application ID created for the function or app when it was registered with Azure Active Directory. When specified, the vectorization connects to the function or app using a managed ID (either system or user-assigned) of the search service and the access token of the function or app, using this value as the resource id for creating the scope of the access token.|
|httpHeaders|object|The headers required to make the HTTP request.|
|httpMethod|string|The method for the HTTP request.|
|timeout|string (duration)|The desired timeout for the request. Default is 30 seconds.|
|uri|string (uri)|The URI of the Web API providing the vectorizer.|

### WebApiVectorizer

Object

Specifies a user-defined vectorizer for generating the vector embedding of a query string. Integration of an external vectorizer is achieved using the custom Web API interface of a skillset.

|Name|Type|Description|
|---|---|---|
|customWebApiParameters|[WebApiParameters](#webapiparameters)|Specifies the properties of the user-defined vectorizer.|
|kind|string:<br><br>customWebApi|The name of the kind of vectorization method being configured for use with vector search.|
|name|string|The name to associate with this particular vectorization method.|

### WordDelimiterTokenFilter

Object

Splits words into subwords and performs optional transformations on subword groups. This token filter is implemented using Apache Lucene.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.WordDelimiterTokenFilter||A URI fragment specifying the type of token filter.|
|catenateAll|boolean|False|A value indicating whether all subword parts will be catenated. For example, if this is set to true, "Azure-Search-1" becomes "AzureSearch1". Default is false.|
|catenateNumbers|boolean|False|A value indicating whether maximum runs of number parts will be catenated. For example, if this is set to true, "1-2" becomes "12". Default is false.|
|catenateWords|boolean|False|A value indicating whether maximum runs of word parts will be catenated. For example, if this is set to true, "Azure-Search" becomes "AzureSearch". Default is false.|
|generateNumberParts|boolean|True|A value indicating whether to generate number subwords. Default is true.|
|generateWordParts|boolean|True|A value indicating whether to generate part words. If set, causes parts of words to be generated; for example "AzureSearch" becomes "Azure" "Search". Default is true.|
|name|string||The name of the token filter. It must only contain letters, digits, spaces, dashes or underscores, can only start and end with alphanumeric characters, and is limited to 128 characters.|
|preserveOriginal|boolean|False|A value indicating whether original words will be preserved and added to the subword list. Default is false.|
|protectedWords|string[]||A list of tokens to protect from being delimited.|
|splitOnCaseChange|boolean|True|A value indicating whether to split words on caseChange. For example, if this is set to true, "AzureSearch" becomes "Azure" "Search". Default is true.|
|splitOnNumerics|boolean|True|A value indicating whether to split on numbers. For example, if this is set to true, "Azure1Search" becomes "Azure" "1" "Search". Default is true.|
|stemEnglishPossessive|boolean|True|A value indicating whether to remove trailing "'s" for each subword. Default is true.|
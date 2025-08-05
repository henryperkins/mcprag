## In this article

1. [URI Parameters](#uri-parameters)
2. [Request Header](#request-headers)
3. [Request Body](#request-body)
4. [Responses](#response)
5. [Examples](#examples)
6. [Definitions](#definitions)

Creates a new skillset in a search service.

```
POST {endpoint}/skillsets?api-version=2025-05-01-preview
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
|name|True|string|The name of the skillset.|
|skills|True|SearchIndexerSkill[]:<br><br>- [ConditionalSkill](#conditionalskill)[]<br>- [KeyPhraseExtractionSkill](#keyphraseextractionskill)[]<br>- [OcrSkill](#ocrskill)[]<br>- [ImageAnalysisSkill](#imageanalysisskill)[]<br>- [LanguageDetectionSkill](#languagedetectionskill)[]<br>- [ShaperSkill](#shaperskill)[]<br>- [MergeSkill](#mergeskill)[]<br>- [EntityRecognitionSkill](#entityrecognitionskill)[]<br>- [SentimentSkill](#sentimentskill)[]<br>- [SentimentSkillV3](#sentimentskillv3)[]<br>- [EntityLinkingSkill](#entitylinkingskill)[]<br>- [EntityRecognitionSkillV3](#entityrecognitionskillv3)[]<br>- [PIIDetectionSkill](#piidetectionskill)[]<br>- [SplitSkill](#splitskill)[]<br>- [CustomEntityLookupSkill](#customentitylookupskill)[]<br>- [TextTranslationSkill](#texttranslationskill)[]<br>- [DocumentExtractionSkill](#documentextractionskill)[]<br>- [DocumentIntelligenceLayoutSkill](#documentintelligencelayoutskill)[]<br>- [WebApiSkill](#webapiskill)[]<br>- [AmlSkill](#amlskill)[]<br>- [AzureOpenAIEmbeddingSkill](#azureopenaiembeddingskill)[]<br>- [VisionVectorizeSkill](#visionvectorizeskill)[]<br>- [ChatCompletionSkill](#chatcompletionskill)[]|A list of skills in the skillset.|
|@odata.etag||string|The ETag of the skillset.|
|cognitiveServices||CognitiveServicesAccount:<br><br>- [DefaultCognitiveServicesAccount](#defaultcognitiveservicesaccount)<br>- [CognitiveServicesAccountKey](#cognitiveservicesaccountkey)<br>- [AIServicesAccountKey](#aiservicesaccountkey)<br>- [AIServicesAccountIdentity](#aiservicesaccountidentity)|Details about the Azure AI service to be used when running skills.|
|description||string|The description of the skillset.|
|encryptionKey||[SearchResourceEncryptionKey](#searchresourceencryptionkey)|A description of an encryption key that you create in Azure Key Vault. This key is used to provide an additional level of encryption-at-rest for your skillset definition when you want full assurance that no one, not even Microsoft, can decrypt your skillset definition. Once you have encrypted your skillset definition, it will always remain encrypted. The search service will ignore attempts to set this property to null. You can change this property as needed if you want to rotate your encryption key; Your skillset definition will be unaffected. Encryption with customer-managed keys is not available for free search services, and is only available for paid services created on or after January 1, 2019.|
|indexProjections||[SearchIndexerIndexProjections](#searchindexerindexprojections)|Definition of additional projections to secondary search index(es).|
|knowledgeStore||[SearchIndexerKnowledgeStore](#searchindexerknowledgestore)|Definition of additional projections to Azure blob, table, or files, of enriched data.|

## Responses

|Name|Type|Description|
|---|---|---|
|201 Created|[SearchIndexerSkillset](#searchindexerskillset)|The skillset is successfully created.|
|Other Status Codes|[ErrorResponse](#errorresponse)|Error response.|

## Examples

### SearchServiceCreateSkillset

#### Sample request

- [HTTP](#tabpanel_1_HTTP)

```
POST https://previewexampleservice.search.windows.net/skillsets?api-version=2025-05-01-preview


{
  "name": "tempskillset",
  "description": "Skillset for extracting entities and more",
  "skills": [
    {
      "@odata.type": "#Microsoft.Skills.Text.LanguageDetectionSkill",
      "name": "skill2",
      "inputs": [
        {
          "name": "text",
          "source": "/document/content"
        },
        {
          "name": "countryHint",
          "source": "/document/countryHint"
        }
      ],
      "outputs": [
        {
          "name": "languageCode",
          "targetName": "languageCode"
        }
      ]
    },
    {
      "textSplitMode": "pages",
      "maximumPageLength": 4000,
      "unit": "azureOpenAITokens",
      "azureOpenAITokenizerParameters": {
        "encoderModelName": "cl100k_base",
        "allowedSpecialTokens": [
          "[START]",
          "[END]"
        ]
      },
      "@odata.type": "#Microsoft.Skills.Text.SplitSkill",
      "name": "skill3",
      "inputs": [
        {
          "name": "text",
          "source": "/document/content"
        },
        {
          "name": "languageCode",
          "source": "/document/languageCode"
        }
      ],
      "outputs": [
        {
          "name": "textItems",
          "targetName": "pages"
        }
      ]
    },
    {
      "@odata.type": "#Microsoft.Skills.Text.KeyPhraseExtractionSkill",
      "name": "skill4",
      "context": "/document/pages/*",
      "inputs": [
        {
          "name": "text",
          "source": "/document/content"
        },
        {
          "name": "languageCode",
          "source": "/document/languageCode"
        }
      ],
      "outputs": [
        {
          "name": "keyPhrases",
          "targetName": "keyPhrases"
        }
      ]
    },
    {
      "uri": "https://contoso.example.org/",
      "httpMethod": "POST",
      "timeout": "PT5S",
      "@odata.type": "#Microsoft.Skills.Custom.WebApiSkill",
      "name": "skill5",
      "inputs": [
        {
          "name": "text",
          "source": "/document/content"
        },
        {
          "name": "languageCode",
          "source": "/document/languageCode"
        }
      ],
      "outputs": [
        {
          "name": "customresult",
          "targetName": "result"
        }
      ]
    },
    {
      "outputMode": "oneToMany",
      "markdownHeaderDepth": "h3",
      "@odata.type": "#Microsoft.Skills.Util.DocumentIntelligenceLayoutSkill",
      "name": "docIntelligenceLayoutSkill",
      "context": "/document",
      "inputs": [
        {
          "name": "file_data",
          "source": "/document/content"
        }
      ],
      "outputs": [
        {
          "name": "markdown_document",
          "targetName": "markdown_document"
        }
      ]
    },
    {
      "outputFormat": "text",
      "outputMode": "oneToMany",
      "extractionOptions": [
        "images",
        "locationMetadata"
      ],
      "chunkingProperties": {
        "unit": "characters",
        "maximumLength": 500,
        "overlapLength": 50
      },
      "@odata.type": "#Microsoft.Skills.Util.DocumentIntelligenceLayoutSkill",
      "name": "docIntelligenceLayoutSkill#2",
      "context": "/document",
      "inputs": [
        {
          "name": "file_data",
          "source": "/document/content"
        }
      ],
      "outputs": [
        {
          "name": "text_sections",
          "targetName": "text_sections"
        },
        {
          "name": "normalized_images",
          "targetName": "normalized_images"
        }
      ]
    },
    {
      "apiKey": "<api-key>",
      "commonModelParameters": {
        "model": "gpt-4o",
        "frequencyPenalty": 0,
        "presencePenalty": 0,
        "maxTokens": 0,
        "temperature": 0,
        "seed": 0,
        "stop": []
      },
      "extraParameters": {
        "safe_mode": true
      },
      "extraParametersBehavior": "error",
      "responseFormat": {
        "type": "jsonSchema",
        "jsonSchemaProperties": {
          "name": "Some Name",
          "description": "Some Description",
          "strict": true,
          "schema": {
            "type": "object",
            "properties": "{\"steps\": {\"type\": \"array\", \"description\": \"A list of reasoning steps.\", \"items\": {\"type\": \"string\"}}, \"answer\": {\"type\": \"string\", \"description\": \"The final answer.\"}}",
            "required": [
              "steps",
              "answer"
            ],
            "additionalProperties": false
          }
        }
      },
      "uri": "https://azs-grok-aoai.openai.azure.com/openai/deployments/azs-grok-gpt-4o/chat/completions",
      "timeout": "PT30S",
      "degreeOfParallelism": 5,
      "@odata.type": "#Microsoft.Skills.Custom.ChatCompletionSkill",
      "name": "chatCompletionSkill",
      "context": "/document/normalized_images/*",
      "inputs": [
        {
          "name": "text",
          "source": "/document/content"
        },
        {
          "name": "systemMessage",
          "source": "/document/system_message"
        },
        {
          "name": "userMessage",
          "source": "/document/user_message"
        },
        {
          "name": "image",
          "source": "/document/normalized_images/*"
        },
        {
          "name": "imageDetail",
          "source": "/document/detail"
        }
      ],
      "outputs": [
        {
          "name": "response",
          "targetName": "response"
        }
      ]
    }
  ],
  "cognitiveServices": {
    "key": "myKey",
    "subdomainUrl": "https://mySubdomainName.cognitiveservices.azure.com",
    "@odata.type": "#Microsoft.Azure.Search.AIServicesByKey",
    "description": "Description of the Azure AI service resource attached to a skillset"
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
  "name": "tempskillset",
  "description": "Skillset for extracting entities and more",
  "skills": [
    {
      "@odata.type": "#Microsoft.Skills.Text.LanguageDetectionSkill",
      "name": "skill2",
      "inputs": [
        {
          "name": "text",
          "source": "/document/content",
          "inputs": []
        },
        {
          "name": "countryHint",
          "source": "/document/countryHint",
          "inputs": []
        }
      ],
      "outputs": [
        {
          "name": "languageCode",
          "targetName": "languageCode"
        }
      ]
    },
    {
      "@odata.type": "#Microsoft.Skills.Text.SplitSkill",
      "name": "skill3",
      "textSplitMode": "pages",
      "maximumPageLength": 4000,
      "unit": "azureOpenAITokens",
      "inputs": [
        {
          "name": "text",
          "source": "/document/content",
          "inputs": []
        },
        {
          "name": "languageCode",
          "source": "/document/languageCode",
          "inputs": []
        }
      ],
      "outputs": [
        {
          "name": "textItems",
          "targetName": "pages"
        }
      ],
      "azureOpenAITokenizerParameters": {
        "encoderModelName": "cl100k_base",
        "allowedSpecialTokens": [
          "[START]",
          "[END]"
        ]
      }
    },
    {
      "@odata.type": "#Microsoft.Skills.Text.KeyPhraseExtractionSkill",
      "name": "skill4",
      "context": "/document/pages/*",
      "inputs": [
        {
          "name": "text",
          "source": "/document/content",
          "inputs": []
        },
        {
          "name": "languageCode",
          "source": "/document/languageCode",
          "inputs": []
        }
      ],
      "outputs": [
        {
          "name": "keyPhrases",
          "targetName": "keyPhrases"
        }
      ]
    },
    {
      "@odata.type": "#Microsoft.Skills.Custom.WebApiSkill",
      "name": "skill5",
      "uri": "https://contoso.example.org/",
      "httpMethod": "POST",
      "timeout": "PT5S",
      "inputs": [
        {
          "name": "text",
          "source": "/document/content",
          "inputs": []
        },
        {
          "name": "languageCode",
          "source": "/document/languageCode",
          "inputs": []
        }
      ],
      "outputs": [
        {
          "name": "customresult",
          "targetName": "result"
        }
      ]
    },
    {
      "@odata.type": "#Microsoft.Skills.Util.DocumentIntelligenceLayoutSkill",
      "name": "docIntelligenceLayoutSkill",
      "context": "/document",
      "outputMode": "oneToMany",
      "markdownHeaderDepth": "h3",
      "extractionOptions": [],
      "inputs": [
        {
          "name": "file_data",
          "source": "/document/content",
          "inputs": []
        }
      ],
      "outputs": [
        {
          "name": "markdown_document",
          "targetName": "markdown_document"
        }
      ]
    },
    {
      "@odata.type": "#Microsoft.Skills.Util.DocumentIntelligenceLayoutSkill",
      "name": "docIntelligenceLayoutSkill#2",
      "context": "/document",
      "outputMode": "oneToMany",
      "outputFormat": "text",
      "extractionOptions": [
        "images",
        "locationMetadata"
      ],
      "inputs": [
        {
          "name": "file_data",
          "source": "/document/content",
          "inputs": []
        }
      ],
      "outputs": [
        {
          "name": "text_sections",
          "targetName": "text_sections"
        },
        {
          "name": "normalized_images",
          "targetName": "normalized_images"
        }
      ],
      "chunkingProperties": {
        "unit": "characters",
        "maximumLength": 500,
        "overlapLength": 50
      }
    },
    {
      "@odata.type": "#Microsoft.Skills.Custom.ChatCompletionSkill",
      "name": "chatCompletionSkill",
      "context": "/document/normalized_images/*",
      "uri": "https://azs-grok-aoai.openai.azure.com/openai/deployments/azs-grok-gpt-4o/chat/completions",
      "timeout": "PT30S",
      "degreeOfParallelism": 5,
      "apiKey": "<api-key>",
      "extraParametersBehavior": "error",
      "inputs": [
        {
          "name": "text",
          "source": "/document/content",
          "inputs": []
        },
        {
          "name": "systemMessage",
          "source": "/document/system_message",
          "inputs": []
        },
        {
          "name": "userMessage",
          "source": "/document/user_message",
          "inputs": []
        },
        {
          "name": "image",
          "source": "/document/normalized_images/*",
          "inputs": []
        },
        {
          "name": "imageDetail",
          "source": "/document/detail",
          "inputs": []
        }
      ],
      "outputs": [
        {
          "name": "response",
          "targetName": "response"
        }
      ],
      "commonModelParameters": {
        "model": "gpt-4o",
        "frequencyPenalty": 0,
        "presencePenalty": 0,
        "maxTokens": 0,
        "temperature": 0,
        "seed": 0,
        "stop": []
      },
      "extraParameters": {
        "safe_mode": true
      },
      "responseFormat": {
        "type": "jsonSchema",
        "jsonSchemaProperties": {
          "name": "Some Name",
          "description": "Some Description",
          "strict": true,
          "schema": {
            "type": "object",
            "additionalProperties": false,
            "required": [
              "steps",
              "answer"
            ],
            "properties": "{\"steps\": {\"type\": \"array\", \"description\": \"A list of reasoning steps.\", \"items\": {\"type\": \"string\"}}, \"answer\": {\"type\": \"string\", \"description\": \"The final answer.\"}}"
          }
        }
      }
    }
  ],
  "cognitiveServices": {
    "@odata.type": "#Microsoft.Azure.Search.AIServicesByKey",
    "description": "Description of the Azure AI service resource attached to a skillset",
    "key": "myKey",
    "subdomainUrl": "https://mySubdomainName.cognitiveservices.azure.com"
  },
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

## Definitions

|Name|Description|
|---|---|
|[AIServicesAccountIdentity](#aiservicesaccountidentity)|The multi-region account of an Azure AI service resource that's attached to a skillset.|
|[AIServicesAccountKey](#aiservicesaccountkey)|The account key of an Azure AI service resource that's attached to a skillset, to be used with the resource's subdomain.|
|[AmlSkill](#amlskill)|The AML skill allows you to extend AI enrichment with a custom Azure Machine Learning (AML) model. Once an AML model is trained and deployed, an AML skill integrates it into AI enrichment.|
|[AzureActiveDirectoryApplicationCredentials](#azureactivedirectoryapplicationcredentials)|Credentials of a registered application created for your search service, used for authenticated access to the encryption keys stored in Azure Key Vault.|
|[AzureOpenAIEmbeddingSkill](#azureopenaiembeddingskill)|Allows you to generate a vector embedding for a given text input using the Azure OpenAI resource.|
|[AzureOpenAIModelName](#azureopenaimodelname)|The Azure Open AI model name that will be called.|
|[AzureOpenAITokenizerParameters](#azureopenaitokenizerparameters)||
|[ChatCompletionCommonModelParameters](#chatcompletioncommonmodelparameters)|Common language model parameters for Chat Completions. If omitted, default values are used.|
|[ChatCompletionExtraParametersBehavior](#chatcompletionextraparametersbehavior)|Specifies how 'extraParameters' should be handled by Azure AI Foundry. Defaults to 'error'.|
|[ChatCompletionResponseFormat](#chatcompletionresponseformat)|Determines how the language model's response should be serialized. Defaults to 'text'.|
|[ChatCompletionResponseFormatType](#chatcompletionresponseformattype)|Specifies how the LLM should format the response. Possible values: 'text' (plain string), 'json_object' (arbitrary JSON), or 'json_schema' (adheres to provided schema).|
|[ChatCompletionSchema](#chatcompletionschema)|Object defining the custom schema the model will use to structure its output.|
|[ChatCompletionSkill](#chatcompletionskill)|A skill that calls a language model via Azure AI Foundry's Chat Completions endpoint.|
|[CognitiveServicesAccountKey](#cognitiveservicesaccountkey)|The multi-region account key of an Azure AI service resource that's attached to a skillset.|
|[ConditionalSkill](#conditionalskill)|A skill that enables scenarios that require a Boolean operation to determine the data to assign to an output.|
|[CustomEntity](#customentity)|An object that contains information about the matches that were found, and related metadata.|
|[CustomEntityAlias](#customentityalias)|A complex object that can be used to specify alternative spellings or synonyms to the root entity name.|
|[CustomEntityLookupSkill](#customentitylookupskill)|A skill looks for text from a custom, user-defined list of words and phrases.|
|[CustomEntityLookupSkillLanguage](#customentitylookupskilllanguage)|The language codes supported for input text by CustomEntityLookupSkill.|
|[DefaultCognitiveServicesAccount](#defaultcognitiveservicesaccount)|An empty object that represents the default Azure AI service resource for a skillset.|
|[DocumentExtractionSkill](#documentextractionskill)|A skill that extracts content from a file within the enrichment pipeline.|
|[DocumentIntelligenceLayoutSkill](#documentintelligencelayoutskill)|A skill that extracts content and layout information, via Azure AI Services, from files within the enrichment pipeline.|
|[DocumentIntelligenceLayoutSkillChunkingProperties](#documentintelligencelayoutskillchunkingproperties)|Controls the cardinality for chunking the content.|
|[DocumentIntelligenceLayoutSkillChunkingUnit](#documentintelligencelayoutskillchunkingunit)|Controls the cardinality of the chunk unit. Default is 'characters'|
|[DocumentIntelligenceLayoutSkillExtractionOptions](#documentintelligencelayoutskillextractionoptions)|Controls the cardinality of the content extracted from the document by the skill.|
|[DocumentIntelligenceLayoutSkillMarkdownHeaderDepth](#documentintelligencelayoutskillmarkdownheaderdepth)|The depth of headers in the markdown output. Default is h6.|
|[DocumentIntelligenceLayoutSkillOutputFormat](#documentintelligencelayoutskilloutputformat)|Controls the cardinality of the output format. Default is 'markdown'.|
|[DocumentIntelligenceLayoutSkillOutputMode](#documentintelligencelayoutskilloutputmode)|Controls the cardinality of the output produced by the skill. Default is 'oneToMany'.|
|[EntityCategory](#entitycategory)|A string indicating what entity categories to return.|
|[EntityLinkingSkill](#entitylinkingskill)|Using the Text Analytics API, extracts linked entities from text.|
|[EntityRecognitionSkill](#entityrecognitionskill)|This skill is deprecated. Use the V3.EntityRecognitionSkill instead.|
|[EntityRecognitionSkillLanguage](#entityrecognitionskilllanguage)|Deprecated. The language codes supported for input text by EntityRecognitionSkill.|
|[EntityRecognitionSkillV3](#entityrecognitionskillv3)|Using the Text Analytics API, extracts entities of different types from text.|
|[ErrorAdditionalInfo](#erroradditionalinfo)|The resource management error additional info.|
|[ErrorDetail](#errordetail)|The error detail.|
|[ErrorResponse](#errorresponse)|Error response|
|[ImageAnalysisSkill](#imageanalysisskill)|A skill that analyzes image files. It extracts a rich set of visual features based on the image content.|
|[ImageAnalysisSkillLanguage](#imageanalysisskilllanguage)|The language codes supported for input by ImageAnalysisSkill.|
|[ImageDetail](#imagedetail)|A string indicating which domain-specific details to return.|
|[IndexProjectionMode](#indexprojectionmode)|Defines behavior of the index projections in relation to the rest of the indexer.|
|[InputFieldMappingEntry](#inputfieldmappingentry)|Input field mapping for a skill.|
|[JsonSchemaProperties](#jsonschemaproperties)|An open dictionary for extended properties. Required if 'type' == 'json_schema'|
|[KeyPhraseExtractionSkill](#keyphraseextractionskill)|A skill that uses text analytics for key phrase extraction.|
|[KeyPhraseExtractionSkillLanguage](#keyphraseextractionskilllanguage)|The language codes supported for input text by KeyPhraseExtractionSkill.|
|[LanguageDetectionSkill](#languagedetectionskill)|A skill that detects the language of input text and reports a single language code for every document submitted on the request. The language code is paired with a score indicating the confidence of the analysis.|
|[LineEnding](#lineending)|Defines the sequence of characters to use between the lines of text recognized by the OCR skill. The default value is "space".|
|[MergeSkill](#mergeskill)|A skill for merging two or more strings into a single unified string, with an optional user-defined delimiter separating each component part.|
|[OcrSkill](#ocrskill)|A skill that extracts text from image files.|
|[OcrSkillLanguage](#ocrskilllanguage)|The language codes supported for input by OcrSkill.|
|[OutputFieldMappingEntry](#outputfieldmappingentry)|Output field mapping for a skill.|
|[PIIDetectionSkill](#piidetectionskill)|Using the Text Analytics API, extracts personal information from an input text and gives you the option of masking it.|
|[PIIDetectionSkillMaskingMode](#piidetectionskillmaskingmode)|A string indicating what maskingMode to use to mask the personal information detected in the input text.|
|[SearchIndexerDataNoneIdentity](#searchindexerdatanoneidentity)|Clears the identity property of a datasource.|
|[SearchIndexerDataUserAssignedIdentity](#searchindexerdatauserassignedidentity)|Specifies the identity for a datasource to use.|
|[SearchIndexerIndexProjections](#searchindexerindexprojections)|Definition of additional projections to secondary search indexes.|
|[SearchIndexerIndexProjectionSelector](#searchindexerindexprojectionselector)|Description for what data to store in the designated search index.|
|[SearchIndexerIndexProjectionsParameters](#searchindexerindexprojectionsparameters)|A dictionary of index projection-specific configuration properties. Each name is the name of a specific property. Each value must be of a primitive type.|
|[SearchIndexerKnowledgeStore](#searchindexerknowledgestore)|Definition of additional projections to azure blob, table, or files, of enriched data.|
|[SearchIndexerKnowledgeStoreFileProjectionSelector](#searchindexerknowledgestorefileprojectionselector)|Projection definition for what data to store in Azure Files.|
|[SearchIndexerKnowledgeStoreObjectProjectionSelector](#searchindexerknowledgestoreobjectprojectionselector)|Projection definition for what data to store in Azure Blob.|
|[SearchIndexerKnowledgeStoreParameters](#searchindexerknowledgestoreparameters)|A dictionary of knowledge store-specific configuration properties. Each name is the name of a specific property. Each value must be of a primitive type.|
|[SearchIndexerKnowledgeStoreProjection](#searchindexerknowledgestoreprojection)|Container object for various projection selectors.|
|[SearchIndexerKnowledgeStoreTableProjectionSelector](#searchindexerknowledgestoretableprojectionselector)|Description for what data to store in Azure Tables.|
|[SearchIndexerSkillset](#searchindexerskillset)|A list of skills.|
|[SearchResourceEncryptionKey](#searchresourceencryptionkey)|A customer-managed encryption key in Azure Key Vault. Keys that you create and manage can be used to encrypt or decrypt data-at-rest, such as indexes and synonym maps.|
|[SentimentSkill](#sentimentskill)|This skill is deprecated. Use the V3.SentimentSkill instead.|
|[SentimentSkillLanguage](#sentimentskilllanguage)|Deprecated. The language codes supported for input text by SentimentSkill.|
|[SentimentSkillV3](#sentimentskillv3)|Using the Text Analytics API, evaluates unstructured text and for each record, provides sentiment labels (such as "negative", "neutral" and "positive") based on the highest confidence score found by the service at a sentence and document-level.|
|[ShaperSkill](#shaperskill)|A skill for reshaping the outputs. It creates a complex type to support composite fields (also known as multipart fields).|
|[SplitSkill](#splitskill)|A skill to split a string into chunks of text.|
|[SplitSkillEncoderModelName](#splitskillencodermodelname)|Only applies if the unit is set to azureOpenAITokens. Options include 'R50k_base', 'P50k_base', 'P50k_edit' and 'CL100k_base'. The default value is 'CL100k_base'.|
|[SplitSkillLanguage](#splitskilllanguage)|The language codes supported for input text by SplitSkill.|
|[SplitSkillUnit](#splitskillunit)|A value indicating which unit to use.|
|[TextSplitMode](#textsplitmode)|A value indicating which split mode to perform.|
|[TextTranslationSkill](#texttranslationskill)|A skill to translate text from one language to another.|
|[TextTranslationSkillLanguage](#texttranslationskilllanguage)|The language codes supported for input text by TextTranslationSkill.|
|[VisionVectorizeSkill](#visionvectorizeskill)|Allows you to generate a vector embedding for a given image or text input using the Azure AI Services Vision Vectorize API.|
|[VisualFeature](#visualfeature)|The strings indicating what visual feature types to return.|
|[WebApiSkill](#webapiskill)|A skill that can call a Web API endpoint, allowing you to extend a skillset by having it call your custom code.|

### AIServicesAccountIdentity

Object

The multi-region account of an Azure AI service resource that's attached to a skillset.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.AIServicesByIdentity|A URI fragment specifying the type of Azure AI service resource attached to a skillset.|
|description|string|Description of the Azure AI service resource attached to a skillset.|
|identity|SearchIndexerDataIdentity:<br><br>- [SearchIndexerDataNoneIdentity](#searchindexerdatanoneidentity)<br>- [SearchIndexerDataUserAssignedIdentity](#searchindexerdatauserassignedidentity)|The user-assigned managed identity used for connections to AI Service. If not specified, the system-assigned managed identity is used. On updates to the skillset, if the identity is unspecified, the value remains unchanged. If set to "none", the value of this property is cleared.|
|subdomainUrl|string|The subdomain url for the corresponding AI Service.|

### AIServicesAccountKey

Object

The account key of an Azure AI service resource that's attached to a skillset, to be used with the resource's subdomain.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.AIServicesByKey|A URI fragment specifying the type of Azure AI service resource attached to a skillset.|
|description|string|Description of the Azure AI service resource attached to a skillset.|
|key|string|The key used to provision the Azure AI service resource attached to a skillset.|
|subdomainUrl|string|The subdomain url for the corresponding AI Service.|

### AmlSkill

Object

The AML skill allows you to extend AI enrichment with a custom Azure Machine Learning (AML) model. Once an AML model is trained and deployed, an AML skill integrates it into AI enrichment.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Skills.Custom.AmlSkill|A URI fragment specifying the type of skill.|
|context|string|Represents the level at which operations take place, such as the document root or document content (for example, /document or /document/content). The default is /document.|
|degreeOfParallelism|integer (int32)|(Optional) When specified, indicates the number of calls the indexer will make in parallel to the endpoint you have provided. You can decrease this value if your endpoint is failing under too high of a request load, or raise it if your endpoint is able to accept more requests and you would like an increase in the performance of the indexer. If not set, a default value of 5 is used. The degreeOfParallelism can be set to a maximum of 10 and a minimum of 1.|
|description|string|The description of the skill which describes the inputs, outputs, and usage of the skill.|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]|Inputs of the skills could be a column in the source data set, or the output of an upstream skill.|
|key|string|(Required for key authentication) The key for the AML service.|
|name|string|The name of the skill which uniquely identifies it within the skillset. A skill with no name defined will be given a default name of its 1-based index in the skills array, prefixed with the character '#'.|
|outputs|[OutputFieldMappingEntry](#outputfieldmappingentry)[]|The output of a skill is either a field in a search index, or a value that can be consumed as an input by another skill.|
|region|string|(Optional for token authentication). The region the AML service is deployed in.|
|resourceId|string|(Required for token authentication). The Azure Resource Manager resource ID of the AML service. It should be in the format subscriptions/{guid}/resourceGroups/{resource-group-name}/Microsoft.MachineLearningServices/workspaces/{workspace-name}/services/{service_name}.|
|timeout|string (duration)|(Optional) When specified, indicates the timeout for the http client making the API call.|
|uri|string (uri)|(Required for no authentication or key authentication) The scoring URI of the AML service to which the JSON payload will be sent. Only the https URI scheme is allowed.|

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
|gpt-4o||
|gpt-4o-mini||
|gpt-4.1||
|gpt-4.1-mini||
|gpt-4.1-nano||

### AzureOpenAITokenizerParameters

Object

|Name|Type|Description|
|---|---|---|
|allowedSpecialTokens|string[]|(Optional) Only applies if the unit is set to azureOpenAITokens. This parameter defines a collection of special tokens that are permitted within the tokenization process.|
|encoderModelName|[SplitSkillEncoderModelName](#splitskillencodermodelname)|Only applies if the unit is set to azureOpenAITokens. Options include 'R50k_base', 'P50k_base', 'P50k_edit' and 'CL100k_base'. The default value is 'CL100k_base'.|

### ChatCompletionCommonModelParameters

Object

Common language model parameters for Chat Completions. If omitted, default values are used.

|Name|Type|Default value|Description|
|---|---|---|---|
|frequencyPenalty|number|0|A float in the range [-2,2] that reduces or increases likelihood of repeated tokens. Default is 0.|
|maxTokens|integer (int32)||Maximum number of tokens to generate.|
|model|string||The name of the model to use (e.g., 'gpt-4o', etc.). Default is null if not specified.|
|presencePenalty|number|0|A float in the range [-2,2] that penalizes new tokens based on their existing presence. Default is 0.|
|seed|integer (int32)||Random seed for controlling deterministic outputs. If omitted, randomization is used.|
|stop|string[]||List of stop sequences that will cut off text generation. Default is none.|
|temperature|number|0.7|Sampling temperature. Default is 0.7.|

Enumeration

Specifies how 'extraParameters' should be handled by Azure AI Foundry. Defaults to 'error'.

|Value|Description|
|---|---|
|pass-through||
|drop|Drops all extra parameters.|
|error|Raises an error if any extra parameter is present.|

### ChatCompletionResponseFormat

Object

Determines how the language model's response should be serialized. Defaults to 'text'.

|Name|Type|Default value|Description|
|---|---|---|---|
|jsonSchemaProperties|[JsonSchemaProperties](#jsonschemaproperties)||An open dictionary for extended properties. Required if 'type' == 'json_schema'|
|type|[ChatCompletionResponseFormatType](#chatcompletionresponseformattype)|text|Specifies how the LLM should format the response. Possible values: 'text' (plain string), 'json_object' (arbitrary JSON), or 'json_schema' (adheres to provided schema).|

### ChatCompletionResponseFormatType

Enumeration

Specifies how the LLM should format the response. Possible values: 'text' (plain string), 'json_object' (arbitrary JSON), or 'json_schema' (adheres to provided schema).

|Value|Description|
|---|---|
|text||
|jsonObject||
|jsonSchema||

### ChatCompletionSchema

Object

Object defining the custom schema the model will use to structure its output.

|Name|Type|Default value|Description|
|---|---|---|---|
|additionalProperties|boolean|False|Controls whether it is allowable for an object to contain additional keys / values that were not defined in the JSON Schema. Default is false.|
|properties|string||A JSON-formatted string that defines the output schema's properties and constraints for the model.|
|required|string[]||An array of the property names that are required to be part of the model's response. All properties must be included for structured outputs.|
|type|string|object|Type of schema representation. Usually 'object'. Default is 'object'.|

### ChatCompletionSkill

Object

A skill that calls a language model via Azure AI Foundry's Chat Completions endpoint.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Skills.Custom.ChatCompletionSkill||A URI fragment specifying the type of skill.|
|apiKey|string||API key for authenticating to the model. Both apiKey and authIdentity cannot be specified at the same time.|
|authIdentity|SearchIndexerDataIdentity:<br><br>- [SearchIndexerDataNoneIdentity](#searchindexerdatanoneidentity)<br>- [SearchIndexerDataUserAssignedIdentity](#searchindexerdatauserassignedidentity)||The user-assigned managed identity used for outbound connections. If an authResourceId is provided and it's not specified, the system-assigned managed identity is used. On updates to the indexer, if the identity is unspecified, the value remains unchanged. If set to "none", the value of this property is cleared.|
|authResourceId|string||Applies to custom skills that connect to external code in an Azure function or some other application that provides the transformations. This value should be the application ID created for the function or app when it was registered with Azure Active Directory. When specified, the custom skill connects to the function or app using a managed ID (either system or user-assigned) of the search service and the access token of the function or app, using this value as the resource id for creating the scope of the access token.|
|batchSize|integer (int32)||The desired batch size which indicates number of documents.|
|commonModelParameters|[ChatCompletionCommonModelParameters](#chatcompletioncommonmodelparameters)||Common language model parameters that customers can tweak. If omitted, reasonable defaults will be applied.|
|context|string||Represents the level at which operations take place, such as the document root or document content (for example, /document or /document/content). The default is /document.|
|degreeOfParallelism|integer (int32)||If set, the number of parallel calls that can be made to the Web API.|
|description|string||The description of the skill which describes the inputs, outputs, and usage of the skill.|
|extraParameters|object||Open-type dictionary for model-specific parameters that should be appended to the chat completions call. Follows Azure AI Foundry’s extensibility pattern.|
|extraParametersBehavior|[ChatCompletionExtraParametersBehavior](#chatcompletionextraparametersbehavior)|error|How extra parameters are handled by Azure AI Foundry. Default is 'error'.|
|httpHeaders|object||The headers required to make the http request.|
|httpMethod|string||The method for the http request.|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]||Inputs of the skills could be a column in the source data set, or the output of an upstream skill.|
|name|string||The name of the skill which uniquely identifies it within the skillset. A skill with no name defined will be given a default name of its 1-based index in the skills array, prefixed with the character '#'.|
|outputs|[OutputFieldMappingEntry](#outputfieldmappingentry)[]||The output of a skill is either a field in a search index, or a value that can be consumed as an input by another skill.|
|responseFormat|[ChatCompletionResponseFormat](#chatcompletionresponseformat)||Determines how the LLM should format its response. Defaults to 'text' response type.|
|timeout|string (duration)||The desired timeout for the request. Default is 30 seconds.|
|uri|string||The url for the Web API.|

### CognitiveServicesAccountKey

Object

The multi-region account key of an Azure AI service resource that's attached to a skillset.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.CognitiveServicesByKey|A URI fragment specifying the type of Azure AI service resource attached to a skillset.|
|description|string|Description of the Azure AI service resource attached to a skillset.|
|key|string|The key used to provision the Azure AI service resource attached to a skillset.|

### ConditionalSkill

Object

A skill that enables scenarios that require a Boolean operation to determine the data to assign to an output.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Skills.Util.ConditionalSkill|A URI fragment specifying the type of skill.|
|context|string|Represents the level at which operations take place, such as the document root or document content (for example, /document or /document/content). The default is /document.|
|description|string|The description of the skill which describes the inputs, outputs, and usage of the skill.|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]|Inputs of the skills could be a column in the source data set, or the output of an upstream skill.|
|name|string|The name of the skill which uniquely identifies it within the skillset. A skill with no name defined will be given a default name of its 1-based index in the skills array, prefixed with the character '#'.|
|outputs|[OutputFieldMappingEntry](#outputfieldmappingentry)[]|The output of a skill is either a field in a search index, or a value that can be consumed as an input by another skill.|

### CustomEntity

Object

An object that contains information about the matches that were found, and related metadata.

|Name|Type|Description|
|---|---|---|
|accentSensitive|boolean|Defaults to false. Boolean value denoting whether comparisons with the entity name should be sensitive to accent.|
|aliases|[CustomEntityAlias](#customentityalias)[]|An array of complex objects that can be used to specify alternative spellings or synonyms to the root entity name.|
|caseSensitive|boolean|Defaults to false. Boolean value denoting whether comparisons with the entity name should be sensitive to character casing. Sample case insensitive matches of "Microsoft" could be: microsoft, microSoft, MICROSOFT.|
|defaultAccentSensitive|boolean|Changes the default accent sensitivity value for this entity. It be used to change the default value of all aliases accentSensitive values.|
|defaultCaseSensitive|boolean|Changes the default case sensitivity value for this entity. It be used to change the default value of all aliases caseSensitive values.|
|defaultFuzzyEditDistance|integer (int32)|Changes the default fuzzy edit distance value for this entity. It can be used to change the default value of all aliases fuzzyEditDistance values.|
|description|string|This field can be used as a passthrough for custom metadata about the matched text(s). The value of this field will appear with every match of its entity in the skill output.|
|fuzzyEditDistance|integer (int32)|Defaults to 0. Maximum value of 5. Denotes the acceptable number of divergent characters that would still constitute a match with the entity name. The smallest possible fuzziness for any given match is returned. For instance, if the edit distance is set to 3, "Windows10" would still match "Windows", "Windows10" and "Windows 7". When case sensitivity is set to false, case differences do NOT count towards fuzziness tolerance, but otherwise do.|
|id|string|This field can be used as a passthrough for custom metadata about the matched text(s). The value of this field will appear with every match of its entity in the skill output.|
|name|string|The top-level entity descriptor. Matches in the skill output will be grouped by this name, and it should represent the "normalized" form of the text being found.|
|subtype|string|This field can be used as a passthrough for custom metadata about the matched text(s). The value of this field will appear with every match of its entity in the skill output.|
|type|string|This field can be used as a passthrough for custom metadata about the matched text(s). The value of this field will appear with every match of its entity in the skill output.|

### CustomEntityAlias

Object

A complex object that can be used to specify alternative spellings or synonyms to the root entity name.

|Name|Type|Description|
|---|---|---|
|accentSensitive|boolean|Determine if the alias is accent sensitive.|
|caseSensitive|boolean|Determine if the alias is case sensitive.|
|fuzzyEditDistance|integer (int32)|Determine the fuzzy edit distance of the alias.|
|text|string|The text of the alias.|

### CustomEntityLookupSkill

Object

A skill looks for text from a custom, user-defined list of words and phrases.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Skills.Text.CustomEntityLookupSkill|A URI fragment specifying the type of skill.|
|context|string|Represents the level at which operations take place, such as the document root or document content (for example, /document or /document/content). The default is /document.|
|defaultLanguageCode|[CustomEntityLookupSkillLanguage](#customentitylookupskilllanguage)|A value indicating which language code to use. Default is `en`.|
|description|string|The description of the skill which describes the inputs, outputs, and usage of the skill.|
|entitiesDefinitionUri|string|Path to a JSON or CSV file containing all the target text to match against. This entity definition is read at the beginning of an indexer run. Any updates to this file during an indexer run will not take effect until subsequent runs. This config must be accessible over HTTPS.|
|globalDefaultAccentSensitive|boolean|A global flag for AccentSensitive. If AccentSensitive is not set in CustomEntity, this value will be the default value.|
|globalDefaultCaseSensitive|boolean|A global flag for CaseSensitive. If CaseSensitive is not set in CustomEntity, this value will be the default value.|
|globalDefaultFuzzyEditDistance|integer (int32)|A global flag for FuzzyEditDistance. If FuzzyEditDistance is not set in CustomEntity, this value will be the default value.|
|inlineEntitiesDefinition|[CustomEntity](#customentity)[]|The inline CustomEntity definition.|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]|Inputs of the skills could be a column in the source data set, or the output of an upstream skill.|
|name|string|The name of the skill which uniquely identifies it within the skillset. A skill with no name defined will be given a default name of its 1-based index in the skills array, prefixed with the character '#'.|
|outputs|[OutputFieldMappingEntry](#outputfieldmappingentry)[]|The output of a skill is either a field in a search index, or a value that can be consumed as an input by another skill.|

### CustomEntityLookupSkillLanguage

Enumeration

The language codes supported for input text by CustomEntityLookupSkill.

|Value|Description|
|---|---|
|da|Danish|
|de|German|
|en|English|
|es|Spanish|
|fi|Finnish|
|fr|French|
|it|Italian|
|ko|Korean|
|pt|Portuguese|

### DefaultCognitiveServicesAccount

Object

An empty object that represents the default Azure AI service resource for a skillset.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Azure.Search.DefaultCognitiveServices|A URI fragment specifying the type of Azure AI service resource attached to a skillset.|
|description|string|Description of the Azure AI service resource attached to a skillset.|

Object

A skill that extracts content from a file within the enrichment pipeline.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Skills.Util.DocumentExtractionSkill|A URI fragment specifying the type of skill.|
|configuration|object|A dictionary of configurations for the skill.|
|context|string|Represents the level at which operations take place, such as the document root or document content (for example, /document or /document/content). The default is /document.|
|dataToExtract|string|The type of data to be extracted for the skill. Will be set to 'contentAndMetadata' if not defined.|
|description|string|The description of the skill which describes the inputs, outputs, and usage of the skill.|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]|Inputs of the skills could be a column in the source data set, or the output of an upstream skill.|
|name|string|The name of the skill which uniquely identifies it within the skillset. A skill with no name defined will be given a default name of its 1-based index in the skills array, prefixed with the character '#'.|
|outputs|[OutputFieldMappingEntry](#outputfieldmappingentry)[]|The output of a skill is either a field in a search index, or a value that can be consumed as an input by another skill.|
|parsingMode|string|The parsingMode for the skill. Will be set to 'default' if not defined.|

### DocumentIntelligenceLayoutSkill

Object

A skill that extracts content and layout information, via Azure AI Services, from files within the enrichment pipeline.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Skills.Util.DocumentIntelligenceLayoutSkill||A URI fragment specifying the type of skill.|
|chunkingProperties|[DocumentIntelligenceLayoutSkillChunkingProperties](#documentintelligencelayoutskillchunkingproperties)||Controls the cardinality for chunking the content.|
|context|string||Represents the level at which operations take place, such as the document root or document content (for example, /document or /document/content). The default is /document.|
|description|string||The description of the skill which describes the inputs, outputs, and usage of the skill.|
|extractionOptions|[DocumentIntelligenceLayoutSkillExtractionOptions](#documentintelligencelayoutskillextractionoptions)[]||Controls the cardinality of the content extracted from the document by the skill|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]||Inputs of the skills could be a column in the source data set, or the output of an upstream skill.|
|markdownHeaderDepth|[DocumentIntelligenceLayoutSkillMarkdownHeaderDepth](#documentintelligencelayoutskillmarkdownheaderdepth)|h6|The depth of headers in the markdown output. Default is h6.|
|name|string||The name of the skill which uniquely identifies it within the skillset. A skill with no name defined will be given a default name of its 1-based index in the skills array, prefixed with the character '#'.|
|outputFormat|[DocumentIntelligenceLayoutSkillOutputFormat](#documentintelligencelayoutskilloutputformat)|markdown|Controls the cardinality of the output format. Default is 'markdown'.|
|outputMode|[DocumentIntelligenceLayoutSkillOutputMode](#documentintelligencelayoutskilloutputmode)|oneToMany|Controls the cardinality of the output produced by the skill. Default is 'oneToMany'.|
|outputs|[OutputFieldMappingEntry](#outputfieldmappingentry)[]||The output of a skill is either a field in a search index, or a value that can be consumed as an input by another skill.|

### DocumentIntelligenceLayoutSkillChunkingProperties

Object

Controls the cardinality for chunking the content.

|Name|Type|Default value|Description|
|---|---|---|---|
|maximumLength|integer (int32)||The maximum chunk length in characters. Default is 500.|
|overlapLength|integer (int32)||The length of overlap provided between two text chunks. Default is 0.|
|unit|[DocumentIntelligenceLayoutSkillChunkingUnit](#documentintelligencelayoutskillchunkingunit)|characters|The unit of the chunk.|

### DocumentIntelligenceLayoutSkillChunkingUnit

Enumeration

Controls the cardinality of the chunk unit. Default is 'characters'

|Value|Description|
|---|---|
|characters|Specifies chunk by characters.|

Enumeration

Controls the cardinality of the content extracted from the document by the skill.

|Value|Description|
|---|---|
|images|Specify that image content should be extracted from the document.|
|locationMetadata|Specify that location metadata should be extracted from the document.|

Enumeration

The depth of headers in the markdown output. Default is h6.

|Value|Description|
|---|---|
|h1|Header level 1.|
|h2|Header level 2.|
|h3|Header level 3.|
|h4|Header level 4.|
|h5|Header level 5.|
|h6|Header level 6.|

### DocumentIntelligenceLayoutSkillOutputFormat

Enumeration

Controls the cardinality of the output format. Default is 'markdown'.

|Value|Description|
|---|---|
|text|Specify the format of the output as text.|
|markdown|Specify the format of the output as markdown.|

### DocumentIntelligenceLayoutSkillOutputMode

Enumeration

Controls the cardinality of the output produced by the skill. Default is 'oneToMany'.

|Value|Description|
|---|---|
|oneToMany|Specify that the output should be parsed as 'oneToMany'.|

### EntityCategory

Enumeration

A string indicating what entity categories to return.

|Value|Description|
|---|---|
|location|Entities describing a physical location.|
|organization|Entities describing an organization.|
|person|Entities describing a person.|
|quantity|Entities describing a quantity.|
|datetime|Entities describing a date and time.|
|url|Entities describing a URL.|
|email|Entities describing an email address.|

### EntityLinkingSkill

Object

Using the Text Analytics API, extracts linked entities from text.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Skills.Text.V3.EntityLinkingSkill|A URI fragment specifying the type of skill.|
|context|string|Represents the level at which operations take place, such as the document root or document content (for example, /document or /document/content). The default is /document.|
|defaultLanguageCode|string|A value indicating which language code to use. Default is `en`.|
|description|string|The description of the skill which describes the inputs, outputs, and usage of the skill.|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]|Inputs of the skills could be a column in the source data set, or the output of an upstream skill.|
|minimumPrecision|number (double)<br><br>minimum: 0  <br>maximum: 1|A value between 0 and 1 that be used to only include entities whose confidence score is greater than the value specified. If not set (default), or if explicitly set to null, all entities will be included.|
|modelVersion|string|The version of the model to use when calling the Text Analytics service. It will default to the latest available when not specified. We recommend you do not specify this value unless absolutely necessary.|
|name|string|The name of the skill which uniquely identifies it within the skillset. A skill with no name defined will be given a default name of its 1-based index in the skills array, prefixed with the character '#'.|
|outputs|[OutputFieldMappingEntry](#outputfieldmappingentry)[]|The output of a skill is either a field in a search index, or a value that can be consumed as an input by another skill.|

### EntityRecognitionSkill

Object

This skill is deprecated. Use the V3.EntityRecognitionSkill instead.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Skills.Text.EntityRecognitionSkill|A URI fragment specifying the type of skill.|
|categories|[EntityCategory](#entitycategory)[]|A list of entity categories that should be extracted.|
|context|string|Represents the level at which operations take place, such as the document root or document content (for example, /document or /document/content). The default is /document.|
|defaultLanguageCode|[EntityRecognitionSkillLanguage](#entityrecognitionskilllanguage)|A value indicating which language code to use. Default is `en`.|
|description|string|The description of the skill which describes the inputs, outputs, and usage of the skill.|
|includeTypelessEntities|boolean|Determines whether or not to include entities which are well known but don't conform to a pre-defined type. If this configuration is not set (default), set to null or set to false, entities which don't conform to one of the pre-defined types will not be surfaced.|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]|Inputs of the skills could be a column in the source data set, or the output of an upstream skill.|
|minimumPrecision|number (double)|A value between 0 and 1 that be used to only include entities whose confidence score is greater than the value specified. If not set (default), or if explicitly set to null, all entities will be included.|
|name|string|The name of the skill which uniquely identifies it within the skillset. A skill with no name defined will be given a default name of its 1-based index in the skills array, prefixed with the character '#'.|
|outputs|[OutputFieldMappingEntry](#outputfieldmappingentry)[]|The output of a skill is either a field in a search index, or a value that can be consumed as an input by another skill.|

### EntityRecognitionSkillLanguage

Enumeration

Deprecated. The language codes supported for input text by EntityRecognitionSkill.

|Value|Description|
|---|---|
|ar|Arabic|
|cs|Czech|
|zh-Hans|Chinese-Simplified|
|zh-Hant|Chinese-Traditional|
|da|Danish|
|nl|Dutch|
|en|English|
|fi|Finnish|
|fr|French|
|de|German|
|el|Greek|
|hu|Hungarian|
|it|Italian|
|ja|Japanese|
|ko|Korean|
|no|Norwegian (Bokmaal)|
|pl|Polish|
|pt-PT|Portuguese (Portugal)|
|pt-BR|Portuguese (Brazil)|
|ru|Russian|
|es|Spanish|
|sv|Swedish|
|tr|Turkish|

### EntityRecognitionSkillV3

Object

Using the Text Analytics API, extracts entities of different types from text.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Skills.Text.V3.EntityRecognitionSkill|A URI fragment specifying the type of skill.|
|categories|string[]|A list of entity categories that should be extracted.|
|context|string|Represents the level at which operations take place, such as the document root or document content (for example, /document or /document/content). The default is /document.|
|defaultLanguageCode|string|A value indicating which language code to use. Default is `en`.|
|description|string|The description of the skill which describes the inputs, outputs, and usage of the skill.|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]|Inputs of the skills could be a column in the source data set, or the output of an upstream skill.|
|minimumPrecision|number (double)<br><br>minimum: 0  <br>maximum: 1|A value between 0 and 1 that be used to only include entities whose confidence score is greater than the value specified. If not set (default), or if explicitly set to null, all entities will be included.|
|modelVersion|string|The version of the model to use when calling the Text Analytics API. It will default to the latest available when not specified. We recommend you do not specify this value unless absolutely necessary.|
|name|string|The name of the skill which uniquely identifies it within the skillset. A skill with no name defined will be given a default name of its 1-based index in the skills array, prefixed with the character '#'.|
|outputs|[OutputFieldMappingEntry](#outputfieldmappingentry)[]|The output of a skill is either a field in a search index, or a value that can be consumed as an input by another skill.|

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

### ImageAnalysisSkill

Object

A skill that analyzes image files. It extracts a rich set of visual features based on the image content.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Skills.Vision.ImageAnalysisSkill|A URI fragment specifying the type of skill.|
|context|string|Represents the level at which operations take place, such as the document root or document content (for example, /document or /document/content). The default is /document.|
|defaultLanguageCode|[ImageAnalysisSkillLanguage](#imageanalysisskilllanguage)|A value indicating which language code to use. Default is `en`.|
|description|string|The description of the skill which describes the inputs, outputs, and usage of the skill.|
|details|[ImageDetail](#imagedetail)[]|A string indicating which domain-specific details to return.|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]|Inputs of the skills could be a column in the source data set, or the output of an upstream skill.|
|name|string|The name of the skill which uniquely identifies it within the skillset. A skill with no name defined will be given a default name of its 1-based index in the skills array, prefixed with the character '#'.|
|outputs|[OutputFieldMappingEntry](#outputfieldmappingentry)[]|The output of a skill is either a field in a search index, or a value that can be consumed as an input by another skill.|
|visualFeatures|[VisualFeature](#visualfeature)[]|A list of visual features.|

### ImageAnalysisSkillLanguage

Enumeration

The language codes supported for input by ImageAnalysisSkill.

|Value|Description|
|---|---|
|ar|Arabic|
|az|Azerbaijani|
|bg|Bulgarian|
|bs|Bosnian Latin|
|ca|Catalan|
|cs|Czech|
|cy|Welsh|
|da|Danish|
|de|German|
|el|Greek|
|en|English|
|es|Spanish|
|et|Estonian|
|eu|Basque|
|fi|Finnish|
|fr|French|
|ga|Irish|
|gl|Galician|
|he|Hebrew|
|hi|Hindi|
|hr|Croatian|
|hu|Hungarian|
|id|Indonesian|
|it|Italian|
|ja|Japanese|
|kk|Kazakh|
|ko|Korean|
|lt|Lithuanian|
|lv|Latvian|
|mk|Macedonian|
|ms|Malay Malaysia|
|nb|Norwegian (Bokmal)|
|nl|Dutch|
|pl|Polish|
|prs|Dari|
|pt-BR|Portuguese-Brazil|
|pt|Portuguese-Portugal|
|pt-PT|Portuguese-Portugal|
|ro|Romanian|
|ru|Russian|
|sk|Slovak|
|sl|Slovenian|
|sr-Cyrl|Serbian - Cyrillic RS|
|sr-Latn|Serbian - Latin RS|
|sv|Swedish|
|th|Thai|
|tr|Turkish|
|uk|Ukrainian|
|vi|Vietnamese|
|zh|Chinese Simplified|
|zh-Hans|Chinese Simplified|
|zh-Hant|Chinese Traditional|

### ImageDetail

Enumeration

A string indicating which domain-specific details to return.

|Value|Description|
|---|---|
|celebrities|Details recognized as celebrities.|
|landmarks|Details recognized as landmarks.|

### IndexProjectionMode

Enumeration

Defines behavior of the index projections in relation to the rest of the indexer.

|Value|Description|
|---|---|
|skipIndexingParentDocuments|The source document will be skipped from writing into the indexer's target index.|
|includeIndexingParentDocuments|The source document will be written into the indexer's target index. This is the default pattern.|

### InputFieldMappingEntry

Object

Input field mapping for a skill.

|Name|Type|Description|
|---|---|---|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]|The recursive inputs used when creating a complex type.|
|name|string|The name of the input.|
|source|string|The source of the input.|
|sourceContext|string|The source context used for selecting recursive inputs.|

### JsonSchemaProperties

Object

An open dictionary for extended properties. Required if 'type' == 'json_schema'

|Name|Type|Default value|Description|
|---|---|---|---|
|description|string||Description of the json schema the model will adhere to.|
|name|string||Name of the json schema the model will adhere to|
|schema|[ChatCompletionSchema](#chatcompletionschema)||Object defining the custom schema the model will use to structure its output.|
|strict|boolean|True|Whether or not the model's response should use structured outputs. Default is true|

Object

A skill that uses text analytics for key phrase extraction.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Skills.Text.KeyPhraseExtractionSkill|A URI fragment specifying the type of skill.|
|context|string|Represents the level at which operations take place, such as the document root or document content (for example, /document or /document/content). The default is /document.|
|defaultLanguageCode|[KeyPhraseExtractionSkillLanguage](#keyphraseextractionskilllanguage)|A value indicating which language code to use. Default is `en`.|
|description|string|The description of the skill which describes the inputs, outputs, and usage of the skill.|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]|Inputs of the skills could be a column in the source data set, or the output of an upstream skill.|
|maxKeyPhraseCount|integer (int32)|A number indicating how many key phrases to return. If absent, all identified key phrases will be returned.|
|modelVersion|string|The version of the model to use when calling the Text Analytics service. It will default to the latest available when not specified. We recommend you do not specify this value unless absolutely necessary.|
|name|string|The name of the skill which uniquely identifies it within the skillset. A skill with no name defined will be given a default name of its 1-based index in the skills array, prefixed with the character '#'.|
|outputs|[OutputFieldMappingEntry](#outputfieldmappingentry)[]|The output of a skill is either a field in a search index, or a value that can be consumed as an input by another skill.|

Enumeration

The language codes supported for input text by KeyPhraseExtractionSkill.

|Value|Description|
|---|---|
|da|Danish|
|nl|Dutch|
|en|English|
|fi|Finnish|
|fr|French|
|de|German|
|it|Italian|
|ja|Japanese|
|ko|Korean|
|no|Norwegian (Bokmaal)|
|pl|Polish|
|pt-PT|Portuguese (Portugal)|
|pt-BR|Portuguese (Brazil)|
|ru|Russian|
|es|Spanish|
|sv|Swedish|

### LanguageDetectionSkill

Object

A skill that detects the language of input text and reports a single language code for every document submitted on the request. The language code is paired with a score indicating the confidence of the analysis.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Skills.Text.LanguageDetectionSkill|A URI fragment specifying the type of skill.|
|context|string|Represents the level at which operations take place, such as the document root or document content (for example, /document or /document/content). The default is /document.|
|defaultCountryHint|string|A country code to use as a hint to the language detection model if it cannot disambiguate the language.|
|description|string|The description of the skill which describes the inputs, outputs, and usage of the skill.|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]|Inputs of the skills could be a column in the source data set, or the output of an upstream skill.|
|modelVersion|string|The version of the model to use when calling the Text Analytics service. It will default to the latest available when not specified. We recommend you do not specify this value unless absolutely necessary.|
|name|string|The name of the skill which uniquely identifies it within the skillset. A skill with no name defined will be given a default name of its 1-based index in the skills array, prefixed with the character '#'.|
|outputs|[OutputFieldMappingEntry](#outputfieldmappingentry)[]|The output of a skill is either a field in a search index, or a value that can be consumed as an input by another skill.|

### LineEnding

Enumeration

Defines the sequence of characters to use between the lines of text recognized by the OCR skill. The default value is "space".

|Value|Description|
|---|---|
|space|Lines are separated by a single space character.|
|carriageReturn|Lines are separated by a carriage return ('\r') character.|
|lineFeed|Lines are separated by a single line feed ('\n') character.|
|carriageReturnLineFeed|Lines are separated by a carriage return and a line feed ('\r\n') character.|

### MergeSkill

Object

A skill for merging two or more strings into a single unified string, with an optional user-defined delimiter separating each component part.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Skills.Text.MergeSkill||A URI fragment specifying the type of skill.|
|context|string||Represents the level at which operations take place, such as the document root or document content (for example, /document or /document/content). The default is /document.|
|description|string||The description of the skill which describes the inputs, outputs, and usage of the skill.|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]||Inputs of the skills could be a column in the source data set, or the output of an upstream skill.|
|insertPostTag|string||The tag indicates the end of the merged text. By default, the tag is an empty space.|
|insertPreTag|string||The tag indicates the start of the merged text. By default, the tag is an empty space.|
|name|string||The name of the skill which uniquely identifies it within the skillset. A skill with no name defined will be given a default name of its 1-based index in the skills array, prefixed with the character '#'.|
|outputs|[OutputFieldMappingEntry](#outputfieldmappingentry)[]||The output of a skill is either a field in a search index, or a value that can be consumed as an input by another skill.|

### OcrSkill

Object

A skill that extracts text from image files.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Skills.Vision.OcrSkill||A URI fragment specifying the type of skill.|
|context|string||Represents the level at which operations take place, such as the document root or document content (for example, /document or /document/content). The default is /document.|
|defaultLanguageCode|[OcrSkillLanguage](#ocrskilllanguage)||A value indicating which language code to use. Default is `en`.|
|description|string||The description of the skill which describes the inputs, outputs, and usage of the skill.|
|detectOrientation|boolean|False|A value indicating to turn orientation detection on or not. Default is false.|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]||Inputs of the skills could be a column in the source data set, or the output of an upstream skill.|
|lineEnding|[LineEnding](#lineending)||Defines the sequence of characters to use between the lines of text recognized by the OCR skill. The default value is "space".|
|name|string||The name of the skill which uniquely identifies it within the skillset. A skill with no name defined will be given a default name of its 1-based index in the skills array, prefixed with the character '#'.|
|outputs|[OutputFieldMappingEntry](#outputfieldmappingentry)[]||The output of a skill is either a field in a search index, or a value that can be consumed as an input by another skill.|

### OcrSkillLanguage

Enumeration

The language codes supported for input by OcrSkill.

|Value|Description|
|---|---|
|af|Afrikaans|
|sq|Albanian|
|anp|Angika (Devanagiri)|
|ar|Arabic|
|ast|Asturian|
|awa|Awadhi-Hindi (Devanagiri)|
|az|Azerbaijani (Latin)|
|bfy|Bagheli|
|eu|Basque|
|be|Belarusian (Cyrillic and Latin)|
|be-cyrl|Belarusian (Cyrillic)|
|be-latn|Belarusian (Latin)|
|bho|Bhojpuri-Hindi (Devanagiri)|
|bi|Bislama|
|brx|Bodo (Devanagiri)|
|bs|Bosnian Latin|
|bra|Brajbha|
|br|Breton|
|bg|Bulgarian|
|bns|Bundeli|
|bua|Buryat (Cyrillic)|
|ca|Catalan|
|ceb|Cebuano|
|rab|Chamling|
|ch|Chamorro|
|hne|Chhattisgarhi (Devanagiri)|
|zh-Hans|Chinese Simplified|
|zh-Hant|Chinese Traditional|
|kw|Cornish|
|co|Corsican|
|crh|Crimean Tatar (Latin)|
|hr|Croatian|
|cs|Czech|
|da|Danish|
|prs|Dari|
|dhi|Dhimal (Devanagiri)|
|doi|Dogri (Devanagiri)|
|nl|Dutch|
|en|English|
|myv|Erzya (Cyrillic)|
|et|Estonian|
|fo|Faroese|
|fj|Fijian|
|fil|Filipino|
|fi|Finnish|
|fr|French|
|fur|Frulian|
|gag|Gagauz (Latin)|
|gl|Galician|
|de|German|
|gil|Gilbertese|
|gon|Gondi (Devanagiri)|
|el|Greek|
|kl|Greenlandic|
|gvr|Gurung (Devanagiri)|
|ht|Haitian Creole|
|hlb|Halbi (Devanagiri)|
|hni|Hani|
|bgc|Haryanvi|
|haw|Hawaiian|
|hi|Hindi|
|mww|Hmong Daw (Latin)|
|hoc|Ho (Devanagiri)|
|hu|Hungarian|
|is|Icelandic|
|smn|Inari Sami|
|id|Indonesian|
|ia|Interlingua|
|iu|Inuktitut (Latin)|
|ga|Irish|
|it|Italian|
|ja|Japanese|
|Jns|Jaunsari (Devanagiri)|
|jv|Javanese|
|kea|Kabuverdianu|
|kac|Kachin (Latin)|
|xnr|Kangri (Devanagiri)|
|krc|Karachay-Balkar|
|kaa-cyrl|Kara-Kalpak (Cyrillic)|
|kaa|Kara-Kalpak (Latin)|
|csb|Kashubian|
|kk-cyrl|Kazakh (Cyrillic)|
|kk-latn|Kazakh (Latin)|
|klr|Khaling|
|kha|Khasi|
|quc|K'iche'|
|ko|Korean|
|kfq|Korku|
|kpy|Koryak|
|kos|Kosraean|
|kum|Kumyk (Cyrillic)|
|ku-arab|Kurdish (Arabic)|
|ku-latn|Kurdish (Latin)|
|kru|Kurukh (Devanagiri)|
|ky|Kyrgyz (Cyrillic)|
|lkt|Lakota|
|la|Latin|
|lt|Lithuanian|
|dsb|Lower Sorbian|
|smj|Lule Sami|
|lb|Luxembourgish|
|bfz|Mahasu Pahari (Devanagiri)|
|ms|Malay (Latin)|
|mt|Maltese|
|kmj|Malto (Devanagiri)|
|gv|Manx|
|mi|Maori|
|mr|Marathi|
|mn|Mongolian (Cyrillic)|
|cnr-cyrl|Montenegrin (Cyrillic)|
|cnr-latn|Montenegrin (Latin)|
|nap|Neapolitan|
|ne|Nepali|
|niu|Niuean|
|nog|Nogay|
|sme|Northern Sami (Latin)|
|nb|Norwegian|
|no|Norwegian|
|oc|Occitan|
|os|Ossetic|
|ps|Pashto|
|fa|Persian|
|pl|Polish|
|pt|Portuguese|
|pa|Punjabi (Arabic)|
|ksh|Ripuarian|
|ro|Romanian|
|rm|Romansh|
|ru|Russian|
|sck|Sadri (Devanagiri)|
|sm|Samoan (Latin)|
|sa|Sanskrit (Devanagiri)|
|sat|Santali (Devanagiri)|
|sco|Scots|
|gd|Scottish Gaelic|
|sr|Serbian (Latin)|
|sr-Cyrl|Serbian (Cyrillic)|
|sr-Latn|Serbian (Latin)|
|xsr|Sherpa (Devanagiri)|
|srx|Sirmauri (Devanagiri)|
|sms|Skolt Sami|
|sk|Slovak|
|sl|Slovenian|
|so|Somali (Arabic)|
|sma|Southern Sami|
|es|Spanish|
|sw|Swahili (Latin)|
|sv|Swedish|
|tg|Tajik (Cyrillic)|
|tt|Tatar (Latin)|
|tet|Tetum|
|thf|Thangmi|
|to|Tongan|
|tr|Turkish|
|tk|Turkmen (Latin)|
|tyv|Tuvan|
|hsb|Upper Sorbian|
|ur|Urdu|
|ug|Uyghur (Arabic)|
|uz-arab|Uzbek (Arabic)|
|uz-cyrl|Uzbek (Cyrillic)|
|uz|Uzbek (Latin)|
|vo|Volapük|
|wae|Walser|
|cy|Welsh|
|fy|Western Frisian|
|yua|Yucatec Maya|
|za|Zhuang|
|zu|Zulu|
|unk|Unknown (All)|

### OutputFieldMappingEntry

Object

Output field mapping for a skill.

|Name|Type|Description|
|---|---|---|
|name|string|The name of the output defined by the skill.|
|targetName|string|The target name of the output. It is optional and default to name.|

### PIIDetectionSkill

Object

Using the Text Analytics API, extracts personal information from an input text and gives you the option of masking it.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Skills.Text.PIIDetectionSkill|A URI fragment specifying the type of skill.|
|context|string|Represents the level at which operations take place, such as the document root or document content (for example, /document or /document/content). The default is /document.|
|defaultLanguageCode|string|A value indicating which language code to use. Default is `en`.|
|description|string|The description of the skill which describes the inputs, outputs, and usage of the skill.|
|domain|string|If specified, will set the PII domain to include only a subset of the entity categories. Possible values include: 'phi', 'none'. Default is 'none'.|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]|Inputs of the skills could be a column in the source data set, or the output of an upstream skill.|
|maskingCharacter|string<br><br>maxLength: 1|The character used to mask the text if the maskingMode parameter is set to replace. Default is '*'.|
|maskingMode|[PIIDetectionSkillMaskingMode](#piidetectionskillmaskingmode)|A parameter that provides various ways to mask the personal information detected in the input text. Default is 'none'.|
|minimumPrecision|number (double)<br><br>minimum: 0  <br>maximum: 1|A value between 0 and 1 that be used to only include entities whose confidence score is greater than the value specified. If not set (default), or if explicitly set to null, all entities will be included.|
|modelVersion|string|The version of the model to use when calling the Text Analytics service. It will default to the latest available when not specified. We recommend you do not specify this value unless absolutely necessary.|
|name|string|The name of the skill which uniquely identifies it within the skillset. A skill with no name defined will be given a default name of its 1-based index in the skills array, prefixed with the character '#'.|
|outputs|[OutputFieldMappingEntry](#outputfieldmappingentry)[]|The output of a skill is either a field in a search index, or a value that can be consumed as an input by another skill.|
|piiCategories|string[]|A list of PII entity categories that should be extracted and masked.|

### PIIDetectionSkillMaskingMode

Enumeration

A string indicating what maskingMode to use to mask the personal information detected in the input text.

|Value|Description|
|---|---|
|none|No masking occurs and the maskedText output will not be returned.|
|replace|Replaces the detected entities with the character given in the maskingCharacter parameter. The character will be repeated to the length of the detected entity so that the offsets will correctly correspond to both the input text as well as the output maskedText.|

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

### SearchIndexerIndexProjections

Object

Definition of additional projections to secondary search indexes.

|Name|Type|Description|
|---|---|---|
|parameters|[SearchIndexerIndexProjectionsParameters](#searchindexerindexprojectionsparameters)|A dictionary of index projection-specific configuration properties. Each name is the name of a specific property. Each value must be of a primitive type.|
|selectors|[SearchIndexerIndexProjectionSelector](#searchindexerindexprojectionselector)[]|A list of projections to be performed to secondary search indexes.|

### SearchIndexerIndexProjectionSelector

Object

Description for what data to store in the designated search index.

|Name|Type|Description|
|---|---|---|
|mappings|[InputFieldMappingEntry](#inputfieldmappingentry)[]|Mappings for the projection, or which source should be mapped to which field in the target index.|
|parentKeyFieldName|string|Name of the field in the search index to map the parent document's key value to. Must be a string field that is filterable and not the key field.|
|sourceContext|string|Source context for the projections. Represents the cardinality at which the document will be split into multiple sub documents.|
|targetIndexName|string|Name of the search index to project to. Must have a key field with the 'keyword' analyzer set.|

### SearchIndexerIndexProjectionsParameters

Object

A dictionary of index projection-specific configuration properties. Each name is the name of a specific property. Each value must be of a primitive type.

|Name|Type|Description|
|---|---|---|
|projectionMode|[IndexProjectionMode](#indexprojectionmode)|Defines behavior of the index projections in relation to the rest of the indexer.|

### SearchIndexerKnowledgeStore

Object

Definition of additional projections to azure blob, table, or files, of enriched data.

|Name|Type|Description|
|---|---|---|
|identity|SearchIndexerDataIdentity:<br><br>- [SearchIndexerDataNoneIdentity](#searchindexerdatanoneidentity)<br>- [SearchIndexerDataUserAssignedIdentity](#searchindexerdatauserassignedidentity)|The user-assigned managed identity used for connections to Azure Storage when writing knowledge store projections. If the connection string indicates an identity (ResourceId) and it's not specified, the system-assigned managed identity is used. On updates to the indexer, if the identity is unspecified, the value remains unchanged. If set to "none", the value of this property is cleared.|
|parameters|[SearchIndexerKnowledgeStoreParameters](#searchindexerknowledgestoreparameters)|A dictionary of knowledge store-specific configuration properties. Each name is the name of a specific property. Each value must be of a primitive type.|
|projections|[SearchIndexerKnowledgeStoreProjection](#searchindexerknowledgestoreprojection)[]|A list of additional projections to perform during indexing.|
|storageConnectionString|string|The connection string to the storage account projections will be stored in.|

### SearchIndexerKnowledgeStoreFileProjectionSelector

Object

Projection definition for what data to store in Azure Files.

|Name|Type|Description|
|---|---|---|
|generatedKeyName|string|Name of generated key to store projection under.|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]|Nested inputs for complex projections.|
|referenceKeyName|string|Name of reference key to different projection.|
|source|string|Source data to project.|
|sourceContext|string|Source context for complex projections.|
|storageContainer|string|Blob container to store projections in.|

### SearchIndexerKnowledgeStoreObjectProjectionSelector

Object

Projection definition for what data to store in Azure Blob.

|Name|Type|Description|
|---|---|---|
|generatedKeyName|string|Name of generated key to store projection under.|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]|Nested inputs for complex projections.|
|referenceKeyName|string|Name of reference key to different projection.|
|source|string|Source data to project.|
|sourceContext|string|Source context for complex projections.|
|storageContainer|string|Blob container to store projections in.|

### SearchIndexerKnowledgeStoreParameters

Object

A dictionary of knowledge store-specific configuration properties. Each name is the name of a specific property. Each value must be of a primitive type.

|Name|Type|Default value|Description|
|---|---|---|---|
|synthesizeGeneratedKeyName|boolean|False|Whether or not projections should synthesize a generated key name if one isn't already present.|

### SearchIndexerKnowledgeStoreProjection

Object

Container object for various projection selectors.

|Name|Type|Description|
|---|---|---|
|files|[SearchIndexerKnowledgeStoreFileProjectionSelector](#searchindexerknowledgestorefileprojectionselector)[]|Projections to Azure File storage.|
|objects|[SearchIndexerKnowledgeStoreObjectProjectionSelector](#searchindexerknowledgestoreobjectprojectionselector)[]|Projections to Azure Blob storage.|
|tables|[SearchIndexerKnowledgeStoreTableProjectionSelector](#searchindexerknowledgestoretableprojectionselector)[]|Projections to Azure Table storage.|

### SearchIndexerKnowledgeStoreTableProjectionSelector

Object

Description for what data to store in Azure Tables.

|Name|Type|Description|
|---|---|---|
|generatedKeyName|string|Name of generated key to store projection under.|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]|Nested inputs for complex projections.|
|referenceKeyName|string|Name of reference key to different projection.|
|source|string|Source data to project.|
|sourceContext|string|Source context for complex projections.|
|tableName|string|Name of the Azure table to store projected data in.|

### SearchIndexerSkillset

Object

A list of skills.

|Name|Type|Description|
|---|---|---|
|@odata.etag|string|The ETag of the skillset.|
|cognitiveServices|CognitiveServicesAccount:<br><br>- [AIServicesAccountIdentity](#aiservicesaccountidentity)<br>- [AIServicesAccountKey](#aiservicesaccountkey)<br>- [CognitiveServicesAccountKey](#cognitiveservicesaccountkey)<br>- [DefaultCognitiveServicesAccount](#defaultcognitiveservicesaccount)|Details about the Azure AI service to be used when running skills.|
|description|string|The description of the skillset.|
|encryptionKey|[SearchResourceEncryptionKey](#searchresourceencryptionkey)|A description of an encryption key that you create in Azure Key Vault. This key is used to provide an additional level of encryption-at-rest for your skillset definition when you want full assurance that no one, not even Microsoft, can decrypt your skillset definition. Once you have encrypted your skillset definition, it will always remain encrypted. The search service will ignore attempts to set this property to null. You can change this property as needed if you want to rotate your encryption key; Your skillset definition will be unaffected. Encryption with customer-managed keys is not available for free search services, and is only available for paid services created on or after January 1, 2019.|
|indexProjections|[SearchIndexerIndexProjections](#searchindexerindexprojections)|Definition of additional projections to secondary search index(es).|
|knowledgeStore|[SearchIndexerKnowledgeStore](#searchindexerknowledgestore)|Definition of additional projections to Azure blob, table, or files, of enriched data.|
|name|string|The name of the skillset.|
|skills|SearchIndexerSkill[]:<br><br>- [AmlSkill](#amlskill)[]<br>- [AzureOpenAIEmbeddingSkill](#azureopenaiembeddingskill)[]<br>- [ChatCompletionSkill](#chatcompletionskill)[]<br>- [ConditionalSkill](#conditionalskill)[]<br>- [CustomEntityLookupSkill](#customentitylookupskill)[]<br>- [DocumentExtractionSkill](#documentextractionskill)[]<br>- [DocumentIntelligenceLayoutSkill](#documentintelligencelayoutskill)[]<br>- [EntityLinkingSkill](#entitylinkingskill)[]<br>- [EntityRecognitionSkill](#entityrecognitionskill)[]<br>- [EntityRecognitionSkillV3](#entityrecognitionskillv3)[]<br>- [ImageAnalysisSkill](#imageanalysisskill)[]<br>- [KeyPhraseExtractionSkill](#keyphraseextractionskill)[]<br>- [LanguageDetectionSkill](#languagedetectionskill)[]<br>- [MergeSkill](#mergeskill)[]<br>- [OcrSkill](#ocrskill)[]<br>- [PIIDetectionSkill](#piidetectionskill)[]<br>- [SentimentSkill](#sentimentskill)[]<br>- [SentimentSkillV3](#sentimentskillv3)[]<br>- [ShaperSkill](#shaperskill)[]<br>- [SplitSkill](#splitskill)[]<br>- [TextTranslationSkill](#texttranslationskill)[]<br>- [VisionVectorizeSkill](#visionvectorizeskill)[]<br>- [WebApiSkill](#webapiskill)[]|A list of skills in the skillset.|

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

### SentimentSkill

Object

This skill is deprecated. Use the V3.SentimentSkill instead.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Skills.Text.SentimentSkill|A URI fragment specifying the type of skill.|
|context|string|Represents the level at which operations take place, such as the document root or document content (for example, /document or /document/content). The default is /document.|
|defaultLanguageCode|[SentimentSkillLanguage](#sentimentskilllanguage)|A value indicating which language code to use. Default is `en`.|
|description|string|The description of the skill which describes the inputs, outputs, and usage of the skill.|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]|Inputs of the skills could be a column in the source data set, or the output of an upstream skill.|
|name|string|The name of the skill which uniquely identifies it within the skillset. A skill with no name defined will be given a default name of its 1-based index in the skills array, prefixed with the character '#'.|
|outputs|[OutputFieldMappingEntry](#outputfieldmappingentry)[]|The output of a skill is either a field in a search index, or a value that can be consumed as an input by another skill.|

### SentimentSkillLanguage

Enumeration

Deprecated. The language codes supported for input text by SentimentSkill.

|Value|Description|
|---|---|
|da|Danish|
|nl|Dutch|
|en|English|
|fi|Finnish|
|fr|French|
|de|German|
|el|Greek|
|it|Italian|
|no|Norwegian (Bokmaal)|
|pl|Polish|
|pt-PT|Portuguese (Portugal)|
|ru|Russian|
|es|Spanish|
|sv|Swedish|
|tr|Turkish|

### SentimentSkillV3

Object

Using the Text Analytics API, evaluates unstructured text and for each record, provides sentiment labels (such as "negative", "neutral" and "positive") based on the highest confidence score found by the service at a sentence and document-level.

|Name|Type|Default value|Description|
|---|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Skills.Text.V3.SentimentSkill||A URI fragment specifying the type of skill.|
|context|string||Represents the level at which operations take place, such as the document root or document content (for example, /document or /document/content). The default is /document.|
|defaultLanguageCode|string||A value indicating which language code to use. Default is `en`.|
|description|string||The description of the skill which describes the inputs, outputs, and usage of the skill.|
|includeOpinionMining|boolean|False|If set to true, the skill output will include information from Text Analytics for opinion mining, namely targets (nouns or verbs) and their associated assessment (adjective) in the text. Default is false.|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]||Inputs of the skills could be a column in the source data set, or the output of an upstream skill.|
|modelVersion|string||The version of the model to use when calling the Text Analytics service. It will default to the latest available when not specified. We recommend you do not specify this value unless absolutely necessary.|
|name|string||The name of the skill which uniquely identifies it within the skillset. A skill with no name defined will be given a default name of its 1-based index in the skills array, prefixed with the character '#'.|
|outputs|[OutputFieldMappingEntry](#outputfieldmappingentry)[]||The output of a skill is either a field in a search index, or a value that can be consumed as an input by another skill.|

### ShaperSkill

Object

A skill for reshaping the outputs. It creates a complex type to support composite fields (also known as multipart fields).

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Skills.Util.ShaperSkill|A URI fragment specifying the type of skill.|
|context|string|Represents the level at which operations take place, such as the document root or document content (for example, /document or /document/content). The default is /document.|
|description|string|The description of the skill which describes the inputs, outputs, and usage of the skill.|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]|Inputs of the skills could be a column in the source data set, or the output of an upstream skill.|
|name|string|The name of the skill which uniquely identifies it within the skillset. A skill with no name defined will be given a default name of its 1-based index in the skills array, prefixed with the character '#'.|
|outputs|[OutputFieldMappingEntry](#outputfieldmappingentry)[]|The output of a skill is either a field in a search index, or a value that can be consumed as an input by another skill.|

### SplitSkill

Object

A skill to split a string into chunks of text.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Skills.Text.SplitSkill|A URI fragment specifying the type of skill.|
|azureOpenAITokenizerParameters|[AzureOpenAITokenizerParameters](#azureopenaitokenizerparameters)|Only applies if the unit is set to azureOpenAITokens. If specified, the splitSkill will use these parameters when performing the tokenization. The parameters are a valid 'encoderModelName' and an optional 'allowedSpecialTokens' property.|
|context|string|Represents the level at which operations take place, such as the document root or document content (for example, /document or /document/content). The default is /document.|
|defaultLanguageCode|[SplitSkillLanguage](#splitskilllanguage)|A value indicating which language code to use. Default is `en`.|
|description|string|The description of the skill which describes the inputs, outputs, and usage of the skill.|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]|Inputs of the skills could be a column in the source data set, or the output of an upstream skill.|
|maximumPageLength|integer (int32)|The desired maximum page length. Default is 10000.|
|maximumPagesToTake|integer (int32)|Only applicable when textSplitMode is set to 'pages'. If specified, the SplitSkill will discontinue splitting after processing the first 'maximumPagesToTake' pages, in order to improve performance when only a few initial pages are needed from each document.|
|name|string|The name of the skill which uniquely identifies it within the skillset. A skill with no name defined will be given a default name of its 1-based index in the skills array, prefixed with the character '#'.|
|outputs|[OutputFieldMappingEntry](#outputfieldmappingentry)[]|The output of a skill is either a field in a search index, or a value that can be consumed as an input by another skill.|
|pageOverlapLength|integer (int32)|Only applicable when textSplitMode is set to 'pages'. If specified, n+1th chunk will start with this number of characters/tokens from the end of the nth chunk.|
|textSplitMode|[TextSplitMode](#textsplitmode)|A value indicating which split mode to perform.|
|unit|[SplitSkillUnit](#splitskillunit)|Only applies if textSplitMode is set to pages. There are two possible values. The choice of the values will decide the length (maximumPageLength and pageOverlapLength) measurement. The default is 'characters', which means the length will be measured by character.|

### SplitSkillEncoderModelName

Enumeration

Only applies if the unit is set to azureOpenAITokens. Options include 'R50k_base', 'P50k_base', 'P50k_edit' and 'CL100k_base'. The default value is 'CL100k_base'.

|Value|Description|
|---|---|
|r50k_base|Refers to a base model trained with a 50,000 token vocabulary, often used in general natural language processing tasks.|
|p50k_base|A base model with a 50,000 token vocabulary, optimized for prompt-based tasks.|
|p50k_edit|Similar to p50k_base but fine-tuned for editing or rephrasing tasks with a 50,000 token vocabulary.|
|cl100k_base|A base model with a 100,000 token vocabulary.|

### SplitSkillLanguage

Enumeration

The language codes supported for input text by SplitSkill.

|Value|Description|
|---|---|
|am|Amharic|
|bs|Bosnian|
|cs|Czech|
|da|Danish|
|de|German|
|en|English|
|es|Spanish|
|et|Estonian|
|fi|Finnish|
|fr|French|
|he|Hebrew|
|hi|Hindi|
|hr|Croatian|
|hu|Hungarian|
|id|Indonesian|
|is|Icelandic|
|it|Italian|
|ja|Japanese|
|ko|Korean|
|lv|Latvian|
|nb|Norwegian|
|nl|Dutch|
|pl|Polish|
|pt|Portuguese (Portugal)|
|pt-br|Portuguese (Brazil)|
|ru|Russian|
|sk|Slovak|
|sl|Slovenian|
|sr|Serbian|
|sv|Swedish|
|tr|Turkish|
|ur|Urdu|
|zh|Chinese (Simplified)|

### SplitSkillUnit

Enumeration

A value indicating which unit to use.

|Value|Description|
|---|---|
|characters|The length will be measured by character.|
|azureOpenAITokens|The length will be measured by an AzureOpenAI tokenizer from the tiktoken library.|

### TextSplitMode

Enumeration

A value indicating which split mode to perform.

|Value|Description|
|---|---|
|pages|Split the text into individual pages.|
|sentences|Split the text into individual sentences.|

### TextTranslationSkill

Object

A skill to translate text from one language to another.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Skills.Text.TranslationSkill|A URI fragment specifying the type of skill.|
|context|string|Represents the level at which operations take place, such as the document root or document content (for example, /document or /document/content). The default is /document.|
|defaultFromLanguageCode|[TextTranslationSkillLanguage](#texttranslationskilllanguage)|The language code to translate documents from for documents that don't specify the from language explicitly.|
|defaultToLanguageCode|[TextTranslationSkillLanguage](#texttranslationskilllanguage)|The language code to translate documents into for documents that don't specify the to language explicitly.|
|description|string|The description of the skill which describes the inputs, outputs, and usage of the skill.|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]|Inputs of the skills could be a column in the source data set, or the output of an upstream skill.|
|name|string|The name of the skill which uniquely identifies it within the skillset. A skill with no name defined will be given a default name of its 1-based index in the skills array, prefixed with the character '#'.|
|outputs|[OutputFieldMappingEntry](#outputfieldmappingentry)[]|The output of a skill is either a field in a search index, or a value that can be consumed as an input by another skill.|
|suggestedFrom|[TextTranslationSkillLanguage](#texttranslationskilllanguage)|The language code to translate documents from when neither the fromLanguageCode input nor the defaultFromLanguageCode parameter are provided, and the automatic language detection is unsuccessful. Default is `en`.|

### TextTranslationSkillLanguage

Enumeration

The language codes supported for input text by TextTranslationSkill.

|Value|Description|
|---|---|
|af|Afrikaans|
|ar|Arabic|
|bn|Bangla|
|bs|Bosnian (Latin)|
|bg|Bulgarian|
|yue|Cantonese (Traditional)|
|ca|Catalan|
|zh-Hans|Chinese Simplified|
|zh-Hant|Chinese Traditional|
|hr|Croatian|
|cs|Czech|
|da|Danish|
|nl|Dutch|
|en|English|
|et|Estonian|
|fj|Fijian|
|fil|Filipino|
|fi|Finnish|
|fr|French|
|de|German|
|el|Greek|
|ht|Haitian Creole|
|he|Hebrew|
|hi|Hindi|
|mww|Hmong Daw|
|hu|Hungarian|
|is|Icelandic|
|id|Indonesian|
|it|Italian|
|ja|Japanese|
|sw|Kiswahili|
|tlh|Klingon|
|tlh-Latn|Klingon (Latin script)|
|tlh-Piqd|Klingon (Klingon script)|
|ko|Korean|
|lv|Latvian|
|lt|Lithuanian|
|mg|Malagasy|
|ms|Malay|
|mt|Maltese|
|nb|Norwegian|
|fa|Persian|
|pl|Polish|
|pt|Portuguese|
|pt-br|Portuguese (Brazil)|
|pt-PT|Portuguese (Portugal)|
|otq|Queretaro Otomi|
|ro|Romanian|
|ru|Russian|
|sm|Samoan|
|sr-Cyrl|Serbian (Cyrillic)|
|sr-Latn|Serbian (Latin)|
|sk|Slovak|
|sl|Slovenian|
|es|Spanish|
|sv|Swedish|
|ty|Tahitian|
|ta|Tamil|
|te|Telugu|
|th|Thai|
|to|Tongan|
|tr|Turkish|
|uk|Ukrainian|
|ur|Urdu|
|vi|Vietnamese|
|cy|Welsh|
|yua|Yucatec Maya|
|ga|Irish|
|kn|Kannada|
|mi|Maori|
|ml|Malayalam|
|pa|Punjabi|

### VisionVectorizeSkill

Object

Allows you to generate a vector embedding for a given image or text input using the Azure AI Services Vision Vectorize API.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Skills.Vision.VectorizeSkill|A URI fragment specifying the type of skill.|
|context|string|Represents the level at which operations take place, such as the document root or document content (for example, /document or /document/content). The default is /document.|
|description|string|The description of the skill which describes the inputs, outputs, and usage of the skill.|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]|Inputs of the skills could be a column in the source data set, or the output of an upstream skill.|
|modelVersion|string|The version of the model to use when calling the AI Services Vision service. It will default to the latest available when not specified.|
|name|string|The name of the skill which uniquely identifies it within the skillset. A skill with no name defined will be given a default name of its 1-based index in the skills array, prefixed with the character '#'.|
|outputs|[OutputFieldMappingEntry](#outputfieldmappingentry)[]|The output of a skill is either a field in a search index, or a value that can be consumed as an input by another skill.|

### VisualFeature

Enumeration

The strings indicating what visual feature types to return.

|Value|Description|
|---|---|
|adult|Visual features recognized as adult persons.|
|brands|Visual features recognized as commercial brands.|
|categories|Categories.|
|description|Description.|
|faces|Visual features recognized as people faces.|
|objects|Visual features recognized as objects.|
|tags|Tags.|

### WebApiSkill

Object

A skill that can call a Web API endpoint, allowing you to extend a skillset by having it call your custom code.

|Name|Type|Description|
|---|---|---|
|@odata.type|string:<br><br>#Microsoft.Skills.Custom.WebApiSkill|A URI fragment specifying the type of skill.|
|authIdentity|SearchIndexerDataIdentity:<br><br>- [SearchIndexerDataNoneIdentity](#searchindexerdatanoneidentity)<br>- [SearchIndexerDataUserAssignedIdentity](#searchindexerdatauserassignedidentity)|The user-assigned managed identity used for outbound connections. If an authResourceId is provided and it's not specified, the system-assigned managed identity is used. On updates to the indexer, if the identity is unspecified, the value remains unchanged. If set to "none", the value of this property is cleared.|
|authResourceId|string|Applies to custom skills that connect to external code in an Azure function or some other application that provides the transformations. This value should be the application ID created for the function or app when it was registered with Azure Active Directory. When specified, the custom skill connects to the function or app using a managed ID (either system or user-assigned) of the search service and the access token of the function or app, using this value as the resource id for creating the scope of the access token.|
|batchSize|integer (int32)|The desired batch size which indicates number of documents.|
|context|string|Represents the level at which operations take place, such as the document root or document content (for example, /document or /document/content). The default is /document.|
|degreeOfParallelism|integer (int32)|If set, the number of parallel calls that can be made to the Web API.|
|description|string|The description of the skill which describes the inputs, outputs, and usage of the skill.|
|httpHeaders|object|The headers required to make the http request.|
|httpMethod|string|The method for the http request.|
|inputs|[InputFieldMappingEntry](#inputfieldmappingentry)[]|Inputs of the skills could be a column in the source data set, or the output of an upstream skill.|
|name|string|The name of the skill which uniquely identifies it within the skillset. A skill with no name defined will be given a default name of its 1-based index in the skills array, prefixed with the character '#'.|
|outputs|[OutputFieldMappingEntry](#outputfieldmappingentry)[]|The output of a skill is either a field in a search index, or a value that can be consumed as an input by another skill.|
|timeout|string (duration)|The desired timeout for the request. Default is 30 seconds.|
|uri|string|The url for the Web API.|
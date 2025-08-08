Below is a ready-to-run VS Code REST client file that focuses on the Create/Update endpoints for the main Azure AI Search resources: Data Sources, Indexes, Skillsets, and Indexers. It uses the API versions shown in your notes:

- Core resources (Data Sources, Indexes, Indexers): 2024-07-01
- Skillsets:
  - Create (POST): 2025-05-01-preview
  - Create or Update (PUT): 2025-08-01-preview

Copy this into a .rest or .http file in VS Code, fill in the variables at the top, and send each request as needed.

```
http
@baseUrl = https://YOUR-SEARCH-SERVICE.search.windows.net
@apiKey = YOUR-ADMIN-API-KEY

# Core GA API version for Data Sources, Indexes, Indexers
@apiVersionCore = 2024-07-01

# Preview API versions for Skillsets (per notes)
@apiVersionSkillsetCreate = 2025-05-01-preview
@apiVersionSkillsetPut = 2025-08-01-preview

# Resource names
@dataSourceName = cog-search-demo-ds
@indexName = cog-search-demo-idx
@skillsetName = cog-search-demo-ss
@indexerName = cog-search-demo-idxr

# Storage connection for data source
@storageConnectionString = DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net
@blobContainer = cog-search-demo


### Sanity check: list indexes
GET {{baseUrl}}/indexes?api-version={{apiVersionCore}}  HTTP/1.1
  Content-Type: application/json
  api-key: {{apiKey}}



### Create Data Source (Azure Blob)
# Creates a connection for the indexer to your blob container
POST {{baseUrl}}/datasources?api-version={{apiVersionCore}}  HTTP/1.1
  Content-Type: application/json
  api-key: {{apiKey}}

{
  "name": "{{dataSourceName}}",
  "description": "Blob data source for AI enrichment demo.",
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



### Create Index (schema must include target fields for enriched outputs)
POST {{baseUrl}}/indexes?api-version={{apiVersionCore}}  HTTP/1.1
  Content-Type: application/json
  api-key: {{apiKey}}

{
  "name": "{{indexName}}",
  "defaultScoringProfile": "",
  "fields": [
    { "name": "content", "type": "Edm.String", "searchable": true, "sortable": false, "filterable": false, "facetable": false },
    { "name": "text", "type": "Collection(Edm.String)", "searchable": true, "filterable": true, "sortable": false, "facetable": false },
    { "name": "language", "type": "Edm.String", "searchable": false, "sortable": true, "filterable": true, "facetable": false },
    { "name": "keyPhrases", "type": "Collection(Edm.String)", "searchable": true, "sortable": false, "filterable": true, "facetable": true },
    { "name": "organizations", "type": "Collection(Edm.String)", "searchable": true, "sortable": false, "filterable": true, "facetable": true },
    { "name": "persons", "type": "Collection(Edm.String)", "searchable": true, "sortable": false, "filterable": true, "facetable": true },
    { "name": "locations", "type": "Collection(Edm.String)", "searchable": true, "sortable": false, "filterable": true, "facetable": true },

    { "name": "metadata_storage_path", "type": "Edm.String", "key": true, "searchable": true, "sortable": false, "filterable": false, "facetable": false },
    { "name": "metadata_storage_name", "type": "Edm.String", "searchable": true, "sortable": false, "filterable": false, "facetable": false }
  ]
}



### Create Skillset (POST — template)
# Use when you want to create a brand new skillset.
# Per notes, a skillset must have at least one skill; start with this template and add built-in skills
# (e.g., OCR, Text Merger, Language Detection, Entity Recognition v3, Text Split, Key Phrase Extraction).
POST {{baseUrl}}/skillsets?api-version={{apiVersionSkillsetCreate}}  HTTP/1.1
  Content-Type: application/json
  api-key: {{apiKey}}

{
  "name": "{{skillsetName}}",
  "description": "Template skillset (add skills as needed).",
  "skills": [
    /* Insert one or more skills here.
       Examples from the notes include:
       - OCR over /document/normalized_images/*
       - Text Merger to produce /document/merged_text
       - Language Detection for language code
       - Entity Recognition v3 (organizations, persons, locations)
       - Text Split to produce /document/pages
       - Key Phrase Extraction from /document/pages/*
       Remove this comment block and supply actual skill definitions. */
  ]
  /* Optional sections you can add based on your scenario:
     "cognitiveServices": { ... },   // attach Azure AI services for billable skills
     "knowledgeStore": { ... },      // project outputs to Storage
     "indexProjections": { ... },    // project outputs to secondary indexes
     "encryptionKey": { ... }        // customer-managed key
  */
}



### Create or Update Skillset (PUT — idempotent)
# Use this to create the skillset if it doesn't exist or update it if it does.
# Optional concurrency headers: If-Match (with ETag) or If-None-Match: *
PUT {{baseUrl}}/skillsets('{{skillsetName}}')?api-version={{apiVersionSkillsetPut}}  HTTP/1.1
  Content-Type: application/json
  api-key: {{apiKey}}
  # If-Match: "ETAG-VALUE"     # optional
  # If-None-Match: *           # optional

{
  "name": "{{skillsetName}}",
  "description": "Template skillset (add skills as needed).",
  "skills": [
    /* Same guidance as above: insert your built-in skills here */
  ]
}



### Create Indexer (skills-based indexing)
# Ties together Data Source + Index + Skillset and defines mappings and run-time configuration.
# Creating the indexer starts the pipeline. This sample uses imageAction + OCR + Text Merge scenario per notes.
POST {{baseUrl}}/indexers?api-version={{apiVersionCore}}  HTTP/1.1
  Content-Type: application/json
  api-key: {{apiKey}}

{
  "name": "{{indexerName}}",
  "description": "Demo indexer that does AI enrichment",
  "dataSourceName": "{{dataSourceName}}",
  "targetIndexName": "{{indexName}}",
  "skillsetName": "{{skillsetName}}",

  "fieldMappings": [
    {
      "sourceFieldName": "metadata_storage_path",
      "targetFieldName": "metadata_storage_path",
      "mappingFunction": { "name": "base64Encode" }
    },
    {
      "sourceFieldName": "metadata_storage_name",
      "targetFieldName": "metadata_storage_name"
    }
  ],

  "outputFieldMappings": [
    { "sourceFieldName": "/document/merged_text", "targetFieldName": "content" },
    { "sourceFieldName": "/document/normalized_images/*/text", "targetFieldName": "text" },
    { "sourceFieldName": "/document/organizations", "targetFieldName": "organizations" },
    { "sourceFieldName": "/document/language", "targetFieldName": "language" },
    { "sourceFieldName": "/document/persons", "targetFieldName": "persons" },
    { "sourceFieldName": "/document/locations", "targetFieldName": "locations" },
    { "sourceFieldName": "/document/pages/*/keyPhrases/*", "targetFieldName": "keyPhrases" }
  ],

  "parameters": {
    "batchSize": 1,
    "maxFailedItems": -1,
    "maxFailedItemsPerBatch": -1,
    "configuration": {
      "dataToExtract": "contentAndMetadata",
      "imageAction": "generateNormalizedImages"
    }
  }
}



### OPTIONAL: Indexer definition pattern for content-based indexing (no skillset)
# Keeps the pattern handy if you need a plain-text or vector-only ingestion (no enrichment).
# Fill in configuration as needed (e.g., indexedFileNameExtensions for blobs).
POST {{baseUrl}}/indexers?api-version={{apiVersionCore}}  HTTP/1.1
  Content-Type: application/json
  api-key: {{apiKey}}

{
  "name": "content-only-idxr",
  "description": "Content-based indexing (no skillset)",
  "dataSourceName": "{{dataSourceName}}",
  "targetIndexName": "{{indexName}}",
  "parameters": {
    "batchSize": null,
    "maxFailedItems": 0,
    "maxFailedItemsPerBatch": 0,
    "base64EncodeKeys": false,
    "configuration": {
      /* For Azure Blob, you can set:
         "indexedFileNameExtensions": ".pdf,.docx"
      */
    }
  }
}


```

How to use this file

- Order of operations:
  1) Create Data Source
  2) Create Index
  3) Create Skillset (POST) or Create/Update (PUT)
  4) Create Indexer (this kicks off the pipeline)
- Index must include fields for any enriched outputs you plan to map. The index sample above includes fields commonly used in the tutorial (content, language, keyPhrases, organizations, persons, locations, text).
- Field mappings:
  - fieldMappings route unmodified source fields directly to index fields (before skillset runs).
  - outputFieldMappings route skill outputs to index fields (after enrichment).
- Indexer parameters of note:
  - configuration.dataToExtract: contentAndMetadata
  - configuration.imageAction: generateNormalizedImages (enables image extraction; per notes this is computation-intensive and can incur costs)
  - maxFailedItems / maxFailedItemsPerBatch: set to -1 in the demo to ignore errors (appropriate for small demos; increase for production).
- Skillsets:
  - Skills run in parallel unless there are dependencies.
  - Inputs typically bind to /document/content (extracted text) or /document/normalized_images/* (images).
  - Outputs are written into the enrichment tree at the context node (for example, /document/merged_text, /document/pages, etc.).
  - You can attach Azure AI services for billable skills via the cognitiveServices property; for small workloads, the tutorial mentions a free allocation per indexer.


---


Quick Reference: Azure AI Search REST API for Skillsets

Overview
- A skillset is a top-level resource used by indexers to enrich content during indexing.
- Requirements and limits:
  - Unique name per search service.
  - Must contain at least one skill (3–5 typical; maximum 30).
  - Skills can be chained, branched, and repeated (same type multiple times).
  - To run a skillset you need a data source, an index, and an indexer.
  - Consider enabling enrichment caching to reduce cost during development.
- Execution:
  - Independent skills run in parallel; dependent skills are ordered by the service based on inputs/outputs.
  - Output nodes are written into the enrichment tree at the skill’s context.

Base URL and headers
- Base: https://{your-search-service-name}.search.windows.net
- Required headers:
  - api-key: {your-admin-key}
  - Content-Type: application/json
- Optional header:
  - x-ms-client-request-id: {uuid} for tracking

API versions shown in examples
- Create (POST): 2025-05-01-preview
- Manage (GET/PUT/DELETE/LIST): 2025-08-01-preview
Note: Always include api-version; use the latest suitable for your service.

Operations

Create a skillset (POST)
- Endpoint: POST {endpoint}/skillsets?api-version=2025-05-01-preview
- Returns: 201 Created with the SearchIndexerSkillset.

Create or update (idempotent) a skillset (PUT)
- Endpoint: PUT {endpoint}/skillsets('{skillsetName}')?api-version=2025-08-01-preview
- Headers (optional for concurrency): If-Match: "{etag}" or If-None-Match: *
- Returns: 201 Created (new) or 200 OK (updated)

Get a skillset
- Endpoint: GET {endpoint}/skillsets('{skillsetName}')?api-version=2025-08-01-preview
- Returns: 200 OK with the SearchIndexerSkillset

List skillsets
- Endpoint: GET {endpoint}/skillsets?api-version=2025-08-01-preview[&$select=name,description]
- Returns: 200 OK with a list of SearchIndexerSkillset

Delete a skillset
- Endpoint: DELETE {endpoint}/skillsets('{skillsetName}')?api-version=2025-08-01-preview
- Headers (optional): If-Match: "{etag}" or If-None-Match: *
- Returns: 204 No Content; 404 if not found

Skillset JSON anatomy (request body)
Top-level fields:
- name (required): string
- description (optional): string
- skills (required): array of skills (see supported types below)
- cognitiveServices (optional): attach Azure AI services for billable skills
  - Types: DefaultCognitiveServicesAccount, CognitiveServicesAccountKey, AIServicesAccountKey, AIServicesAccountIdentity
  - Must be in same region as Azure AI Search
- knowledgeStore (optional): project enriched output to Azure Storage (tables/objects/files)
- indexProjections (optional): project enriched output to secondary search index(es)
- encryptionKey (optional): customer-managed encryption key in Azure Key Vault
- @odata.etag (optional): ETag for concurrency control

Skill basics (inside skills[])
- @odata.type: the skill type identifier (see list below)
- name: unique within the skillset
- context: where the skill runs in the enrichment tree (default /document)
  - Examples:
    - /document (whole doc)
    - /document/pages/* (per page chunk)
    - /document/normalized_images/* (per image)
- inputs: array of { name, source }
  - source is a path in the enrichment tree (JSON Pointer-like)
  - Use /* to iterate over items in a collection
  - Common sources:
    - /document/content (text extracted from files)
    - /document/normalized_images/* (images normalized by document cracking)
- outputs: array of { name, targetName? }
  - targetName disambiguates node names in the enrichment tree
  - Outputs are added as children of the context node

Supported skill types (skills[])
- Text/NLP: SplitSkill, LanguageDetectionSkill, KeyPhraseExtractionSkill, EntityRecognitionSkill (deprecated), EntityRecognitionSkillV3, EntityLinkingSkill, SentimentSkill (deprecated), SentimentSkillV3, PIIDetectionSkill, TextTranslationSkill, CustomEntityLookupSkill, ShaperSkill, MergeSkill
- Vision/Doc: OcrSkill, ImageAnalysisSkill, DocumentExtractionSkill, DocumentIntelligenceLayoutSkill, VisionVectorizeSkill
- Custom/ML/LLM: WebApiSkill, AmlSkill, AzureOpenAIEmbeddingSkill, ChatCompletionSkill
- Utility: ConditionalSkill

Pathing and chaining tips
- Reference a prior skill’s output in a downstream skill via its path, e.g., /document/orgs for a list, or /document/orgs/* for each element.
- Setting context to a collection (e.g., /document/pages/*) controls both how many times the skill runs and where outputs land.
- Example: Split text into pages, then run key phrases per page:
  - Split outputs /document/pages; downstream skills use context and input of /document/pages/*

HTTP examples
Create (POST) — minimal non-billable example
```http
POST https://{endpoint}/skillsets?api-version=2025-05-01-preview
Content-Type: application/json
api-key: {apiKey}

{
  "name": "quickref-ss",
  "description": "Minimal skillset using Split",
  "skills": [
    {
      "@odata.type": "#Microsoft.Skills.Text.SplitSkill",
      "textSplitMode": "pages",
      "maximumPageLength": 4000,
      "inputs": [
        { "name": "text", "source": "/document/content" }
      ],
      "outputs": [
        { "name": "textItems", "targetName": "pages" }
      ]
    }
  ]
}
```

Create (POST) — typical multi-skill (OCR → Merge → Split → Language → Key Phrases → Entities)
```http
POST https://{endpoint}/skillsets?api-version=2024-07-01
Content-Type: application/json
api-key: {apiKey}

{
  "name": "cog-search-demo-ss",
  "description": "Apply OCR, detect language, extract entities, and extract key-phrases.",
  "cognitiveServices": null,
  "skills": [
    {
      "@odata.type": "#Microsoft.Skills.Vision.OcrSkill",
      "context": "/document/normalized_images/*",
      "defaultLanguageCode": "en",
      "detectOrientation": true,
      "inputs": [{ "name": "image", "source": "/document/normalized_images/*" }],
      "outputs": [{ "name": "text" }]
    },
    {
      "@odata.type": "#Microsoft.Skills.Text.MergeSkill",
      "context": "/document",
      "insertPreTag": " ",
      "insertPostTag": " ",
      "inputs": [
        { "name": "text", "source": "/document/content" },
        { "name": "itemsToInsert", "source": "/document/normalized_images/*/text" },
        { "name": "offsets", "source": "/document/normalized_images/*/contentOffset" }
      ],
      "outputs": [{ "name": "mergedText", "targetName": "merged_text" }]
    },
    {
      "@odata.type": "#Microsoft.Skills.Text.SplitSkill",
      "context": "/document",
      "textSplitMode": "pages",
      "maximumPageLength": 4000,
      "defaultLanguageCode": "en",
      "inputs": [{ "name": "text", "source": "/document/merged_text" }],
      "outputs": [{ "name": "textItems", "targetName": "pages" }]
    },
    {
      "@odata.type": "#Microsoft.Skills.Text.LanguageDetectionSkill",
      "context": "/document",
      "inputs": [{ "name": "text", "source": "/document/merged_text" }],
      "outputs": [{ "name": "languageName", "targetName": "language" }]
    },
    {
      "@odata.type": "#Microsoft.Skills.Text.KeyPhraseExtractionSkill",
      "context": "/document/pages/*",
      "inputs": [{ "name": "text", "source": "/document/pages/*" }],
      "outputs": [{ "name": "keyPhrases", "targetName": "keyPhrases" }]
    },
    {
      "@odata.type": "#Microsoft.Skills.Text.V3.EntityRecognitionSkill",
      "categories": ["Organization"],
      "context": "/document",
      "inputs": [{ "name": "text", "source": "/document/merged_text" }],
      "outputs": [{ "name": "organizations", "targetName": "organizations" }]
    }
  ]
}
```

Create or update (PUT) — with ETag concurrency (example shows advanced skills)
```http
PUT https://{endpoint}/skillsets('tempskillset')?api-version=2025-08-01-preview
Content-Type: application/json
api-key: {apiKey}
If-Match: "0x1234568AE7E58A1"

{
  "name": "tempskillset",
  "description": "Skillset for extracting entities and more",
  "skills": [
    { "@odata.type": "#Microsoft.Skills.Text.LanguageDetectionSkill",
      "name": "skill2",
      "inputs": [
        { "name": "text", "source": "/document/content" },
        { "name": "countryHint", "source": "/document/countryHint" }
      ],
      "outputs": [{ "name": "languageCode", "targetName": "languageCode" }]
    },
    { "@odata.type": "#Microsoft.Skills.Text.SplitSkill",
      "name": "skill3",
      "textSplitMode": "pages",
      "maximumPageLength": 4000,
      "unit": "azureOpenAITokens",
      "azureOpenAITokenizerParameters": { "encoderModelName": "cl100k_base", "allowedSpecialTokens": ["[START]","[END]"] },
      "inputs": [
        { "name": "text", "source": "/document/content" },
        { "name": "languageCode", "source": "/document/languageCode" }
      ],
      "outputs": [{ "name": "textItems", "targetName": "pages" }]
    },
    { "@odata.type": "#Microsoft.Skills.Util.DocumentIntelligenceLayoutSkill",
      "name": "docIntelligenceLayoutSkill#2",
      "context": "/document",
      "outputFormat": "text",
      "outputMode": "oneToMany",
      "extractionOptions": ["images","locationMetadata"],
      "chunkingProperties": { "unit": "characters", "maximumLength": 500, "overlapLength": 50 },
      "inputs": [{ "name": "file_data", "source": "/document/content" }],
      "outputs": [
        { "name": "text_sections", "targetName": "text_sections" },
        { "name": "normalized_images", "targetName": "normalized_images" }
      ]
    },
    { "@odata.type": "#Microsoft.Skills.Custom.ChatCompletionSkill",
      "name": "chatCompletionSkill",
      "context": "/document/normalized_images/*",
      "uri": "https://{aoai-subdomain}/openai/deployments/{deployment}/chat/completions",
      "timeout": "PT30S",
      "degreeOfParallelism": 5,
      "apiKey": "<api-key>",
      "inputs": [
        { "name": "text", "source": "/document/content" },
        { "name": "systemMessage", "source": "/document/system_message" },
        { "name": "userMessage", "source": "/document/user_message" },
        { "name": "image", "source": "/document/normalized_images/*" },
        { "name": "imageDetail", "source": "/document/detail" }
      ],
      "outputs": [{ "name": "response", "targetName": "response" }],
      "commonModelParameters": { "model": "gpt-4o", "temperature": 0 },
      "extraParametersBehavior": "error",
      "responseFormat": {
        "type": "jsonSchema",
        "jsonSchemaProperties": {
          "name": "Some Name",
          "description": "Some Description",
          "strict": true,
          "schema": {
            "type": "object",
            "required": ["steps","answer"],
            "additionalProperties": false,
            "properties": "{\"steps\": {\"type\": \"array\", \"items\": {\"type\": \"string\"}}, \"answer\": {\"type\": \"string\"}}"
          }
        }
      }
    }
  ],
  "cognitiveServices": {
    "@odata.type": "#Microsoft.Azure.Search.AIServicesByKey",
    "key": "myKey",
    "subdomainUrl": "https://mySubdomainName.cognitiveservices.azure.com",
    "description": "Description of the Azure AI service resource attached to a skillset"
  },
  "@odata.etag": "0x1234568AE7E58A1"
}
```
Get
```http
GET https://{endpoint}/skillsets('tempskillset')?api-version=2025-08-01-preview
api-key: {apiKey}
```

List (optionally select fields)
```http
GET https://{endpoint}/skillsets?api-version=2025-08-01-preview&$select=name,description
api-key: {apiKey}
```

Delete (with optional concurrency header)
```http
DELETE https://{endpoint}/skillsets('tempskillset')?api-version=2025-08-01-preview
api-key: {apiKey}
If-Match: "0x1234568AE7E58A1"
```

Responses and status codes
- POST /skillsets: 201 Created (returns SearchIndexerSkillset); errors return ErrorResponse.
- PUT /skillsets('{name}'): 201 Created (new) or 200 OK (updated); errors return ErrorResponse.
- GET /skillsets('{name}'): 200 OK with skillset.
- GET /skillsets: 200 OK with list.
- DELETE /skillsets('{name}'): 204 No Content; 404 Not Found; errors return ErrorResponse.

Concurrency via ETags
- Read the skillset to obtain @odata.etag.
- Use If-Match: "{etag}" on PUT/DELETE to update/delete only if unchanged.
- Use If-None-Match: * on PUT to create only if it doesn’t already exist.

Design tips and prerequisites
- Context controls invocation count and output location:
  - /document: once per document
  - /document/pages/*: once per page (from SplitSkill)
  - /document/normalized_images/*: once per image
- Inputs/outputs:
  - Input names are skill-specific (e.g., text, languageCode, image).
  - Output names are skill-specific; use targetName to disambiguate.
- Chaining:
  - Pass outputs by path to downstream skills (e.g., /document/pages/*).
- Billable skills:
  - If using billable skills (Language, Vision, etc.), attach an Azure AI services resource via cognitiveServices. Omit or set to null for small workloads if you rely on the free allocation (20 transactions per indexer in tutorials).
- Knowledge Store and Index Projections:
  - Use knowledgeStore to persist enriched outputs into Azure Storage.
  - Use indexProjections for projecting enriched data to secondary search indexes.
- Limits:
  - Max 30 skills per skillset.
- Testing:
  - You need a data source, index, and indexer to run/test the skillset.

Advanced notes
- SplitSkill token-based chunking:
  - unit: "azureOpenAITokens"
  - azureOpenAITokenizerParameters: { encoderModelName: "cl100k_base", allowedSpecialTokens: [...] }
- DocumentIntelligenceLayoutSkill:
  - outputFormat: "markdown" (default) or "text"
  - outputMode: "oneToMany" (default)
  - extractionOptions: e.g., "images", "locationMetadata"
  - chunkingProperties: unit, maximumLength, overlapLength
- ChatCompletionSkill:
  - Calls Azure AI Foundry’s chat completions endpoint.
  - Supports responseFormat types: text, json_object, json_schema.
  - Common knobs: model, temperature, maxTokens, stop, degreeOfParallelism, timeout.
  - Inputs can include systemMessage, userMessage, text, image, imageDetail.
  - extraParametersBehavior (default: error) and extraParameters dictionary for model-specific options.

Optional parameters on PUT (management)
- Prefer, If-Match, If-None-Match, x-ms-client-request-id
- IgnoreResetRequirementsParameter, DisableCacheReprocessingChangeDetectionParameter (advanced scenarios)

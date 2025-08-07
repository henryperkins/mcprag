# Tool Test Results

## 1. create_datasource Tool

**Request:**
```json
{
  "name": "test-datasource-blob",
  "datasource_type": "azureblob",
  "connection_info": {
    "connectionString": "DefaultEndpointsProtocol=https;AccountName=teststorage;AccountKey=test123==;EndpointSuffix=core.windows.net"
  },
  "container": {
    "name": "test-container",
    "query": "/"
  },
  "description": "Test blob storage datasource",
  "test_connection": false
}
```

**Response:**
```json
{
  "ok": false,
  "error": "Client error '400 Bad Request' for url 'https://oairesourcesearch.search.windows.net/datasources/test-datasource-blob?api-version=2025-05-01-preview'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400",
  "code": "error"
}
```

## 2. create_skillset Tool

**Request:**
```json
{
  "name": "test-skillset",
  "skills": [
    {
      "@odata.type": "#Microsoft.Skills.Text.EntityRecognitionSkill",
      "name": "entity-recognition",
      "description": "Extract entities",
      "context": "/document",
      "categories": ["Person", "Location", "Organization"],
      "defaultLanguageCode": "en",
      "inputs": [
        {
          "name": "text",
          "source": "/document/content"
        }
      ],
      "outputs": [
        {
          "name": "entities",
          "targetName": "entities"
        }
      ]
    }
  ],
  "description": "Test skillset for entity extraction"
}
```

**Response:**
```json
{
  "ok": false,
  "error": "Client error '400 Bad Request' for url 'https://oairesourcesearch.search.windows.net/skillsets/test-skillset?api-version=2025-05-01-preview'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400",
  "code": "error"
}
```

## 3. rebuild_index Tool

**Request:**
```json
{
  "confirm": false
}
```

**Response:**
```json
{
  "ok": false,
  "error": "Must set confirm=True to rebuild index. This operation deletes all data!",
  "code": "error"
}
```

## Summary

- **create_datasource**: Failed with 400 Bad Request - Azure API rejected the datasource definition (likely invalid connection string or missing required fields)
- **create_skillset**: Failed with 400 Bad Request - Azure API rejected the skillset definition (may require valid cognitive services configuration)
- **rebuild_index**: Working correctly - properly enforces confirmation requirement before allowing destructive operation
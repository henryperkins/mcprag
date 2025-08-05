"""
Automated Schema Generation and Negotiation with Azure AI Search

This module provides automated schema generation based on Azure's capabilities
and our implemented features, creating a negotiation mechanism between what
Azure expects and what we've built.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
from pathlib import Path

from .rest import AzureSearchClient, SearchOperations
from .automation import IndexAutomation
from .config import AzureSearchConfig

logger = logging.getLogger(__name__)


class SchemaAutomation:
    """Automates schema generation and negotiation with Azure AI Search."""
    
    # Azure AI Search field type mappings
    FIELD_TYPES = {
        "string": "Edm.String",
        "int": "Edm.Int32",
        "long": "Edm.Int64",
        "double": "Edm.Double",
        "boolean": "Edm.Boolean",
        "datetime": "Edm.DateTimeOffset",
        "collection_string": "Collection(Edm.String)",
        "collection_single": "Collection(Edm.Single)",  # For vectors
        "geography_point": "Edm.GeographyPoint"
    }
    
    # Feature requirements mapping
    FEATURE_REQUIREMENTS = {
        "vector_search": {
            "required_fields": [
                {
                    "name": "content_vector",
                    "type": "collection_single",
                    "searchable": True,
                    "dimensions": None,  # Will be detected
                    "vectorSearchProfile": "vector-profile"
                }
            ],
            "index_config": {
                "vectorSearch": {
                    "algorithms": [],
                    "profiles": [],
                    "vectorizers": []
                }
            }
        },
        "semantic_search": {
            "required_fields": [
                {
                    "name": "content",
                    "type": "string",
                    "searchable": True,
                    "analyzer": "en.microsoft"
                }
            ],
            "index_config": {
                "semanticSearch": {
                    "configurations": []
                }
            }
        },
        "faceted_search": {
            "required_fields": [
                {
                    "name": "repository",
                    "type": "string",
                    "facetable": True,
                    "filterable": True
                },
                {
                    "name": "language",
                    "type": "string",
                    "facetable": True,
                    "filterable": True
                }
            ]
        },
        "scoring_profiles": {
            "index_config": {
                "scoringProfiles": []
            }
        }
    }
    
    def __init__(self, endpoint: str = None, api_key: str = None):
        """Initialize schema automation."""
        config = AzureSearchConfig.from_env()
        self.endpoint = endpoint or config.endpoint
        self.api_key = api_key or config.api_key
        self.client = AzureSearchClient(self.endpoint, self.api_key)
        self.ops = SearchOperations(self.client)
        self.index_automation = IndexAutomation(self.endpoint, self.api_key)
        
    async def detect_azure_capabilities(self) -> Dict[str, Any]:
        """Detect Azure AI Search service capabilities and limits.
        
        Returns:
            Dictionary of detected capabilities
        """
        capabilities = {
            "api_version": self.client.api_version,
            "detected_features": [],
            "limits": {},
            "recommendations": []
        }
        
        import os
        if os.getenv("ACS_DETECT_CAPABILITIES", "true").lower() in ("0", "false", "no"):
            return capabilities
        try:
            # Try to create a test index with various features to detect support
            test_index_name = f"test-capabilities-{int(datetime.utcnow().timestamp())}"
            
            # Test vector search support
            vector_test = await self._test_vector_search_support(test_index_name)
            if vector_test["supported"]:
                capabilities["detected_features"].append("vector_search")
                capabilities["limits"]["max_vector_dimensions"] = vector_test.get("max_dimensions", 3072)
                
            # Test semantic search support
            semantic_test = await self._test_semantic_search_support(test_index_name)
            if semantic_test["supported"]:
                capabilities["detected_features"].append("semantic_search")
                
            # Test custom analyzers
            analyzer_test = await self._test_custom_analyzers(test_index_name)
            if analyzer_test["supported"]:
                capabilities["detected_features"].append("custom_analyzers")
                
            # Clean up test index
            try:
                await self.ops.delete_index(test_index_name)
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error detecting capabilities: {e}")
            
        return capabilities
    
    async def generate_schema_from_features(
        self,
        features: List[str],
        custom_fields: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate schema based on requested features.
        
        Args:
            features: List of features to enable (e.g., ["vector_search", "semantic_search"])
            custom_fields: Additional custom fields to include
            
        Returns:
            Complete index schema
        """
        # Detect Azure capabilities first
        capabilities = await self.detect_azure_capabilities()
        
        # Start with base schema
        schema = {
            "name": "generated-index",
            "fields": [
                {
                    "name": "id",
                    "type": "Edm.String",
                    "key": True,
                    "searchable": False,
                    "filterable": True,
                    "retrievable": True
                }
            ],
            "suggesters": [],
            "scoringProfiles": [],
            "corsOptions": {
                "allowedOrigins": ["*"],
                "maxAgeInSeconds": 300
            }
        }
        
        # Add fields for each requested feature
        for feature in features:
            if feature in self.FEATURE_REQUIREMENTS:
                req = self.FEATURE_REQUIREMENTS[feature]
                
                # Add required fields
                for field_template in req.get("required_fields", []):
                    field = field_template.copy()
                    
                    # Handle vector dimensions
                    if field.get("type") == "collection_single" and field.get("dimensions") is None:
                        field["dimensions"] = capabilities["limits"].get("max_vector_dimensions", 3072)
                    
                    # Convert type names
                    if field.get("type") in self.FIELD_TYPES:
                        field["type"] = self.FIELD_TYPES[field["type"]]
                        
                    schema["fields"].append(field)
                
                # Add index configuration
                if "index_config" in req:
                    for key, value in req["index_config"].items():
                        if key == "vectorSearch" and "vector_search" in capabilities["detected_features"]:
                            schema[key] = self._generate_vector_search_config(
                                capabilities["limits"].get("max_vector_dimensions", 3072)
                            )
                        elif key == "semanticSearch" and "semantic_search" in capabilities["detected_features"]:
                            schema[key] = self._generate_semantic_search_config()
                        else:
                            schema[key] = value
        
        # Add custom fields
        if custom_fields:
            for field in custom_fields:
                # Ensure proper type conversion
                if field.get("type") in self.FIELD_TYPES:
                    field["type"] = self.FIELD_TYPES[field["type"]]
                schema["fields"].append(field)
                
        # Remove duplicate fields
        seen = set()
        unique_fields = []
        for field in schema["fields"]:
            if field["name"] not in seen:
                seen.add(field["name"])
                unique_fields.append(field)
        schema["fields"] = unique_fields
        
        return schema
    
    async def negotiate_schema_with_azure(
        self,
        desired_schema: Dict[str, Any],
        index_name: str
    ) -> Dict[str, Any]:
        """Negotiate schema with Azure to find compatible configuration.
        
        Args:
            desired_schema: The schema we want to create
            index_name: Name for the index
            
        Returns:
            Negotiated schema that Azure accepts
        """
        negotiation_result = {
            "original": desired_schema,
            "negotiated": None,
            "changes": [],
            "warnings": [],
            "success": False
        }
        
        # Start with desired schema
        test_schema = desired_schema.copy()
        test_schema["name"] = index_name
        
        # Try to create/validate the schema
        try:
            # First, try to create as-is
            validation = await self.index_automation.validate_index_schema(
                index_name,
                test_schema
            )
            
            if validation["valid"]:
                negotiation_result["negotiated"] = test_schema
                negotiation_result["success"] = True
                return negotiation_result
                
        except Exception as e:
            logger.info(f"Initial schema validation failed: {e}")
            
        # If initial attempt failed, try adjustments
        adjusted_schema = await self._adjust_schema_for_compatibility(test_schema)
        
        try:
            # Create adjusted schema
            result = await self.index_automation.ensure_index_exists(adjusted_schema)
            
            if result["created"] or result["current"]:
                negotiation_result["negotiated"] = adjusted_schema
                negotiation_result["success"] = True
                
                # Document changes
                negotiation_result["changes"] = self._document_schema_changes(
                    desired_schema,
                    adjusted_schema
                )
                
        except Exception as e:
            negotiation_result["warnings"].append(f"Failed to create index: {str(e)}")
            
        return negotiation_result
    
    async def update_existing_index_schema(
        self,
        index_name: str,
        new_features: List[str]
    ) -> Dict[str, Any]:
        """Update existing index to support new features.
        
        Args:
            index_name: Existing index name
            new_features: List of new features to add
            
        Returns:
            Update result
        """
        result = {
            "success": False,
            "changes": [],
            "warnings": [],
            "requires_reindex": False
        }
        
        try:
            # Get current schema
            current_schema = await self.ops.get_index(index_name)
            
            # Generate schema with new features
            updated_schema = await self.generate_schema_from_features(
                new_features,
                custom_fields=current_schema["fields"]
            )
            
            # Check what can be updated without reindexing
            safe_updates = self._identify_safe_updates(current_schema, updated_schema)
            
            if safe_updates["can_update"]:
                # Apply safe updates
                for change in safe_updates["changes"]:
                    result["changes"].append(change)
                    
                # Update index
                await self.ops.create_index(updated_schema)
                result["success"] = True
            else:
                result["requires_reindex"] = True
                result["warnings"].append(
                    "Schema changes require reindexing. "
                    "Consider creating a new index and migrating data."
                )
                
        except Exception as e:
            result["warnings"].append(f"Failed to update schema: {str(e)}")
            
        return result
    
    def _generate_vector_search_config(self, dimensions: int) -> Dict[str, Any]:
        """Generate vector search configuration."""
        return {
            "algorithms": [
                {
                    "name": f"hnsw-{dimensions}",
                    "kind": "hnsw",
                    "hnswParameters": {
                        "metric": "cosine",
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500
                    }
                }
            ],
            "profiles": [
                {
                    "name": f"test-profile-{dimensions}",
                    "algorithm": f"hnsw-{dimensions}"
                }
            ]
        }
    
    def _generate_semantic_search_config(self) -> Dict[str, Any]:
        """Generate semantic search configuration."""
        return {
            "configurations": [
                {
                    "name": "semantic-config",
                    "prioritizedFields": {
                        "titleField": {
                            "fieldName": "title"
                        },
                        "prioritizedContentFields": [
                            {
                                "fieldName": "content"
                            },
                            {
                                "fieldName": "description"
                            }
                        ]
                    }
                }
            ]
        }
    
    async def _test_vector_search_support(self, test_index_name: str) -> Dict[str, Any]:
        """Test if vector search is supported."""
        result = {"supported": False}
        
        # Try different vector dimensions
        for dimensions in [3072, 1536, 1024, 512]:
            test_schema = {
                "name": test_index_name,
                "fields": [
                    {
                        "name": "id",
                        "type": "Edm.String",
                        "key": True
                    },
                    {
                        "name": "vector",
                        "type": "Collection(Edm.Single)",
                        "searchable": True,
                        "dimensions": dimensions,
                        "vectorSearchProfile": f"test-profile-{dimensions}"
                    }
                ],
                "vectorSearch": self._generate_vector_search_config(dimensions)
            }
            
            try:
                await self.ops.create_index(test_schema)
                result["supported"] = True
                result["max_dimensions"] = dimensions
                await self.ops.delete_index(test_index_name)
                break
            except:
                continue
                
        return result
    
    async def _test_semantic_search_support(self, test_index_name: str) -> Dict[str, Any]:
        """Test if semantic search is supported."""
        test_schema = {
            "name": test_index_name,
            "fields": [
                {
                    "name": "id",
                    "type": "Edm.String",
                    "key": True
                },
                {
                    "name": "content",
                    "type": "Edm.String",
                    "searchable": True
                }
            ],
            "semanticSearch": self._generate_semantic_search_config()
        }
        
        try:
            await self.ops.create_index(test_schema)
            await self.ops.delete_index(test_index_name)
            return {"supported": True}
        except:
            return {"supported": False}
    
    async def _test_custom_analyzers(self, test_index_name: str) -> Dict[str, Any]:
        """Test if custom analyzers are supported."""
        test_schema = {
            "name": test_index_name,
            "fields": [
                {
                    "name": "id",
                    "type": "Edm.String",
                    "key": True
                },
                {
                    "name": "content",
                    "type": "Edm.String",
                    "searchable": True,
                    "analyzer": "test-analyzer"
                }
            ],
            "analyzers": [
                {
                    "name": "test-analyzer",
                    "@odata.type": "#Microsoft.Azure.Search.CustomAnalyzer",
                    "tokenizer": "standard",
                    "tokenFilters": ["lowercase", "asciifolding"]
                }
            ]
        }
        
        try:
            await self.ops.create_index(test_schema)
            await self.ops.delete_index(test_index_name)
            return {"supported": True}
        except:
            return {"supported": False}
    
    async def _adjust_schema_for_compatibility(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Adjust schema for Azure compatibility."""
        adjusted = schema.copy()
        
        # Common adjustments
        adjustments = []
        
        # 1. Ensure all searchable fields are strings
        for field in adjusted["fields"]:
            if field.get("searchable") and field["type"] not in ["Edm.String", "Collection(Edm.String)"]:
                field["searchable"] = False
                adjustments.append(f"Removed searchable from non-string field '{field['name']}'")
                
        # 2. Fix vector field configuration
        for field in adjusted["fields"]:
            if field["type"] == "Collection(Edm.Single)" and field.get("dimensions"):
                # Ensure vector fields are not marked as other attributes
                field["filterable"] = False
                field["sortable"] = False
                field["facetable"] = False
                field["retrievable"] = False
                
                # Ensure searchable is True for vector fields
                field["searchable"] = True
                
        # 3. Validate analyzer names
        if "analyzers" in adjusted:
            valid_analyzers = {a["name"] for a in adjusted["analyzers"]}
            for field in adjusted["fields"]:
                if field.get("analyzer") and field["analyzer"] not in valid_analyzers:
                    # Use default analyzer
                    field["analyzer"] = "standard.lucene"
                    adjustments.append(f"Changed analyzer for field '{field['name']}' to standard")
                    
        logger.info(f"Schema adjustments: {adjustments}")
        return adjusted
    
    def _document_schema_changes(self, original: Dict[str, Any], negotiated: Dict[str, Any]) -> List[str]:
        """Document changes between original and negotiated schema."""
        changes = []
        
        # Compare fields
        orig_fields = {f["name"]: f for f in original.get("fields", [])}
        neg_fields = {f["name"]: f for f in negotiated.get("fields", [])}
        
        # Check removed fields
        for name in set(orig_fields.keys()) - set(neg_fields.keys()):
            changes.append(f"Removed field '{name}'")
            
        # Check added fields  
        for name in set(neg_fields.keys()) - set(orig_fields.keys()):
            changes.append(f"Added field '{name}'")
            
        # Check modified fields
        for name in set(orig_fields.keys()) & set(neg_fields.keys()):
            orig = orig_fields[name]
            neg = neg_fields[name]
            
            for attr in ["type", "searchable", "filterable", "facetable", "sortable"]:
                if orig.get(attr) != neg.get(attr):
                    changes.append(f"Changed {attr} for field '{name}' from {orig.get(attr)} to {neg.get(attr)}")
                    
        return changes
    
    def _identify_safe_updates(self, current: Dict[str, Any], desired: Dict[str, Any]) -> Dict[str, Any]:
        """Identify updates that can be made without reindexing."""
        result = {
            "can_update": True,
            "changes": [],
            "unsafe_changes": []
        }
        
        current_fields = {f["name"]: f for f in current.get("fields", [])}
        desired_fields = {f["name"]: f for f in desired.get("fields", [])}
        
        # Check for unsafe changes
        for name, field in current_fields.items():
            if name in desired_fields:
                desired_field = desired_fields[name]
                
                # Type changes require reindex
                if field["type"] != desired_field["type"]:
                    result["unsafe_changes"].append(f"Type change for field '{name}'")
                    result["can_update"] = False
                    
                # Key field changes require reindex
                if field.get("key") != desired_field.get("key"):
                    result["unsafe_changes"].append(f"Key attribute change for field '{name}'")
                    result["can_update"] = False
                    
        # Adding new fields is generally safe
        for name in set(desired_fields.keys()) - set(current_fields.keys()):
            result["changes"].append(f"Add new field '{name}'")
            
        return result


# Example usage and integration
async def automated_schema_example():
    """Example of automated schema generation."""
    automation = SchemaAutomation()
    
    # 1. Detect Azure capabilities
    capabilities = await automation.detect_azure_capabilities()
    print("Detected capabilities:", capabilities)
    
    # 2. Generate schema based on features
    schema = await automation.generate_schema_from_features(
        features=["vector_search", "semantic_search", "faceted_search"],
        custom_fields=[
            {
                "name": "custom_field",
                "type": "string",
                "searchable": True
            }
        ]
    )
    
    # 3. Negotiate with Azure
    result = await automation.negotiate_schema_with_azure(
        schema,
        "my-automated-index"
    )
    
    if result["success"]:
        print("Schema negotiation successful!")
        print("Changes made:", result["changes"])
    else:
        print("Schema negotiation failed:", result["warnings"])
    
    # 4. Save negotiated schema
    with open("negotiated_schema.json", "w") as f:
        json.dump(result["negotiated"], f, indent=2)


if __name__ == "__main__":
    import asyncio
    asyncio.run(automated_schema_example())
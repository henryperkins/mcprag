"""
CLI integration for automated schema generation and negotiation.

This extends the CLI with commands for:
- Detecting Azure capabilities
- Generating schemas from features
- Negotiating schemas with Azure
- Updating existing schemas
"""

import argparse
import json
import logging
from typing import List, Dict, Any
import asyncio
from pathlib import Path

from .schema_automation import SchemaAutomation

logger = logging.getLogger(__name__)


async def cmd_detect_capabilities(args):
    """Detect Azure AI Search capabilities."""
    logger.info("Detecting Azure AI Search capabilities...")
    
    automation = SchemaAutomation()
    capabilities = await automation.detect_azure_capabilities()
    
    print("\n🔍 Azure AI Search Capabilities")
    print("=" * 40)
    print(f"API Version: {capabilities['api_version']}")
    print(f"\nDetected Features:")
    for feature in capabilities['detected_features']:
        print(f"  ✅ {feature}")
    
    if capabilities.get('limits'):
        print(f"\nService Limits:")
        for limit, value in capabilities['limits'].items():
            print(f"  • {limit}: {value}")
    
    if capabilities.get('recommendations'):
        print(f"\nRecommendations:")
        for rec in capabilities['recommendations']:
            print(f"  💡 {rec}")
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(capabilities, f, indent=2)
        print(f"\n💾 Capabilities saved to: {args.output}")
    
    return 0


async def cmd_generate_schema(args):
    """Generate schema from features."""
    logger.info(f"Generating schema for features: {args.features}")
    
    automation = SchemaAutomation()
    
    # Load custom fields if provided
    custom_fields = []
    if args.custom_fields:
        with open(args.custom_fields, 'r') as f:
            custom_fields = json.load(f)
    
    # Generate schema
    schema = await automation.generate_schema_from_features(
        features=args.features,
        custom_fields=custom_fields
    )
    
    # Update schema name
    schema["name"] = args.name
    
    print(f"\n📋 Generated Schema: {args.name}")
    print("=" * 40)
    print(f"Fields: {len(schema['fields'])}")
    
    # List key features
    if "vectorSearch" in schema:
        print("✅ Vector Search enabled")
        if schema["vectorSearch"]["profiles"]:
            profile = schema["vectorSearch"]["profiles"][0]
            print(f"   Profile: {profile['name']}")
            
    if "semanticSearch" in schema:
        print("✅ Semantic Search enabled")
        
    if "scoringProfiles" in schema and schema["scoringProfiles"]:
        print(f"✅ Scoring Profiles: {len(schema['scoringProfiles'])}")
    
    # Save schema
    output_file = args.output or f"{args.name}_schema.json"
    with open(output_file, 'w') as f:
        json.dump(schema, f, indent=2)
    
    print(f"\n💾 Schema saved to: {output_file}")
    
    # Show field summary
    print("\nField Summary:")
    for field in schema["fields"][:10]:  # Show first 10 fields
        attrs = []
        if field.get("key"):
            attrs.append("key")
        if field.get("searchable"):
            attrs.append("searchable")
        if field.get("filterable"):
            attrs.append("filterable")
        if field.get("facetable"):
            attrs.append("facetable")
        
        attrs_str = f" ({', '.join(attrs)})" if attrs else ""
        print(f"  • {field['name']}: {field['type']}{attrs_str}")
    
    if len(schema["fields"]) > 10:
        print(f"  ... and {len(schema['fields']) - 10} more fields")
    
    return 0


async def cmd_negotiate_schema(args):
    """Negotiate schema with Azure."""
    logger.info(f"Negotiating schema for index: {args.index_name}")
    
    automation = SchemaAutomation()
    
    # Load desired schema
    with open(args.schema_file, 'r') as f:
        desired_schema = json.load(f)
    
    # Negotiate with Azure
    result = await automation.negotiate_schema_with_azure(
        desired_schema,
        args.index_name
    )
    
    print(f"\n🤝 Schema Negotiation: {args.index_name}")
    print("=" * 40)
    
    if result["success"]:
        print("✅ Negotiation successful!")
        
        if result["changes"]:
            print("\nChanges made:")
            for change in result["changes"]:
                print(f"  • {change}")
        else:
            print("✅ No changes needed - schema accepted as-is")
            
        # Save negotiated schema
        output_file = args.output or f"{args.index_name}_negotiated.json"
        with open(output_file, 'w') as f:
            json.dump(result["negotiated"], f, indent=2)
        print(f"\n💾 Negotiated schema saved to: {output_file}")
        
        # Optionally create the index
        if args.create_index:
            print(f"\n🏗️  Creating index with negotiated schema...")
            automation = SchemaAutomation()
            await automation.index_automation.ensure_index_exists(result["negotiated"])
            print("✅ Index created successfully!")
            
    else:
        print("❌ Negotiation failed!")
        
        if result["warnings"]:
            print("\nWarnings:")
            for warning in result["warnings"]:
                print(f"  ⚠️  {warning}")
    
    return 0 if result["success"] else 1


async def cmd_update_schema(args):
    """Update existing index schema."""
    logger.info(f"Updating schema for index: {args.index_name}")
    
    automation = SchemaAutomation()
    
    # Update with new features
    result = await automation.update_existing_index_schema(
        args.index_name,
        args.features
    )
    
    print(f"\n🔄 Schema Update: {args.index_name}")
    print("=" * 40)
    
    if result["success"]:
        print("✅ Update successful!")
        
        if result["changes"]:
            print("\nChanges applied:")
            for change in result["changes"]:
                print(f"  • {change}")
    else:
        if result["requires_reindex"]:
            print("❌ Update requires reindexing!")
            print("\nRecommendation:")
            print("  1. Create a new index with updated schema")
            print("  2. Reindex data from current index")
            print("  3. Switch alias to new index")
            print("  4. Delete old index")
            
            # Generate migration schema
            if args.generate_migration:
                print("\n📋 Generating migration schema...")
                schema = await automation.generate_schema_from_features(
                    args.features
                )
                migration_file = f"{args.index_name}_migration.json"
                with open(migration_file, 'w') as f:
                    json.dump(schema, f, indent=2)
                print(f"💾 Migration schema saved to: {migration_file}")
    
    if result["warnings"]:
        print("\nWarnings:")
        for warning in result["warnings"]:
            print(f"  ⚠️  {warning}")
    
    return 0 if result["success"] else 1


async def cmd_compare_schemas(args):
    """Compare two schemas and show differences."""
    logger.info("Comparing schemas...")
    
    # Load schemas
    with open(args.schema1, 'r') as f:
        schema1 = json.load(f)
    
    with open(args.schema2, 'r') as f:
        schema2 = json.load(f)
    
    print(f"\n🔍 Schema Comparison")
    print("=" * 40)
    print(f"Schema 1: {args.schema1} ({schema1.get('name', 'unnamed')})")
    print(f"Schema 2: {args.schema2} ({schema2.get('name', 'unnamed')})")
    
    # Compare fields
    fields1 = {f["name"]: f for f in schema1.get("fields", [])}
    fields2 = {f["name"]: f for f in schema2.get("fields", [])}
    
    # Fields only in schema1
    only_in_1 = set(fields1.keys()) - set(fields2.keys())
    if only_in_1:
        print(f"\nFields only in Schema 1:")
        for name in sorted(only_in_1):
            print(f"  - {name} ({fields1[name]['type']})")
    
    # Fields only in schema2
    only_in_2 = set(fields2.keys()) - set(fields1.keys())
    if only_in_2:
        print(f"\nFields only in Schema 2:")
        for name in sorted(only_in_2):
            print(f"  + {name} ({fields2[name]['type']})")
    
    # Common fields with differences
    common = set(fields1.keys()) & set(fields2.keys())
    differences = []
    
    for name in common:
        f1 = fields1[name]
        f2 = fields2[name]
        
        diffs = []
        for attr in ["type", "searchable", "filterable", "facetable", "sortable", "key"]:
            if f1.get(attr) != f2.get(attr):
                diffs.append(f"{attr}: {f1.get(attr)} → {f2.get(attr)}")
        
        if diffs:
            differences.append((name, diffs))
    
    if differences:
        print(f"\nField differences:")
        for name, diffs in differences:
            print(f"  ~ {name}:")
            for diff in diffs:
                print(f"    • {diff}")
    
    # Compare features
    features1 = []
    features2 = []
    
    if "vectorSearch" in schema1:
        features1.append("Vector Search")
    if "vectorSearch" in schema2:
        features2.append("Vector Search")
        
    if "semanticSearch" in schema1:
        features1.append("Semantic Search")
    if "semanticSearch" in schema2:
        features2.append("Semantic Search")
        
    if schema1.get("scoringProfiles"):
        features1.append(f"Scoring Profiles ({len(schema1['scoringProfiles'])})")
    if schema2.get("scoringProfiles"):
        features2.append(f"Scoring Profiles ({len(schema2['scoringProfiles'])})")
    
    print(f"\nFeatures:")
    print(f"  Schema 1: {', '.join(features1) or 'None'}")
    print(f"  Schema 2: {', '.join(features2) or 'None'}")
    
    return 0


def add_schema_commands(subparsers):
    """Add schema automation commands to CLI."""
    
    # detect-capabilities command
    detect_parser = subparsers.add_parser(
        'detect-capabilities',
        help='Detect Azure AI Search service capabilities'
    )
    detect_parser.add_argument(
        '--output',
        type=str,
        help='Save capabilities to JSON file'
    )
    
    # generate-schema command
    generate_parser = subparsers.add_parser(
        'generate-schema',
        help='Generate schema from features'
    )
    generate_parser.add_argument(
        '--name',
        type=str,
        required=True,
        help='Index name'
    )
    generate_parser.add_argument(
        '--features',
        nargs='+',
        choices=['vector_search', 'semantic_search', 'faceted_search', 'scoring_profiles'],
        required=True,
        help='Features to enable'
    )
    generate_parser.add_argument(
        '--custom-fields',
        type=str,
        help='JSON file with custom field definitions'
    )
    generate_parser.add_argument(
        '--output',
        type=str,
        help='Output file for schema (default: {name}_schema.json)'
    )
    
    # negotiate-schema command
    negotiate_parser = subparsers.add_parser(
        'negotiate-schema',
        help='Negotiate schema with Azure'
    )
    negotiate_parser.add_argument(
        '--index-name',
        type=str,
        required=True,
        help='Target index name'
    )
    negotiate_parser.add_argument(
        '--schema-file',
        type=str,
        required=True,
        help='Schema JSON file to negotiate'
    )
    negotiate_parser.add_argument(
        '--output',
        type=str,
        help='Output file for negotiated schema'
    )
    negotiate_parser.add_argument(
        '--create-index',
        action='store_true',
        help='Create index with negotiated schema'
    )
    
    # update-schema command
    update_parser = subparsers.add_parser(
        'update-schema',
        help='Update existing index schema'
    )
    update_parser.add_argument(
        '--index-name',
        type=str,
        required=True,
        help='Index to update'
    )
    update_parser.add_argument(
        '--features',
        nargs='+',
        choices=['vector_search', 'semantic_search', 'faceted_search', 'scoring_profiles'],
        required=True,
        help='New features to add'
    )
    update_parser.add_argument(
        '--generate-migration',
        action='store_true',
        help='Generate migration schema if reindex required'
    )
    
    # compare-schemas command
    compare_parser = subparsers.add_parser(
        'compare-schemas',
        help='Compare two index schemas'
    )
    compare_parser.add_argument(
        'schema1',
        type=str,
        help='First schema JSON file'
    )
    compare_parser.add_argument(
        'schema2',
        type=str,
        help='Second schema JSON file'
    )
    
    # Return command mapping
    return {
        'detect-capabilities': cmd_detect_capabilities,
        'generate-schema': cmd_generate_schema,
        'negotiate-schema': cmd_negotiate_schema,
        'update-schema': cmd_update_schema,
        'compare-schemas': cmd_compare_schemas
    }


# Example integration with main CLI
if __name__ == "__main__":
    async def test_commands():
        """Test schema automation commands."""
        
        # Test capability detection
        class Args:
            output = "capabilities.json"
            
        await cmd_detect_capabilities(Args())
        
        # Test schema generation
        class Args:
            name = "test-index"
            features = ["vector_search", "semantic_search"]
            custom_fields = None
            output = None
            
        await cmd_generate_schema(Args())
    
    asyncio.run(test_commands())
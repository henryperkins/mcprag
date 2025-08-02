#!/usr/bin/env python3
"""
Create a new Azure AI Search index with 3072-dimensional vector fields.

- Uses EnhancedIndexBuilder to build the index
- Creates/uses a compliant synonym map name ("code-synonyms")
- Avoids previous error by referencing the correct synonym map name
- Uses a new index name: f"{ACS_INDEX_NAME or 'codebase-mcp-sota'}-3072"

Requirements:
  - Environment variables:
      ACS_ENDPOINT
      ACS_ADMIN_KEY
      (optional) ACS_INDEX_NAME
      (optional) AZURE_OPENAI_ENDPOINT
      (optional) AZURE_OPENAI_DEPLOYMENT_NAME
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SynonymMap

from enhanced_rag.azure_integration.enhanced_index_builder import EnhancedIndexBuilder


def ensure_env():
    endpoint = os.getenv("ACS_ENDPOINT")
    key = os.getenv("ACS_ADMIN_KEY")
    if not endpoint or not key:
        print("ERROR: ACS_ENDPOINT and ACS_ADMIN_KEY must be set in environment", file=sys.stderr)
        sys.exit(2)
    return endpoint, key


def upsert_synonym_map(endpoint: str, key: str, name: str = "code-synonyms") -> str:
    """
    Ensure a valid synonym map exists with a compliant name.
    Returns the synonym map name to be used by fields.
    """
    sic = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(key))
    # Keep the synonyms identical to those in builder but with a valid name
    synonyms = "\n".join(
        [
            "func, function, method, procedure",
            "err, error, exception",
            "init, initialize, constructor, ctor",
            "auth, authenticate, authorization, authorize",
            "db, database, storage",
        ]
    )
    sm = SynonymMap(name=name, synonyms=synonyms)
    try:
        sic.create_or_update_synonym_map(sm)
        print(f"✅ Upserted SynonymMap: {name}")
    except Exception as e:
        print(f"⚠️  Warning upserting SynonymMap '{name}': {e}", file=sys.stderr)
    return name


async def create_index_3072():
    endpoint, key = ensure_env()

    # Determine base index name and derive new name
    base = os.getenv("ACS_INDEX_NAME", "codebase-mcp-sota")
    new_index = f"{base}-3072"

    print(f"Creating 3072-d index: {new_index}")

    # Ensure synonym map exists under a compliant name
    synonym_map_name = upsert_synonym_map(endpoint, key, name="code-synonyms")

    # Build the index using builder
    builder = EnhancedIndexBuilder()

    # Patch: EnhancedIndexBuilder currently sets field synonym_map_names to "code_synonyms".
    # Azure requires valid resource to exist and names must use only lowercase/digits/dashes.
    # We'll create the index first using builder, then patch the field references to the valid name.
    index = await builder.create_enhanced_rag_index(
        index_name=new_index,
        description="Enhanced 3072-d code search index",
        enable_vectors=True,
        enable_semantic=True,
    )

    # Now fetch created index to patch synonym map references to our valid name
    sic = builder.index_client
    idx = sic.get_index(new_index)
    changed = False
    for f in idx.fields:
        # Any field that references synonyms should use our compliant synonym map
        names = getattr(f, "synonym_map_names", None)
        if names:
            # Replace any non-compliant entry with the correct one
            new_names = []
            for n in names:
                # Accept already correct names, replace others with our valid synonym map
                if n == synonym_map_name:
                    new_names.append(n)
                else:
                    # normalize: any other entry becomes correct synonym map
                    new_names.append(synonym_map_name)
            if new_names != names:
                f.synonym_map_names = new_names
                changed = True

    if changed:
        idx = sic.create_or_update_index(idx)
        print(f"🔧 Patched synonym map references to '{synonym_map_name}'")

    # Validate vector dimensions
    res = await builder.validate_vector_dimensions(new_index, 3072)
    print("Validation:", res)

    if not res.get("ok"):
        print("❌ Vector dimension validation failed", file=sys.stderr)
        sys.exit(3)

    print(f"✅ Created index '{new_index}' with 3072-dimensional vectors")


def main():
    try:
        asyncio.run(create_index_3072())
    except KeyboardInterrupt:
        print("Aborted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
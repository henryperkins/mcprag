#!/usr/bin/env python3
"""Test vector embeddings functionality."""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vector_embeddings import VectorEmbedder


def test_vector_embeddings():
    """Test that vector embeddings are working correctly."""

    print("Testing Vector Embeddings Configuration...")
    print("-" * 50)

    # Check environment variables
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT") or os.getenv(
        "AZURE_OPENAI_EMBEDDING_MODEL"
    )

    print(f"Azure OpenAI Endpoint: {endpoint}")
    print(f"API Key: {'Configured' if api_key else 'Not configured'}")
    print(f"Deployment/Model: {deployment}")
    print("-" * 50)

    try:
        # Initialize embedder
        embedder = VectorEmbedder()
        print("✅ VectorEmbedder initialized successfully")

        # Test single embedding
        test_text = "def calculate_sum(a: int, b: int) -> int: return a + b"
        print(f"\nTesting embedding generation for: '{test_text}'")

        embedding = embedder.generate_embedding(test_text)

        if embedding:
            print(f"✅ Embedding generated successfully!")
            print(f"   Embedding dimensions: {len(embedding)}")
            print(f"   First 5 values: {embedding[:5]}")
        else:
            print("❌ Failed to generate embedding")
            return False

        # Test code embedding with context
        code = "def process_data(items): return [x * 2 for x in items]"
        context = "function process_data in utils.py\nDoubles each item in the list"

        print(f"\nTesting code embedding with context...")
        code_embedding = embedder.generate_code_embedding(code, context)

        if code_embedding:
            print(f"✅ Code embedding generated successfully!")
            print(f"   Embedding dimensions: {len(code_embedding)}")
        else:
            print("❌ Failed to generate code embedding")
            return False

        # Test batch embeddings
        texts = [
            "class DataProcessor",
            "async function fetchData()",
            "import numpy as np",
        ]

        print(f"\nTesting batch embeddings for {len(texts)} texts...")
        batch_embeddings = embedder.generate_embeddings_batch(texts)

        successful = sum(1 for e in batch_embeddings if e is not None)
        print(f"✅ Generated {successful}/{len(texts)} embeddings successfully")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = test_vector_embeddings()

    if success:
        print("\n✨ Vector embeddings are enabled and working correctly!")
        print("\nNext steps:")
        print(
            "1. Run 'python3 smart_indexer.py --repo-path /path/to/repo --repo-name name'"
        )
        print(
            "2. The indexer will automatically generate embeddings for each code chunk"
        )
        print("3. Azure Cognitive Search will use these for semantic search")
    else:
        print("\n❌ Vector embeddings test failed. Please check your configuration.")

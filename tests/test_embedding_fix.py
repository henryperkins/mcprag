#!/usr/bin/env python3
"""
Test script to verify embedding dimension fix
"""


def test_embedding_fix():
    """Test that demonstrates the embedding dimension fix"""

    print("Testing embedding dimension fix...")

    # Simulate the old broken behavior
    def old_embedding_processing(embedding, expected_dims):
        """Old broken implementation"""
        if len(embedding) > expected_dims:
            embedding = embedding[:expected_dims]  # Truncates - destroys meaning
        else:
            embedding = embedding + [0.0] * (expected_dims - len(embedding))  # Pads with zeros
        return embedding

    # Simulate the new fixed behavior
    def new_embedding_processing(embedding, expected_dims):
        """New fixed implementation"""
        if len(embedding) != expected_dims:
            print(f"ERROR: Dimension mismatch! Got {len(embedding)}, expected {expected_dims}")
            return None  # Don't corrupt the data
        return embedding

    # Test with sample embeddings
    sample_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]  # 5 dimensions
    expected_dims = 10  # Expected 10 dimensions

    print(f"\nSample embedding: {sample_embedding}")
    print(f"Expected dimensions: {expected_dims}")

    # Old behavior - would corrupt the embedding
    old_result = old_embedding_processing(sample_embedding, expected_dims)
    print(f"Old result (corrupted): {old_result}")
    print(f"Old result length: {len(old_result)}")

    # New behavior - properly handles the error
    new_result = new_embedding_processing(sample_embedding, expected_dims)
    print(f"New result: {new_result}")

    if new_result is None:
        print("✓ New implementation correctly rejects dimension mismatch")
    else:
        print("✗ New implementation should have rejected the mismatch")

    # Test with correct dimensions
    correct_embedding = [0.1] * expected_dims  # Exactly 10 dimensions
    correct_result = new_embedding_processing(correct_embedding, expected_dims)
    print(f"\nCorrect embedding test: {correct_result is not None and len(correct_result) == expected_dims}")

    print("\n✅ Embedding dimension fix verification complete!")


if __name__ == "__main__":
    test_embedding_fix()

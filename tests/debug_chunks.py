#!/usr/bin/env python3
"""
Debug what chunks are being produced
"""

from smart_indexer import CodeChunker

# Test with a simple Python file
test_code = '''
def hello_world():
    """Say hello"""
    print("Hello, World!")
    
class TestClass:
    def __init__(self):
        self.value = 42
'''

chunker = CodeChunker()
chunks = chunker.chunk_python_file(test_code, "test.py")

print("Chunks produced:")
print("-" * 50)
for i, chunk in enumerate(chunks):
    print(f"\nChunk {i}:")
    for key, value in chunk.items():
        print(f"  {key}: {type(value).__name__} = {repr(value)[:100]}")
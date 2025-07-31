#!/usr/bin/env python3
"""
Test field creation with different approaches
"""

from azure.search.documents.indexes.models import (
    SearchField,
    SearchableField,
    SimpleField,
    SearchFieldDataType
)

# Test different ways to create collection fields
print("Testing field creation:")

# Using SearchableField
f1 = SearchableField(
    name="test_searchable",
    type=SearchFieldDataType.Collection(SearchFieldDataType.String),
    searchable=True
)
print(f"SearchableField type: {f1.type}")

# Using SimpleField  
f2 = SimpleField(
    name="test_simple",
    type=SearchFieldDataType.Collection(SearchFieldDataType.String)
)
print(f"SimpleField type: {f2.type}")

# Using SearchField
f3 = SearchField(
    name="test_search",
    type=SearchFieldDataType.Collection(SearchFieldDataType.String),
    searchable=True
)
print(f"SearchField type: {f3.type}")
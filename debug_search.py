#!/usr/bin/env python
"""Debug script to investigate search issues."""

import asyncio
import logging
from enhanced_rag.retrieval.multi_stage_pipeline import MultiStageRetriever
from enhanced_rag.core.models import SearchQuery, SearchIntent

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

async def main():
    print("Initializing MultiStageRetriever...")
    retriever = MultiStageRetriever()
    
    # Create a simple search query
    query = SearchQuery(
        query="function",
        intent=SearchIntent.UNDERSTAND,
        language="python"
    )
    
    print("\n1. Testing vector search directly...")
    try:
        vector_results = await retriever._execute_vector_search(query)
        print(f"Vector search returned {len(vector_results)} results")
        if vector_results:
            print(f"First result: {vector_results[0]}")
    except Exception as e:
        print(f"Vector search failed: {e}")
    
    print("\n2. Testing keyword search directly...")
    try:
        keyword_results = await retriever._execute_keyword_search(query)
        print(f"Keyword search returned {len(keyword_results)} results")
        if keyword_results:
            print(f"First result: {keyword_results[0]}")
    except Exception as e:
        print(f"Keyword search failed: {e}")
    
    print("\n3. Testing document fetch...")
    if keyword_results and len(keyword_results) > 0:
        doc_id = keyword_results[0][0]
        print(f"Fetching document with ID: {doc_id}")
        try:
            doc = await retriever._fetch_document(doc_id)
            if doc:
                print(f"Document fetched successfully: {doc.file_path}")
            else:
                print("Document fetch returned None")
        except Exception as e:
            print(f"Document fetch failed: {e}")
    
    print("\n4. Testing full retrieve method...")
    try:
        results = await retriever.retrieve(query)
        print(f"Full retrieve returned {len(results)} results")
        if results:
            print(f"First result: {results[0].file_path}")
    except Exception as e:
        print(f"Full retrieve failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
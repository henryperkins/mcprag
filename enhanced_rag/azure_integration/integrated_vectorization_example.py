"""
Example of using integrated vectorization with Azure AI Search
Demonstrates the use of standard skills for Text Split and Azure OpenAI Embedding
"""

import os
import asyncio
from dotenv import load_dotenv

from enhanced_rag.azure_integration import (
    IndexerIntegration,
    DataSourceType,
    EnhancedIndexBuilder
)
from enhanced_rag.core.config import get_config

# Load environment variables
load_dotenv()


async def create_integrated_vectorization_pipeline():
    """
    Example of creating a complete integrated vectorization pipeline
    with Azure AI Search using the standard skills
    """
    
    # Get configuration
    config = get_config()
    
    # 1. Create the index with vectorizer configuration
    print("Step 1: Creating index with integrated vectorization...")
    index_builder = EnhancedIndexBuilder()
    
    # Build index with 3072-dimensional vectors
    index_definition = index_builder.build_index(
        index_name=config.azure.index_name,
        vector_dimensions=config.embedding.dimensions,  # 3072
        enable_integrated_vectorization=True,
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "text-embedding-3-large")
    )
    
    # Create the index
    index = index_builder.create_or_update_index(index_definition)
    print(f"✅ Created index: {index.name}")
    
    # 2. Set up the indexer with integrated vectorization
    print("\nStep 2: Creating indexer with standard skills...")
    indexer_integration = IndexerIntegration()
    
    # Example: Index from Azure Blob Storage
    indexer = await indexer_integration.create_integrated_vectorization_indexer(
        name="code-repo-integrated-indexer",
        data_source_type=DataSourceType.AZURE_BLOB,
        connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
        container_name="code-repositories",
        index_name=config.azure.index_name,
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "text-embedding-3-large"),
        schedule_interval_minutes=60  # Run every hour
    )
    
    print(f"✅ Created indexer: {indexer.name}")
    
    # 3. Run the indexer on-demand (optional)
    print("\nStep 3: Running indexer on-demand...")
    success = await indexer_integration.run_indexer_on_demand(indexer.name)
    if success:
        print("✅ Indexer started successfully")
    
    # 4. Monitor indexer status
    print("\nStep 4: Monitoring indexer status...")
    await asyncio.sleep(5)  # Wait a bit for indexer to start
    
    status = await indexer_integration.monitor_indexer_status(indexer.name)
    print(f"Indexer Status: {status.get('status', 'Unknown')}")
    print(f"Last Result: {status.get('last_result', 'N/A')}")
    
    return index, indexer


async def demonstrate_standard_skills():
    """
    Demonstrate the usage of standard skills independently
    """
    from enhanced_rag.azure_integration.standard_skills import (
        TextSplitSkill,
        AzureOpenAIEmbeddingSkill,
        StandardSkillsetBuilder
    )
    
    print("\n=== Standard Skills Demonstration ===\n")
    
    # 1. Text Split Skill
    print("1. Text Split Skill:")
    text_splitter = TextSplitSkill(
        text_split_mode="pages",
        maximum_page_length=2000,
        page_overlap_length=500
    )
    
    sample_text = """
    def calculate_fibonacci(n):
        '''Calculate the nth Fibonacci number using dynamic programming.'''
        if n <= 0:
            return []
        elif n == 1:
            return [0]
        elif n == 2:
            return [0, 1]
        
        fib = [0, 1]
        for i in range(2, n):
            fib.append(fib[i-1] + fib[i-2])
        
        return fib
    
    def is_prime(num):
        '''Check if a number is prime.'''
        if num < 2:
            return False
        for i in range(2, int(num ** 0.5) + 1):
            if num % i == 0:
                return False
        return True
    """
    
    chunks = text_splitter.process_text(sample_text)
    print(f"  - Split text into {len(chunks)} chunks")
    print(f"  - First chunk length: {len(chunks[0]) if chunks else 0} characters")
    
    # 2. Azure OpenAI Embedding Skill Configuration
    print("\n2. Azure OpenAI Embedding Skill:")
    embedding_skill = AzureOpenAIEmbeddingSkill(
        resource_uri=os.getenv("AZURE_OPENAI_ENDPOINT"),
        deployment_id=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "text-embedding-3-large"),
        model_name="text-embedding-3-large",
        dimensions=3072
    )
    
    skill_def = embedding_skill.to_skill_definition()
    print(f"  - Model: {skill_def['modelName']}")
    print(f"  - Dimensions: {skill_def['dimensions']}")
    print(f"  - Input source: {skill_def['inputs'][0]['source']}")
    
    # 3. Standard Skillset Builder
    print("\n3. Standard Skillset Builder:")
    builder = StandardSkillsetBuilder(
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "text-embedding-3-large"),
        text_split_config={
            "text_split_mode": "pages",
            "maximum_page_length": 2000,
            "page_overlap_length": 500
        },
        embedding_config={
            "model_name": "text-embedding-3-large",
            "dimensions": 3072
        }
    )
    
    skillset_def = builder.build_skillset_definition("example-skillset")
    print(f"  - Skillset name: {skillset_def['name']}")
    print(f"  - Number of skills: {len(skillset_def['skills'])}")
    print(f"  - Skills: {[s['name'] for s in skillset_def['skills']]}")


async def main():
    """Main function to run the examples"""
    
    print("=== Integrated Vectorization Example ===\n")
    
    # Check required environment variables
    required_vars = [
        "ACS_ENDPOINT",
        "ACS_ADMIN_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_STORAGE_CONNECTION_STRING"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"⚠️  Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these in your .env file")
        return
    
    try:
        # Run the integrated vectorization pipeline example
        index, indexer = await create_integrated_vectorization_pipeline()
        
        # Demonstrate standard skills
        await demonstrate_standard_skills()
        
        print("\n✅ Example completed successfully!")
        print(f"\nCreated resources:")
        print(f"  - Index: {index.name}")
        print(f"  - Indexer: {indexer.name}")
        print(f"\nThe indexer will run automatically based on the schedule.")
        print("You can also trigger it manually using the Azure portal or API.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
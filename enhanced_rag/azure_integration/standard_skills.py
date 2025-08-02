"""
Standard Azure AI Search Skills Implementation
Implements Text Split and Azure OpenAI Embedding skills for integrated vectorization
"""

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TextSplitSkill:
    """
    Implementation of Microsoft.Skills.Text.SplitSkill
    Splits text into chunks for vectorization
    """
    
    def __init__(
        self,
        text_split_mode: str = "pages",
        maximum_page_length: int = 2000,
        page_overlap_length: int = 500,
        maximum_pages_to_take: int = 0,
        default_language_code: str = "en"
    ):
        """
        Initialize Text Split skill
        
        Args:
            text_split_mode: How to split text ("pages" or "sentences")
            maximum_page_length: Maximum length of each page in characters
            page_overlap_length: Number of overlapping characters between pages
            maximum_pages_to_take: Maximum number of pages to output (0 for all)
            default_language_code: Default language for text processing
        """
        self.text_split_mode = text_split_mode
        self.maximum_page_length = maximum_page_length
        self.page_overlap_length = page_overlap_length
        self.maximum_pages_to_take = maximum_pages_to_take
        self.default_language_code = default_language_code
    
    def to_skill_definition(self) -> Dict[str, Any]:
        """
        Convert to Azure Search skill definition
        
        Returns:
            Dictionary representing the skill for use in a skillset
        """
        return {
            "@odata.type": "#Microsoft.Skills.Text.SplitSkill",
            "name": "text-split-skill",
            "description": "Split text into chunks for vectorization",
            "textSplitMode": self.text_split_mode,
            "maximumPageLength": self.maximum_page_length,
            "pageOverlapLength": self.page_overlap_length,
            "maximumPagesToTake": self.maximum_pages_to_take,
            "defaultLanguageCode": self.default_language_code,
            "inputs": [
                {
                    "name": "text",
                    "source": "/document/content"
                }
            ],
            "outputs": [
                {
                    "name": "textItems",
                    "targetName": "pages"
                }
            ]
        }
    
    def process_text(self, text: str) -> List[str]:
        """
        Process text and split into chunks (for local testing)
        
        Args:
            text: Input text to split
            
        Returns:
            List of text chunks
        """
        if self.text_split_mode == "pages":
            chunks = []
            start = 0
            
            while start < len(text):
                # Calculate end position
                end = min(start + self.maximum_page_length, len(text))
                
                # Extract chunk
                chunk = text[start:end]
                chunks.append(chunk)
                
                # Move start position with overlap
                start = end - self.page_overlap_length
                
                # Apply maximum pages limit if specified
                if self.maximum_pages_to_take > 0 and len(chunks) >= self.maximum_pages_to_take:
                    break
            
            return chunks
        
        elif self.text_split_mode == "sentences":
            # Simple sentence splitting (production would use NLP)
            import re
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if self.maximum_pages_to_take > 0:
                sentences = sentences[:self.maximum_pages_to_take]
            
            return sentences
        
        else:
            raise ValueError(f"Unknown text split mode: {self.text_split_mode}")


class AzureOpenAIEmbeddingSkill:
    """
    Implementation of Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill
    Generates embeddings using Azure OpenAI
    """
    
    def __init__(
        self,
        resource_uri: str,
        deployment_id: str,
        model_name: str = "text-embedding-3-large",
        dimensions: int = 0
    ):
        """
        Initialize Azure OpenAI Embedding skill
        
        Args:
            resource_uri: Azure OpenAI endpoint URI
            deployment_id: Deployment name in Azure OpenAI
            model_name: Model name (e.g., text-embedding-3-large)
            dimensions: Number of dimensions for embeddings
        """
        if not dimensions:
            from enhanced_rag.core.config import get_config
            dimensions = get_config().embedding.dimensions
        self.resource_uri = resource_uri
        self.deployment_id = deployment_id
        self.model_name = model_name
        self.dimensions = dimensions
    
    def to_skill_definition(self) -> Dict[str, Any]:
        """
        Convert to Azure Search skill definition
        
        Returns:
            Dictionary representing the skill for use in a skillset
        """
        return {
            "@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill",
            "name": "azure-openai-embedding-skill",
            "description": "Generate embeddings using Azure OpenAI",
            "resourceUri": self.resource_uri,
            "deploymentId": self.deployment_id,
            "modelName": self.model_name,
            "dimensions": self.dimensions,
            "inputs": [
                {
                    "name": "text",
                    "source": "/document/pages/*"  # Process each chunk from text split
                }
            ],
            "outputs": [
                {
                    "name": "embedding",
                    "targetName": "content_vector"
                }
            ]
        }


class StandardSkillsetBuilder:
    """
    Builder for creating skillsets with standard Azure AI Search skills
    """
    
    def __init__(
        self,
        azure_openai_endpoint: str,
        azure_openai_deployment: str,
        text_split_config: Optional[Dict[str, Any]] = None,
        embedding_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize skillset builder
        
        Args:
            azure_openai_endpoint: Azure OpenAI endpoint
            azure_openai_deployment: Azure OpenAI deployment name
            text_split_config: Configuration for text splitting
            embedding_config: Configuration for embeddings
        """
        self.azure_openai_endpoint = azure_openai_endpoint
        self.azure_openai_deployment = azure_openai_deployment
        
        # Initialize text split skill
        split_config = text_split_config or {}
        self.text_split_skill = TextSplitSkill(**split_config)
        
        # Initialize embedding skill
        embed_config = embedding_config or {}
        embed_config.setdefault('resource_uri', azure_openai_endpoint)
        embed_config.setdefault('deployment_id', azure_openai_deployment)
        self.embedding_skill = AzureOpenAIEmbeddingSkill(**embed_config)
    
    def build_skillset_definition(self, name: str = "integrated-vectorization-skillset") -> Dict[str, Any]:
        """
        Build complete skillset definition
        
        Args:
            name: Name for the skillset
            
        Returns:
            Complete skillset definition for Azure Search
        """
        return {
            "name": name,
            "description": "Skillset for integrated vectorization with text chunking and embedding",
            "skills": [
                self.text_split_skill.to_skill_definition(),
                self.embedding_skill.to_skill_definition()
            ],
            "cognitiveServices": {
                "@odata.type": "#Microsoft.Azure.Search.CognitiveServicesByKey",
                "description": "Azure OpenAI resource for embeddings",
                "key": None  # Uses managed identity if configured
            }
        }
    
    def build_index_mapping(self) -> List[Dict[str, Any]]:
        """
        Build output field mappings for indexer
        
        Returns:
            List of field mappings for the indexer
        """
        return [
            {
                "sourceFieldName": "/document/pages/*",
                "targetFieldName": "content"
            },
            {
                "sourceFieldName": "/document/pages/*/content_vector",
                "targetFieldName": "content_vector"
            }
        ]


# Example usage
def create_standard_skillset(
    azure_openai_endpoint: str,
    azure_openai_deployment: str
) -> Dict[str, Any]:
    """
    Create a standard skillset for integrated vectorization
    
    Args:
        azure_openai_endpoint: Azure OpenAI endpoint
        azure_openai_deployment: Deployment name
        
    Returns:
        Skillset definition
    """
    builder = StandardSkillsetBuilder(
        azure_openai_endpoint=azure_openai_endpoint,
        azure_openai_deployment=azure_openai_deployment,
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
    
    return builder.build_skillset_definition()

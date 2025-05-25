import os
from typing import List
import openai
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

load_dotenv()

class VectorEmbedder:
    def __init__(self):
        # Setup Azure OpenAI
        openai.api_type = "azure"
        openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
        openai.api_key = os.getenv("AZURE_OPENAI_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
        openai.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")

        # Support both naming conventions for deployment
        self.embedding_model = os.getenv("EMBEDDING_MODEL") or os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a piece of text."""
        try:
            response = openai.Embedding.create(
                input=text,
                engine=self.embedding_model
            )
            return response['data'][0]['embedding']
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None

    def generate_code_embedding(self, code: str, context: str) -> List[float]:
        """Generate embedding for code with semantic context."""
        # Combine code and context for richer embeddings
        combined_text = f"{context}\n\nCode:\n{code}"

        # Truncate if too long (max ~8000 tokens for most models)
        max_length = 6000
        if len(combined_text) > max_length:
            combined_text = combined_text[:max_length] + "..."

        return self.generate_embedding(combined_text)

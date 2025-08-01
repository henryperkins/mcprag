import os
import logging
from typing import List, Sequence, Optional
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Optional dependency: ``openai``
# ---------------------------------------------------------------------------
# Unit-test environments (or fresh checkouts) might not have the official
# OpenAI SDK installed.  To keep the rest of this module importable we fall
# back to a minimal stub that exposes only the attributes we access.
# ---------------------------------------------------------------------------

from types import SimpleNamespace


def _build_openai_stub():  # noqa: D401 – helper returns stub module
    class _DummyEmbeddingResponse:
        """Mimic the object returned by ``openai.Embedding.create``"""

        def __init__(self, emb):
            self.data = [SimpleNamespace(embedding=emb)]

        # Allow dictionary-style access ["data"] used occasionally
        def __getitem__(self, key):
            if key == "data":
                return self.data
            raise KeyError(key)

    def _fake_create(*_, **__):  # noqa: D401 – matches real signature loosely
        return _DummyEmbeddingResponse([0.0, 0.0, 0.0, 0.0])

    # Build a stub module with attributes the library expects
    embeddings_ns = SimpleNamespace(create=_fake_create)

    # Create a fake client class
    class FakeClient:
        def __init__(self, **kwargs):
            self.embeddings = embeddings_ns

    return FakeClient


try:
    from openai import OpenAI, AzureOpenAI  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – sandbox or dev env
    OpenAI = _build_openai_stub()  # type: ignore
    AzureOpenAI = _build_openai_stub()  # type: ignore


# ---------------------------------------------------------------------------
# Helper to normalise environment variables
# ---------------------------------------------------------------------------


def _get_env(name: str) -> Optional[str]:
    value = os.getenv(name)
    return value.strip() if value else None


class VectorEmbedder:
    """Thin wrapper around the OpenAI embedding endpoint that works in both
    Azure-hosted and public-cloud modes while remaining mock-friendly for unit
    tests (see *tests/test_vector_embedder.py*).
    """

    def __init__(self):
        # ------------------------------------------------------------------
        # Resolve credentials / endpoints
        # ------------------------------------------------------------------

        self.endpoint: str = _get_env("AZURE_OPENAI_ENDPOINT") or ""
        # Accept both legacy and new env-var names for the API key
        self.api_key: str = (
            _get_env("AZURE_OPENAI_API_KEY")
            or _get_env("AZURE_OPENAI_KEY")
            or _get_env("OPENAI_API_KEY")
            or ""
        )

        if not self.api_key:
            raise ValueError(
                "API key for OpenAI or Azure OpenAI must be provided via environment variables"
            )

        self.api_version = _get_env("AZURE_OPENAI_API_VERSION") or "2024-10-21"

        # Detect whether we should use Azure-specific parameters
        self.use_azure: bool = bool(self.endpoint)

        # Normalised model name / deployment id
        self.model_name: str = (
            _get_env("AZURE_OPENAI_EMBEDDING_MODEL")
            or _get_env("EMBEDDING_MODEL")
            or _get_env("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
            or "text-embedding-ada-002"
        )

        # ------------------------------------------------------------------
        # Instantiate client (real or patched by unit-tests)
        # ------------------------------------------------------------------

        # *tests/test_vector_embedder.py* patches ``vector_embeddings.OpenAI``
        # to intercept this call, therefore we must construct the client via
        # that symbol instead of the canonical import path.
        if self.use_azure:
            # Use AzureOpenAI client for Azure endpoints
            self._client = AzureOpenAI(
                api_key=self.api_key,
                azure_endpoint=self.endpoint,
                api_version=self.api_version,
            )  # type: ignore[arg-type]
        else:
            # Use standard OpenAI client
            self._client = OpenAI(api_key=self.api_key)  # type: ignore[arg-type]

    # ----------------------------------------------------------------------
    # Public helpers
    # ----------------------------------------------------------------------

    def generate_embedding(self, text: str) -> List[float]:
        """Return a single embedding vector for *text*.

        On error, ``None`` is returned so callers can decide how to handle
        partial failures (see *generate_embeddings_batch* tests).
        """

        try:
            response = self._client.embeddings.create(
                input=text,
                model=self.model_name,
            )
            return response.data[0].embedding  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover – exercised via mocks
            logging.getLogger(__name__).warning("Embedding API error: %s", exc)
            return None  # type: ignore[return-value]

    def generate_embeddings_batch(self, texts: Sequence[str]) -> List[List[float]]:
        """Generate embeddings for *texts* in a single batch request for
        efficiency. Any failures are logged and translated into ``None``
        placeholders so the caller can keep the original ordering intact.
        """
        if not texts:
            return []

        try:
            response = self._client.embeddings.create(
                input=list(texts),  # Pass the whole list
                model=self.model_name,
            )
            # Sort embeddings by original index to handle out-of-order responses
            embeddings = sorted(response.data, key=lambda e: e.index)
            return [e.embedding for e in embeddings]
        except Exception as exc:  # pragma: no cover – exercised via mocks
            logging.getLogger(__name__).warning("Embedding batch API error: %s", exc)
            # On batch failure, return None for all items
            return [None] * len(texts)  # type: ignore[list-item]

    # Convenience alias used by the indexer -------------------------------------------------

    def generate_code_embedding(self, code: str, context: str) -> List[float]:
        # Combine *context* and *code* to improve semantic signal, then defer
        # to *generate_embedding* for the actual API call.
        combined = f"{context}\n\nCode:\n{code}"

        MAX_INPUT_CHARS = 6000  # guard against oversized requests
        if len(combined) > MAX_INPUT_CHARS:
            combined = combined[:MAX_INPUT_CHARS] + "..."

        return self.generate_embedding(combined)

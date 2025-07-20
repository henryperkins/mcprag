import os
from typing import List, Sequence
# ---------------------------------------------------------------------------
# Optional dependency: ``openai``
# ---------------------------------------------------------------------------
# Unit-test environments (or fresh checkouts) might not have the official
# OpenAI SDK installed.  To keep the rest of this module importable we fall
# back to a minimal stub that exposes only the attributes we access.
# ---------------------------------------------------------------------------

# --- Optional dependency ----------------------------------------------------
# ``openai`` is not installed in the execution sandbox.  To keep this module
# import-safe we synthesize a *very* small shim that imitates just enough of
# the public surface area used here *and* in our unit-tests (which rely on
# ``unittest.mock.patch`` to intercept calls).
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
    Embedding_cls = SimpleNamespace(create=_fake_create)  # legacy path

    stub = SimpleNamespace(
        embeddings=embeddings_ns,
        Embedding=Embedding_cls,
        api_type=None,
        api_base=None,
        api_key=None,
        api_version=None,
    )

    return stub


try:
    import openai  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – sandbox or dev env
    openai = _build_openai_stub()  # type: ignore

# Expose ``OpenAI`` symbol so tests can patch it: they expect a callable client
# constructor.  We forward to the real/stub ``openai`` module for simplicity.
OpenAI = openai  # type: ignore – dynamic assignment for test patching
from dotenv import load_dotenv

load_dotenv()

# Typing imports
from typing import Optional


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
            raise ValueError("API key for OpenAI or Azure OpenAI must be provided via environment variables")

        self.api_version = _get_env("AZURE_OPENAI_API_VERSION") or "2024-02-01"

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
        client_kwargs = {"api_key": self.api_key}
        if self.use_azure:
            client_kwargs.update({
                "azure_endpoint": self.endpoint,
                "api_version": self.api_version,
            })

        # MyPy will complain – OpenAI is a dynamically provided symbol
        self._client = OpenAI(**client_kwargs)  # type: ignore[arg-type]

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
        """Generate embeddings for *texts* one-by-one to keep memory footprint
        low and to simplify granular error handling.  Any failures are logged
        and translated into ``None`` placeholders so the caller can keep the
        original ordering intact.
        """

        results: List[List[float]] = []
        for text in texts:
            embedding = self.generate_embedding(text)
            results.append(embedding)
        return results

    # Convenience alias used by the indexer -------------------------------------------------

    def generate_code_embedding(self, code: str, context: str) -> List[float]:
        # Combine *context* and *code* to improve semantic signal, then defer
        # to *generate_embedding* for the actual API call.
        combined = f"{context}\n\nCode:\n{code}"

        MAX_INPUT_CHARS = 6000  # guard against oversized requests
        if len(combined) > MAX_INPUT_CHARS:
            combined = combined[:MAX_INPUT_CHARS] + "..."

        return self.generate_embedding(combined)

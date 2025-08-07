"""Light-weight REST-based replacement for the original EnhancedIndexBuilder.

This builder produces a JSON index schema (loaded from the canonical
`azure_search_index_schema.json` file at project root) and ensures the index
exists via the `IndexAutomation` helper (which utilises REST API calls).

It intentionally covers ONLY the subset of functionality required by callers
in this repository (primarily index creation & basic validation).  Advanced
SDK-specific features such as custom analyzers or synonym map provisioning are
out of scope and should be migrated separately using the automation layer.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, Any, List, Optional

from .automation import IndexAutomation
from .config import AzureSearchConfig

logger = logging.getLogger(__name__)


class EnhancedIndexBuilder:  # noqa: D401 – keep original public name
    """REST-based index builder compatible with the legacy interface."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        if config:
            self._cfg = config
        else:
            try:
                from enhanced_rag.core.config import get_config
                core = get_config()
                self._cfg = {
                    "endpoint": core.azure.endpoint,
                    "api_key": core.azure.admin_key,
                    "api_version": getattr(core.azure, "api_version", "2025-05-01-preview"),
                }
            except Exception:
                self._cfg = AzureSearchConfig.from_env().to_dict()
        self._index_automation = IndexAutomation(
            endpoint=self._cfg["endpoint"],
            api_key=self._cfg["api_key"],
            api_version=self._cfg.get("api_version", "2025-05-01-preview"),
        )

    # ------------------------------------------------------------------
    # Public API (subset)
    # ------------------------------------------------------------------

    async def create_enhanced_rag_index(
        self,
        index_name: str,
        description: str = "",
        enable_vectors: bool = True,
        enable_semantic: bool = True,
        **kwargs,
    ) -> Any:  # noqa: ANN401 – return SimpleNamespace for compat
        """Ensure *index_name* exists with the schema defined in the JSON file.

        The implementation ignores most feature flags for now – making the
        migration incremental.  The canonical schema should already include
        vector & semantic search configuration.
        """
        schema_path = Path("azure_search_index_schema.json")
        if not schema_path.exists():
            raise FileNotFoundError(
                "Index schema file 'azure_search_index_schema.json' not found"
            )

        index_def = json.loads(schema_path.read_text())
        index_def["name"] = index_name

        result = await self._index_automation.ensure_index_exists(index_def)

        # Return an object with `.name` attribute to preserve backwards-compat
        return SimpleNamespace(name=index_name, operation=result)

    # ------------------------------------------------------------------
    # Simple validation helpers – far less comprehensive than SDK version
    # ------------------------------------------------------------------

    async def validate_index_schema(
        self,
        index_name: str,
        required_fields: List[str],
    ) -> Dict[str, Any]:
        """Check presence of *required_fields* in the live index."""
        # Fetch current schema through automation helper
        current = await self._index_automation.ops.get_index(index_name)
        field_names = {f["name"] for f in current.get("fields", [])}

        missing = [f for f in required_fields if f not in field_names]

        return {
            "valid": len(missing) == 0,
            "missing_fields": missing,
            "total_fields": len(field_names),
            "has_vector_search": bool(current.get("vectorSearch")),
            "has_semantic_search": bool(current.get("semantic")),
            "scoring_profiles": [p.get("name") for p in current.get("scoringProfiles", [])],
        }

    async def validate_vector_dimensions(
        self,
        index_name: str,
        expected_dimensions: int = 3072,
        vector_field_name: str = "content_vector"
    ) -> Dict[str, Any]:
        """Validate vector field dimensions in the index."""
        try:
            current = await self._index_automation.ops.get_index(index_name)
            fields = current.get("fields", [])

            vector_field = None
            for field in fields:
                if field["name"] == vector_field_name:
                    vector_field = field
                    break

            if not vector_field:
                return {
                    "valid": False,
                    "error": f"Vector field '{vector_field_name}' not found",
                    "expected_dimensions": expected_dimensions,
                    "actual_dimensions": None
                }

            actual_dimensions = vector_field.get("dimensions")

            return {
                "valid": actual_dimensions == expected_dimensions,
                "expected_dimensions": expected_dimensions,
                "actual_dimensions": actual_dimensions,
                "vector_field_name": vector_field_name
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "expected_dimensions": expected_dimensions,
                "actual_dimensions": None
            }

    def create_rag_optimized_index(
        self,
        index_name: str,
        description: str = "",
        enable_vectors: bool = True,
        enable_semantic: bool = True,
        vector_dimensions: int = 3072
    ) -> Dict[str, Any]:
        """Create a RAG-optimized index schema."""
        # Load the canonical schema
        schema_path = Path("azure_search_index_schema.json")
        if not schema_path.exists():
            raise FileNotFoundError(
                "Index schema file 'azure_search_index_schema.json' not found"
            )

        index_def = json.loads(schema_path.read_text())
        index_def["name"] = index_name

        # Update vector dimensions if specified
        if enable_vectors and "fields" in index_def:
            for field in index_def["fields"]:
                if field.get("type") == "Collection(Edm.Single)" and field.get("dimensions"):
                    field["dimensions"] = vector_dimensions

        return index_def

    def create_or_update_index(self, index_def: Dict[str, Any]) -> Any:
        """Synchronously create or update an index."""
        # This is a synchronous wrapper - we'll need to run the async method
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                self._index_automation.ensure_index_exists(index_def)
            )
            return SimpleNamespace(name=index_def["name"], operation=result)
        finally:
            loop.close()

    @property
    def index_client(self):
        """Compatibility property for index client access."""
        # Return a mock object that provides the needed methods
        class MockIndexClient:
            def __init__(self, builder):
                self.builder = builder

            def delete_index(self, index_name: str):
                """Delete an index."""
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(
                        self.builder._index_automation.ops.delete_index(index_name)
                    )
                finally:
                    loop.close()

            def get_index(self, index_name: str):
                """Get index definition."""
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        self.builder._index_automation.ops.get_index(index_name)
                    )
                    return SimpleNamespace(**result)
                finally:
                    loop.close()

        return MockIndexClient(self)

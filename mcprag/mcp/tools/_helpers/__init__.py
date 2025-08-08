"""Helper modules for MCP tools."""

from .formatting import (
    sanitize_text,
    sanitize_highlights,
    normalize_items,
    first_highlight,
    truncate_snippets,
    headline_from_content,
    extract_exact_terms,
    get_snippet_headline,
)
from ..base import check_component
from .search_impl import (
    search_code_impl,
    search_microsoft_docs_impl,
    explain_ranking_impl,
)

__all__ = [
    # Formatting helpers
    "sanitize_text",
    "sanitize_highlights",
    "normalize_items",
    "first_highlight",
    "truncate_snippets",
    "headline_from_content",
    "extract_exact_terms",
    "get_snippet_headline",
    # Validation helpers
    "check_component",
    # Implementation helpers
    "search_code_impl",
    "search_microsoft_docs_impl",
    "explain_ranking_impl",
]

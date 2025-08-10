"""
FilterManager: builds safe Azure Cognitive Search filter expressions.
"""
from typing import List, Optional


class FilterManager:
    """Centralized filter expression builder for Azure Cognitive Search"""

    @staticmethod
    def escape(value: str) -> str:
        """Escape single quotes for OData filter expressions"""
        return str(value).replace("'", "''")

    @classmethod
    def repository(cls, repository: Optional[str]) -> Optional[str]:
        """Build repository filter clause using exact field matching.
        Uses exact match on repository field for precise filtering."""
        if not repository:
            return None
        safe = cls.escape(repository)
        
        # Use exact field matching for repository
        # This ensures precise filtering without false positives
        return f"repository eq '{safe}'"

    @classmethod
    def language(cls, language: Optional[str]) -> Optional[str]:
        """Build language filter clause"""
        if not language:
            return None
        return f"language eq '{cls.escape(language)}'"

    @classmethod
    def framework(cls, framework: Optional[str]) -> Optional[str]:
        """Build framework filter clause"""
        if not framework:
            return None
        return f"framework eq '{cls.escape(framework)}'"

    @classmethod
    def exclude_terms(cls, terms: List[str]) -> Optional[str]:
        """Build exclusion filter for terms"""
        parts = []
        for t in terms or []:
            safe = cls.escape(t)
            parts.append(f"not search.ismatch('{safe}', 'content')")
            parts.append(f"not search.ismatch('{safe}', 'tags')")
        return " and ".join(parts) if parts else None

    @classmethod
    def exact_terms(cls, terms: List[str]) -> Optional[str]:
        """Build exact term matching filter"""
        if not terms:
            return None
        term_filters = []
        for t in terms:
            safe = cls.escape(t)
            term_filters.append("(" + " or ".join([
                f"search.ismatch('{safe}', 'content')",
                f"search.ismatch('{safe}', 'function_name')",
                f"search.ismatch('{safe}', 'class_name')",
                f"search.ismatch('{safe}', 'docstring')",
            ]) + ")")
        return " and ".join(term_filters) if term_filters else None

    @staticmethod
    def combine_and(*clauses: Optional[str]) -> Optional[str]:
        """Combine multiple filter clauses with AND operator"""
        kept = [c for c in clauses if c]
        if not kept:
            return None
        if len(kept) == 1:
            return kept[0]
        return "(" + ") and (".join(kept) + ")"

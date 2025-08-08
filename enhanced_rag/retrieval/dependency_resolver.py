"""
Dependency resolution for code search
"""

import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
import ast
import re

from ..core.config import get_config, Config

logger = logging.getLogger(__name__)


@dataclass
class Dependency:
    """Represents a code dependency"""
    file_id: str
    file_path: str
    dependency_type: str  # import, function_call, inheritance, etc.
    relevance_score: float
    context: Dict[str, Any]


class DependencyResolver:
    """
    Resolves code dependencies to include related functions and modules
    """

    def __init__(self, config: Optional[Config | Dict[str, Any]] = None):
        # Normalize to a Config instance for consistent attribute access
        if config is None:
            self.config: Config = get_config()
        elif isinstance(config, Config):
            self.config = config
        elif isinstance(config, dict):
            try:
                self.config = Config(**config)
            except Exception:
                logger.warning("Invalid config dict passed to DependencyResolver; falling back to get_config()")
                self.config = get_config()
        else:
            self.config = get_config()
        self.dependency_cache = {}

    async def resolve_dependencies(
        self,
        query: str,
        current_file: Optional[str] = None,
        depth: int = 2
    ) -> List[Dependency]:
        """
        Resolve dependencies related to the query

        Args:
            query: Search query
            current_file: Current file path for context
            depth: How deep to traverse dependencies

        Returns:
            List of relevant dependencies
        """
        dependencies = []

        # Extract entities from query (functions, classes, modules)
        entities = self._extract_entities_from_query(query)

        # Find direct dependencies
        for entity in entities:
            deps = await self._find_entity_dependencies(entity, current_file)
            dependencies.extend(deps)

        # Traverse dependency graph if depth > 1
        if depth > 1:
            expanded_deps = await self._expand_dependencies(dependencies, depth - 1)
            dependencies.extend(expanded_deps)

        # Deduplicate and score
        unique_deps = self._deduplicate_dependencies(dependencies)
        scored_deps = self._score_dependencies(unique_deps, query, current_file)

        return sorted(scored_deps, key=lambda d: d.relevance_score, reverse=True)

    def _extract_entities_from_query(self, query: str) -> List[str]:
        """Extract function, class, and module names from query"""
        entities = []

        # Common patterns for code entities
        patterns = [
            r'\b(\w+)\s*\(',  # Function calls
            r'class\s+(\w+)',  # Class definitions
            r'from\s+(\w+)',   # Module imports
            r'import\s+(\w+)', # Direct imports
            r'(\w+)\.(\w+)',   # Method calls
        ]

        for pattern in patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    entities.extend([m for m in match if m])
                else:
                    entities.append(match)

        # Also check for camelCase and snake_case identifiers
        words = query.split()
        for word in words:
            if re.match(r'^[a-zA-Z_]\w*$', word) and len(word) > 2:
                entities.append(word)

        return list(set(entities))

    async def _find_entity_dependencies(
        self,
        entity: str,
        current_file: Optional[str] = None
    ) -> List[Dependency]:
        """Find dependencies for a specific entity"""
        dependencies = []

        # Check cache first
        cache_key = f"{entity}:{current_file}"
        if cache_key in self.dependency_cache:
            return self.dependency_cache[cache_key]

        # Find imports
        import_deps = await self._find_import_dependencies(entity, current_file)
        dependencies.extend(import_deps)

        # Find function calls
        call_deps = await self._find_function_call_dependencies(entity)
        dependencies.extend(call_deps)

        # Find class inheritance
        inheritance_deps = await self._find_inheritance_dependencies(entity)
        dependencies.extend(inheritance_deps)

        # Cache results
        self.dependency_cache[cache_key] = dependencies

        return dependencies

    async def _find_import_dependencies(
        self,
        entity: str,
        current_file: Optional[str] = None
    ) -> List[Dependency]:
        """Find import-related dependencies"""
        dependencies = []

        # This would normally query the search index for import statements
        # For now, return a placeholder implementation

        # Example: If entity is "authenticate", find files that export it
        if current_file:
            dep = Dependency(
                file_id=f"import_{entity}",
                file_path=f"auth/{entity}.py",
                dependency_type="import",
                relevance_score=0.8,
                context={"entity": entity, "source_file": current_file}
            )
            dependencies.append(dep)

        return dependencies

    async def _find_function_call_dependencies(
        self,
        entity: str
    ) -> List[Dependency]:
        """Find where a function is called"""
        dependencies = []

        # This would query for function calls in the codebase
        # Placeholder for now

        dep = Dependency(
            file_id=f"call_{entity}",
            file_path=f"utils/{entity}_usage.py",
            dependency_type="function_call",
            relevance_score=0.7,
            context={"function": entity}
        )
        dependencies.append(dep)

        return dependencies

    async def _find_inheritance_dependencies(
        self,
        entity: str
    ) -> List[Dependency]:
        """Find class inheritance relationships"""
        dependencies = []

        # This would look for class inheritance patterns
        # Placeholder implementation

        if entity[0].isupper():  # Likely a class name
            dep = Dependency(
                file_id=f"inherit_{entity}",
                file_path=f"models/{entity.lower()}.py",
                dependency_type="inheritance",
                relevance_score=0.75,
                context={"class": entity}
            )
            dependencies.append(dep)

        return dependencies

    async def _expand_dependencies(
        self,
        initial_deps: List[Dependency],
        remaining_depth: int
    ) -> List[Dependency]:
        """Expand dependencies recursively"""
        if remaining_depth <= 0:
            return []

        expanded = []
        for dep in initial_deps[:10]:  # Limit expansion to prevent explosion
            # Extract entities from dependency
            entities = self._extract_entities_from_file(dep.file_path)

            for entity in entities[:5]:  # Limit entities per file
                sub_deps = await self._find_entity_dependencies(entity, dep.file_path)
                expanded.extend(sub_deps)

        # Recursively expand if needed
        if remaining_depth > 1:
            further_expanded = await self._expand_dependencies(expanded, remaining_depth - 1)
            expanded.extend(further_expanded)

        return expanded

    def _extract_entities_from_file(self, file_path: str) -> List[str]:
        """Extract entities from a file path"""
        # Extract potential entity names from file path
        parts = file_path.split('/')
        filename = parts[-1].replace('.py', '').replace('.js', '')

        entities = [filename]

        # Convert snake_case to potential function names
        if '_' in filename:
            entities.append(filename.replace('_', ''))

        # Convert to camelCase
        if '_' in filename:
            parts = filename.split('_')
            camel = parts[0] + ''.join(p.capitalize() for p in parts[1:])
            entities.append(camel)

        return entities

    def _deduplicate_dependencies(
        self,
        dependencies: List[Dependency]
    ) -> List[Dependency]:
        """Remove duplicate dependencies"""
        seen = set()
        unique = []

        for dep in dependencies:
            key = f"{dep.file_id}:{dep.dependency_type}"
            if key not in seen:
                seen.add(key)
                unique.append(dep)

        return unique

    def _score_dependencies(
        self,
        dependencies: List[Dependency],
        query: str,
        current_file: Optional[str] = None
    ) -> List[Dependency]:
        """Score dependencies based on relevance"""
        query_lower = query.lower()

        for dep in dependencies:
            # Base score from dependency type
            score = dep.relevance_score

            # Boost if dependency contains query terms
            if any(term in dep.file_path.lower() for term in query_lower.split()):
                score *= 1.2

            # Boost if same module/package as current file
            if current_file and self._same_module(dep.file_path, current_file):
                score *= 1.3

            # Penalty for deep dependencies
            if dep.dependency_type == "transitive":
                score *= 0.8

            dep.relevance_score = min(score, 1.0)

        return dependencies

    def _same_module(self, path1: str, path2: str) -> bool:
        """Check if two paths are in the same module"""
        parts1 = path1.split('/')
        parts2 = path2.split('/')

        # Same directory
        if len(parts1) > 1 and len(parts2) > 1:
            return parts1[:-1] == parts2[:-1]

        return False

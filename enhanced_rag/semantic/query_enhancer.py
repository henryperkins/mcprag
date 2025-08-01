"""
Contextual Query Enhancer
Enhances queries based on current context and intent
"""

import logging
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict
import re

from ..core.interfaces import QueryEnhancer
from ..core.models import CodeContext, SearchIntent
from ..core.config import get_config
from .intent_classifier import IntentClassifier

logger = logging.getLogger(__name__)


class ContextualQueryEnhancer(QueryEnhancer):
    """
    Enhances search queries by incorporating:
    - Current file context (imports, functions, classes)
    - Detected intent
    - Language and framework-specific terminology
    - Project conventions and patterns
    """

    def __init__(self, config: Optional[Dict] = None):
        # Use provided config or fallback to default values
        if config:
            self.config = config
        else:
            # Try to get semantic config, fallback to empty dict
            try:
                full_config = get_config()
                self.config = getattr(full_config, 'semantic', {})
                if hasattr(self.config, 'model_dump'):
                    self.config = self.config.model_dump()
            except Exception:
                self.config = {}

        self.intent_classifier = IntentClassifier()
        self._initialize_enhancements()

    def _initialize_enhancements(self):
        """Initialize enhancement mappings"""
        
        # Domain-specific query aliases for vector/embedding debugging
        self.query_aliases = {
            'vector': ['embedding', 'dense_vector', 'content_vector', 'code_vector', 'text_vector', 'feature_vector'],
            'embedding': ['vector', 'dense_vector', 'representation', 'encoding'],
            'issues': ['error', 'exception', 'ValueError', 'IndexError', 'None', 'NaN', 'problem', 'bug'],
            'problems': ['issues', 'errors', 'exceptions', 'failures', 'bugs'],
            'search': ['query', 'retrieve', 'find', 'similarity_search', 'vector_search', 'semantic_search'],
            'index': ['indices', 'search_index', 'vector_index', 'inverted_index'],
            'dimension': ['dims', 'shape', 'size', 'length', 'dimensionality'],
            'similarity': ['distance', 'cosine', 'euclidean', 'dot_product', 'similarity_score'],
        }
        
        # Vector-specific semantic expansions
        self.vector_expansions = {
            'vector_search': ['similarity_search', 'knn_search', 'nearest_neighbor', 'semantic_search'],
            'embedding': ['vector_representation', 'dense_embedding', 'feature_encoding'],
            'vectorizer': ['embedder', 'encoder', 'transformer', 'feature_extractor'],
            'dimension': ['vector_dimension', 'embedding_size', 'feature_dimension'],
            'cosine': ['cosine_similarity', 'angular_distance', 'normalized_dot_product'],
            'euclidean': ['euclidean_distance', 'l2_distance', 'squared_distance'],
            'hnsw': ['hierarchical_navigable_small_world', 'graph_index', 'approximate_nearest_neighbor'],
            'knn': ['k_nearest_neighbors', 'nearest_neighbor', 'similarity_search'],
            'index_corruption': ['index_error', 'corrupted_index', 'rebuild_index', 'reindex'],
            'nan_values': ['not_a_number', 'invalid_values', 'null_embeddings', 'missing_vectors'],
        }

        # Language-specific enhancements
        self.language_enhancements = {
            'python': {
                'synonyms': {
                    'function': ['def', 'method', 'callable'],
                    'class': ['class', 'type', 'object'],
                    'import': ['import', 'from', 'module'],
                    'list': ['list', 'array', 'sequence'],
                    'dict': ['dict', 'dictionary', 'mapping', 'hashmap'],
                },
                'common_patterns': ['decorator', 'context manager', 'generator', 'comprehension'],
                'frameworks': {
                    'django': ['model', 'view', 'template', 'orm', 'queryset', 'migration'],
                    'flask': ['route', 'blueprint', 'request', 'response', 'session'],
                    'fastapi': ['router', 'dependency', 'pydantic', 'async', 'endpoint'],
                    'pytest': ['fixture', 'parametrize', 'mock', 'assert'],
                }
            },
            'javascript': {
                'synonyms': {
                    'function': ['function', 'method', 'arrow function', 'callback'],
                    'class': ['class', 'constructor', 'prototype'],
                    'import': ['import', 'require', 'module'],
                    'array': ['array', 'list', 'collection'],
                    'object': ['object', 'hash', 'map', 'dictionary'],
                },
                'common_patterns': ['promise', 'async/await', 'closure', 'callback', 'event'],
                'frameworks': {
                    'react': ['component', 'hook', 'state', 'props', 'jsx', 'context'],
                    'angular': ['component', 'service', 'directive', 'pipe', 'module'],
                    'vue': ['component', 'computed', 'watch', 'directive', 'mixin'],
                    'express': ['middleware', 'router', 'request', 'response'],
                }
            },
            'typescript': {
                'synonyms': {
                    'interface': ['interface', 'type', 'contract'],
                    'type': ['type', 'interface', 'generic'],
                    'enum': ['enum', 'enumeration', 'constant'],
                },
                'common_patterns': ['generic', 'decorator', 'type guard', 'namespace'],
                'frameworks': {
                    # Inherits from JavaScript
                }
            },
            'java': {
                'synonyms': {
                    'method': ['method', 'function'],
                    'class': ['class', 'interface', 'abstract class'],
                    'package': ['package', 'namespace', 'module'],
                    'list': ['List', 'ArrayList', 'LinkedList', 'Collection'],
                    'map': ['Map', 'HashMap', 'TreeMap', 'Dictionary'],
                },
                'common_patterns': ['singleton', 'factory', 'builder', 'observer', 'strategy'],
                'frameworks': {
                    'spring': ['bean', 'component', 'service', 'repository', 'controller'],
                    'hibernate': ['entity', 'query', 'session', 'criteria'],
                }
            },
            'go': {
                'synonyms': {
                    'function': ['func', 'method'],
                    'struct': ['struct', 'type'],
                    'interface': ['interface', 'contract'],
                    'slice': ['slice', 'array', 'list'],
                    'map': ['map', 'dictionary', 'hash'],
                },
                'common_patterns': ['goroutine', 'channel', 'defer', 'context'],
                'frameworks': {
                    'gin': ['handler', 'middleware', 'route', 'context'],
                    'echo': ['handler', 'middleware', 'route', 'context'],
                }
            }
        }

        # Intent-specific enhancement strategies
        self.intent_enhancements = {
            SearchIntent.IMPLEMENT: {
                'add_terms': ['example', 'implementation', 'code', 'how to'],
                'boost_terms': ['working', 'complete', 'production'],
                'exclude_terms': ['deprecated', 'outdated', 'legacy'],
            },
            SearchIntent.DEBUG: {
                'add_terms': ['error', 'fix', 'solution', 'troubleshoot'],
                'boost_terms': ['resolved', 'solved', 'workaround'],
                'exclude_terms': ['todo', 'fixme'],
            },
            SearchIntent.UNDERSTAND: {
                'add_terms': ['explanation', 'documentation', 'overview'],
                'boost_terms': ['tutorial', 'guide', 'explained'],
                'exclude_terms': ['stub', 'mock', 'test'],
            },
            SearchIntent.REFACTOR: {
                'add_terms': ['refactor', 'improve', 'optimize', 'best practice'],
                'boost_terms': ['clean', 'efficient', 'modern'],
                'exclude_terms': ['legacy', 'deprecated', 'old'],
            },
            SearchIntent.TEST: {
                'add_terms': ['test', 'testing', 'unit test', 'mock'],
                'boost_terms': ['coverage', 'assertion', 'fixture'],
                'exclude_terms': ['production', 'live'],
            },
            SearchIntent.DOCUMENT: {
                'add_terms': ['documentation', 'docstring', 'comment'],
                'boost_terms': ['readme', 'api doc', 'example'],
                'exclude_terms': ['todo', 'fixme', 'wip'],
            }
        }

        # Common abbreviations and expansions
        self.abbreviations = {
            'auth': 'authentication authorization',
            'db': 'database',
            'api': 'application programming interface',
            'ui': 'user interface',
            'ux': 'user experience',
            'crud': 'create read update delete',
            'orm': 'object relational mapping',
            'mvc': 'model view controller',
            'rest': 'representational state transfer',
            'jwt': 'json web token',
            'sql': 'structured query language',
            'nosql': 'non sql database',
            'ci': 'continuous integration',
            'cd': 'continuous deployment delivery',
            'di': 'dependency injection',
            'ioc': 'inversion of control',
            'dto': 'data transfer object',
            'dao': 'data access object',
        }

    async def classify_intent(self, query: str) -> str:
        """Classify query intent"""
        intent = await self.intent_classifier.classify_intent(query)
        return intent.value

    async def enhance_query(
        self,
        query: str,
        context: CodeContext,
        intent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate enhanced query variants based on context and intent

        Args:
            query: Original search query
            context: Current code context
            intent: Optional pre-classified intent

        Returns:
            Dict with 'queries' (enhanced variants) and 'exclude_terms'
        """
        # Classify intent if not provided
        if not intent:
            intent_enum = await self.intent_classifier.classify_intent(query)
            intent = intent_enum.value
        else:
            intent_enum = SearchIntent(intent)

        enhanced_queries = [query]  # Always include original
        exclude_terms = []  # Track terms to exclude

        # Apply context-based enhancements
        context_enhanced = await self._apply_context_enhancements(query, context)
        enhanced_queries.extend(context_enhanced)

        # Apply intent-based enhancements and collect exclude terms
        intent_enhanced, intent_exclude = self._apply_intent_enhancements_with_excludes(query, intent_enum)
        enhanced_queries.extend(intent_enhanced)
        exclude_terms.extend(intent_exclude)

        # Apply language-specific enhancements
        if context.language:
            language_enhanced = self._apply_language_enhancements(query, context.language, context.framework)
            enhanced_queries.extend(language_enhanced)

        # Apply abbreviation expansions
        abbrev_enhanced = self._expand_abbreviations(query)
        enhanced_queries.extend(abbrev_enhanced)
        
        # Apply domain-specific query aliases (e.g., vector -> embedding)
        alias_enhanced = self._apply_query_aliases(query)
        enhanced_queries.extend(alias_enhanced)
        
        # Apply vector-specific semantic expansions
        vector_enhanced = self._apply_vector_expansions(query)
        enhanced_queries.extend(vector_enhanced)

        # Generate semantic variants
        semantic_variants = await self.generate_variants(query, max_variants=5)
        enhanced_queries.extend(semantic_variants)

        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for q in enhanced_queries:
            q_normalized = ' '.join(q.lower().split())
            if q_normalized not in seen:
                seen.add(q_normalized)
                unique_queries.append(q)

        # Limit to reasonable number
        return {
            'queries': unique_queries[:15],
            'exclude_terms': list(set(exclude_terms))  # Remove duplicate excludes
        }

    async def generate_variants(
        self,
        query: str,
        max_variants: int = 10
    ) -> List[str]:
        """
        Generate semantic variants of the query

        Args:
            query: Original query
            max_variants: Maximum number of variants to generate

        Returns:
            List of query variants
        """
        variants = []
        words = query.lower().split()

        # Synonym replacement
        for i, word in enumerate(words):
            # Check common programming synonyms
            synonyms = self._get_programming_synonyms(word)
            for synonym in synonyms[:2]:  # Limit synonyms per word
                variant_words = words.copy()
                variant_words[i] = synonym
                variants.append(' '.join(variant_words))

        # Query restructuring
        if len(words) >= 3:
            # Try different word orders for key terms
            if any(action in words for action in ['implement', 'create', 'add', 'build']):
                # Move action word to different positions
                for i, word in enumerate(words):
                    if word in ['implement', 'create', 'add', 'build']:
                        # Move to front
                        reordered = [word] + words[:i] + words[i+1:]
                        variants.append(' '.join(reordered))
                        # Move to end
                        reordered = words[:i] + words[i+1:] + [word]
                        variants.append(' '.join(reordered))

        # Add question forms
        if not any(query.lower().startswith(q) for q in ['how', 'what', 'why', 'when', 'where']):
            variants.append(f"how to {query}")
            variants.append(f"what is {query}")

        # Add code-specific variants
        if 'function' in query.lower():
            variants.append(query.replace('function', 'method'))
            variants.append(query.replace('function', 'def'))

        return variants[:max_variants]

    async def _apply_context_enhancements(
        self,
        query: str,
        context: CodeContext
    ) -> List[str]:
        """Apply enhancements based on current code context"""
        enhanced = []

        # Add imports context
        if context.imports:
            # Find relevant imports for the query
            relevant_imports = self._find_relevant_imports(query, context.imports)
            if relevant_imports:
                imports_str = ' '.join(relevant_imports[:3])  # Top 3 imports
                enhanced.append(f"{query} {imports_str}")

        # Add current function/class context
        if context.functions:
            # If query might be about current function
            for func in context.functions[:2]:  # Consider top 2 functions
                if isinstance(func, dict) and 'name' in func:
                    func_name = func['name']
                    if self._is_relevant_to_query(func_name, query):
                        enhanced.append(f"{query} {func_name}")

        if context.classes:
            # If query might be about current class
            for cls in context.classes[:2]:  # Consider top 2 classes
                if isinstance(cls, dict) and 'name' in cls:
                    class_name = cls['name']
                    if self._is_relevant_to_query(class_name, query):
                        enhanced.append(f"{query} {class_name}")

        # Add framework context
        if context.framework:
            enhanced.append(f"{query} {context.framework}")

        # Add language context (if not already present)
        if context.language and context.language.lower() not in query.lower():
            enhanced.append(f"{query} {context.language}")

        # Add file type context
        file_type = self._detect_file_type(context.current_file)
        if file_type and file_type not in query.lower():
            enhanced.append(f"{query} {file_type}")

        return enhanced

    def _apply_intent_enhancements(
        self,
        query: str,
        intent: SearchIntent
    ) -> List[str]:
        """Apply enhancements based on detected intent"""
        enhanced = []

        intent_config = self.intent_enhancements.get(intent, {})

        # Add intent-specific terms
        for term in intent_config.get('add_terms', []):
            if term not in query.lower():
                enhanced.append(f"{query} {term}")

        # Add boost terms
        for term in intent_config.get('boost_terms', []):
            if term not in query.lower():
                enhanced.append(f"{term} {query}")

        # Create exclusion queries (these would be used as filters)
        exclude_terms = intent_config.get('exclude_terms', [])
        if exclude_terms:
            # Note: These would be applied as filters in the search, not in the query
            pass

        return enhanced
    
    def _apply_intent_enhancements_with_excludes(
        self,
        query: str,
        intent: SearchIntent
    ) -> tuple[List[str], List[str]]:
        """Apply enhancements based on detected intent, returning both enhancements and exclude terms"""
        enhanced = []
        exclude_terms = []

        intent_config = self.intent_enhancements.get(intent, {})

        # Add intent-specific terms
        for term in intent_config.get('add_terms', []):
            if term not in query.lower():
                enhanced.append(f"{query} {term}")

        # Add boost terms
        for term in intent_config.get('boost_terms', []):
            if term not in query.lower():
                enhanced.append(f"{term} {query}")

        # Collect exclusion terms
        exclude_terms = intent_config.get('exclude_terms', [])

        return enhanced, exclude_terms

    def _apply_language_enhancements(
        self,
        query: str,
        language: str,
        framework: Optional[str] = None
    ) -> List[str]:
        """Apply language and framework-specific enhancements"""
        enhanced = []

        lang_config = self.language_enhancements.get(language.lower(), {})

        # Apply language-specific synonyms
        synonyms = lang_config.get('synonyms', {})
        for term, syns in synonyms.items():
            if term in query.lower():
                for syn in syns[:2]:  # Limit synonyms
                    if syn != term and syn not in query.lower():
                        enhanced.append(query.replace(term, syn))

        # Add common patterns for the language
        patterns = lang_config.get('common_patterns', [])
        for pattern in patterns:
            if self._is_pattern_relevant(pattern, query):
                enhanced.append(f"{query} {pattern}")

        # Add framework-specific terms
        if framework:
            framework_terms = lang_config.get('frameworks', {}).get(framework.lower(), [])
            for term in framework_terms[:3]:  # Top 3 framework terms
                if term not in query.lower():
                    enhanced.append(f"{query} {term}")

        return enhanced

    def _expand_abbreviations(self, query: str) -> List[str]:
        """Expand common abbreviations in the query"""
        enhanced = []
        words = query.lower().split()

        for word in words:
            if word in self.abbreviations:
                expansion = self.abbreviations[word]
                # Replace abbreviation with expansion
                expanded_query = query.lower().replace(word, expansion)
                enhanced.append(expanded_query)

                # Also add version with both abbreviation and expansion
                enhanced.append(f"{query} {expansion}")

        return enhanced

    def _find_relevant_imports(self, query: str, imports: List[str]) -> List[str]:
        """Find imports relevant to the query"""
        query_lower = query.lower()
        relevant = []

        for imp in imports:
            imp_lower = imp.lower()
            # Check if import is mentioned in query
            if any(part in query_lower for part in imp_lower.split('.')):
                relevant.append(imp)
                continue

            # Check if import is related to query terms
            # For example, if query is about "authentication", include auth-related imports
            if self._is_import_related(imp_lower, query_lower):
                relevant.append(imp)

        # Sort by relevance (simple length-based for now)
        relevant.sort(key=lambda x: len(x))

        return relevant

    def _is_relevant_to_query(self, name: str, query: str) -> bool:
        """Check if a name (function/class) is relevant to the query"""
        name_lower = name.lower()
        query_lower = query.lower()

        # Direct mention
        if name_lower in query_lower:
            return True

        # Partial match
        name_parts = re.split(r'[_\-\s]+', name_lower)
        query_parts = re.split(r'[_\-\s]+', query_lower)

        # Check if any significant part matches
        for name_part in name_parts:
            if len(name_part) > 3:  # Skip short parts
                for query_part in query_parts:
                    if name_part in query_part or query_part in name_part:
                        return True

        return False

    def _detect_file_type(self, file_path: str) -> Optional[str]:
        """Detect the type of file (e.g., test, model, view, etc.)"""
        file_lower = file_path.lower()

        if 'test' in file_lower:
            return 'test'
        elif any(term in file_lower for term in ['model', 'schema', 'entity']):
            return 'model'
        elif any(term in file_lower for term in ['view', 'component', 'ui']):
            return 'view'
        elif any(term in file_lower for term in ['controller', 'handler', 'route']):
            return 'controller'
        elif any(term in file_lower for term in ['service', 'manager', 'provider']):
            return 'service'
        elif any(term in file_lower for term in ['util', 'helper', 'common']):
            return 'utility'
        elif any(term in file_lower for term in ['config', 'settings']):
            return 'configuration'

        return None

    def _is_pattern_relevant(self, pattern: str, query: str) -> bool:
        """Check if a language pattern is relevant to the query"""
        pattern_lower = pattern.lower()
        query_lower = query.lower()

        # Check for direct mention
        if pattern_lower in query_lower:
            return True

        # Check for related terms
        pattern_keywords = {
            'decorator': ['decorate', 'wrap', 'modify'],
            'generator': ['yield', 'iterate', 'generate'],
            'async': ['asynchronous', 'await', 'concurrent'],
            'promise': ['async', 'then', 'resolve'],
            'closure': ['scope', 'function', 'variable'],
        }

        if pattern_lower in pattern_keywords:
            keywords = pattern_keywords[pattern_lower]
            if any(keyword in query_lower for keyword in keywords):
                return True

        return False

    def _is_import_related(self, import_name: str, query: str) -> bool:
        """Check if an import is related to the query"""
        # Common import-to-concept mappings
        import_concepts = {
            'auth': ['authentication', 'authorization', 'login', 'security'],
            'test': ['testing', 'mock', 'assert', 'fixture'],
            'http': ['request', 'response', 'api', 'endpoint'],
            'database': ['db', 'query', 'model', 'orm'],
            'cache': ['caching', 'memory', 'redis', 'performance'],
            'log': ['logging', 'debug', 'trace', 'error'],
            'config': ['configuration', 'settings', 'environment'],
        }

        for key, concepts in import_concepts.items():
            if key in import_name:
                if any(concept in query for concept in concepts):
                    return True

        return False

    def _get_programming_synonyms(self, word: str) -> List[str]:
        """Get programming-specific synonyms for a word"""
        # Common programming synonyms
        synonym_map = {
            'function': ['method', 'func', 'procedure', 'routine'],
            'class': ['type', 'object', 'struct'],
            'variable': ['var', 'parameter', 'param', 'attribute'],
            'array': ['list', 'collection', 'sequence', 'vector'],
            'dictionary': ['dict', 'map', 'hash', 'object'],
            'string': ['str', 'text', 'chars'],
            'integer': ['int', 'number', 'numeric'],
            'boolean': ['bool', 'flag', 'true/false'],
            'error': ['exception', 'fault', 'bug', 'issue'],
            'create': ['make', 'build', 'construct', 'initialize'],
            'delete': ['remove', 'destroy', 'drop', 'clear'],
            'update': ['modify', 'change', 'alter', 'edit'],
            'get': ['fetch', 'retrieve', 'find', 'read'],
            'set': ['assign', 'update', 'write', 'store'],
        }

        return synonym_map.get(word, [])
    
    def _apply_query_aliases(self, query: str) -> List[str]:
        """Apply domain-specific query aliases (e.g., vector -> embedding)"""
        enhanced = []
        query_lower = query.lower()
        words = query_lower.split()
        
        # Check each word for aliases
        for i, word in enumerate(words):
            if word in self.query_aliases:
                aliases = self.query_aliases[word]
                for alias in aliases[:3]:  # Limit to top 3 aliases
                    if alias not in query_lower:
                        # Replace the word with its alias
                        new_words = words.copy()
                        new_words[i] = alias
                        enhanced.append(' '.join(new_words))
                        
                        # Also add query with both original and alias
                        enhanced.append(f"{query} {alias}")
        
        # Check multi-word patterns
        if 'vector issues' in query_lower or 'vector problems' in query_lower:
            enhanced.extend([
                query.replace('vector issues', 'embedding errors'),
                query.replace('vector problems', 'embedding exceptions'),
                f"{query} dimension mismatch",
                f"{query} NaN values",
                f"{query} None embedding"
            ])
        
        return enhanced
    
    def _apply_vector_expansions(self, query: str) -> List[str]:
        """Apply vector-specific semantic expansions"""
        enhanced = []
        query_lower = query.lower()
        
        # Check for vector-specific terms and expand them
        for term, expansions in self.vector_expansions.items():
            if term in query_lower:
                for expansion in expansions[:2]:  # Limit expansions
                    if expansion not in query_lower:
                        enhanced.append(f"{query} {expansion}")
                        
        # Special handling for debugging vector search issues
        if any(term in query_lower for term in ['vector', 'embedding', 'search']):
            if any(term in query_lower for term in ['issue', 'problem', 'error', 'debug']):
                # Add specific vector debugging terms
                debug_terms = [
                    'dimension mismatch',
                    'shape error',
                    'NaN embedding',
                    'null vector',
                    'index corruption',
                    'similarity threshold',
                    'empty results'
                ]
                for term in debug_terms:
                    if term not in query_lower:
                        enhanced.append(f"{query} {term}")
        
        return enhanced

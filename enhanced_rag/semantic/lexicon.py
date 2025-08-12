"""
Centralized semantic lexicon for query enhancement and rewriting
"""

# Domain-specific query aliases for vector/embedding debugging
QUERY_ALIASES = {
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
VECTOR_EXPANSIONS = {
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

# Common programming verbs and their variations
VERB_VARIATIONS = {
    'create': ['create', 'make', 'build', 'construct', 'generate', 'add'],
    'update': ['update', 'modify', 'change', 'edit', 'alter', 'revise'],
    'delete': ['delete', 'remove', 'destroy', 'drop', 'clear', 'erase'],
    'get': ['get', 'fetch', 'retrieve', 'find', 'read', 'load'],
    'set': ['set', 'assign', 'store', 'save', 'write', 'put'],
    'implement': ['implement', 'create', 'build', 'develop', 'code'],
    'fix': ['fix', 'repair', 'resolve', 'solve', 'debug', 'patch'],
    'optimize': ['optimize', 'improve', 'enhance', 'speed up', 'refactor'],
    'test': ['test', 'check', 'verify', 'validate', 'assert'],
    'understand': ['understand', 'explain', 'learn', 'comprehend', 'grasp'],
}

# Common programming nouns and their variations
NOUN_VARIATIONS = {
    'function': ['function', 'method', 'procedure', 'routine', 'operation'],
    'variable': ['variable', 'var', 'parameter', 'argument', 'value'],
    'class': ['class', 'type', 'object', 'entity', 'model'],
    'error': ['error', 'exception', 'bug', 'issue', 'problem'],
    'database': ['database', 'db', 'datastore', 'storage', 'repository'],
    'api': ['api', 'endpoint', 'interface', 'service', 'route'],
    'authentication': ['authentication', 'auth', 'login', 'signin', 'authorization'],
    'component': ['component', 'module', 'unit', 'element', 'widget'],
}

# Query templates for different search intents
QUERY_TEMPLATES = {
    'example': [
        "{topic} example",
        "how to {action}",
        "{action} implementation",
        "{topic} sample code",
        "{topic} usage",
    ],
    'definition': [
        "what is {term}",
        "{term} definition",
        "{term} meaning",
        "{term} explanation",
        "define {term}",
    ],
    'error': [
        "{error} error",
        "fix {error}",
        "resolve {error}",
        "{error} troubleshooting",
        "debug {error}",
    ],
    'comparison': [
        "{option1} vs {option2}",
        "difference between {option1} and {option2}",
        "compare {option1} {option2}",
        "{option1} or {option2}",
        "when to use {option1} vs {option2}",
    ]
}

# Question word transformations
QUESTION_TRANSFORMS = {
    'how': ['how', 'what is the way', 'what steps'],
    'what': ['what', 'which', 'what kind of'],
    'why': ['why', 'what is the reason', 'what causes'],
    'when': ['when', 'at what time', 'in which case'],
    'where': ['where', 'in which location', 'at what place'],
}

# Language-specific enhancements
LANGUAGE_ENHANCEMENTS = {
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
            'class': ['class', 'object'],
            'interface': ['interface', 'contract'],
            'package': ['package', 'namespace'],
        },
        'common_patterns': ['annotation', 'generics', 'lambda', 'stream'],
        'frameworks': {
            'spring': ['bean', 'component', 'service', 'repository', 'controller'],
            'junit': ['test', 'assert', 'mock', 'before', 'after'],
        }
    }
}
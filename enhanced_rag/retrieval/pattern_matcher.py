"""
DEPRECATED: Use enhanced_rag.pattern_registry instead
Pattern matching for architectural and design patterns in code - Legacy file
"""

import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
import re
from enum import Enum

from ..core.config import get_config

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Types of code patterns"""
    DESIGN_PATTERN = "design_pattern"
    ARCHITECTURAL = "architectural"
    FRAMEWORK_SPECIFIC = "framework_specific"
    ERROR_HANDLING = "error_handling"
    TESTING = "testing"
    SECURITY = "security"


@dataclass
class Pattern:
    """Represents a code pattern match"""
    file_id: str
    pattern_type: PatternType
    pattern_name: str
    confidence: float
    context: Dict[str, Any]


class PatternMatcher:
    """
    Matches architectural and design patterns in code
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or get_config()
        self._initialize_patterns()
        
    def _initialize_patterns(self):
        """Initialize pattern definitions"""
        self.patterns = {
            PatternType.DESIGN_PATTERN: {
                'singleton': {
                    'keywords': ['instance', 'getInstance', '_instance', 'singleton'],
                    'patterns': [r'class.*Singleton', r'getInstance\s*\(', r'_instance\s*=\s*None']
                },
                'factory': {
                    'keywords': ['factory', 'create', 'build', 'make'],
                    'patterns': [r'class.*Factory', r'create\w+\s*\(', r'build\w+\s*\(']
                },
                'observer': {
                    'keywords': ['observer', 'subscribe', 'notify', 'listener', 'event'],
                    'patterns': [r'class.*Observer', r'subscribe\s*\(', r'notify.*\(', r'addEventListener']
                },
                'strategy': {
                    'keywords': ['strategy', 'algorithm', 'policy'],
                    'patterns': [r'class.*Strategy', r'setStrategy\s*\(', r'execute.*Strategy']
                },
                'decorator': {
                    'keywords': ['decorator', 'wrapper', 'enhance'],
                    'patterns': [r'@\w+', r'class.*Decorator', r'wrap\w+\s*\(']
                }
            },
            PatternType.ARCHITECTURAL: {
                'mvc': {
                    'keywords': ['model', 'view', 'controller', 'mvc'],
                    'patterns': [r'class.*Controller', r'class.*Model', r'class.*View']
                },
                'microservice': {
                    'keywords': ['service', 'api', 'endpoint', 'route'],
                    'patterns': [r'@app\.route', r'@router\.(get|post|put|delete)', r'class.*Service']
                },
                'repository': {
                    'keywords': ['repository', 'dao', 'persistence'],
                    'patterns': [r'class.*Repository', r'class.*DAO', r'save\s*\(', r'find.*By']
                },
                'event_driven': {
                    'keywords': ['event', 'message', 'publisher', 'subscriber', 'queue'],
                    'patterns': [r'publish\s*\(', r'emit\s*\(', r'on\s*\(.*event', r'EventEmitter']
                }
            },
            PatternType.FRAMEWORK_SPECIFIC: {
                'django': {
                    'keywords': ['django', 'models', 'views', 'serializers'],
                    'patterns': [r'from django', r'class.*\(models\.Model\)', r'class.*View']
                },
                'react': {
                    'keywords': ['react', 'component', 'useState', 'useEffect'],
                    'patterns': [r'import.*from.*react', r'useState\s*\(', r'function.*Component']
                },
                'spring': {
                    'keywords': ['spring', 'bean', 'autowired', 'service'],
                    'patterns': [r'@Service', r'@Controller', r'@Autowired', r'@Bean']
                }
            },
            PatternType.ERROR_HANDLING: {
                'try_catch': {
                    'keywords': ['try', 'catch', 'except', 'finally', 'error'],
                    'patterns': [r'try\s*:', r'except.*:', r'catch\s*\(', r'finally\s*:']
                },
                'validation': {
                    'keywords': ['validate', 'check', 'verify', 'assert'],
                    'patterns': [r'validate\w+\s*\(', r'assert\s+', r'if.*is.*None']
                },
                'vector_dimension_mismatch': {
                    'keywords': ['dimension', 'shape', 'size', 'mismatch', 'vector', 'embedding'],
                    'patterns': [
                        r'len\s*\(.*vector.*\)\s*!=',
                        r'\.shape\[0\]\s*!=',
                        r'dimension.*mismatch',
                        r'shape.*!=',
                        r'size.*!=.*embedding',
                        r'ValueError.*dimension',
                        r'IndexError.*vector'
                    ]
                },
                'embedding_none_or_nan': {
                    'keywords': ['embedding', 'vector', 'None', 'NaN', 'null', 'isnan'],
                    'patterns': [
                        r'if\s+.*embedding.*is\s+None',
                        r'if\s+.*vector.*is\s+None',
                        r'np\.isnan\s*\(.*embedding',
                        r'math\.isnan\s*\(.*vector',
                        r'pd\.isna\s*\(.*embedding',
                        r'embedding\s*==\s*None',
                        r'not\s+.*embedding',
                        r'embedding\s+is\s+not\s+None'
                    ]
                },
                'index_corruption': {
                    'keywords': ['index', 'corrupt', 'rebuild', 'recreate', 'invalid', 'search'],
                    'patterns': [
                        r'index.*corrupt',
                        r'rebuild.*index',
                        r'recreate.*index',
                        r'index.*invalid',
                        r'reindex',
                        r'clear.*index.*rebuild'
                    ]
                },
                'similarity_metrics': {
                    'keywords': ['cosine', 'euclidean', 'similarity', 'distance', 'knn', 'hnsw'],
                    'patterns': [
                        r'cosine_similarity',
                        r'euclidean_distance',
                        r'l2_distance',
                        r'dot_product',
                        r'similarity_score',
                        r'k_nearest_neighbors',
                        r'knn_search',
                        r'hnsw.*index'
                    ]
                },
                'vector_search_errors': {
                    'keywords': ['vector_search', 'similarity_search', 'empty', 'no results', 'threshold'],
                    'patterns': [
                        r'vector_search.*failed',
                        r'similarity_search.*error',
                        r'empty.*results',
                        r'no.*results.*found',
                        r'threshold.*too.*high',
                        r'min_score.*not.*met',
                        r'search.*timeout'
                    ]
                }
            },
            PatternType.TESTING: {
                'unit_test': {
                    'keywords': ['test', 'assert', 'expect', 'mock'],
                    'patterns': [r'def test_', r'class.*Test', r'assert.*==', r'expect\(.*\)']
                },
                'integration_test': {
                    'keywords': ['integration', 'e2e', 'fixture', 'setup'],
                    'patterns': [r'@pytest\.fixture', r'setUp\s*\(', r'tearDown\s*\(']
                }
            },
            PatternType.SECURITY: {
                'authentication': {
                    'keywords': ['auth', 'login', 'token', 'jwt', 'session'],
                    'patterns': [r'authenticate\s*\(', r'jwt\.', r'session\[', r'@login_required']
                },
                'authorization': {
                    'keywords': ['permission', 'role', 'access', 'authorize'],
                    'patterns': [r'hasPermission\s*\(', r'@requires_permission', r'checkAccess\s*\(']
                }
            }
        }
    
    async def find_patterns(
        self,
        query: str,
        context: Optional[str] = None,
        pattern_types: Optional[List[PatternType]] = None
    ) -> List[Pattern]:
        """
        Find patterns related to the query
        
        Args:
            query: Search query
            context: Additional context
            pattern_types: Specific pattern types to look for
            
        Returns:
            List of pattern matches
        """
        if pattern_types is None:
            pattern_types = list(PatternType)
        
        patterns_found = []
        query_lower = query.lower()
        
        for pattern_type in pattern_types:
            if pattern_type not in self.patterns:
                continue
                
            for pattern_name, pattern_def in self.patterns[pattern_type].items():
                confidence = self._calculate_pattern_confidence(
                    query_lower,
                    pattern_def,
                    context
                )
                
                if confidence > 0.3:  # Threshold for relevance
                    pattern = Pattern(
                        file_id=f"{pattern_type.value}_{pattern_name}",
                        pattern_type=pattern_type,
                        pattern_name=pattern_name,
                        confidence=confidence,
                        context={
                            'query': query,
                            'matched_keywords': self._get_matched_keywords(query_lower, pattern_def),
                            'context': context
                        }
                    )
                    patterns_found.append(pattern)
        
        # Sort by confidence
        patterns_found.sort(key=lambda p: p.confidence, reverse=True)
        
        return patterns_found
    
    def _calculate_pattern_confidence(
        self,
        query: str,
        pattern_def: Dict[str, Any],
        context: Optional[str] = None
    ) -> float:
        """Calculate confidence score for a pattern match"""
        confidence = 0.0
        
        # Check keyword matches
        keywords = pattern_def.get('keywords', [])
        keyword_matches = sum(1 for kw in keywords if kw in query)
        if keywords:
            confidence += (keyword_matches / len(keywords)) * 0.6
        
        # Check pattern regex matches
        patterns = pattern_def.get('patterns', [])
        pattern_matches = 0
        for pattern in patterns:
            if re.search(pattern, query, re.IGNORECASE):
                pattern_matches += 1
        if patterns:
            confidence += (pattern_matches / len(patterns)) * 0.4
        
        # Boost if context contains related terms
        if context and keywords:
            context_lower = context.lower()
            context_matches = sum(1 for kw in keywords if kw in context_lower)
            confidence += (context_matches / len(keywords)) * 0.2
        
        return min(confidence, 1.0)
    
    def _get_matched_keywords(
        self,
        query: str,
        pattern_def: Dict[str, Any]
    ) -> List[str]:
        """Get keywords that matched in the query"""
        keywords = pattern_def.get('keywords', [])
        return [kw for kw in keywords if kw in query]
    
    async def suggest_patterns(
        self,
        code_context: Dict[str, Any]
    ) -> List[Pattern]:
        """
        Suggest patterns based on code context
        
        Args:
            code_context: Current code context
            
        Returns:
            List of suggested patterns
        """
        suggestions = []
        
        # Extract relevant information from context
        imports = code_context.get('imports', [])
        functions = code_context.get('functions', [])
        classes = code_context.get('classes', [])
        
        # Check for framework-specific patterns
        for framework, pattern_def in self.patterns[PatternType.FRAMEWORK_SPECIFIC].items():
            if any(kw in ' '.join(imports).lower() for kw in pattern_def['keywords']):
                pattern = Pattern(
                    file_id=f"suggest_{framework}",
                    pattern_type=PatternType.FRAMEWORK_SPECIFIC,
                    pattern_name=framework,
                    confidence=0.8,
                    context={'reason': 'Framework detected in imports'}
                )
                suggestions.append(pattern)
        
        # Check for design patterns based on class/function names
        all_names = ' '.join(functions + classes).lower()
        for pattern_name, pattern_def in self.patterns[PatternType.DESIGN_PATTERN].items():
            if any(kw in all_names for kw in pattern_def['keywords']):
                pattern = Pattern(
                    file_id=f"suggest_{pattern_name}",
                    pattern_type=PatternType.DESIGN_PATTERN,
                    pattern_name=pattern_name,
                    confidence=0.6,
                    context={'reason': 'Pattern keywords found in code'}
                )
                suggestions.append(pattern)
        
        return suggestions
    
    def get_pattern_examples(
        self,
        pattern_type: PatternType,
        pattern_name: str
    ) -> Dict[str, Any]:
        """Get examples and explanation for a specific pattern"""
        examples = {
            (PatternType.DESIGN_PATTERN, 'singleton'): {
                'description': 'Ensures a class has only one instance',
                'example': '''class Singleton:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance''',
                'use_cases': ['Database connections', 'Configuration managers', 'Logging']
            },
            (PatternType.DESIGN_PATTERN, 'factory'): {
                'description': 'Creates objects without specifying their exact class',
                'example': '''class AnimalFactory:
    @staticmethod
    def create_animal(animal_type):
        if animal_type == "dog":
            return Dog()
        elif animal_type == "cat":
            return Cat()''',
                'use_cases': ['Object creation with complex logic', 'Plugin systems']
            },
            (PatternType.ERROR_HANDLING, 'vector_dimension_mismatch'): {
                'description': 'Handles vector/embedding dimension mismatches',
                'example': '''if len(query_vector) != len(doc_vector):
    raise ValueError(f"Dimension mismatch: query {len(query_vector)} != doc {len(doc_vector)}")
    
# Or with numpy
if embedding.shape[0] != expected_dim:
    raise IndexError(f"Expected embedding dimension {expected_dim}, got {embedding.shape[0]}")''',
                'use_cases': ['Vector search validation', 'Embedding compatibility checks']
            },
            (PatternType.ERROR_HANDLING, 'embedding_none_or_nan'): {
                'description': 'Handles missing or invalid embeddings',
                'example': '''if embedding is None:
    logger.warning("Embedding is None, skipping document")
    return None
    
# Check for NaN values
if np.isnan(embedding).any():
    raise ValueError("Embedding contains NaN values")''',
                'use_cases': ['Embedding validation', 'Vector search preprocessing']
            },
            (PatternType.ERROR_HANDLING, 'similarity_metrics'): {
                'description': 'Different similarity/distance calculations',
                'example': '''# Cosine similarity
from sklearn.metrics.pairwise import cosine_similarity
similarity = cosine_similarity([query_vector], [doc_vector])[0][0]

# Euclidean distance
distance = np.linalg.norm(query_vector - doc_vector)

# Dot product similarity
similarity = np.dot(query_vector, doc_vector)''',
                'use_cases': ['Vector search ranking', 'Similarity calculations']
            }
        }
        
        return examples.get((pattern_type, pattern_name), {
            'description': f'{pattern_name} pattern',
            'example': 'No example available',
            'use_cases': []
        })
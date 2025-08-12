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
from ..pattern_registry import PatternRegistry, PatternType

logger = logging.getLogger(__name__)


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
        self.pattern_registry = PatternRegistry()
        self.patterns = self.pattern_registry.patterns
    
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
"""
Unified pattern registry for code analysis
Consolidates pattern recognition functionality across the system
"""

import logging
import re
from typing import Dict, List, Optional, Any, Set, Union
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Types of code patterns"""
    DESIGN_PATTERN = "design_pattern"
    ARCHITECTURAL = "architectural"
    FRAMEWORK_SPECIFIC = "framework_specific"
    ERROR_HANDLING = "error_handling"
    TESTING = "testing"
    SECURITY = "security"
    CODE_STRUCTURE = "code_structure"


@dataclass
class PatternMatch:
    """Represents a pattern match result"""
    pattern_type: PatternType
    pattern_name: str
    confidence: float
    matched_keywords: List[str]
    matched_patterns: List[str]
    context: Dict[str, Any]
    file_id: Optional[str] = None


class PatternRegistry:
    """
    Unified pattern registry that consolidates all pattern matching functionality
    """
    
    _instance = None
    _patterns_cache = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialize_patterns()
            self._compiled_patterns = {}
            self._initialized = True
    
    def _initialize_patterns(self):
        """Initialize comprehensive pattern definitions"""
        self.patterns = {
            PatternType.DESIGN_PATTERN: {
                'singleton': {
                    'keywords': ['singleton', 'instance', 'getInstance', '_instance'],
                    'patterns': [
                        r'class.*Singleton',
                        r'getInstance\s*\(',
                        r'_instance\s*=\s*None',
                        r'__new__.*cls\._instance'
                    ],
                    'description': 'Ensures a class has only one instance'
                },
                'factory': {
                    'keywords': ['factory', 'create', 'build', 'make', 'produce'],
                    'patterns': [
                        r'class.*Factory',
                        r'create\w+\s*\(',
                        r'build\w+\s*\(',
                        r'@staticmethod.*create'
                    ],
                    'description': 'Creates objects without specifying exact class'
                },
                'observer': {
                    'keywords': ['observer', 'subscribe', 'notify', 'listener', 'event'],
                    'patterns': [
                        r'class.*Observer',
                        r'subscribe\s*\(',
                        r'notify.*\(',
                        r'addEventListener',
                        r'addListener'
                    ],
                    'description': 'Defines one-to-many dependency between objects'
                },
                'strategy': {
                    'keywords': ['strategy', 'algorithm', 'policy'],
                    'patterns': [
                        r'class.*Strategy',
                        r'setStrategy\s*\(',
                        r'execute.*Strategy'
                    ],
                    'description': 'Defines family of algorithms and makes them interchangeable'
                },
                'decorator': {
                    'keywords': ['decorator', 'wrapper', 'enhance'],
                    'patterns': [
                        r'@\w+',
                        r'class.*Decorator',
                        r'wrap\w+\s*\(',
                        r'@wraps'
                    ],
                    'description': 'Adds behavior to objects dynamically'
                }
            },
            
            PatternType.ARCHITECTURAL: {
                'mvc': {
                    'keywords': ['model', 'view', 'controller', 'mvc'],
                    'patterns': [
                        r'class.*Controller',
                        r'class.*Model',
                        r'class.*View'
                    ],
                    'description': 'Model-View-Controller architectural pattern'
                },
                'microservice': {
                    'keywords': ['service', 'api', 'endpoint', 'route'],
                    'patterns': [
                        r'@app\.route',
                        r'@router\.(get|post|put|delete)',
                        r'class.*Service'
                    ],
                    'description': 'Microservice architecture pattern'
                },
                'repository': {
                    'keywords': ['repository', 'dao', 'persistence'],
                    'patterns': [
                        r'class.*Repository',
                        r'class.*DAO',
                        r'save\s*\(',
                        r'find.*By'
                    ],
                    'description': 'Data access abstraction pattern'
                }
            },
            
            PatternType.ERROR_HANDLING: {
                'try_catch': {
                    'keywords': ['try', 'catch', 'except', 'finally', 'error'],
                    'patterns': [
                        r'try\s*:',
                        r'except.*:',
                        r'catch\s*\(',
                        r'finally\s*:',
                        r'raise\s+\w+Error'
                    ],
                    'description': 'Exception handling patterns'
                },
                'validation': {
                    'keywords': ['validate', 'check', 'verify', 'assert'],
                    'patterns': [
                        r'validate\w+\s*\(',
                        r'assert\s+',
                        r'if.*is.*None',
                        r'if\s+not\s+.*:\s*raise'
                    ],
                    'description': 'Input validation patterns'
                },
                'vector_dimension_mismatch': {
                    'keywords': ['dimension', 'shape', 'size', 'mismatch', 'vector', 'embedding'],
                    'patterns': [
                        r'len\s*\(.*vector.*\)\s*!=',
                        r'\.shape\[0\]\s*!=',
                        r'dimension.*mismatch',
                        r'ValueError.*dimension'
                    ],
                    'description': 'Vector dimension validation'
                },
                'embedding_validation': {
                    'keywords': ['embedding', 'vector', 'None', 'NaN', 'null', 'isnan'],
                    'patterns': [
                        r'if\s+.*embedding.*is\s+None',
                        r'np\.isnan\s*\(.*embedding',
                        r'embedding\s*==\s*None'
                    ],
                    'description': 'Embedding validation patterns'
                }
            },
            
            PatternType.TESTING: {
                'unit_test': {
                    'keywords': ['test', 'assert', 'expect', 'mock'],
                    'patterns': [
                        r'def\s+test_\w+',
                        r'class.*Test',
                        r'assert.*==',
                        r'@pytest\.',
                        r'expect\(.*\)'
                    ],
                    'description': 'Unit testing patterns'
                },
                'integration_test': {
                    'keywords': ['integration', 'e2e', 'fixture', 'setup'],
                    'patterns': [
                        r'@pytest\.fixture',
                        r'setUp\s*\(',
                        r'tearDown\s*\('
                    ],
                    'description': 'Integration testing patterns'
                }
            },
            
            PatternType.FRAMEWORK_SPECIFIC: {
                'django': {
                    'keywords': ['django', 'models', 'views', 'serializers'],
                    'patterns': [
                        r'from django',
                        r'class.*\(models\.Model\)',
                        r'class.*View'
                    ],
                    'description': 'Django framework patterns'
                },
                'react': {
                    'keywords': ['react', 'component', 'useState', 'useEffect'],
                    'patterns': [
                        r'import.*from.*react',
                        r'useState\s*\(',
                        r'function.*Component'
                    ],
                    'description': 'React framework patterns'
                },
                'fastapi': {
                    'keywords': ['fastapi', 'router', 'dependency', 'pydantic'],
                    'patterns': [
                        r'from fastapi',
                        r'@app\.(get|post|put|delete)',
                        r'@router\.(get|post|put|delete)',
                        r'Depends\s*\('
                    ],
                    'description': 'FastAPI framework patterns'
                }
            },
            
            PatternType.CODE_STRUCTURE: {
                'initialization': {
                    'keywords': ['init', 'setup', 'constructor'],
                    'patterns': [
                        r'def\s+__init__\s*\(',
                        r'self\.\w+\s*=',
                        r'super\(\).__init__'
                    ],
                    'description': 'Object initialization patterns'
                },
                'api_endpoint': {
                    'keywords': ['endpoint', 'route', 'api', 'handler'],
                    'patterns': [
                        r'@app\.(get|post|put|delete)\(',
                        r'@router\.(get|post|put|delete)\(',
                        r'async\s+def\s+\w+.*request'
                    ],
                    'description': 'API endpoint patterns'
                }
            }
        }
    
    @lru_cache(maxsize=1000)
    def _get_compiled_pattern(self, pattern_str: str) -> re.Pattern:
        """Get compiled regex pattern with caching"""
        return re.compile(pattern_str, re.IGNORECASE | re.DOTALL)
    
    def recognize_patterns(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None,
        pattern_types: Optional[List[PatternType]] = None
    ) -> List[PatternMatch]:
        """
        Recognize patterns in code
        
        Args:
            code: Code to analyze
            context: Additional context
            pattern_types: Specific pattern types to check
            
        Returns:
            List of pattern matches sorted by confidence
        """
        if pattern_types is None:
            pattern_types = list(PatternType)
        
        matches = []
        code_lower = code.lower()
        
        for pattern_type in pattern_types:
            if pattern_type not in self.patterns:
                continue
                
            for pattern_name, pattern_def in self.patterns[pattern_type].items():
                confidence, matched_kw, matched_patterns = self._calculate_confidence(
                    code, code_lower, pattern_def, context
                )
                
                if confidence > 0.1:  # Low threshold to catch weak matches
                    match = PatternMatch(
                        pattern_type=pattern_type,
                        pattern_name=pattern_name,
                        confidence=confidence,
                        matched_keywords=matched_kw,
                        matched_patterns=matched_patterns,
                        context=context or {}
                    )
                    matches.append(match)
        
        # Sort by confidence descending
        matches.sort(key=lambda x: x.confidence, reverse=True)
        return matches
    
    def _calculate_confidence(
        self,
        code: str,
        code_lower: str,
        pattern_def: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> tuple[float, List[str], List[str]]:
        """Calculate confidence score for pattern match"""
        confidence = 0.0
        matched_keywords = []
        matched_patterns = []
        
        # Check keyword matches (40% weight)
        keywords = pattern_def.get('keywords', [])
        if keywords:
            keyword_matches = [kw for kw in keywords if kw.lower() in code_lower]
            matched_keywords = keyword_matches
            confidence += (len(keyword_matches) / len(keywords)) * 0.4
        
        # Check regex pattern matches (50% weight)
        patterns = pattern_def.get('patterns', [])
        if patterns:
            pattern_matches = []
            for pattern_str in patterns:
                compiled_pattern = self._get_compiled_pattern(pattern_str)
                if compiled_pattern.search(code):
                    pattern_matches.append(pattern_str)
            
            matched_patterns = pattern_matches
            confidence += (len(pattern_matches) / len(patterns)) * 0.5
        
        # Context boost (10% weight)
        if context and keywords:
            context_str = str(context).lower()
            context_matches = [kw for kw in keywords if kw.lower() in context_str]
            confidence += (len(context_matches) / len(keywords)) * 0.1
        
        return min(confidence, 1.0), matched_keywords, matched_patterns
    
    def get_dominant_pattern(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[PatternMatch]:
        """Get the most confident pattern match"""
        matches = self.recognize_patterns(code, context)
        return matches[0] if matches else None
    
    def get_patterns_by_type(self, pattern_type: PatternType) -> Dict[str, Dict[str, Any]]:
        """Get all patterns of a specific type"""
        return self.patterns.get(pattern_type, {})
    
    def get_pattern_info(
        self,
        pattern_type: PatternType,
        pattern_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get information about a specific pattern"""
        patterns = self.get_patterns_by_type(pattern_type)
        return patterns.get(pattern_name)
    
    def suggest_patterns(
        self,
        file_context: Dict[str, Any]
    ) -> List[PatternMatch]:
        """
        Suggest relevant patterns based on file context
        
        Args:
            file_context: Context including imports, functions, classes
            
        Returns:
            List of suggested patterns
        """
        suggestions = []
        
        imports = file_context.get('imports', [])
        functions = file_context.get('functions', [])
        classes = file_context.get('classes', [])
        
        # Framework detection from imports
        imports_str = ' '.join(imports).lower()
        for pattern_name, pattern_def in self.patterns[PatternType.FRAMEWORK_SPECIFIC].items():
            keywords = pattern_def.get('keywords', [])
            if any(kw in imports_str for kw in keywords):
                suggestions.append(PatternMatch(
                    pattern_type=PatternType.FRAMEWORK_SPECIFIC,
                    pattern_name=pattern_name,
                    confidence=0.8,
                    matched_keywords=[kw for kw in keywords if kw in imports_str],
                    matched_patterns=[],
                    context={'reason': 'Framework detected in imports'}
                ))
        
        # Pattern detection from names
        all_names = ' '.join(functions + classes).lower()
        for pattern_type in [PatternType.DESIGN_PATTERN, PatternType.ARCHITECTURAL]:
            for pattern_name, pattern_def in self.patterns[pattern_type].items():
                keywords = pattern_def.get('keywords', [])
                matched_kw = [kw for kw in keywords if kw in all_names]
                if matched_kw:
                    suggestions.append(PatternMatch(
                        pattern_type=pattern_type,
                        pattern_name=pattern_name,
                        confidence=0.6,
                        matched_keywords=matched_kw,
                        matched_patterns=[],
                        context={'reason': 'Pattern keywords in code structure'}
                    ))
        
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        return suggestions


# Global instance
pattern_registry = PatternRegistry()


def get_pattern_registry() -> PatternRegistry:
    """Get the global pattern registry instance"""
    return pattern_registry

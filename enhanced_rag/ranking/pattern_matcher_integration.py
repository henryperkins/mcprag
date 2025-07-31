"""
Pattern matching scorer for ranking integration
"""

import logging
from typing import List, Dict, Optional, Set
import re

from ..core.models import SearchResult, EnhancedContext
from ..code_understanding.pattern_recognizer import PatternRecognizer
from ..retrieval.pattern_matcher import PatternMatcher

logger = logging.getLogger(__name__)


class PatternMatchScorer:
    """Calculate pattern matching scores for ranking"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.recognizer = PatternRecognizer(self.config)
        self.matcher = PatternMatcher(self.config)
        
        # Pattern keyword mappings
        self.pattern_keywords = {
            'singleton': ['singleton', 'instance', 'getInstance', '_instance'],
            'factory': ['factory', 'create', 'build', 'make', 'produce'],
            'observer': ['observer', 'listener', 'subscribe', 'notify', 'event'],
            'decorator': ['decorator', 'wrapper', 'enhance', '@'],
            'strategy': ['strategy', 'algorithm', 'policy', 'behavior'],
            'adapter': ['adapter', 'adaptor', 'wrapper', 'bridge'],
            'template': ['template', 'abstract', 'hook', 'skeleton'],
            'async': ['async', 'await', 'promise', 'future', 'concurrent'],
            'cache': ['cache', 'memoize', 'store', 'cached'],
            'retry': ['retry', 'resilient', 'fallback', 'circuit breaker'],
            'repository': ['repository', 'dao', 'persistence', 'storage'],
            'mvc': ['controller', 'model', 'view', 'mvc', 'mvvm'],
            'dependency_injection': ['inject', 'di', 'ioc', 'container']
        }
        
        # Pattern relationships for similarity scoring
        self.pattern_relations = {
            'factory': ['builder', 'abstract_factory', 'prototype'],
            'observer': ['pub_sub', 'event_emitter', 'mediator'],
            'decorator': ['wrapper', 'proxy', 'adapter'],
            'strategy': ['state', 'template', 'visitor'],
            'repository': ['dao', 'unit_of_work', 'data_mapper']
        }
    
    async def calculate_pattern_score(
        self,
        result: SearchResult,
        query: str,
        context: Optional[EnhancedContext] = None
    ) -> float:
        """
        Calculate pattern match score between query and result
        
        Returns score between 0 and 1
        """
        try:
            # Extract patterns from result
            result_patterns = await self._extract_result_patterns(result)
            
            # Extract expected patterns from query
            query_patterns = await self._extract_query_patterns(query, context)
            
            if not query_patterns:
                # No patterns expected, return neutral score
                return 0.5
            
            # Calculate similarity score
            score = self._calculate_pattern_similarity(result_patterns, query_patterns)
            
            # Boost score if result contains pattern implementations
            if await self._has_pattern_implementation(result, query_patterns):
                score = min(score * 1.2, 1.0)
            
            return score
            
        except Exception as e:
            logger.error(f"Error calculating pattern score: {e}")
            return 0.0
    
    async def _extract_result_patterns(self, result: SearchResult) -> Dict[str, float]:
        """Extract patterns from search result with confidence scores"""
        patterns = {}
        
        # Use pattern recognizer if available
        try:
            recognized = await self.recognizer.recognize_patterns(
                result.content,
                result.language
            )
            patterns.update(recognized)
        except:
            pass
        
        # Fallback to keyword-based detection
        content_lower = result.content.lower()
        
        for pattern, keywords in self.pattern_keywords.items():
            keyword_count = sum(1 for kw in keywords if kw in content_lower)
            if keyword_count > 0:
                # Calculate confidence based on keyword density
                confidence = min(keyword_count * 0.3, 1.0)
                patterns[pattern] = max(patterns.get(pattern, 0), confidence)
        
        # Check for pattern-specific structures
        patterns.update(self._detect_structural_patterns(result))
        
        return patterns
    
    async def _extract_query_patterns(
        self,
        query: str,
        context: Optional[EnhancedContext]
    ) -> Set[str]:
        """Extract expected patterns from query and context"""
        patterns = set()
        query_lower = query.lower()
        
        # Direct pattern mentions in query
        for pattern, keywords in self.pattern_keywords.items():
            if any(kw in query_lower for kw in keywords):
                patterns.add(pattern)
        
        # Intent-based pattern inference
        intent_patterns = {
            'implement cache': ['cache', 'memoize'],
            'implement singleton': ['singleton'],
            'create factory': ['factory', 'builder'],
            'add observer': ['observer', 'event'],
            'implement repository': ['repository', 'dao'],
            'add retry logic': ['retry', 'circuit_breaker'],
            'implement async': ['async', 'promise']
        }
        
        for intent_phrase, expected_patterns in intent_patterns.items():
            if intent_phrase in query_lower:
                patterns.update(expected_patterns)
        
        # Context-based patterns
        if context:
            # Add patterns from current file
            if hasattr(context, 'current_patterns'):
                patterns.update(context.current_patterns[:3])
            
            # Add patterns common in the module
            if hasattr(context, 'module_patterns'):
                patterns.update(context.module_patterns[:2])
        
        return patterns
    
    def _calculate_pattern_similarity(
        self,
        result_patterns: Dict[str, float],
        query_patterns: Set[str]
    ) -> float:
        """Calculate similarity between result patterns and expected patterns"""
        if not query_patterns:
            return 0.5
        
        score = 0.0
        max_possible_score = len(query_patterns)
        
        for expected_pattern in query_patterns:
            # Direct match
            if expected_pattern in result_patterns:
                score += result_patterns[expected_pattern]
            else:
                # Check related patterns
                for base_pattern, related in self.pattern_relations.items():
                    if expected_pattern == base_pattern:
                        for related_pattern in related:
                            if related_pattern in result_patterns:
                                score += result_patterns[related_pattern] * 0.7
                                break
                    elif expected_pattern in related and base_pattern in result_patterns:
                        score += result_patterns[base_pattern] * 0.7
                        break
        
        # Normalize to 0-1
        return min(score / max_possible_score, 1.0)
    
    def _detect_structural_patterns(self, result: SearchResult) -> Dict[str, float]:
        """Detect patterns based on code structure"""
        patterns = {}
        content = result.content
        
        # Singleton pattern detection
        if re.search(r'class.*\{[\s\S]*?_instance\s*=\s*None', content):
            patterns['singleton'] = 0.8
        elif '_instance' in content and 'getInstance' in content:
            patterns['singleton'] = 0.6
        
        # Factory pattern detection
        if re.search(r'def\s+create\w+\s*\(.*?\)\s*->\s*\w+:', content):
            patterns['factory'] = 0.7
        elif re.search(r'class\s+\w*Factory', content):
            patterns['factory'] = 0.8
        
        # Observer pattern detection
        if 'subscribe' in content and 'notify' in content:
            patterns['observer'] = 0.7
        elif re.search(r'class\s+\w*Observer', content):
            patterns['observer'] = 0.8
        
        # Decorator pattern detection
        if re.search(r'@\w+\s*\n\s*def', content):
            patterns['decorator'] = 0.6
        elif re.search(r'class\s+\w*Decorator', content):
            patterns['decorator'] = 0.8
        
        # Async pattern detection
        if result.language == 'python':
            if 'async def' in content or 'await ' in content:
                patterns['async'] = 0.9
        elif result.language in ['javascript', 'typescript']:
            if 'async ' in content or 'await ' in content or 'Promise' in content:
                patterns['async'] = 0.9
        
        return patterns
    
    async def _has_pattern_implementation(
        self,
        result: SearchResult,
        query_patterns: Set[str]
    ) -> bool:
        """Check if result contains actual pattern implementation"""
        # Simple heuristic: if result has class/function definitions
        # and matches expected patterns, likely an implementation
        
        has_implementation = False
        
        if result.language == 'python':
            has_implementation = bool(re.search(r'class\s+\w+.*?:', result.content))
            has_implementation |= bool(re.search(r'def\s+\w+.*?:', result.content))
        elif result.language in ['javascript', 'typescript']:
            has_implementation = bool(re.search(r'class\s+\w+\s*\{', result.content))
            has_implementation |= bool(re.search(r'function\s+\w+\s*\(', result.content))
        
        return has_implementation and len(query_patterns) > 0
    
    def get_pattern_explanation(
        self,
        result_patterns: Dict[str, float],
        query_patterns: Set[str]
    ) -> str:
        """Generate explanation for pattern matching"""
        explanations = []
        
        for pattern in query_patterns:
            if pattern in result_patterns:
                confidence = result_patterns[pattern]
                if confidence > 0.7:
                    explanations.append(f"Strong {pattern} pattern match")
                else:
                    explanations.append(f"Possible {pattern} pattern")
        
        if explanations:
            return "Pattern matches: " + ", ".join(explanations)
        else:
            return "No direct pattern matches found"
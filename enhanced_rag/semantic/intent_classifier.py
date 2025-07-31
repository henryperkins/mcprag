"""
Intent Classifier
Classifies user query intent to optimize search strategy
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

from ..core.models import SearchIntent
from ..core.config import get_config

logger = logging.getLogger(__name__)


class IntentClassifier:
    """
    Classifies search queries into intent categories:
    - implement: User wants to implement new functionality
    - debug: User is debugging an issue
    - understand: User wants to understand existing code
    - refactor: User wants to refactor/improve code
    - test: User wants to write tests
    - document: User wants to document code
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._initialize_patterns()
    
    def _initialize_patterns(self):
        """Initialize intent detection patterns"""
        
        # Keywords strongly associated with each intent
        self.intent_keywords = {
            SearchIntent.IMPLEMENT: {
                'strong': ['implement', 'create', 'add', 'build', 'develop', 'make', 'write', 'code', 'feature'],
                'moderate': ['new', 'setup', 'initialize', 'start', 'begin', 'introduce'],
                'context': ['function', 'class', 'method', 'component', 'module', 'api', 'endpoint']
            },
            SearchIntent.DEBUG: {
                'strong': ['debug', 'fix', 'error', 'bug', 'issue', 'problem', 'crash', 'fail', 'exception'],
                'moderate': ['wrong', 'broken', 'not working', 'doesn\'t work', 'investigate', 'troubleshoot'],
                'context': ['stacktrace', 'traceback', 'log', 'message', 'warning']
            },
            SearchIntent.UNDERSTAND: {
                'strong': ['understand', 'explain', 'how does', 'what does', 'why', 'learn', 'documentation'],
                'moderate': ['work', 'purpose', 'meaning', 'logic', 'flow', 'architecture'],
                'context': ['code', 'function', 'algorithm', 'pattern', 'design']
            },
            SearchIntent.REFACTOR: {
                'strong': ['refactor', 'improve', 'optimize', 'clean', 'restructure', 'reorganize'],
                'moderate': ['better', 'performance', 'simplify', 'reduce', 'enhance', 'update'],
                'context': ['code', 'structure', 'design', 'pattern', 'quality']
            },
            SearchIntent.TEST: {
                'strong': ['test', 'testing', 'unit test', 'integration test', 'coverage', 'mock', 'assert'],
                'moderate': ['verify', 'validate', 'check', 'ensure', 'confirm'],
                'context': ['function', 'method', 'behavior', 'scenario', 'case']
            },
            SearchIntent.DOCUMENT: {
                'strong': ['document', 'documentation', 'docstring', 'comment', 'readme', 'explain'],
                'moderate': ['describe', 'annotate', 'clarify', 'note'],
                'context': ['code', 'api', 'function', 'class', 'module']
            }
        }
        
        # Regex patterns for intent detection
        self.intent_patterns = {
            SearchIntent.IMPLEMENT: [
                r'how (?:to|do i|can i) (?:implement|create|add|build)',
                r'(?:implement|create|add|build) (?:a|an|the)? ?\w+',
                r'(?:want|need) to (?:implement|create|add|build)',
                r'(?:code|write) (?:a|an|the)? ?\w+ (?:function|class|method)',
            ],
            SearchIntent.DEBUG: [
                r'(?:error|exception|bug|issue):?\s*\w+',
                r'\w+ (?:error|exception|failing|failed|not working)',
                r'(?:debug|fix|solve|resolve) (?:this|the)? ?(?:error|issue|problem)',
                r'why (?:is|does) \w+ (?:failing|not working|throwing)',
            ],
            SearchIntent.UNDERSTAND: [
                r'(?:what|how) (?:does|is) \w+ (?:work|do)',
                r'(?:explain|understand) (?:this|the)? ?\w+',
                r'(?:purpose|meaning) of \w+',
                r'(?:documentation|docs) (?:for|about) \w+',
            ],
            SearchIntent.REFACTOR: [
                r'(?:refactor|improve|optimize) (?:this|the)? ?\w+',
                r'make \w+ (?:better|faster|cleaner|simpler)',
                r'(?:reduce|simplify) \w+ complexity',
                r'best (?:practice|way) (?:to|for) \w+',
            ],
            SearchIntent.TEST: [
                r'(?:write|create|add) (?:test|tests) (?:for|to)',
                r'(?:unit|integration) test \w+',
                r'test (?:coverage|scenario|case) for',
                r'how to (?:test|mock) \w+',
            ],
            SearchIntent.DOCUMENT: [
                r'(?:write|add|create) (?:documentation|docs|docstring)',
                r'document (?:this|the)? ?\w+',
                r'(?:comment|annotate) (?:this|the)? ?code',
                r'(?:readme|api docs?) for',
            ]
        }
        
        # Common programming task patterns
        self.task_patterns = {
            'api': ['endpoint', 'route', 'request', 'response', 'rest', 'graphql'],
            'database': ['query', 'sql', 'orm', 'migration', 'schema', 'model'],
            'authentication': ['auth', 'login', 'token', 'jwt', 'oauth', 'permission'],
            'frontend': ['component', 'ui', 'render', 'state', 'props', 'dom'],
            'backend': ['server', 'api', 'service', 'controller', 'middleware'],
            'testing': ['test', 'mock', 'stub', 'assert', 'expect', 'suite'],
            'performance': ['optimize', 'cache', 'speed', 'performance', 'latency'],
            'security': ['secure', 'encrypt', 'hash', 'validate', 'sanitize', 'xss', 'csrf'],
        }
    
    async def classify_intent(self, query: str) -> SearchIntent:
        """
        Classify the intent of a search query
        
        Args:
            query: The search query to classify
            
        Returns:
            SearchIntent enum value
        """
        query_lower = query.lower()
        scores = defaultdict(float)
        
        # Check keyword matches
        for intent, keywords in self.intent_keywords.items():
            # Strong keywords get higher weight
            for keyword in keywords['strong']:
                if keyword in query_lower:
                    scores[intent] += 3.0
            
            # Moderate keywords
            for keyword in keywords['moderate']:
                if keyword in query_lower:
                    scores[intent] += 1.5
            
            # Context keywords
            for keyword in keywords['context']:
                if keyword in query_lower:
                    scores[intent] += 0.5
        
        # Check regex patterns
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    scores[intent] += 2.5
        
        # Analyze query structure
        structure_score = self._analyze_query_structure(query_lower)
        for intent, score in structure_score.items():
            scores[intent] += score
        
        # Get the intent with highest score
        if scores:
            best_intent = max(scores.items(), key=lambda x: x[1])
            
            # Only return if confidence is high enough
            if best_intent[1] >= 2.0:
                logger.debug(f"Classified query '{query}' as intent: {best_intent[0].value} (score: {best_intent[1]})")
                return best_intent[0]
        
        # Default to understand if no clear intent
        logger.debug(f"No clear intent for query '{query}', defaulting to UNDERSTAND")
        return SearchIntent.UNDERSTAND
    
    def _analyze_query_structure(self, query: str) -> Dict[SearchIntent, float]:
        """Analyze query structure for intent clues"""
        scores = defaultdict(float)
        
        # Questions typically indicate understanding intent
        if query.startswith(('what', 'how', 'why', 'when', 'where', 'who')):
            scores[SearchIntent.UNDERSTAND] += 1.0
        
        # Imperative mood often indicates implementation
        if query.startswith(('create', 'add', 'implement', 'build', 'make')):
            scores[SearchIntent.IMPLEMENT] += 1.5
        
        # Error patterns indicate debugging
        if any(pattern in query for pattern in ['error:', 'exception:', 'traceback:', 'failed:']):
            scores[SearchIntent.DEBUG] += 2.0
        
        # Task-specific patterns
        for task, keywords in self.task_patterns.items():
            if any(keyword in query for keyword in keywords):
                # Different tasks have different typical intents
                if task in ['api', 'database', 'frontend', 'backend']:
                    scores[SearchIntent.IMPLEMENT] += 0.5
                elif task == 'testing':
                    scores[SearchIntent.TEST] += 1.0
                elif task == 'performance':
                    scores[SearchIntent.REFACTOR] += 0.7
                elif task == 'security':
                    scores[SearchIntent.DEBUG] += 0.3
                    scores[SearchIntent.IMPLEMENT] += 0.3
        
        return scores
    
    def get_intent_context(self, intent: SearchIntent) -> Dict[str, any]:
        """
        Get contextual information for a given intent
        
        Returns:
            Dict with intent-specific search strategies and enhancements
        """
        intent_context = {
            SearchIntent.IMPLEMENT: {
                'search_focus': ['examples', 'patterns', 'templates', 'similar implementations'],
                'boost_factors': ['working_examples', 'complete_implementations', 'recent_code'],
                'include_dependencies': True,
                'prefer_languages': True,
                'search_depth': 'deep'
            },
            SearchIntent.DEBUG: {
                'search_focus': ['error_handling', 'edge_cases', 'fixes', 'known_issues'],
                'boost_factors': ['error_patterns', 'exception_handling', 'defensive_code'],
                'include_dependencies': True,
                'prefer_languages': True,
                'search_depth': 'moderate'
            },
            SearchIntent.UNDERSTAND: {
                'search_focus': ['documentation', 'comments', 'high_level_overview', 'architecture'],
                'boost_factors': ['well_documented', 'clear_structure', 'design_patterns'],
                'include_dependencies': False,
                'prefer_languages': False,
                'search_depth': 'shallow'
            },
            SearchIntent.REFACTOR: {
                'search_focus': ['best_practices', 'clean_code', 'performance', 'patterns'],
                'boost_factors': ['quality_metrics', 'recent_refactors', 'optimized_code'],
                'include_dependencies': True,
                'prefer_languages': True,
                'search_depth': 'moderate'
            },
            SearchIntent.TEST: {
                'search_focus': ['test_examples', 'test_patterns', 'mocking', 'assertions'],
                'boost_factors': ['test_coverage', 'test_frameworks', 'test_utilities'],
                'include_dependencies': True,
                'prefer_languages': True,
                'search_depth': 'moderate'
            },
            SearchIntent.DOCUMENT: {
                'search_focus': ['docstrings', 'comments', 'readme', 'api_docs'],
                'boost_factors': ['documentation_quality', 'examples', 'clarity'],
                'include_dependencies': False,
                'prefer_languages': False,
                'search_depth': 'shallow'
            }
        }
        
        return intent_context.get(intent, {})
    
    def suggest_query_improvements(self, query: str, intent: SearchIntent) -> List[str]:
        """
        Suggest improvements to the query based on detected intent
        
        Args:
            query: Original query
            intent: Detected intent
            
        Returns:
            List of suggested query improvements
        """
        suggestions = []
        query_lower = query.lower()
        
        # Intent-specific suggestions
        if intent == SearchIntent.IMPLEMENT:
            if 'example' not in query_lower:
                suggestions.append(f"{query} example implementation")
            if 'pattern' not in query_lower:
                suggestions.append(f"{query} design pattern")
            if not any(lang in query_lower for lang in ['python', 'javascript', 'java', 'go', 'rust']):
                suggestions.append(f"{query} [specify language]")
                
        elif intent == SearchIntent.DEBUG:
            if 'error' not in query_lower and 'exception' not in query_lower:
                suggestions.append(f"{query} error handling")
            if 'fix' not in query_lower:
                suggestions.append(f"fix {query}")
            suggestions.append(f"{query} common issues")
            
        elif intent == SearchIntent.UNDERSTAND:
            if 'how' not in query_lower and 'what' not in query_lower:
                suggestions.append(f"how does {query} work")
            suggestions.append(f"{query} explanation")
            suggestions.append(f"{query} documentation")
            
        elif intent == SearchIntent.REFACTOR:
            suggestions.append(f"{query} best practices")
            suggestions.append(f"optimize {query}")
            suggestions.append(f"{query} clean code")
            
        elif intent == SearchIntent.TEST:
            if 'unit' not in query_lower and 'integration' not in query_lower:
                suggestions.append(f"{query} unit test")
            suggestions.append(f"{query} test examples")
            suggestions.append(f"mock {query}")
            
        elif intent == SearchIntent.DOCUMENT:
            suggestions.append(f"{query} documentation template")
            suggestions.append(f"{query} docstring example")
            suggestions.append(f"{query} API documentation")
        
        return suggestions[:3]  # Return top 3 suggestions
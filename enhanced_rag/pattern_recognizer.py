"""
DEPRECATED: Use enhanced_rag.pattern_registry instead
Pattern recognizer for code understanding - Legacy file for compatibility
"""

import logging
from typing import Dict, List, Optional, Any
import re

logger = logging.getLogger(__name__)


class PatternRecognizer:
    """
    Stub implementation of pattern recognizer for code analysis
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.patterns = self._initialize_patterns()

    def _initialize_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Initialize common code patterns"""
        return {
            'error_handling': [
                re.compile(r'try\s*:\s*.*except', re.DOTALL),
                re.compile(r'if\s+.*error.*:', re.IGNORECASE),
                re.compile(r'raise\s+\w+Error'),
            ],
            'validation': [
                re.compile(r'if\s+not\s+.*:\s*raise'),
                re.compile(r'assert\s+.*'),
                re.compile(r'validate_\w+'),
            ],
            'initialization': [
                re.compile(r'def\s+__init__\s*\('),
                re.compile(r'self\.\w+\s*='),
                re.compile(r'super\(\).__init__'),
            ],
            'api_endpoint': [
                re.compile(r'@app\.(get|post|put|delete)\('),
                re.compile(r'@router\.(get|post|put|delete)\('),
                re.compile(r'async\s+def\s+\w+.*request'),
            ],
            'test_pattern': [
                re.compile(r'def\s+test_\w+'),
                re.compile(r'@pytest\.'),
                re.compile(r'assert\s+.*=='),
            ]
        }

    def recognize_patterns(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Recognize patterns in code and return confidence scores

        Args:
            code: Code snippet to analyze
            context: Additional context

        Returns:
            Dict mapping pattern names to confidence scores (0-1)
        """
        pattern_scores = {}

        for pattern_name, patterns in self.patterns.items():
            score = 0.0
            matches = 0

            for pattern in patterns:
                if pattern.search(code):
                    matches += 1

            if patterns:
                score = matches / len(patterns)

            pattern_scores[pattern_name] = min(score, 1.0)

        return pattern_scores

    def get_dominant_pattern(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Get the most dominant pattern in the code"""
        scores = self.recognize_patterns(code, context)

        if not scores:
            return None

        # Return pattern with highest score
        return max(scores.items(), key=lambda x: x[1])[0]

    def extract_pattern_context(
        self,
        code: str,
        pattern_type: str
    ) -> List[str]:
        """Extract specific context for a pattern type"""
        contexts = []

        if pattern_type not in self.patterns:
            return contexts

        for pattern in self.patterns[pattern_type]:
            matches = pattern.findall(code)
            contexts.extend(matches)

        return contexts

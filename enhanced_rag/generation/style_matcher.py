"""
Style matching engine that analyzes and applies coding styles
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass

from ..core.models import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class StyleProfile:
    """Represents a coding style profile"""
    language: str
    indentation: str  # 'spaces' or 'tabs'
    indent_size: int
    quote_style: str  # 'single', 'double', or 'mixed'
    naming_convention: Dict[str, str]  # function, variable, class naming styles
    line_length: int
    trailing_comma: bool
    semicolons: bool  # For JS/TS
    brace_style: str  # 'same-line' or 'new-line'
    blank_lines: Dict[str, int]  # before/after functions, classes, etc.
    comment_style: str  # 'inline', 'block', 'docstring'
    import_style: str  # 'grouped', 'alphabetical', 'by-type'
    space_around_operators: bool
    space_after_keywords: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'language': self.language,
            'indentation': self.indentation,
            'indent_size': self.indent_size,
            'quote_style': self.quote_style,
            'naming_convention': self.naming_convention,
            'line_length': self.line_length,
            'trailing_comma': self.trailing_comma,
            'semicolons': self.semicolons,
            'brace_style': self.brace_style,
            'blank_lines': self.blank_lines,
            'comment_style': self.comment_style,
            'import_style': self.import_style,
            'space_around_operators': self.space_around_operators,
            'space_after_keywords': self.space_after_keywords
        }


class StyleMatcher:
    """
    Analyzes code style from examples and applies consistent formatting
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize style matcher"""
        self.config = config or {}
        
        # Default style profiles by language
        self.default_styles = self._initialize_default_styles()
        
        # Style detection patterns
        self.detection_patterns = self._initialize_detection_patterns()
    
    def _initialize_default_styles(self) -> Dict[str, StyleProfile]:
        """Initialize default style profiles for each language"""
        return {
            'python': StyleProfile(
                language='python',
                indentation='spaces',
                indent_size=4,
                quote_style='single',
                naming_convention={
                    'function': 'snake_case',
                    'variable': 'snake_case',
                    'class': 'PascalCase',
                    'constant': 'UPPER_SNAKE_CASE'
                },
                line_length=79,
                trailing_comma=True,
                semicolons=False,
                brace_style='same-line',
                blank_lines={'before_function': 2, 'before_class': 2, 'after_imports': 2},
                comment_style='docstring',
                import_style='grouped',
                space_around_operators=True,
                space_after_keywords=True
            ),
            'javascript': StyleProfile(
                language='javascript',
                indentation='spaces',
                indent_size=2,
                quote_style='single',
                naming_convention={
                    'function': 'camelCase',
                    'variable': 'camelCase',
                    'class': 'PascalCase',
                    'constant': 'UPPER_SNAKE_CASE'
                },
                line_length=100,
                trailing_comma=True,
                semicolons=True,
                brace_style='same-line',
                blank_lines={'before_function': 1, 'before_class': 1, 'after_imports': 1},
                comment_style='inline',
                import_style='grouped',
                space_around_operators=True,
                space_after_keywords=True
            ),
            'typescript': StyleProfile(
                language='typescript',
                indentation='spaces',
                indent_size=2,
                quote_style='single',
                naming_convention={
                    'function': 'camelCase',
                    'variable': 'camelCase',
                    'class': 'PascalCase',
                    'interface': 'PascalCase',
                    'type': 'PascalCase',
                    'constant': 'UPPER_SNAKE_CASE'
                },
                line_length=100,
                trailing_comma=True,
                semicolons=True,
                brace_style='same-line',
                blank_lines={'before_function': 1, 'before_class': 1, 'after_imports': 1},
                comment_style='inline',
                import_style='grouped',
                space_around_operators=True,
                space_after_keywords=True
            )
        }
    
    def _initialize_detection_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize patterns for style detection"""
        return {
            'indentation': {
                'tabs': re.compile(r'^\t+', re.MULTILINE),
                'spaces': re.compile(r'^[ ]+', re.MULTILINE),
                'size': re.compile(r'^( +)', re.MULTILINE)
            },
            'quotes': {
                'single': re.compile(r"'[^']*'"),
                'double': re.compile(r'"[^"]*"')
            },
            'naming': {
                'snake_case': re.compile(r'\b[a-z]+(?:_[a-z]+)*\b'),
                'camelCase': re.compile(r'\b[a-z][a-zA-Z0-9]*\b'),
                'PascalCase': re.compile(r'\b[A-Z][a-zA-Z0-9]*\b'),
                'UPPER_SNAKE_CASE': re.compile(r'\b[A-Z]+(?:_[A-Z]+)*\b')
            },
            'semicolons': re.compile(r';$', re.MULTILINE),
            'trailing_comma': re.compile(r',\s*[\]\}\)]', re.MULTILINE),
            'brace_style': {
                'same_line': re.compile(r'\)\s*{'),
                'new_line': re.compile(r'\)\s*\n\s*{')
            },
            'operators': {
                'spaced': re.compile(r'\s+[+\-*/%=<>!&|]+\s+'),
                'unspaced': re.compile(r'[a-zA-Z0-9][+\-*/%=<>!&|]+[a-zA-Z0-9]')
            }
        }
    
    async def analyze_style(
        self,
        examples: List[SearchResult],
        language: str
    ) -> Dict[str, Any]:
        """
        Analyze coding style from examples
        
        Args:
            examples: Code examples to analyze
            language: Programming language
            
        Returns:
            Style analysis results
        """
        if not examples:
            # Return default style for language
            default = self.default_styles.get(language.lower())
            if default:
                return {
                    'profile': default.to_dict(),
                    'consistency_score': 1.0,
                    'detected_from_examples': False
                }
            return {'error': f'No default style for {language}'}
        
        # Analyze each example
        style_features = defaultdict(Counter)
        
        for example in examples[:20]:  # Analyze top 20 examples
            # Prefer canonical 'code_snippet'; fallback to legacy 'content' and dict-shaped examples for backwards compatibility
            code_sample = getattr(example, "code_snippet", None) or getattr(example, "content", None)
            if code_sample is None and isinstance(example, dict):
                code_sample = example.get("code_snippet") or example.get("content")
            code_sample = code_sample or ""
            features = self._extract_style_features(code_sample, language)
            
            for feature_type, feature_value in features.items():
                style_features[feature_type][feature_value] += 1
        
        # Build style profile from most common features
        profile = self._build_style_profile(style_features, language)
        
        # Calculate consistency score
        consistency = self._calculate_consistency(style_features)
        
        return {
            'profile': profile.to_dict(),
            'consistency_score': consistency,
            'detected_from_examples': True,
            'sample_count': len(examples)
        }
    
    def _extract_style_features(
        self,
        code: str,
        language: str
    ) -> Dict[str, Any]:
        """Extract style features from code"""
        features = {}
        
        # Indentation
        indent_matches = self.detection_patterns['indentation']['spaces'].findall(code)
        if indent_matches:
            features['indentation'] = 'spaces'
            # Find most common indent size
            sizes = [len(match) for match in indent_matches]
            if sizes:
                features['indent_size'] = max(set(sizes), key=sizes.count)
        elif self.detection_patterns['indentation']['tabs'].search(code):
            features['indentation'] = 'tabs'
            features['indent_size'] = 1
        
        # Quote style
        single_quotes = len(self.detection_patterns['quotes']['single'].findall(code))
        double_quotes = len(self.detection_patterns['quotes']['double'].findall(code))
        
        if single_quotes > double_quotes:
            features['quote_style'] = 'single'
        elif double_quotes > single_quotes:
            features['quote_style'] = 'double'
        else:
            features['quote_style'] = 'mixed'
        
        # Semicolons (JS/TS)
        if language.lower() in ['javascript', 'typescript']:
            semicolons = self.detection_patterns['semicolons'].findall(code)
            features['semicolons'] = len(semicolons) > 5  # Threshold
        
        # Trailing commas
        trailing_commas = self.detection_patterns['trailing_comma'].findall(code)
        features['trailing_comma'] = len(trailing_commas) > 2
        
        # Brace style
        same_line = len(self.detection_patterns['brace_style']['same_line'].findall(code))
        new_line = len(self.detection_patterns['brace_style']['new_line'].findall(code))
        features['brace_style'] = 'same-line' if same_line >= new_line else 'new-line'
        
        # Operator spacing
        spaced = len(self.detection_patterns['operators']['spaced'].findall(code))
        unspaced = len(self.detection_patterns['operators']['unspaced'].findall(code))
        features['space_around_operators'] = spaced > unspaced
        
        # Line length (approximate)
        lines = code.split('\n')
        if lines:
            features['line_length'] = max(len(line) for line in lines)
        
        # Naming conventions
        features['naming'] = self._detect_naming_conventions(code, language)
        
        return features
    
    def _detect_naming_conventions(
        self,
        code: str,
        language: str
    ) -> Dict[str, str]:
        """Detect naming conventions used in code"""
        conventions = {}
        
        if language.lower() == 'python':
            # Function names
            func_names = re.findall(r'def\s+(\w+)', code)
            if func_names:
                conventions['function'] = self._identify_naming_style(func_names)
            
            # Class names
            class_names = re.findall(r'class\s+(\w+)', code)
            if class_names:
                conventions['class'] = self._identify_naming_style(class_names)
        
        elif language.lower() in ['javascript', 'typescript']:
            # Function names
            func_names = re.findall(r'function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s+)?function', code)
            func_names = [n[0] or n[1] for n in func_names if n[0] or n[1]]
            if func_names:
                conventions['function'] = self._identify_naming_style(func_names)
            
            # Class names
            class_names = re.findall(r'class\s+(\w+)', code)
            if class_names:
                conventions['class'] = self._identify_naming_style(class_names)
            
            # TypeScript interfaces
            if language.lower() == 'typescript':
                interface_names = re.findall(r'interface\s+(\w+)', code)
                if interface_names:
                    conventions['interface'] = self._identify_naming_style(interface_names)
        
        return conventions
    
    def _identify_naming_style(self, names: List[str]) -> str:
        """Identify the naming style from a list of names"""
        if not names:
            return 'unknown'
        
        style_counts = Counter()
        
        for name in names:
            if '_' in name and name.islower():
                style_counts['snake_case'] += 1
            elif '_' in name and name.isupper():
                style_counts['UPPER_SNAKE_CASE'] += 1
            elif name[0].islower() and any(c.isupper() for c in name[1:]):
                style_counts['camelCase'] += 1
            elif name[0].isupper() and not name.isupper():
                style_counts['PascalCase'] += 1
        
        if style_counts:
            return style_counts.most_common(1)[0][0]
        
        return 'unknown'
    
    def _build_style_profile(
        self,
        style_features: Dict[str, Counter],
        language: str
    ) -> StyleProfile:
        """Build style profile from analyzed features"""
        # Start with default profile
        profile = self.default_styles.get(
            language.lower(),
            self.default_styles['python']
        )
        
        # Override with detected features
        if 'indentation' in style_features:
            most_common = style_features['indentation'].most_common(1)
            if most_common:
                profile.indentation = most_common[0][0]
        
        if 'indent_size' in style_features:
            most_common = style_features['indent_size'].most_common(1)
            if most_common:
                profile.indent_size = most_common[0][0]
        
        if 'quote_style' in style_features:
            most_common = style_features['quote_style'].most_common(1)
            if most_common:
                profile.quote_style = most_common[0][0]
        
        if 'semicolons' in style_features:
            most_common = style_features['semicolons'].most_common(1)
            if most_common:
                profile.semicolons = most_common[0][0]
        
        if 'trailing_comma' in style_features:
            most_common = style_features['trailing_comma'].most_common(1)
            if most_common:
                profile.trailing_comma = most_common[0][0]
        
        if 'brace_style' in style_features:
            most_common = style_features['brace_style'].most_common(1)
            if most_common:
                profile.brace_style = most_common[0][0]
        
        if 'space_around_operators' in style_features:
            most_common = style_features['space_around_operators'].most_common(1)
            if most_common:
                profile.space_around_operators = most_common[0][0]
        
        if 'line_length' in style_features:
            # Use 90th percentile for line length
            lengths = []
            for length, count in style_features['line_length'].items():
                lengths.extend([length] * count)
            if lengths:
                lengths.sort()
                percentile_90 = lengths[int(len(lengths) * 0.9)]
                profile.line_length = min(percentile_90, 120)  # Cap at 120
        
        if 'naming' in style_features:
            for category, style in style_features['naming'].most_common():
                if isinstance(style, dict):
                    profile.naming_convention.update(style)
        
        return profile
    
    def _calculate_consistency(self, style_features: Dict[str, Counter]) -> float:
        """Calculate style consistency score"""
        if not style_features:
            return 0.0
        
        consistency_scores = []
        
        for feature_type, counter in style_features.items():
            if not counter:
                continue
            
            total = sum(counter.values())
            if total == 0:
                continue
            
            # Calculate entropy (lower = more consistent)
            entropy = 0.0
            for count in counter.values():
                if count > 0:
                    prob = count / total
                    entropy -= prob * (prob if prob > 0 else 0)
            
            # Convert entropy to consistency score (1 = perfectly consistent)
            max_entropy = -(1/len(counter)) * len(counter) if len(counter) > 1 else 0
            consistency = 1.0 - (entropy / max_entropy) if max_entropy > 0 else 1.0
            
            consistency_scores.append(consistency)
        
        return sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0.0
    
    async def apply_style(
        self,
        code: str,
        style_info: Dict[str, Any]
    ) -> str:
        """
        Apply style formatting to code
        
        Args:
            code: Code to format
            style_info: Style information from analyze_style
            
        Returns:
            Formatted code
        """
        if 'error' in style_info:
            return code  # Return unchanged
        
        profile_dict = style_info.get('profile', {})
        if not profile_dict:
            return code
        
        # Convert dict back to StyleProfile
        profile = StyleProfile(**profile_dict)
        
        # Apply formatting rules
        formatted = code
        
        # Fix indentation
        if profile.indentation == 'spaces':
            formatted = self._convert_to_spaces(formatted, profile.indent_size)
        elif profile.indentation == 'tabs':
            formatted = self._convert_to_tabs(formatted)
        
        # Fix quotes (simple replacement - be careful with escaping)
        if profile.quote_style == 'single':
            formatted = self._convert_quotes(formatted, 'single')
        elif profile.quote_style == 'double':
            formatted = self._convert_quotes(formatted, 'double')
        
        # Add/remove semicolons (JS/TS)
        if profile.language.lower() in ['javascript', 'typescript']:
            if profile.semicolons:
                formatted = self._add_semicolons(formatted)
            else:
                formatted = self._remove_semicolons(formatted)
        
        # Fix operator spacing
        if profile.space_around_operators:
            formatted = self._add_operator_spacing(formatted)
        
        # Apply line length limit (wrap long lines)
        formatted = self._wrap_long_lines(formatted, profile.line_length)
        
        return formatted
    
    def _convert_to_spaces(self, code: str, indent_size: int) -> str:
        """Convert indentation to spaces"""
        lines = code.split('\n')
        formatted_lines = []
        
        for line in lines:
            # Count leading tabs/spaces
            indent_level = 0
            i = 0
            while i < len(line):
                if line[i] == '\t':
                    indent_level += 1
                    i += 1
                elif line[i] == ' ':
                    # Count spaces as partial indent
                    space_count = 0
                    while i < len(line) and line[i] == ' ':
                        space_count += 1
                        i += 1
                    indent_level += space_count / indent_size
                else:
                    break
            
            # Rebuild line with correct indentation
            indent_level = int(indent_level)
            formatted_line = ' ' * (indent_level * indent_size) + line[i:]
            formatted_lines.append(formatted_line)
        
        return '\n'.join(formatted_lines)
    
    def _convert_to_tabs(self, code: str) -> str:
        """Convert indentation to tabs"""
        lines = code.split('\n')
        formatted_lines = []
        
        for line in lines:
            # Count leading spaces
            space_count = 0
            for char in line:
                if char == ' ':
                    space_count += 1
                else:
                    break
            
            # Assume 4 spaces = 1 tab (common default)
            tab_count = space_count // 4
            formatted_line = '\t' * tab_count + line[space_count:]
            formatted_lines.append(formatted_line)
        
        return '\n'.join(formatted_lines)
    
    def _convert_quotes(self, code: str, style: str) -> str:
        """Convert quote style (simple implementation)"""
        # This is a simplified version - in production, use a proper parser
        if style == 'single':
            # Convert double to single (careful with escaping)
            code = re.sub(r'"([^"]*)"', r"'\1'", code)
        elif style == 'double':
            # Convert single to double
            code = re.sub(r"'([^']*)'", r'"\1"', code)
        
        return code
    
    def _add_semicolons(self, code: str) -> str:
        """Add semicolons to JavaScript/TypeScript code"""
        lines = code.split('\n')
        formatted_lines = []
        
        for line in lines:
            stripped = line.rstrip()
            # Add semicolon if line ends with certain patterns
            if (stripped and 
                not stripped.endswith((';', '{', '}', ',', '//', '/*')) and
                not stripped.strip().startswith(('//', '/*', '*'))):
                
                # Check if it's a complete statement
                if any(stripped.strip().startswith(kw) for kw in ['const', 'let', 'var', 'return', 'throw']):
                    line = stripped + ';' + line[len(stripped):]
            
            formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    def _remove_semicolons(self, code: str) -> str:
        """Remove semicolons from JavaScript/TypeScript code"""
        # Remove semicolons at end of lines (except in for loops)
        return re.sub(r';(\s*)$', r'\1', code, flags=re.MULTILINE)
    
    def _add_operator_spacing(self, code: str) -> str:
        """Add spacing around operators"""
        # Simple implementation - add spaces around common operators
        operators = ['+', '-', '*', '/', '%', '=', '<', '>', '&', '|', '!']
        
        for op in operators:
            # Skip if already spaced
            if f' {op} ' not in code:
                # Add spaces (careful with edge cases like ++ or --)
                if op not in ['+', '-'] or f'{op}{op}' not in code:
                    code = re.sub(rf'([a-zA-Z0-9_\)\]])({re.escape(op)})([a-zA-Z0-9_\(\[])', 
                                 rf'\1 \2 \3', code)
        
        return code
    
    def _wrap_long_lines(self, code: str, max_length: int) -> str:
        """Wrap long lines (simple implementation)"""
        lines = code.split('\n')
        formatted_lines = []
        
        for line in lines:
            if len(line) <= max_length:
                formatted_lines.append(line)
            else:
                # Simple wrapping at commas or operators
                # This is a very basic implementation
                formatted_lines.append(line)  # For now, don't wrap
        
        return '\n'.join(formatted_lines)
    
    def merge_styles(
        self,
        detected_style: Dict[str, Any],
        user_style_guide: Optional[str]
    ) -> Dict[str, Any]:
        """
        Merge detected style with user preferences
        
        Args:
            detected_style: Style detected from examples
            user_style_guide: User-provided style guide
            
        Returns:
            Merged style information
        """
        if not user_style_guide:
            return detected_style
        
        # Parse user style guide (simple key=value format)
        user_prefs = {}
        for line in user_style_guide.split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip().lower()
                value = value.strip()
                
                # Convert string values to appropriate types
                if value.lower() in ['true', 'false']:
                    value = value.lower() == 'true'
                elif value.isdigit():
                    value = int(value)
                
                user_prefs[key] = value
        
        # Override detected style with user preferences
        merged = detected_style.copy()
        if 'profile' in merged and user_prefs:
            for key, value in user_prefs.items():
                if key in merged['profile']:
                    merged['profile'][key] = value
        
        return merged
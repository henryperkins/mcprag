"""
Multi-Variant Query Rewriter
Generates multiple query variants for comprehensive search
"""

import re
import logging
from typing import List, Dict, Set, Optional, Tuple
from itertools import combinations, permutations
from collections import defaultdict

# Make NLTK optional
try:
    import nltk
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False
    nltk = None

from ..core.models import SearchIntent, CodeContext
from ..core.config import get_config
from .lexicon import (
    QUERY_TEMPLATES,
    VERB_VARIATIONS,
    NOUN_VARIATIONS,
    QUESTION_TRANSFORMS
)

logger = logging.getLogger(__name__)

# Download required NLTK data (if available and not already present)
if NLTK_AVAILABLE:
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
    
    try:
        nltk.data.find('taggers/averaged_perceptron_tagger')
    except LookupError:
        nltk.download('averaged_perceptron_tagger', quiet=True)


class MultiVariantQueryRewriter:
    """
    Generates multiple query variants using various techniques:
    - Syntactic variations (word order, phrasing)
    - Semantic variations (synonyms, related terms)
    - Structural variations (questions, statements, commands)
    - Technical variations (camelCase, snake_case, abbreviations)
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._initialize_rewriter()
    
    def _initialize_rewriter(self):
        """Initialize rewriting resources"""
        
        # Import from centralized lexicon
        self.query_templates = QUERY_TEMPLATES
        self.verb_variations = VERB_VARIATIONS
        self.noun_variations = NOUN_VARIATIONS
        self.question_transforms = QUESTION_TRANSFORMS
        
        # Technical term variations (kept local as they use methods)
        self.case_variations = {
            'camelCase': self._to_camel_case,
            'PascalCase': self._to_pascal_case,
            'snake_case': self._to_snake_case,
            'kebab-case': self._to_kebab_case,
            'UPPER_CASE': self._to_upper_case,
        }
    
    async def rewrite_query(
        self,
        query: str,
        intent: Optional[SearchIntent] = None,
        context: Optional[CodeContext] = None,
        max_variants: int = 10
    ) -> List[str]:
        """
        Generate multiple query variants
        
        Args:
            query: Original query
            intent: Optional detected intent
            context: Optional code context
            max_variants: Maximum number of variants to generate
            
        Returns:
            List of query variants
        """
        variants = set()
        variants.add(query)  # Always include original
        
        # Clean and tokenize query
        query_clean = self._clean_query(query)
        if NLTK_AVAILABLE:
            tokens = nltk.word_tokenize(query_clean)
            pos_tags = nltk.pos_tag(tokens)
        else:
            # Fallback: simple split
            tokens = query_clean.split()
            pos_tags = [(token, 'NN') for token in tokens]
        
        # Apply different rewriting strategies
        
        # 1. Syntactic variations
        syntactic_variants = self._generate_syntactic_variants(query_clean, pos_tags)
        variants.update(syntactic_variants)
        
        # 2. Semantic variations
        semantic_variants = self._generate_semantic_variants(query_clean, tokens)
        variants.update(semantic_variants)
        
        # 3. Template-based variations
        template_variants = self._generate_template_variants(query_clean, intent)
        variants.update(template_variants)
        
        # 4. Technical variations
        technical_variants = self._generate_technical_variants(query_clean)
        variants.update(technical_variants)
        
        # 5. Context-aware variations
        if context:
            context_variants = await self._generate_context_variants(query_clean, context)
            variants.update(context_variants)
        
        # 6. Intent-specific variations
        if intent:
            intent_variants = self._generate_intent_variants(query_clean, intent)
            variants.update(intent_variants)
        
        # Filter and rank variants
        filtered_variants = self._filter_variants(list(variants), query)
        ranked_variants = self._rank_variants(filtered_variants, query, intent)
        
        return ranked_variants[:max_variants]
    
    def _generate_syntactic_variants(self, query: str, pos_tags: List[Tuple[str, str]]) -> Set[str]:
        """Generate syntactic variations of the query"""
        variants = set()
        
        # 1. Word order variations (for short queries)
        words = query.split()
        if 2 <= len(words) <= 5:
            # Try swapping adjacent non-stopword pairs
            for i in range(len(words) - 1):
                if not self._is_stopword(words[i]) and not self._is_stopword(words[i + 1]):
                    swapped = words.copy()
                    swapped[i], swapped[i + 1] = swapped[i + 1], swapped[i]
                    variants.add(' '.join(swapped))
        
        # 2. Question to statement conversion
        if query.startswith(('how', 'what', 'why', 'when', 'where')):
            statement = self._question_to_statement(query)
            if statement:
                variants.add(statement)
        
        # 3. Statement to question conversion
        elif not query.endswith('?'):
            question = self._statement_to_question(query)
            if question:
                variants.add(question)
        
        # 4. Active/passive voice (simplified)
        if any(tag.startswith('VB') for _, tag in pos_tags):
            passive = self._to_passive_voice(query, pos_tags)
            if passive:
                variants.add(passive)
        
        # 5. Gerund form variations
        for word, tag in pos_tags:
            if tag.startswith('VB') and not tag.endswith('G'):
                gerund = self._to_gerund_form(query, word)
                if gerund:
                    variants.add(gerund)
        
        return variants
    
    def _generate_semantic_variants(self, query: str, tokens: List[str]) -> Set[str]:
        """Generate semantic variations using synonyms"""
        variants = set()
        
        # Replace verbs with synonyms
        for i, token in enumerate(tokens):
            token_lower = token.lower()
            if token_lower in self.verb_variations:
                for synonym in self.verb_variations[token_lower][:3]:  # Top 3 synonyms
                    if synonym != token_lower:
                        variant_tokens = tokens.copy()
                        variant_tokens[i] = synonym
                        variants.add(' '.join(variant_tokens))
        
        # Replace nouns with synonyms
        for i, token in enumerate(tokens):
            token_lower = token.lower()
            if token_lower in self.noun_variations:
                for synonym in self.noun_variations[token_lower][:3]:  # Top 3 synonyms
                    if synonym != token_lower:
                        variant_tokens = tokens.copy()
                        variant_tokens[i] = synonym
                        variants.add(' '.join(variant_tokens))
        
        # Combine verb and noun replacements (limited combinations)
        verb_indices = [i for i, t in enumerate(tokens) if t.lower() in self.verb_variations]
        noun_indices = [i for i, t in enumerate(tokens) if t.lower() in self.noun_variations]
        
        if verb_indices and noun_indices:
            # Just one combination to avoid explosion
            variant_tokens = tokens.copy()
            if verb_indices:
                verb_idx = verb_indices[0]
                verb = tokens[verb_idx].lower()
                if verb in self.verb_variations:
                    variant_tokens[verb_idx] = self.verb_variations[verb][0]
            if noun_indices:
                noun_idx = noun_indices[0]
                noun = tokens[noun_idx].lower()
                if noun in self.noun_variations:
                    variant_tokens[noun_idx] = self.noun_variations[noun][0]
            variants.add(' '.join(variant_tokens))
        
        return variants
    
    def _generate_template_variants(self, query: str, intent: Optional[SearchIntent]) -> Set[str]:
        """Generate variations using query templates"""
        variants = set()
        
        # Try to extract action and object from query
        action, obj = self._extract_action_object(query)
        
        if action and obj:
            # Apply how_to templates
            if any(word in query.lower() for word in ['how', 'implement', 'create', 'build']):
                for template in self.query_templates['how_to']:
                    variant = template.format(action=action, object=obj)
                    variants.add(variant)
            
            # Apply implementation templates
            if intent == SearchIntent.IMPLEMENT or 'implement' in query.lower():
                for template in self.query_templates['implementation']:
                    variant = template.format(feature=obj)
                    variants.add(variant)
        
        # Extract concept for what_is templates
        concept = self._extract_concept(query)
        if concept:
            if 'what' in query.lower() or intent == SearchIntent.UNDERSTAND:
                for template in self.query_templates['what_is']:
                    variant = template.format(concept=concept)
                    variants.add(variant)
        
        # Extract error for debugging templates
        error = self._extract_error(query)
        if error:
            if intent == SearchIntent.DEBUG or any(word in query.lower() for word in ['error', 'fix', 'debug']):
                for template in self.query_templates['debugging']:
                    variant = template.format(error=error)
                    variants.add(variant)
        
        return variants
    
    def _generate_technical_variants(self, query: str) -> Set[str]:
        """Generate technical variations (case styles, abbreviations)"""
        variants = set()
        
        # Apply case variations to multi-word terms
        words = query.split()
        for i in range(len(words) - 1):
            # Check for potential multi-word terms
            term = f"{words[i]} {words[i + 1]}"
            if self._is_technical_term(term):
                # Apply different case styles
                for style_name, style_func in self.case_variations.items():
                    styled_term = style_func(term)
                    variant = query.replace(term, styled_term)
                    variants.add(variant)
        
        # Handle single word technical terms
        for word in words:
            if self._is_technical_term(word) and len(word) > 3:
                for style_name, style_func in self.case_variations.items():
                    styled_word = style_func(word)
                    if styled_word != word:
                        variant = query.replace(word, styled_word)
                        variants.add(variant)
        
        # Add common abbreviations/expansions
        abbreviations = {
            'authentication': 'auth',
            'authorization': 'authz',
            'database': 'db',
            'application': 'app',
            'configuration': 'config',
            'environment': 'env',
            'development': 'dev',
            'production': 'prod',
            'repository': 'repo',
        }
        
        for full, abbrev in abbreviations.items():
            if full in query.lower():
                variants.add(query.lower().replace(full, abbrev))
            if abbrev in query.lower():
                variants.add(query.lower().replace(abbrev, full))
        
        return variants
    
    async def _generate_context_variants(self, query: str, context: CodeContext) -> Set[str]:
        """Generate variants based on code context"""
        variants = set()
        
        # Add language-specific variants
        if context.language:
            lang_variant = f"{query} {context.language}"
            variants.add(lang_variant)
            
            # Language-specific syntax
            if context.language.lower() == 'python':
                variants.add(f"{query} python syntax")
            elif context.language.lower() in ['javascript', 'typescript']:
                variants.add(f"{query} javascript ES6")
        
        # Add framework-specific variants
        if context.framework:
            framework_variant = f"{query} {context.framework}"
            variants.add(framework_variant)
            
            # Framework-specific patterns
            framework_patterns = {
                'django': ['django orm', 'django views', 'django models'],
                'react': ['react hooks', 'react component', 'react state'],
                'spring': ['spring boot', 'spring bean', 'spring mvc'],
            }
            
            if context.framework.lower() in framework_patterns:
                for pattern in framework_patterns[context.framework.lower()]:
                    if pattern not in query.lower():
                        variants.add(f"{query} {pattern}")
        
        # Add variants based on imports
        if context.imports:
            # Find most relevant imports
            relevant_imports = self._find_relevant_imports(query, context.imports)
            for imp in relevant_imports[:2]:  # Top 2 imports
                import_name = imp.split('.')[-1]  # Get last part of import
                if import_name not in query:
                    variants.add(f"{query} {import_name}")
        
        return variants
    
    def _generate_intent_variants(self, query: str, intent: SearchIntent) -> Set[str]:
        """Generate variants specific to the detected intent"""
        variants = set()
        
        intent_keywords = {
            SearchIntent.IMPLEMENT: ['example', 'tutorial', 'how to', 'step by step'],
            SearchIntent.DEBUG: ['fix', 'solve', 'error', 'not working'],
            SearchIntent.UNDERSTAND: ['explanation', 'how does', 'what is', 'documentation'],
            SearchIntent.REFACTOR: ['best practice', 'improve', 'optimize', 'clean code'],
            SearchIntent.TEST: ['unit test', 'test case', 'mock', 'assertion'],
            SearchIntent.DOCUMENT: ['documentation', 'docstring', 'comment', 'example'],
        }
        
        keywords = intent_keywords.get(intent, [])
        for keyword in keywords:
            if keyword not in query.lower():
                variants.add(f"{query} {keyword}")
                variants.add(f"{keyword} {query}")
        
        return variants
    
    def _filter_variants(self, variants: List[str], original_query: str) -> List[str]:
        """Filter out low-quality variants"""
        filtered = []
        original_lower = original_query.lower()
        original_words = set(original_lower.split())
        
        for variant in variants:
            variant_lower = variant.lower()
            
            # Skip if too similar to original
            if variant_lower == original_lower:
                if variant != original_query:  # Keep if only case differs
                    filtered.append(variant)
                continue
            
            # Skip if too different (less than 50% word overlap)
            variant_words = set(variant_lower.split())
            overlap = len(original_words & variant_words)
            if overlap < len(original_words) * 0.5:
                continue
            
            # Skip if too long (more than 2x original length)
            if len(variant) > len(original_query) * 2:
                continue
            
            # Skip if contains repeated words
            words = variant_lower.split()
            if len(words) != len(set(words)):
                continue
            
            filtered.append(variant)
        
        return filtered
    
    def _rank_variants(
        self,
        variants: List[str],
        original_query: str,
        intent: Optional[SearchIntent]
    ) -> List[str]:
        """Rank variants by quality and relevance"""
        scored_variants = []
        
        for variant in variants:
            score = 0
            
            # Original query gets highest score
            if variant == original_query:
                score += 10
            
            # Prefer variants that maintain key terms
            key_terms = self._extract_key_terms(original_query)
            for term in key_terms:
                if term in variant.lower():
                    score += 2
            
            # Prefer variants with good structure
            if self._has_good_structure(variant):
                score += 1
            
            # Intent-specific scoring
            if intent:
                if self._matches_intent_pattern(variant, intent):
                    score += 3
            
            # Length penalty (prefer concise variants)
            length_ratio = len(variant) / len(original_query)
            if 0.8 <= length_ratio <= 1.2:
                score += 1
            elif length_ratio > 1.5:
                score -= 1
            
            scored_variants.append((variant, score))
        
        # Sort by score (descending) and return variants only
        scored_variants.sort(key=lambda x: x[1], reverse=True)
        return [variant for variant, _ in scored_variants]
    
    # Helper methods
    
    def _clean_query(self, query: str) -> str:
        """Clean and normalize query"""
        # Remove extra whitespace
        query = ' '.join(query.split())
        # Remove trailing punctuation (except ?)
        if query.endswith('.') or query.endswith('!'):
            query = query[:-1]
        return query
    
    def _is_stopword(self, word: str) -> bool:
        """Check if word is a stopword"""
        stopwords = {
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must',
            'can', 'this', 'that', 'these', 'those', 'i', 'you',
            'he', 'she', 'it', 'we', 'they', 'them', 'their',
            'what', 'which', 'who', 'when', 'where', 'why', 'how',
            'all', 'each', 'every', 'some', 'any', 'few', 'more',
            'most', 'other', 'such', 'only', 'own', 'same', 'so',
            'than', 'too', 'very', 'just', 'but', 'and', 'or',
            'if', 'then', 'else', 'when', 'at', 'by', 'for',
            'with', 'about', 'against', 'between', 'into', 'through',
            'during', 'before', 'after', 'above', 'below', 'to',
            'from', 'up', 'down', 'in', 'out', 'on', 'off',
            'over', 'under', 'again', 'further', 'once'
        }
        return word.lower() in stopwords
    
    def _is_technical_term(self, term: str) -> bool:
        """Check if term is a technical programming term"""
        technical_indicators = [
            # Patterns
            lambda t: '_' in t,  # snake_case
            lambda t: any(c.isupper() for c in t[1:]),  # camelCase or PascalCase
            lambda t: '-' in t,  # kebab-case
            lambda t: t.isupper() and len(t) > 2,  # CONSTANTS
            
            # Common technical terms
            lambda t: t.lower() in {
                'api', 'url', 'uri', 'http', 'sql', 'orm', 'mvc',
                'json', 'xml', 'yaml', 'csv', 'regex', 'auth',
                'crud', 'rest', 'graphql', 'websocket', 'ajax',
                'dom', 'css', 'html', 'jsx', 'tsx', 'cli', 'gui',
                'sdk', 'ide', 'ci', 'cd', 'tdd', 'bdd', 'dry',
                'solid', 'kiss', 'yagni', 'jwt', 'oauth', 'saml'
            }
        ]
        
        return any(check(term) for check in technical_indicators)
    
    def _to_camel_case(self, text: str) -> str:
        """Convert text to camelCase"""
        words = re.split(r'[\s_\-]+', text)
        if not words:
            return text
        return words[0].lower() + ''.join(w.capitalize() for w in words[1:])
    
    def _to_pascal_case(self, text: str) -> str:
        """Convert text to PascalCase"""
        words = re.split(r'[\s_\-]+', text)
        return ''.join(w.capitalize() for w in words)
    
    def _to_snake_case(self, text: str) -> str:
        """Convert text to snake_case"""
        # Handle camelCase
        text = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
        text = re.sub('([a-z0-9])([A-Z])', r'\1_\2', text)
        # Handle spaces and hyphens
        text = re.sub(r'[\s\-]+', '_', text)
        return text.lower()
    
    def _to_kebab_case(self, text: str) -> str:
        """Convert text to kebab-case"""
        # Handle camelCase
        text = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', text)
        text = re.sub('([a-z0-9])([A-Z])', r'\1-\2', text)
        # Handle spaces and underscores
        text = re.sub(r'[\s_]+', '-', text)
        return text.lower()
    
    def _to_upper_case(self, text: str) -> str:
        """Convert text to UPPER_CASE"""
        return self._to_snake_case(text).upper()
    
    def _question_to_statement(self, query: str) -> Optional[str]:
        """Convert question to statement form"""
        query_lower = query.lower()
        
        # How to X -> X tutorial/guide
        if query_lower.startswith('how to '):
            rest = query[7:]
            return f"{rest} tutorial"
        
        # What is X -> X explanation
        if query_lower.startswith('what is '):
            rest = query[8:]
            return f"{rest} explanation"
        
        # Why does X -> X reason
        if query_lower.startswith('why does '):
            rest = query[9:]
            return f"{rest} reason"
        
        return None
    
    def _statement_to_question(self, query: str) -> Optional[str]:
        """Convert statement to question form"""
        # Simple heuristic: add "how to" for action-like queries
        tokens = query.split()
        if tokens and tokens[0].lower() in self.verb_variations:
            return f"how to {query}"
        
        # Add "what is" for noun-like queries
        if tokens and tokens[0].lower() in self.noun_variations:
            return f"what is {query}"
        
        return None
    
    def _to_passive_voice(self, query: str, pos_tags: List[Tuple[str, str]]) -> Optional[str]:
        """Simple passive voice conversion (limited)"""
        # This is a very simplified implementation
        # Real passive voice conversion would require more sophisticated NLP
        return None
    
    def _to_gerund_form(self, query: str, verb: str) -> Optional[str]:
        """Convert verb to gerund form in query"""
        gerund = verb + 'ing'
        # Handle common cases
        if verb.endswith('e') and not verb.endswith('ee'):
            gerund = verb[:-1] + 'ing'
        elif verb.endswith('y') and len(verb) > 2 and verb[-2] not in 'aeiou':
            gerund = verb[:-1] + 'ying'
        
        return query.replace(verb, gerund)
    
    def _extract_action_object(self, query: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract action and object from query"""
        tokens = query.lower().split()
        
        # Find verb (action)
        action = None
        for token in tokens:
            if token in self.verb_variations:
                action = token
                break
        
        # Find noun (object) after action
        obj = None
        if action and action in tokens:
            action_idx = tokens.index(action)
            # Look for nouns after the action
            for i in range(action_idx + 1, len(tokens)):
                if not self._is_stopword(tokens[i]):
                    obj = tokens[i]
                    # Check if next word is also part of object
                    if i + 1 < len(tokens) and not self._is_stopword(tokens[i + 1]):
                        obj += ' ' + tokens[i + 1]
                    break
        
        return action, obj
    
    def _extract_concept(self, query: str) -> Optional[str]:
        """Extract main concept from query"""
        tokens = query.lower().split()
        
        # Remove question words and stopwords
        concept_tokens = []
        skip_words = {'what', 'is', 'are', 'how', 'does', 'do', 'the', 'a', 'an'}
        
        for token in tokens:
            if token not in skip_words and not self._is_stopword(token):
                concept_tokens.append(token)
        
        if concept_tokens:
            return ' '.join(concept_tokens[:2])  # Max 2 words
        
        return None
    
    def _extract_error(self, query: str) -> Optional[str]:
        """Extract error description from query"""
        query_lower = query.lower()
        
        # Look for error patterns
        error_patterns = [
            r'(?:error|exception):\s*(\w+)',
            r'(\w+)\s*(?:error|exception)',
            r'(?:fix|debug|resolve)\s+(\w+)',
        ]
        
        for pattern in error_patterns:
            match = re.search(pattern, query_lower)
            if match:
                return match.group(1)
        
        # Look for "not working" pattern
        if 'not working' in query_lower:
            tokens = query_lower.split()
            idx = tokens.index('not')
            if idx > 0:
                return tokens[idx - 1]
        
        return None
    
    def _find_relevant_imports(self, query: str, imports: List[str]) -> List[str]:
        """Find imports relevant to query"""
        query_lower = query.lower()
        relevant = []
        
        for imp in imports:
            imp_parts = imp.lower().split('.')
            # Check if any part of import is in query
            if any(part in query_lower for part in imp_parts if len(part) > 2):
                relevant.append(imp)
        
        return relevant[:3]  # Top 3
    
    def _extract_key_terms(self, query: str) -> List[str]:
        """Extract key terms from query"""
        tokens = query.lower().split()
        key_terms = []
        
        for token in tokens:
            # Skip stopwords and short words
            if not self._is_stopword(token) and len(token) > 2:
                # Prioritize technical terms
                if self._is_technical_term(token):
                    key_terms.insert(0, token)  # Add to front
                else:
                    key_terms.append(token)
        
        return key_terms[:5]  # Top 5 terms
    
    def _has_good_structure(self, query: str) -> bool:
        """Check if query has good grammatical structure"""
        # Simple heuristics
        tokens = query.split()
        
        # Good length
        if 2 <= len(tokens) <= 10:
            return True
        
        # Starts with question word
        if tokens[0].lower() in self.question_transforms:
            return True
        
        # Has verb-noun structure
        has_verb = any(token.lower() in self.verb_variations for token in tokens)
        has_noun = any(token.lower() in self.noun_variations for token in tokens)
        if has_verb and has_noun:
            return True
        
        return False
    
    def _matches_intent_pattern(self, query: str, intent: SearchIntent) -> bool:
        """Check if query matches intent-specific patterns"""
        query_lower = query.lower()
        
        intent_patterns = {
            SearchIntent.IMPLEMENT: [
                'how to', 'implement', 'create', 'build', 'example', 'tutorial'
            ],
            SearchIntent.DEBUG: [
                'error', 'fix', 'debug', 'not working', 'issue', 'problem'
            ],
            SearchIntent.UNDERSTAND: [
                'what is', 'how does', 'explain', 'understand', 'documentation'
            ],
            SearchIntent.REFACTOR: [
                'refactor', 'improve', 'optimize', 'best practice', 'clean'
            ],
            SearchIntent.TEST: [
                'test', 'unit test', 'mock', 'assert', 'coverage'
            ],
            SearchIntent.DOCUMENT: [
                'document', 'docstring', 'comment', 'readme', 'description'
            ]
        }
        
        patterns = intent_patterns.get(intent, [])
        return any(pattern in query_lower for pattern in patterns)
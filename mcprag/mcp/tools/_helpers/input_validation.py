"""Input validation for search operations."""

import re
from typing import Optional, List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

# Constants for validation
MAX_QUERY_LENGTH = 400
MAX_QUERY_WORDS = 50
MIN_QUERY_LENGTH = 1
MAX_RESULTS_LIMIT = 20
MIN_RESULTS_LIMIT = 1
MAX_SKIP_VALUE = 1000  # Reasonable limit for pagination
VALID_DETAIL_LEVELS = {"full", "compact", "ultra"}
VALID_ORDER_BY = {"relevance", "date", "path", "language"}
VALID_LANGUAGES = {
    "python", "javascript", "typescript", "java", "csharp", "cpp", "c",
    "go", "rust", "ruby", "php", "swift", "kotlin", "scala", "r",
    "matlab", "perl", "lua", "dart", "elixir", "clojure", "haskell",
    "ocaml", "fsharp", "vb", "powershell", "shell", "bash", "sql",
    "html", "css", "xml", "json", "yaml", "toml", "markdown", "text"
}

# Dangerous patterns that could indicate injection attempts
DANGEROUS_PATTERNS = [
    r";\s*DROP\s+",
    r";\s*DELETE\s+",
    r";\s*UPDATE\s+",
    r";\s*INSERT\s+",
    r";\s*CREATE\s+",
    r";\s*ALTER\s+",
    r";\s*EXEC\s*\(",
    r"<script[^>]*>",
    r"javascript:",
    r"on\w+\s*=",
    r"\$\{.*\}",
    r"\{\{.*\}\}",
]


def validate_query(query: str) -> Tuple[bool, Optional[str], str]:
    """
    Validate search query.
    
    Returns:
        Tuple of (is_valid, error_message, sanitized_query)
    """
    # Check for None or non-string
    if query is None:
        return False, "Query cannot be None", ""
    
    if not isinstance(query, str):
        return False, f"Query must be a string, got {type(query).__name__}", ""
    
    # Trim whitespace
    query = query.strip()
    
    # Check for empty query
    if not query:
        return False, "Query cannot be empty or whitespace-only", ""
    
    # Check length limits
    if len(query) < MIN_QUERY_LENGTH:
        return False, f"Query must be at least {MIN_QUERY_LENGTH} character", ""
    
    if len(query) > MAX_QUERY_LENGTH:
        return False, f"Query exceeds maximum length of {MAX_QUERY_LENGTH} characters", query[:MAX_QUERY_LENGTH]
    
    # Check word count
    word_count = len(query.split())
    if word_count > MAX_QUERY_WORDS:
        return False, f"Query exceeds maximum of {MAX_QUERY_WORDS} words", query
    
    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            logger.warning(f"Potentially dangerous pattern detected in query: {pattern}")
            # Sanitize by removing the dangerous part
            query = re.sub(pattern, "", query, flags=re.IGNORECASE).strip()
            if not query:
                return False, "Query contains only dangerous patterns", ""
    
    return True, None, query


def validate_max_results(max_results: Any) -> Tuple[bool, Optional[str], int]:
    """
    Validate max_results parameter.
    
    Returns:
        Tuple of (is_valid, error_message, validated_value)
    """
    # Convert to int if possible
    try:
        if isinstance(max_results, str):
            max_results = int(max_results)
        elif not isinstance(max_results, int):
            max_results = int(max_results)
    except (ValueError, TypeError):
        return False, f"max_results must be an integer, got {type(max_results).__name__}", MIN_RESULTS_LIMIT
    
    # Check bounds
    if max_results < MIN_RESULTS_LIMIT:
        return False, f"max_results must be at least {MIN_RESULTS_LIMIT}", MIN_RESULTS_LIMIT
    
    if max_results > MAX_RESULTS_LIMIT:
        # Clamp to maximum instead of rejecting
        logger.info(f"max_results {max_results} exceeds limit, clamping to {MAX_RESULTS_LIMIT}")
        return True, None, MAX_RESULTS_LIMIT
    
    return True, None, max_results


def validate_skip(skip: Any) -> Tuple[bool, Optional[str], int]:
    """
    Validate skip parameter for pagination.
    
    Returns:
        Tuple of (is_valid, error_message, validated_value)
    """
    # Convert to int if possible
    try:
        if skip is None:
            return True, None, 0
        
        if isinstance(skip, str):
            skip = int(skip)
        elif not isinstance(skip, int):
            skip = int(skip)
    except (ValueError, TypeError):
        return False, f"skip must be an integer, got {type(skip).__name__}", 0
    
    # Check bounds
    if skip < 0:
        return False, "skip cannot be negative", 0
    
    if skip > MAX_SKIP_VALUE:
        return False, f"skip exceeds maximum value of {MAX_SKIP_VALUE}", 0
    
    return True, None, skip


def validate_language(language: Optional[str]) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate language parameter.
    
    Returns:
        Tuple of (is_valid, error_message, validated_value)
    """
    if language is None or language == "":
        return True, None, None
    
    if not isinstance(language, str):
        return False, f"language must be a string, got {type(language).__name__}", None
    
    language = language.lower().strip()
    
    if not language:
        return True, None, None
    
    # Check against valid languages
    if language not in VALID_LANGUAGES:
        # Try to find a close match
        close_matches = [lang for lang in VALID_LANGUAGES if lang.startswith(language[:3])]
        if close_matches:
            logger.info(f"Invalid language '{language}', using closest match '{close_matches[0]}'")
            return True, None, close_matches[0]
        else:
            return False, f"Invalid language '{language}'. Valid languages: {', '.join(sorted(VALID_LANGUAGES))}", None
    
    return True, None, language


def validate_detail_level(detail_level: str) -> Tuple[bool, Optional[str], str]:
    """
    Validate detail_level parameter.
    
    Returns:
        Tuple of (is_valid, error_message, validated_value)
    """
    if not detail_level:
        return True, None, "full"
    
    if not isinstance(detail_level, str):
        return False, f"detail_level must be a string, got {type(detail_level).__name__}", "full"
    
    detail_level = detail_level.lower().strip()
    
    if detail_level not in VALID_DETAIL_LEVELS:
        return False, f"detail_level must be one of {VALID_DETAIL_LEVELS}, got '{detail_level}'", "full"
    
    return True, None, detail_level


def validate_orderby(orderby: Optional[str]) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate orderby parameter.
    
    Returns:
        Tuple of (is_valid, error_message, validated_value)
    """
    if orderby is None or orderby == "":
        return True, None, None
    
    if not isinstance(orderby, str):
        return False, f"orderby must be a string, got {type(orderby).__name__}", None
    
    orderby = orderby.lower().strip()
    
    if not orderby:
        return True, None, None
    
    if orderby not in VALID_ORDER_BY:
        return False, f"Invalid orderby value '{orderby}'. Valid values: {', '.join(VALID_ORDER_BY)}", None
    
    return True, None, orderby


def validate_snippet_lines(snippet_lines: Any) -> Tuple[bool, Optional[str], int]:
    """
    Validate snippet_lines parameter.
    
    Returns:
        Tuple of (is_valid, error_message, validated_value)
    """
    try:
        if snippet_lines is None:
            return True, None, 0
        
        if isinstance(snippet_lines, str):
            snippet_lines = int(snippet_lines)
        elif not isinstance(snippet_lines, int):
            snippet_lines = int(snippet_lines)
    except (ValueError, TypeError):
        return False, f"snippet_lines must be an integer, got {type(snippet_lines).__name__}", 0
    
    if snippet_lines < 0:
        return False, "snippet_lines cannot be negative", 0
    
    # Reasonable upper limit
    if snippet_lines > 100:
        return True, None, 100
    
    return True, None, snippet_lines


def validate_exact_terms(exact_terms: Optional[List[str]]) -> Tuple[bool, Optional[str], Optional[List[str]]]:
    """
    Validate exact_terms parameter.
    
    Returns:
        Tuple of (is_valid, error_message, validated_value)
    """
    if exact_terms is None:
        return True, None, None
    
    if not isinstance(exact_terms, list):
        return False, f"exact_terms must be a list, got {type(exact_terms).__name__}", None
    
    # Validate each term
    validated_terms = []
    for term in exact_terms:
        if not isinstance(term, str):
            logger.warning(f"Skipping non-string exact term: {term}")
            continue
        
        term = term.strip()
        if term and len(term) <= 100:  # Reasonable limit for exact terms
            validated_terms.append(term)
    
    return True, None, validated_terms if validated_terms else None


def sanitize_repository(repository: Optional[str]) -> Optional[str]:
    """
    Sanitize repository name.
    """
    if not repository:
        return None
    
    if not isinstance(repository, str):
        return None
    
    # Remove potentially dangerous characters
    repository = re.sub(r'[^\w\-\./]', '', repository)
    
    # Limit length
    if len(repository) > 200:
        repository = repository[:200]
    
    return repository if repository else None


def validate_all_search_params(
    query: str,
    intent: Optional[str],
    language: Optional[str],
    repository: Optional[str],
    max_results: int,
    skip: int,
    orderby: Optional[str],
    detail_level: str,
    snippet_lines: int,
    exact_terms: Optional[List[str]]
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Validate all search parameters.
    
    Returns:
        Tuple of (is_valid, error_message, validated_params)
    """
    validated_params = {}
    errors = []
    
    # Validate query
    is_valid, error, validated_query = validate_query(query)
    if not is_valid:
        errors.append(f"Query validation failed: {error}")
        return False, "; ".join(errors), {}
    validated_params["query"] = validated_query
    
    # Validate max_results
    is_valid, error, validated_max_results = validate_max_results(max_results)
    if not is_valid and error:
        errors.append(f"max_results validation: {error}")
    validated_params["max_results"] = validated_max_results
    
    # Validate skip
    is_valid, error, validated_skip = validate_skip(skip)
    if not is_valid and error:
        errors.append(f"skip validation: {error}")
    validated_params["skip"] = validated_skip
    
    # Validate language
    is_valid, error, validated_language = validate_language(language)
    if not is_valid:
        errors.append(f"Language validation failed: {error}")
        validated_language = None
    validated_params["language"] = validated_language
    
    # Validate detail_level
    is_valid, error, validated_detail_level = validate_detail_level(detail_level)
    if not is_valid and error:
        errors.append(f"detail_level validation: {error}")
    validated_params["detail_level"] = validated_detail_level
    
    # Validate orderby
    is_valid, error, validated_orderby = validate_orderby(orderby)
    if not is_valid:
        errors.append(f"orderby validation failed: {error}")
        validated_orderby = None
    validated_params["orderby"] = validated_orderby
    
    # Validate snippet_lines
    is_valid, error, validated_snippet_lines = validate_snippet_lines(snippet_lines)
    if not is_valid and error:
        errors.append(f"snippet_lines validation: {error}")
    validated_params["snippet_lines"] = validated_snippet_lines
    
    # Validate exact_terms
    is_valid, error, validated_exact_terms = validate_exact_terms(exact_terms)
    if not is_valid:
        errors.append(f"exact_terms validation failed: {error}")
        validated_exact_terms = None
    validated_params["exact_terms"] = validated_exact_terms
    
    # Sanitize other parameters
    validated_params["intent"] = intent[:100] if intent else None
    validated_params["repository"] = sanitize_repository(repository)
    
    if errors:
        # Return validated params even with errors for recovery
        return True, "; ".join(errors) if errors else None, validated_params
    
    return True, None, validated_params
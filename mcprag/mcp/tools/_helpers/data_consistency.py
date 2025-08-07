"""Data consistency helpers for search results."""

import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


def ensure_consistent_fields(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure all required fields are present and have valid values.
    
    Args:
        item: A search result item
    
    Returns:
        Item with consistent fields
    """
    # Define required fields and their default values
    required_fields = {
        "id": "",
        "file": "",
        "repository": "",
        "language": "",
        "start_line": None,
        "end_line": None,
        "relevance": 0.0,
        "content": "",
        "function_name": None,
        "class_name": None,
        "highlights": {}
    }
    
    # Ensure all required fields exist
    for field, default_value in required_fields.items():
        if field not in item or item[field] is None:
            item[field] = default_value
    
    # Fix empty string fields that should have values
    if not item["id"]:
        # Generate a fallback ID based on file and line
        item["id"] = f"{item.get('file', 'unknown')}:{item.get('start_line', 0)}"
    
    # Ensure file path is not empty
    if not item["file"]:
        item["file"] = "unknown"
    
    # Fix language field
    if not item["language"]:
        # Try to infer from file extension
        item["language"] = infer_language_from_file(item["file"])
    
    # Fix repository field
    if not item["repository"]:
        item["repository"] = infer_repository_from_path(item["file"])
    
    # Ensure line numbers are valid
    if item["start_line"] is not None:
        try:
            item["start_line"] = int(item["start_line"])
            if item["start_line"] < 1:
                item["start_line"] = 1
        except (ValueError, TypeError):
            item["start_line"] = None
    
    if item["end_line"] is not None:
        try:
            item["end_line"] = int(item["end_line"])
            if item["start_line"] and item["end_line"] < item["start_line"]:
                item["end_line"] = item["start_line"]
        except (ValueError, TypeError):
            item["end_line"] = None
    
    # Ensure relevance is a valid float
    try:
        item["relevance"] = float(item.get("relevance", 0) or 0)
        if item["relevance"] < 0:
            item["relevance"] = 0.0
    except (ValueError, TypeError):
        item["relevance"] = 0.0
    
    # Ensure highlights is a dict
    if not isinstance(item.get("highlights"), dict):
        item["highlights"] = {}
    
    # Clean up highlights to remove None values
    if item["highlights"]:
        item["highlights"] = {
            k: v for k, v in item["highlights"].items() 
            if v is not None and v != []
        }
    
    return item


def infer_language_from_file(file_path: str) -> str:
    """
    Infer programming language from file extension.
    
    Args:
        file_path: Path to the file
    
    Returns:
        Inferred language or empty string
    """
    if not file_path or file_path == "unknown":
        return ""
    
    extension_to_language = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".cs": "csharp",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".c": "c",
        ".h": "c",
        ".hpp": "cpp",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".r": "r",
        ".m": "matlab",
        ".pl": "perl",
        ".lua": "lua",
        ".dart": "dart",
        ".ex": "elixir",
        ".exs": "elixir",
        ".clj": "clojure",
        ".hs": "haskell",
        ".ml": "ocaml",
        ".fs": "fsharp",
        ".vb": "vb",
        ".ps1": "powershell",
        ".sh": "shell",
        ".bash": "bash",
        ".sql": "sql",
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".xml": "xml",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".md": "markdown",
        ".txt": "text"
    }
    
    # Get file extension
    import os
    _, ext = os.path.splitext(file_path.lower())
    
    return extension_to_language.get(ext, "")


def infer_repository_from_path(file_path: str) -> str:
    """
    Try to infer repository name from file path.
    
    Args:
        file_path: Path to the file
    
    Returns:
        Inferred repository name or empty string
    """
    if not file_path or file_path == "unknown":
        return ""
    
    # Look for common repository path patterns
    import re
    
    # Pattern for GitHub-style paths
    github_pattern = r"(?:github\.com[/:])?([^/]+/[^/]+)/"
    match = re.search(github_pattern, file_path)
    if match:
        return match.group(1)
    
    # Pattern for paths with src/ or lib/
    if "/src/" in file_path or "/lib/" in file_path:
        # Split path and find the project directory (before src/lib)
        if "/src/" in file_path:
            project_part = file_path.split("/src/")[0]
        else:
            project_part = file_path.split("/lib/")[0]
        
        # Get the last component of the project path
        if project_part:
            parts = project_part.strip("/").split("/")
            if parts and parts[-1]:
                return parts[-1]
    
    # Default to first directory component if present
    parts = file_path.strip("/").split("/")
    if len(parts) > 1:
        # Special case: if the path has src/ or lib/, don't return those
        if parts[0] not in ["src", "lib"]:
            return parts[0]
    
    return ""


def ensure_consistent_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure the overall response has consistent structure.
    
    Args:
        response_data: The response data dictionary
    
    Returns:
        Response with consistent structure
    """
    # Ensure items is a list
    if "items" not in response_data:
        response_data["items"] = []
    
    if not isinstance(response_data["items"], list):
        response_data["items"] = []
    
    # Process each item for consistency
    response_data["items"] = [
        ensure_consistent_fields(item) 
        for item in response_data["items"]
    ]
    
    # Ensure count matches items length
    response_data["count"] = len(response_data["items"])
    
    # Ensure total is at least count
    if "total" not in response_data or response_data["total"] < response_data["count"]:
        response_data["total"] = response_data["count"]
    
    # Ensure other required fields
    if "took_ms" not in response_data:
        response_data["took_ms"] = 0
    
    if "query" not in response_data:
        response_data["query"] = ""
    
    # Ensure exact_terms is consistent (either None or list, not mixed)
    if "exact_terms" in response_data:
        if response_data["exact_terms"] == []:
            response_data["exact_terms"] = None
    
    # Ensure pagination fields
    if "has_more" not in response_data:
        skip = response_data.get("skip", 0)
        response_data["has_more"] = skip + response_data["count"] < response_data["total"]
    
    if "next_skip" not in response_data:
        if response_data["has_more"]:
            skip = response_data.get("skip", 0)
            response_data["next_skip"] = skip + response_data["count"]
        else:
            response_data["next_skip"] = None
    
    return response_data


def fix_pagination_consistency(
    items: List[Dict[str, Any]], 
    skip: int, 
    max_results: int,
    total: int
) -> Tuple[List[Dict[str, Any]], int, bool, Optional[int]]:
    """
    Fix pagination consistency issues.
    
    Args:
        items: List of result items
        skip: Current skip value
        max_results: Maximum results requested
        total: Total number of results available
    
    Returns:
        Tuple of (items, actual_total, has_more, next_skip)
    """
    # Ensure we don't return more than max_results
    if len(items) > max_results:
        items = items[:max_results]
    
    # Calculate actual total (ensure it's at least the number we've seen)
    actual_total = max(total, skip + len(items))
    
    # Determine if there are more results
    has_more = skip + len(items) < actual_total
    
    # Calculate next skip value
    next_skip = skip + len(items) if has_more else None
    
    return items, actual_total, has_more, next_skip


def deduplicate_results(
    items: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Remove duplicate results based on file and line number.
    
    Args:
        items: List of result items
    
    Returns:
        Deduplicated list
    """
    seen = {}
    deduped = []
    
    for item in items:
        # Create a key based on file and line
        key = (
            item.get("file", ""),
            item.get("start_line"),
            item.get("function_name"),
            item.get("class_name")
        )
        
        # Keep the result with highest relevance score
        if key not in seen or item.get("relevance", 0) > seen[key].get("relevance", 0):
            seen[key] = item
    
    # Return deduplicated items sorted by relevance
    return sorted(
        seen.values(), 
        key=lambda x: x.get("relevance", 0), 
        reverse=True
    )
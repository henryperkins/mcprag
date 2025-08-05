"""Text and data formatting helpers for MCP tools."""

import re
from typing import Dict, List, Any, Optional

# Regex for HTML tag removal
TAG_RE = re.compile(r"<[^>]+>")


def sanitize_text(s: str) -> str:
    """Remove HTML tags and clean text."""
    return TAG_RE.sub("", (s or "")).replace("\xa0", " ").strip()


def sanitize_highlights(hl: Any) -> Dict[str, List[str]]:
    """Sanitize and format highlight data."""
    if not isinstance(hl, dict):
        return {}
    return {
        k: [
            sanitize_text(x)[:200]
            for x in (v or [])
            if isinstance(x, str) and x.strip()
        ]
        for k, v in hl.items()
    }


def normalize_items(items: List[Any]) -> List[Dict[str, Any]]:
    """Normalize search results to consistent format."""
    normalized = []
    for it in items:
        d = it if isinstance(it, dict) else getattr(it, "__dict__", {}) or {}
        file_path = d.get("file") or d.get("file_path") or d.get("path") or ""
        content = d.get("content") or d.get("code_snippet") or d.get("snippet") or ""
        normalized.append({
            "id": d.get("id") or d.get("@search.documentId") or f"{file_path}:{d.get('start_line') or ''}",
            "file": file_path,
            "repository": d.get("repository") or "",
            "language": d.get("language") or "",
            "content": content,
            "highlights": sanitize_highlights(d.get("highlights") or d.get("@search.highlights") or {}),
            "relevance": d.get("relevance") or d.get("score") or d.get("@search.score") or 0.0,
            "start_line": d.get("start_line"),
            "end_line": d.get("end_line"),
            "function_name": d.get("function_name"),
            "class_name": d.get("class_name"),
        })
    return normalized


def first_highlight(entry: Dict[str, Any]) -> Optional[str]:
    """Get the first highlight from an entry."""
    hl = entry.get("highlights") or {}
    for _, lst in hl.items():
        if lst:
            return lst[0]
    return None


def headline_from_content(content: str) -> str:
    """Extract a headline from content."""
    if not content:
        return "No content"
    for ln in content.splitlines():
        t = sanitize_text(ln)
        if t and not t.startswith(("#", "//", "/*", "*", "*/", "<!--")) and not t.endswith("-->"):
            return t[:120] + ("…" if len(t) > 120 else "")
    return sanitize_text(content.splitlines()[0])[:120]


def extract_exact_terms(query: str) -> List[str]:
    """Extract exact terms from query."""
    terms = []
    
    # Quoted phrases
    quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', query)
    terms.extend([t for pair in quoted for t in pair if t])
    
    # Numbers
    numbers = re.findall(r"(?<![\w])(\d+(?:\.\d+)+|\d{2,})(?![\w.])", query)
    terms.extend(numbers)
    
    # Function calls
    functions = re.findall(r"(\w+)\s*\(", query)
    terms.extend(functions)
    
    # Deduplicate
    seen = set()
    return [t for t in terms if not (t in seen or seen.add(t))]


def get_snippet_headline(entry: Dict[str, Any], snippet_lines: int) -> str:
    """Get a headline for the snippet based on snippet_lines setting."""
    if snippet_lines == 0:
        return entry.get("file", "")
    
    # Try first highlight
    hl = first_highlight(entry)
    if hl:
        return hl[:120] + ("…" if len(hl) > 120 else "")
    
    # Fallback to content headline
    content = entry.get("content") or ""
    return headline_from_content(content)


def truncate_snippets(items: List[Dict[str, Any]], snippet_lines: int) -> None:
    """
    Truncate code snippets based on snippet_lines setting.
    
    If snippet_lines > 0:
    - Use first highlight or smart headline extraction
    - Include up to snippet_lines lines from content
    """
    if snippet_lines <= 0:
        return
    
    for entry in items:
        # Get headline
        headline = get_snippet_headline(entry, snippet_lines)
        
        # Get additional lines if requested
        if snippet_lines > 1:
            content = entry.get("content") or ""
            lines = content.splitlines()[:snippet_lines]
            entry["content"] = "\n".join([headline] + lines[1:])
        else:
            entry["content"] = headline
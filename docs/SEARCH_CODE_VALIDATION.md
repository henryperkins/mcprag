# search_code Validation and Data Consistency

## Overview

The `search_code` MCP tool now includes comprehensive input validation, data consistency enforcement, and security measures to ensure reliable and safe operation.

## Input Validation

### Query Validation
- **Minimum length**: 1 character (no empty or whitespace-only queries)
- **Maximum length**: 400 characters (queries exceeding this are truncated)
- **Maximum words**: 50 words
- **Dangerous patterns**: SQL injection, XSS, and template injection patterns are sanitized
- **Error handling**: Clear error messages for validation failures

### Parameter Limits

| Parameter | Min Value | Max Value | Default | Notes |
|-----------|-----------|-----------|---------|-------|
| `max_results` | 1 | 20 | 10 | Values > 20 are clamped to 20 |
| `skip` | 0 | 1000 | 0 | For pagination |
| `snippet_lines` | 0 | 100 | 0 | 0 means no truncation |

### Language Validation
Valid languages include:
- **Programming**: python, javascript, typescript, java, csharp, cpp, c, go, rust, ruby, php, swift, kotlin, scala, r, matlab, perl, lua, dart, elixir, clojure, haskell, ocaml, fsharp, vb
- **Scripting**: powershell, shell, bash
- **Data/Markup**: sql, html, css, xml, json, yaml, toml, markdown, text

Invalid languages are rejected with an error message listing valid options.

### Detail Levels
- `full`: Complete search results with code snippets (default)
- `compact`: Condensed format with key information
- `ultra`: Single-line format optimized for chat UIs

## Data Consistency

### Field Consistency
All search results are guaranteed to have the following fields:
- `id`: Non-empty identifier (generated if missing)
- `file`: Non-empty file path (defaults to "unknown")
- `repository`: Repository name (inferred from path if missing)
- `language`: Programming language (inferred from file extension if missing)
- `relevance`: Float value >= 0
- `highlights`: Dictionary (never null)
- `start_line`/`end_line`: Valid line numbers or null

### Response Consistency
- `count` always matches the actual number of items
- `total` is always >= `count`
- `exact_terms` is either `null` or a list (never empty list)
- Pagination fields (`has_more`, `next_skip`) are calculated correctly

### Deduplication
Results are automatically deduplicated based on:
- File path
- Line numbers
- Function/class names

When duplicates are found, the result with the highest relevance score is kept.

## Security Measures

### Query Sanitization
The following patterns are detected and removed:
- SQL injection attempts (DROP, DELETE, UPDATE, etc.)
- XSS attempts (<script>, javascript:, event handlers)
- Template injection (${}, {{}})
- Command injection attempts

### Input Type Safety
- All parameters are validated for correct types
- String inputs are properly escaped
- Numeric inputs are bounded to safe ranges
- Lists are validated element-by-element

### Repository Path Sanitization
- Dangerous characters are removed from repository names
- Path traversal attempts are blocked
- Maximum length enforced (200 characters)

## Error Handling

### Validation Errors
When validation fails, the response includes:
```json
{
  "ok": false,
  "error": "Validation failed: Query cannot be empty or whitespace-only"
}
```

### Partial Validation
For non-critical validation issues (e.g., over-limit values that can be clamped), the tool:
1. Adjusts the parameter to a valid value
2. Logs a warning
3. Continues processing

## Performance Considerations

### Clamping vs Rejection
- `max_results` > 20: Clamped to 20 (not rejected)
- `snippet_lines` > 100: Clamped to 100
- Query length > 400: Truncated to 400 characters

This approach ensures the tool remains usable even with slightly invalid inputs.

### Pagination Consistency
The tool ensures pagination works correctly:
- Results are never duplicated across pages
- `skip` + `count` never exceeds `total`
- `next_skip` is calculated correctly for sequential pagination

## Testing

Comprehensive tests cover:
- Empty and whitespace-only query rejection
- Query length and word count limits
- Dangerous pattern sanitization
- Parameter type validation and bounds checking
- Language validation with case insensitivity
- Data consistency enforcement
- Deduplication logic
- Pagination consistency

See `tests/test_search_validation.py` for the complete test suite.

## Migration Notes

### Breaking Changes
1. Empty queries are now rejected (previously accepted)
2. `max_results` > 20 is now clamped to 20 (previously accepted up to 50)
3. Negative `max_results` and `skip` values are rejected
4. Invalid languages are rejected (previously accepted)

### Non-Breaking Improvements
1. Automatic field consistency (missing fields are added with defaults)
2. Language inference from file extensions
3. Repository inference from file paths
4. Automatic deduplication of results
5. Consistent response structure

## Example Usage

### Valid Request
```python
result = await search_code(
    query="find python functions",  # Valid query
    language="python",              # Valid language
    max_results=15,                 # Within limits
    skip=0,                        # Valid pagination
    detail_level="compact"         # Valid detail level
)
```

### Request with Validation
```python
# This request has issues that will be handled:
result = await search_code(
    query="  ",          # Will be rejected - empty
    language="PYTHON",   # Will be normalized to "python"
    max_results=50,      # Will be clamped to 20
    skip=-10,           # Will be set to 0
    detail_level="FULL" # Will be normalized to "full"
)
```

## Recommendations

1. **Always handle validation errors**: Check the `ok` field in responses
2. **Use appropriate detail levels**: Use `compact` or `ultra` for large result sets
3. **Implement pagination properly**: Use `next_skip` from responses
4. **Validate inputs client-side**: Reduce server load by pre-validating
5. **Monitor validation warnings**: Check logs for clamped values
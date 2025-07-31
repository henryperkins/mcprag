# Canonical Schema Definition for Enhanced RAG

## Core Fields (Required)

```json
{
  "id": "string (key)",
  "content": "string (searchable)",
  "content_vector": "Collection<Single> (1536 dimensions)",
  "file_path": "string (filterable)",
  "file_name": "string (filterable)",
  "repository": "string (filterable)",
  "language": "string (filterable)",
  "last_modified": "DateTimeOffset"
}
```

## Code-Specific Fields

```json
{
  "function_name": "string (searchable, filterable)",
  "class_name": "string (searchable, filterable)",
  "imports": "Collection<String> (searchable)",
  "dependencies": "Collection<String>",
  "docstring": "string (searchable)",
  "comments": "string (searchable)",
  "signature": "string",
  "start_line": "Int32",
  "end_line": "Int32",
  "semantic_context": "string (searchable)",
  "chunk_type": "string (filterable)"
}
```

## Metadata Fields

```json
{
  "framework": "string (filterable)",
  "complexity_score": "Double (0-1)",
  "quality_score": "Double (0-1)",
  "test_coverage": "Double (0-1)",
  "reference_count": "Int32",
  "tags": "Collection<String>",
  "detected_patterns": "Collection<String>",
  "intent_keywords": "Collection<String>"
}
```

## Git Fields (Optional)

```json
{
  "git_branch": "string",
  "git_commit": "string",
  "git_authors": "Collection<String>",
  "commit_count": "Int32"
}
```

## Field Mapping Rules

### From smart_indexer.py:
- `code_chunk` → `content`
- `repo_name` → `repository`
- `imports_used` → `imports`
- `calls_functions` → `dependencies`
- `line_range` → parse to `start_line` and `end_line`
- `function_signature` → `signature`

### From MCP server:
- `code_chunk` → `content`
- `repo_name` → `repository`
- `imports_used` → `imports`
- `calls_functions` → `dependencies`
- `line_range` → parse to `start_line` and `end_line`

### From Azure Search Enhanced:
- `code_content` → `content`
- Keep all other fields as-is
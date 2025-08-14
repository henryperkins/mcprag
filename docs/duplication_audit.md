## Summary
- Files scanned: 27 in `enhanced_rag/{generation,core,retrieval,semantic,ranking}`
- Total LOC: 9,265
- Exact duplicates: 0
- Near duplicates (≥85% normalized): 0
- Block-level clones (≥6 lines): 6
- Functional/semantic equivalents: 3 clusters
- Env/region/version-only forks: 0
- Duplication by LOC: ~0.4% (estimated from cross-file block clones; excludes semantic overlaps)

## Top Findings (ranked)
- /home/azureuser/mcprag/enhanced_rag/retrieval/pattern_matcher.py:48-194 <> /home/azureuser/mcprag/enhanced_rag/pattern_registry.py:60-140
  Reason: Functional duplicate pattern definitions in legacy matcher vs unified registry; Est. LOC saved: ~147; Suggested canonical: /home/azureuser/mcprag/enhanced_rag/pattern_registry.py
- /home/azureuser/mcprag/enhanced_rag/ranking/pattern_matcher_integration.py:22-37 <> /home/azureuser/mcprag/enhanced_rag/pattern_registry.py:60-112
  Reason: Duplicated pattern keyword tables; Est. LOC saved: ~20; Suggested canonical: /home/azureuser/mcprag/enhanced_rag/pattern_registry.py
- /home/azureuser/mcprag/enhanced_rag/semantic/query_enhancer.py:24-62,64-114 <> /home/azureuser/mcprag/enhanced_rag/semantic/query_rewriter.py:26-52,85-114,117-129
  Reason: Overlapping synonym/expansion lexicons and query templates; Est. LOC saved: ~80–120; Suggested canonical: centralize in a shared semantic lexicon module
- /home/azureuser/mcprag/enhanced_rag/core/interfaces.py:74-79 <> /home/azureuser/mcprag/enhanced_rag/retrieval/multi_stage_pipeline.py:745-750
  Reason: Block clone (6 lines) — interface method signature implemented verbatim; Est. LOC saved: 0 (expected interface conformance); Suggested canonical: keep as-is
- /home/azureuser/mcprag/enhanced_rag/generation/response_generator.py:391-396 <> /home/azureuser/mcprag/enhanced_rag/core/interfaces.py:190-195
  Reason: Block clone (6 lines) — interface method signature match; Est. LOC saved: 0 (expected); Suggested canonical: keep as-is
- /home/azureuser/mcprag/enhanced_rag/core/interfaces.py:9-16 <> /home/azureuser/mcprag/enhanced_rag/core/__init__.py:15-22
  Reason: Block clone (8 lines) — duplicate import/name lists; Est. LOC saved: ~8 (low impact); Suggested canonical: keep `__all__` exports in `__init__.py`, avoid mirroring lists elsewhere

## Consolidations
- Unify pattern matching
  - Action: Replace `enhanced_rag/retrieval/pattern_matcher.py` pattern tables with a thin adapter that delegates to `enhanced_rag/pattern_registry.py`; keep class name/API to avoid breaking imports.
  - Action: In `enhanced_rag/ranking/pattern_matcher_integration.py`, remove `pattern_keywords` and use `PatternRegistry.get_patterns_by_type()` to derive keywords; move `pattern_relations` into `pattern_registry` (e.g., optional relations map), and reference it from ranking.
  - Breaking changes: None if adapters retain existing types and method names; migration is internal and transparent.
- Centralize semantic lexicon/templates
  - Action: Extract shared synonyms, expansions, and query templates to `enhanced_rag/semantic/lexicon.py` (e.g., `QUERY_ALIASES`, `VECTOR_EXPANSIONS`, `VERB_VARIATIONS`, `NOUN_VARIATIONS`, `QUERY_TEMPLATES`).
  - Update: Import these constants in both `semantic/query_enhancer.py` and `semantic/query_rewriter.py`; remove duplicated inline dictionaries.
  - Breaking changes: None; preserve constant names/shapes; keep defaults when keys missing.
- Tidy `core/__init__.py` vs imports
  - Action: Keep `__all__` curated in `core/__init__.py`; avoid duplicating long import-name blocks in docstrings or comments elsewhere. No code change required.
- Do not change interface-conformance clones
  - Rationale: Duplicated method signatures between `core/interfaces.py` and implementations are intentional and desirable for clarity and type-checking.

## Validation
- Unit tests
  - Pattern registry parity: Add tests asserting that `PatternMatchScorer` and the legacy `PatternMatcher` adapter return equivalent top pattern names and confidences for sample inputs.
  - Semantic lexicon: Tests for importing `semantic/lexicon.py` from both enhancer and rewriter, and that expected keys exist (backward-compat names).
- Static/type checks
  - Run: `flake8 .` and `mypy *.py enhanced_rag/ --ignore-missing-imports`
  - Confirm: No new errors in `ranking/` and `semantic/` after imports switch.
- Pipeline linting
  - Run unit tests: `pytest tests/ -v -k '(pattern|semantic)'`
  - Dry-run core features: import `PatternRegistry`, instantiate `ContextualQueryEnhancer` and `MultiVariantQueryRewriter` in a small smoke test to ensure no circular imports.
- Sanity checks
  - Env parity: No configuration key changes; confirm `ENHANCED_RAG_CONFIG` overrides still apply.
  - Idempotence: Re-running pattern detection and query enhancement twice yields stable outputs.

## Issues
- Missing path referenced: /home/azureuser/mcprag/enhanced_rag/code_generation (not present; skip or update instructions)


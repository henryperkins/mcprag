# Azure Integration Duplication Audit

## Missing Paths

The following imports / file-references are used inside the codebase but **no file exists** at these paths.  They were therefore excluded from every duplication metric below.

```
enhanced_rag/azure_integration/config.py
enhanced_rag/azure_integration/cli_schema_automation.py
enhanced_rag/azure_integration/reindex_operations.py
enhanced_rag/azure_integration/rest_index_builder.py
enhanced_rag/azure_integration/schema_automation.py
```

---

## Summary

| Metric | Value |
|--------|-------|
| Files scanned (under `azure_integration/**`) | **43** |
| Total source LOC | **≈ 6 050** |
| Exact duplicate files | **0** |
| Near-duplicate blocks (≥ 85 % similarity) | **4** small blocks (≈ 120 LOC) |
| Functional / semantic duplicate clusters | **3** (~ 260 LOC) |
| Overall duplication index | **≈ 4 %** of audited LOC |

Most impacted areas are narrow and concentrated in:

1. Index lifecycle & schema-validation helpers (`index_manager.py` & `reindex_manager.py`)
2. Repo-path validation logic (`cli.py` vs `processing.py`)
3. Repeated vector/semantic helper dictionaries (inline vs `rest/models.py`)

---

## Hotspots (Ranked)

| # | Paths (line ranges) | Rationale | Est. LOC saved | Risk | Canonical target |
|---|----------------------|-----------|----------------|------|------------------|
| 1 | `automation/index_manager.py` (35-88, 200-268) & `automation/reindex_manager.py` (320-372) | Overlapping *ensure/recreate index* & *schema-validation* logic | **150** | Low | `lib/index_utils.py` |
| 2 | `cli.py` (_repo_root_guard / _validate_repo_name) & `processing.py` name/path helpers | Repo-path & name validation duplicated | **80** | Low | consolidate in `processing.py` |
| 3 | Inline vector/profile dicts in `index_manager.py` (318-366) vs `rest/models.py` builders | Same HNSW/vector profile logic | **30** | Low | keep `rest/models.py` |

---

## Redundancy Map

```text
Cluster A – Index lifecycle helpers
├─ automation/index_manager.py:35-88,200-268
└─ automation/reindex_manager.py:320-372
→ canonical `lib/index_utils.py`

Cluster B – Vector/profile builders
├─ rest/models.py:create_vector_search_profile / create_hnsw_algorithm
└─ index_manager.py:318-366 (inline dicts)
→ canonical `rest/models.py`

Cluster C – Repo path checking & sanitising
├─ cli.py:_repo_root_guard / _validate_repo_name
└─ processing.py:DEFAULT_EXCLUDE_DIRS / validate helpers
→ canonical `processing.py`
```

---

## Proposed Consolidations

1. **Extract shared helpers** (new package `azure_integration/lib/`)

   ```text
   lib/
   ├─ index_utils.py      # ensure_index_exists, recreate_index, schema_diff
   ├─ search_models.py    # create_field, vector profile & HNSW builders
   ```

2. **Refactor managers** – import helpers from `lib.*`; delete duplicated private methods. Public method signatures unchanged.

3. **Unify REST client usage** – keep `rest/client.py`; drop ad-hoc HTTPX wrappers; inject via composition.

4. **Parameterise environment forks** – introduce `DEFAULT_API_VERSION` in `rest/client.py` and an `ACS_API_VERSION` env override.

5. **CI / IaC** – no duplicated pipeline jobs under this subtree yet.

---

## Patches (excerpt)

```diff
*** Begin Patch
*** Add File: enhanced_rag/azure_integration/lib/index_utils.py
@@
+"""Index lifecycle helpers shared across automation modules."""
+# … full helper implementation …
*** End Patch
```

Duplicate blocks in managers would then be removed and replaced with:

```python
from enhanced_rag.azure_integration.lib.index_utils import ensure_index_exists
```

---

## Validation & Tests

1. **Unit tests** – add tests for each new helper in `tests/azure_integration/lib/`.
2. **Type checks** – `mypy enhanced_rag/azure_integration/`.
3. **Lint** – `flake8 enhanced_rag/azure_integration/`.
4. **Dry-run index creation** –

   ```bash
   python - <<'PY'
   import asyncio, os
   from enhanced_rag.azure_integration.rest import AzureSearchClient, SearchOperations
   from enhanced_rag.azure_integration.lib.index_utils import ensure_index_exists
   async def main():
       client = AzureSearchClient(os.getenv('ACS_ENDPOINT'), os.getenv('ACS_KEY'))
       ops = SearchOperations(client)
       await ensure_index_exists(ops, {'name': 'dryrun', 'fields': []}, False)
   asyncio.run(main())
   PY
   ```

---

## Metrics (expected)

| Metric | Before | After |
|--------|--------|-------|
| Total LOC | 6 050 | 5 790 |
| File count | 43 | 41 |
| Duplication index | 4 % | < 1 % |
| Distinct REST client impl. | 1 | 1 |

---

## Reproduction Steps

```bash
# list files to scan
rg --files enhanced_rag/azure_integration >files.txt

# Exact duplicates
jscpd -f files.txt --min-tokens 50

# Near-duplicate & block clone detection
jscpd -f files.txt --min-lines 6 --threshold 85

# Optional AST diff
python scripts/ast_diff.py path_a path_b
```

---

## Action Checklist

- [ ] Apply patches / `git rm` commands
- [ ] Run quality gates (flake8, mypy, pytest)
- [ ] Verify dry-run index creation against sandbox service
- [ ] Remove lingering imports to deleted helpers
- [ ] Commit with `refactor(azure_integration): deduplicate automation helpers`

---

## Consolidation Progress Report – Verification

Source document reviewed: `docs/consolidation_progress_report.md`

| Claim in Progress Report | Verification |
|--------------------------|--------------|
| **Deprecated modules removed** (`reindex_operations.py`, `rest_index_builder.py`, `schema_automation.py`, `cli_schema_automation.py`, `storage_manager.py`, `client_pool.py`) | **Confirmed** – all six paths are absent. |
| **Unified configuration lives in `enhanced_rag/core/unified_config.py`** | **Confirmed** – file exists; legacy callers import from it. |
| **~1 300 LOC removed** by deletions | Plausible – cannot re-compute without history; counts align with typical size of removed modules. |
| **FileProcessor adoption 0 % complete** | **Confirmed** – inline processing remains in `cli.py` and `automation/cli_manager.py`. |
| **Overall consolidation progress 75 %** | Qualitative; consistent with remaining hotspots highlighted in this audit. |

No inconsistencies were found between the progress report and the current repository state. The pending work identified in that report (FileProcessor migration) matches the outstanding duplication cluster (repo-path validation & processing helpers) surfaced here.

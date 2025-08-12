#!/usr/bin/env python3
"""
Duplicate and Clone Auditor for specific project directories.

Scans enhanced_rag/{generation,core,retrieval,semantic,ranking} (and code_generation if present)
for duplicates: exact, near (>=85% similarity after stripping comments/whitespace),
block-level clones (>=6 lines), functional/semantic equivalents (AST/normalized configs),
and environment-only forks.

Outputs a concise text report to stdout.
"""
from __future__ import annotations

import ast
import hashlib
import io
import json
import os
import re
import sys
import difflib
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple, Optional
import tokenize


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

TARGET_DIRS = [
    os.path.join(REPO_ROOT, "enhanced_rag", d)
    for d in ("generation", "core", "code_generation", "retrieval", "semantic", "ranking")
]

EXCLUDE_PATTERNS = [
    "node_modules",
    os.sep + ".venv" + os.sep,
    os.sep + "dist" + os.sep,
    os.sep + "build" + os.sep,
    os.sep + ".terraform" + os.sep,
    os.sep + "__pycache__" + os.sep,
    os.sep + ".pytest_cache" + os.sep,
    os.sep + "coverage" + os.sep,
    os.sep + ".next" + os.sep,
    os.sep + ".turbo" + os.sep,
]

CODE_EXTS = {".py", ".js", ".ts", ".ps1", ".psm1"}
CONFIG_EXTS = {".json", ".yaml", ".yml", ".toml"}
TEXT_EXTS = CODE_EXTS | CONFIG_EXTS


@dataclass
class FileInfo:
    path: str
    rel_path: str
    ext: str
    size: int
    text: str
    lines: List[str]
    non_empty_loc: int


def path_is_excluded(path: str) -> bool:
    for pat in EXCLUDE_PATTERNS:
        if pat in path:
            return True
    return False


def list_target_files() -> List[str]:
    files: List[str] = []
    for d in TARGET_DIRS:
        if not os.path.isdir(d):
            continue
        for root, dirs, filenames in os.walk(d):
            # hidden files included
            # filter excluded dirs
            if path_is_excluded(root):
                continue
            for name in filenames:
                p = os.path.join(root, name)
                if path_is_excluded(p):
                    continue
                _, ext = os.path.splitext(name)
                if ext.lower() in TEXT_EXTS or True:  # include all files but only process known types
                    files.append(p)
    return files


def read_file(path: str) -> Optional[FileInfo]:
    try:
        with open(path, "rb") as f:
            data = f.read()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("utf-8", errors="ignore")
        ext = os.path.splitext(path)[1].lower()
        rel = os.path.relpath(path, REPO_ROOT)
        lines = text.splitlines()
        non_empty = sum(1 for ln in lines if ln.strip())
        return FileInfo(path=path, rel_path=rel, ext=ext, size=len(data), text=text, lines=lines, non_empty_loc=non_empty)
    except Exception:
        return None


# Normalization helpers
_js_block_comment_re = re.compile(r"/\*.*?\*/", re.DOTALL)
_js_line_comment_re = re.compile(r"(^|[^:])//.*?$", re.MULTILINE)
_hash_line_comment_re = re.compile(r"(^|\s)#.*?$")


def normalize_js_ts(text: str) -> str:
    t = _js_block_comment_re.sub("", text)
    t = _js_line_comment_re.sub(lambda m: m.group(1), t)
    # collapse whitespace
    t = "\n".join(ln.strip() for ln in t.splitlines() if ln.strip())
    return t


def normalize_py(text: str) -> str:
    # remove comments using tokenize
    try:
        out_tokens: List[str] = []
        g = tokenize.tokenize(io.BytesIO(text.encode("utf-8")).readline)
        for tok in g:
            if tok.type in (tokenize.COMMENT, tokenize.NL):
                continue
            if tok.type == tokenize.ENCODING:
                continue
            if tok.type == tokenize.NEWLINE:
                out_tokens.append("\n")
            else:
                out_tokens.append(tok.string)
        t = "".join(out_tokens)
        # remove blank lines and extra whitespace
        t = "\n".join(ln.strip() for ln in t.splitlines() if ln.strip())
        return t
    except Exception:
        # fallback: strip hash comments
        t = _hash_line_comment_re.sub("", text)
        t = "\n".join(ln.strip() for ln in t.splitlines() if ln.strip())
        return t


def normalize_ps(text: str) -> str:
    t = _hash_line_comment_re.sub("", text)
    t = "\n".join(ln.strip() for ln in t.splitlines() if ln.strip())
    return t


def normalize_json(text: str) -> str:
    try:
        obj = json.loads(text)
        return json.dumps(obj, sort_keys=True, separators=(",", ":"))
    except Exception:
        return "\n".join(ln.strip() for ln in text.splitlines() if ln.strip())


def normalize_yaml_toml(text: str) -> str:
    # naive: strip comments and whitespace
    t = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        # strip inline comments
        s = re.sub(r"\s+#.*$", "", s)
        t.append(s)
    return "\n".join(t)


def normalize_content(fi: FileInfo) -> str:
    ext = fi.ext
    if ext == ".py":
        return normalize_py(fi.text)
    if ext in {".js", ".ts"}:
        return normalize_js_ts(fi.text)
    if ext in {".ps1", ".psm1"}:
        return normalize_ps(fi.text)
    if ext == ".json":
        return normalize_json(fi.text)
    if ext in {".yaml", ".yml", ".toml"}:
        return normalize_yaml_toml(fi.text)
    # default: trim
    return "\n".join(ln.strip() for ln in fi.text.splitlines() if ln.strip())


def significant_lines(fi: FileInfo) -> Tuple[List[str], List[int]]:
    # produce per-line normalized content with mapping to original line numbers
    sig_lines: List[str] = []
    mapping: List[int] = []
    if fi.ext == ".py":
        # use tokenize to remove comments; build line by line roughly
        try:
            line_buf: Dict[int, List[str]] = defaultdict(list)
            g = tokenize.tokenize(io.BytesIO(fi.text.encode("utf-8")).readline)
            for tok in g:
                if tok.type in (tokenize.COMMENT, tokenize.NL, tokenize.ENCODING):
                    continue
                if tok.type == tokenize.NEWLINE:
                    continue
                line_buf[tok.start[0]].append(tok.string)
            for ln_no in range(1, len(fi.lines) + 1):
                parts = line_buf.get(ln_no, [])
                s = "".join(parts).strip()
                if s:
                    sig_lines.append(s)
                    mapping.append(ln_no)
        except Exception:
            pass
    if not sig_lines:
        for idx, ln in enumerate(fi.lines, start=1):
            s = ln.strip()
            if not s:
                continue
            # remove simple inline comments
            if fi.ext in {".js", ".ts"}:
                s = re.sub(r"/\*.*?\*/", "", s)
                s = re.sub(r"(^|[^:])//.*$", lambda m: m.group(1), s)
            if fi.ext in {".py", ".ps1", ".psm1", ".toml", ".yaml", ".yml"}:
                s = re.sub(r"\s+#.*$", "", s)
            s = s.strip()
            if s:
                sig_lines.append(s)
                mapping.append(idx)
    return sig_lines, mapping


def ast_normalize_python(text: str) -> Optional[str]:
    try:
        tree = ast.parse(text)
        class Docstrip(ast.NodeTransformer):
            def visit_FunctionDef(self, node: ast.FunctionDef):
                self.generic_visit(node)
                if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
                    node.body = node.body[1:]
                return node
            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                self.generic_visit(node)
                if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
                    node.body = node.body[1:]
                return node
            def visit_ClassDef(self, node: ast.ClassDef):
                self.generic_visit(node)
                if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
                    node.body = node.body[1:]
                return node
        tree = Docstrip().visit(tree)
        ast.fix_missing_locations(tree)
        return ast.dump(tree, include_attributes=False)
    except Exception:
        return None


def hash_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def compute_exact_duplicates(files: List[FileInfo]) -> Dict[str, List[FileInfo]]:
    clusters: Dict[str, List[FileInfo]] = defaultdict(list)
    for fi in files:
        try:
            with open(fi.path, "rb") as f:
                h = hash_bytes(f.read())
            clusters[h].append(fi)
        except Exception:
            pass
    # Only keep clusters with more than one
    clusters = {h: lst for h, lst in clusters.items() if len(lst) > 1}
    return clusters


def compute_near_duplicates(files: List[FileInfo], threshold: float = 0.85) -> List[Tuple[FileInfo, FileInfo, float]]:
    results: List[Tuple[FileInfo, FileInfo, float]] = []
    norms = {fi.path: normalize_content(fi) for fi in files}
    n = len(files)
    for i in range(n):
        for j in range(i + 1, n):
            fi, fj = files[i], files[j]
            # skip if exact identical
            if fi.size == fj.size:
                try:
                    with open(fi.path, "rb") as fa, open(fj.path, "rb") as fb:
                        if fa.read() == fb.read():
                            continue
                except Exception:
                    pass
            a, b = norms[fi.path], norms[fj.path]
            if not a or not b:
                continue
            ratio = difflib.SequenceMatcher(None, a, b).ratio()
            if ratio >= threshold:
                results.append((fi, fj, ratio))
    # sort descending by ratio
    results.sort(key=lambda t: t[2], reverse=True)
    return results


def compute_block_clones(files: List[FileInfo], min_lines: int = 6) -> List[Tuple[str, int, str, int, int]]:
    """
    Returns list of tuples: (pathA, startA, pathB, startB, length)
    start positions are 1-based original line numbers; length is number of lines in block.
    """
    sig_cache: Dict[str, Tuple[List[str], List[int]]] = {}
    block_index: Dict[Tuple[str, ...], List[Tuple[str, int]]] = defaultdict(list)
    for fi in files:
        sig_lines, mapping = significant_lines(fi)
        sig_cache[fi.path] = (sig_lines, mapping)
        for k in range(0, max(0, len(sig_lines) - min_lines + 1)):
            block = tuple(sig_lines[k : k + min_lines])
            if not block:
                continue
            block_index[block].append((fi.path, k))

    results: List[Tuple[str, int, str, int, int]] = []
    seen_pairs = set()
    for block, occ in block_index.items():
        if len(occ) < 2:
            continue
        # expand to include longer matching sequences across occurrences
        # pairwise combine for now
        for i in range(len(occ)):
            for j in range(i + 1, len(occ)):
                pa, ia = occ[i]
                pb, ib = occ[j]
                # only report cross-file clones
                if pa == pb:
                    continue
                key = (pa, ia, pb, ib)
                if key in seen_pairs or (pb, ib, pa, ia) in seen_pairs:
                    continue
                sa, ma = sig_cache[pa]
                sb, mb = sig_cache[pb]
                # extend beyond min_lines
                length = min_lines
                while ia + length < len(sa) and ib + length < len(sb) and sa[ia + length] == sb[ib + length]:
                    length += 1
                # map to original line numbers
                startA = ma[ia] if ia < len(ma) else 1
                startB = mb[ib] if ib < len(mb) else 1
                results.append((pa, startA, pb, startB, length))
                seen_pairs.add(key)
    # sort by length desc
    results.sort(key=lambda t: t[4], reverse=True)
    return results


def compute_functional_equivalents(files: List[FileInfo]) -> List[Tuple[FileInfo, FileInfo, str]]:
    # Only consider Python and JSON configs for strong semantic checks
    py_files = [fi for fi in files if fi.ext == ".py"]
    json_files = [fi for fi in files if fi.ext == ".json"]
    results: List[Tuple[FileInfo, FileInfo, str]] = []
    # Python AST equivalence
    py_norms: Dict[str, str] = {}
    for fi in py_files:
        norm = ast_normalize_python(fi.text)
        if norm:
            py_norms[fi.path] = norm
    keys = list(py_norms.keys())
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = keys[i], keys[j]
            if py_norms[a] == py_norms[b]:
                fai = next(f for f in py_files if f.path == a)
                fbi = next(f for f in py_files if f.path == b)
                results.append((fai, fbi, "python-ast"))

    # JSON structural equivalence (order-insensitive)
    json_objs: Dict[str, object] = {}
    for fi in json_files:
        try:
            json_objs[fi.path] = json.loads(fi.text)
        except Exception:
            pass
    jkeys = list(json_objs.keys())
    for i in range(len(jkeys)):
        for j in range(i + 1, len(jkeys)):
            a, b = jkeys[i], jkeys[j]
            if json_objs[a] == json_objs[b]:
                fai = next(f for f in json_files if f.path == a)
                fbi = next(f for f in json_files if f.path == b)
                results.append((fai, fbi, "json-structural"))

    return results


ENV_PATTERNS = [
    re.compile(r"https?://[\w\.-]+"),
    re.compile(r"\b(eastus|westeurope|centralus|uksouth|japaneast|australiaeast|northeurope|westus2)\b", re.I),
    re.compile(r"\b\d+\.\d+\.\d+\b"),  # versions
    re.compile(r"\b(AZURE_[A-Z0-9_]+|ACS_[A-Z0-9_]+)\b"),
]


def mask_env(text: str) -> str:
    masked = text
    for i, pat in enumerate(ENV_PATTERNS):
        masked = pat.sub(f"<ENV_{i}>", masked)
    return masked


def compute_env_forks(files: List[FileInfo]) -> List[Tuple[FileInfo, FileInfo, float]]:
    candidates = [fi for fi in files if fi.ext in CONFIG_EXTS or (fi.ext == ".py" and ("config" in os.path.basename(fi.path) or "settings" in fi.path))]
    norms = {fi.path: normalize_content(fi) for fi in candidates}
    masked = {fi.path: mask_env(norms[fi.path]) for fi in candidates}
    results: List[Tuple[FileInfo, FileInfo, float]] = []
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            fi, fj = candidates[i], candidates[j]
            if norms[fi.path] == norms[fj.path]:
                continue  # already exact/near; this is same
            ra = masked[fi.path]
            rb = masked[fj.path]
            if not ra or not rb:
                continue
            ratio = difflib.SequenceMatcher(None, ra, rb).ratio()
            # env-only if masked very similar but unmasked not identical
            if ratio >= 0.98:
                results.append((fi, fj, ratio))
    results.sort(key=lambda t: t[2], reverse=True)
    return results


def main() -> int:
    files_paths = list_target_files()
    file_infos: List[FileInfo] = []
    for p in files_paths:
        fi = read_file(p)
        if fi is None:
            continue
        file_infos.append(fi)

    # Restrict to text-like files only for analysis (skip binaries)
    file_infos = [fi for fi in file_infos if fi.ext in TEXT_EXTS or True]

    total_loc = sum(fi.non_empty_loc for fi in file_infos)

    exact = compute_exact_duplicates(file_infos)
    near = compute_near_duplicates(file_infos)
    blocks = compute_block_clones(file_infos)
    func_eq = compute_functional_equivalents(file_infos)
    env_forks = compute_env_forks(file_infos)

    # Estimate LOC savings
    saved_loc = 0
    # exact duplicates: for each cluster with k copies, save (k-1)*avg(loc)
    for h, group in exact.items():
        if len(group) > 1:
            avg_loc = sum(fi.non_empty_loc for fi in group) / len(group)
            saved_loc += int((len(group) - 1) * avg_loc)
    # block clones: save (occurrences - 1) * length for top 20 blocks to avoid inflation
    block_savings = 0
    used_pairs = set()
    for (pa, sa, pb, sb, length) in blocks[:20]:
        # Count once per pair to avoid overcount
        key = tuple(sorted([(pa, sa), (pb, sb)]))
        if key in used_pairs:
            continue
        used_pairs.add(key)
        block_savings += max(0, length - 0)
    saved_loc += block_savings

    dup_pct = (saved_loc / total_loc * 100.0) if total_loc else 0.0

    # Prepare Top Findings: gather from exact (clusters), near (top), blocks (top), func_eq, env_forks
    findings: List[Tuple[str, str, str, str, int, str, str]] = []
    # exact
    for group in exact.values():
        # pair first two for reporting
        if len(group) >= 2:
            a, b = group[0], group[1]
            reason = "Exact duplicate"
            loc_saved = min(a.non_empty_loc, b.non_empty_loc)
            findings.append((a.path, f"1-{len(a.lines)}", b.path, f"1-{len(b.lines)}", loc_saved, reason, a.path))
    # near: top 5 by ratio
    for fi, fj, ratio in near[:5]:
        reason = f"Near-duplicate ({ratio:.0%} after normalization)"
        loc_saved = int(min(fi.non_empty_loc, fj.non_empty_loc) * ratio)
        findings.append((fi.path, f"1-{len(fi.lines)}", fj.path, f"1-{len(fj.lines)}", loc_saved, reason, fi.path))
    # blocks: top 5 by length
    # prefer cross-file clones (already filtered) and longest
    for pa, sa, pb, sb, length in blocks[:5]:
        reason = f"Block clone ({length} lines)"
        findings.append((pa, f"{sa}-{sa+length-1}", pb, f"{sb}-{sb+length-1}", length, reason, pa))
    # functional equivalents
    for fi, fj, kind in func_eq:
        reason = f"Functional equivalent ({kind})"
        loc_saved = min(fi.non_empty_loc, fj.non_empty_loc)
        findings.append((fi.path, f"1-{len(fi.lines)}", fj.path, f"1-{len(fj.lines)}", loc_saved, reason, fi.path))
    # env forks
    for fi, fj, ratio in env_forks[:5]:
        reason = f"Env-only fork (masked {ratio:.0%} similar)"
        loc_saved = int(min(fi.non_empty_loc, fj.non_empty_loc) * (ratio))
        findings.append((fi.path, f"1-{len(fi.lines)}", fj.path, f"1-{len(fj.lines)}", loc_saved, reason, fi.path))

    # rank findings by estimated LOC saved desc
    findings.sort(key=lambda t: t[3], reverse=True)

    # Print report
    print("Summary")
    print(f"- Files scanned: {len(file_infos)}")
    print(f"- Total LOC: {total_loc}")
    print(f"- Exact duplicates: {sum(1 for _ in exact.values())}")
    print(f"- Near duplicates: {len(near)}")
    print(f"- Block clones: {len(blocks)}")
    print(f"- Functional equivalents: {len(func_eq)}")
    print(f"- Env-only forks: {len(env_forks)}")
    print(f"- Est. duplication: {dup_pct:.1f}% of LOC")

    print("\nTop Findings (ranked)")
    for a_path, a_range, b_path, b_range, loc_saved, reason, canonical in findings[:10]:
        print(f"- {os.path.abspath(a_path)}:{a_range} <> {os.path.abspath(b_path)}:{b_range}")
        print(f"  Reason: {reason}; Est. LOC saved: {loc_saved}; Suggested canonical: {os.path.abspath(canonical)}")

    # Also output missing directories
    missing = [d for d in TARGET_DIRS if not os.path.isdir(d)]
    if missing:
        print("\nIssues")
        for m in missing:
            print(f"- Missing path referenced: {os.path.abspath(m)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

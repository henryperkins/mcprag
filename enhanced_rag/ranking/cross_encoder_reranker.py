"""
Cross-encoder reranker for Enhanced RAG.
Provides optional neural reranking using sentence-transformers CrossEncoder when available,
with safe fallbacks to HuggingFace or lexical overlap scoring.
"""

from __future__ import annotations

import logging
import asyncio
from typing import List, Tuple, Dict, Optional, Any

# Optional deps
try:
    from sentence_transformers import CrossEncoder as STCrossEncoder  # type: ignore
except Exception:
    STCrossEncoder = None  # type: ignore

try:
    import torch  # type: ignore
    from transformers import AutoTokenizer, AutoModelForSequenceClassification  # type: ignore
except Exception:
    torch = None  # type: ignore
    AutoTokenizer = None  # type: ignore
    AutoModelForSequenceClassification = None  # type: ignore

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """
    Lightweight wrapper that exposes an async scoring API:
    - Uses sentence-transformers CrossEncoder if installed.
    - Falls back to HuggingFace transformers sequence classification heads.
    - Falls back to lexical Jaccard overlap if no ML dependencies are present.

    Methods:
      async_score(query, candidates) -> Dict[id, score in 0..1]

    Candidates format: List[(doc_id, text)]
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2", batch_size: int = 32, device: Optional[str] = None):
        self.model_name = model_name
        self.batch_size = max(1, int(batch_size))
        self.device = device
        self._st_model = None
        self._hf_model = None
        self._hf_tokenizer = None
        self._loaded = False

    def _ensure_loaded(self):
        if self._loaded:
            return
        # Try sentence-transformers first
        if STCrossEncoder is not None:
            try:
                self._st_model = STCrossEncoder(self.model_name, device=self.device)
                self._loaded = True
                logger.info("CrossEncoderReranker: loaded sentence-transformers model '%s'", self.model_name)
                return
            except Exception as e:
                logger.warning("CrossEncoderReranker: ST load failed: %s", e)
                self._st_model = None
        # Try HuggingFace fallback
        if AutoTokenizer is not None and AutoModelForSequenceClassification is not None:
            try:
                self._hf_tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self._hf_model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
                if torch is not None:
                    dev = self.device or ("cuda" if torch.cuda.is_available() else "cpu")
                    self._hf_model.to(dev)
                self._loaded = True
                logger.info("CrossEncoderReranker: loaded HF model '%s'", self.model_name)
                return
            except Exception as e:
                logger.warning("CrossEncoderReranker: HF load failed: %s", e)
                self._hf_model = None
                self._hf_tokenizer = None
        # No ML deps, lexical fallback only
        self._loaded = True
        logger.info("CrossEncoderReranker: using lexical fallback (no ML dependencies available)")

    def _score_lexical(self, query: str, texts: List[str]) -> List[float]:
        """Simple Jaccard overlap between query and each text, normalized to 0..1."""
        q_tokens = self._keywords(query)
        scores: List[float] = []
        for t in texts:
            t_tokens = self._keywords(t or "")
            if not q_tokens and not t_tokens:
                scores.append(0.0)
                continue
            inter = len(q_tokens & t_tokens)
            union = len(q_tokens | t_tokens) or 1
            scores.append(inter / union)
        return scores

    def _keywords(self, text: str) -> set:
        import re
        words = re.findall(r"\b[a-zA-Z_]\w+\b", (text or "").lower())
        stop = {"the","is","at","which","on","and","a","an","as","by","for","if","in","it","of","or","to"}
        return {w for w in words if len(w) > 2 and w not in stop}

    def _normalize(self, scores: List[float]) -> List[float]:
        if not scores:
            return scores
        # Replace NaN/inf
        clean = []
        for s in scores:
            try:
                if s != s or s == float("inf") or s == float("-inf"):
                    clean.append(0.0)
                else:
                    clean.append(float(s))
            except Exception:
                clean.append(0.0)
        lo = min(clean)
        hi = max(clean)
        if hi <= lo:
            return [0.5 for _ in clean]
        rng = hi - lo
        return [(s - lo) / rng for s in clean]

    def _score_with_st(self, query: str, texts: List[str]) -> List[float]:
        assert self._st_model is not None
        pairs = [(query, t if t is not None else "") for t in texts]
        try:
            scores = self._st_model.predict(pairs, batch_size=self.batch_size, show_progress_bar=False)
            return self._normalize([float(s) for s in scores])
        except Exception as e:
            logger.warning("CrossEncoderReranker: ST predict failed: %s", e)
            return self._score_lexical(query, texts)

    def _score_with_hf(self, query: str, texts: List[str]) -> List[float]:
        assert self._hf_model is not None and self._hf_tokenizer is not None
        all_scores: List[float] = []
        try:
            model = self._hf_model
            tok = self._hf_tokenizer
            if torch is None:
                return self._score_lexical(query, texts)
            dev = next(model.parameters()).device  # type: ignore
            for i in range(0, len(texts), self.batch_size):
                batch = texts[i:i+self.batch_size]
                inputs = tok([query]*len(batch), batch, padding=True, truncation=True, return_tensors="pt", max_length=512)
                inputs = {k: v.to(dev) for k, v in inputs.items()}
                with torch.no_grad():  # type: ignore
                    out = model(**inputs)
                logits = out.logits
                if logits.shape[-1] == 1:
                    # sigmoid for binary relevance
                    probs = torch.sigmoid(logits).squeeze(-1)  # type: ignore
                else:
                    probs = torch.softmax(logits, dim=-1)[..., -1]  # type: ignore
                all_scores.extend([float(x) for x in probs.detach().cpu().tolist()])  # type: ignore
            return self._normalize(all_scores)
        except Exception as e:
            logger.warning("CrossEncoderReranker: HF predict failed: %s", e)
            return self._score_lexical(query, texts)

    def score(self, query: str, candidates: List[Tuple[str, str]]) -> Dict[str, float]:
        """
        Synchronous scoring API (used under the hood by async_score).
        Returns dict {doc_id: normalized_score}
        """
        self._ensure_loaded()
        ids = [cid for cid, _ in candidates]
        texts = [txt for _, txt in candidates]

        if self._st_model is not None:
            scores = self._score_with_st(query, texts)
        elif self._hf_model is not None:
            scores = self._score_with_hf(query, texts)
        else:
            scores = self._score_lexical(query, texts)

        # Align lengths safely
        if len(scores) != len(ids):
            logger.debug("CrossEncoderReranker: score length mismatch (%d != %d)", len(scores), len(ids))
            m = min(len(scores), len(ids))
            ids = ids[:m]
            scores = scores[:m]
        return {i: s for i, s in zip(ids, scores)}

    async def async_score(self, query: str, candidates: List[Tuple[str, str]]) -> Dict[str, float]:
        """
        Async scoring that offloads heavy CPU work to a thread executor when needed.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.score, query, candidates)
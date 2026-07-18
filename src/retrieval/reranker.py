"""Cross-encoder reranker for NexusRAG.

Uses Gemini as an LLM-based relevance scorer to rerank the fused
candidate list produced by HybridRetriever.

Why Gemini instead of a local cross-encoder?
- Avoids a 1.3 GB local BAAI/bge-reranker-large download
- Uses the same API key already configured for embeddings + generation
- Comparable quality for enterprise RAG at this scale

Scoring approach
----------------
For each (query, passage) pair we ask Gemini to assign a relevance
score from 0–10 with a compact JSON response.  Passages are reranked
by descending score and the top-K are returned.
"""

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

import requests

from src.config import config

logger = logging.getLogger(__name__)

_SCORE_PROMPT = """\
You are a relevance scoring engine for an enterprise search system.

Given a user question and a text passage, rate how relevant the passage \
is to answering the question.

Score from 0 to 10:
  10 = Passage directly and completely answers the question
   7 = Passage is highly relevant and contains key information
   4 = Passage is somewhat relevant but only partially addresses the question
   1 = Passage is tangentially related
   0 = Passage is irrelevant

Respond with ONLY a JSON object: {{"score": <integer 0-10>}}

Question: {query}

Passage: {passage}
"""


class CrossEncoderReranker:
    """Reranks retrieved candidates using Gemini-based relevance scoring.

    Args:
        top_k: Number of top results to return after reranking.
        model: Gemini model name (defaults to ``config.GEMINI_MODEL``).
        api_key: Gemini API key (defaults to ``config.GEMINI_API_KEY``).
        passage_max_chars: Maximum passage length sent to the LLM
            (longer passages are truncated to control token cost).
    """

    _BASE = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        top_k: int = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        passage_max_chars: int = 800,
    ):
        self.top_k = top_k or config.RERANK_TOP_K
        self._model = (model or config.GEMINI_MODEL).split("/")[-1]
        self._api_key = api_key or config.GEMINI_API_KEY
        self._passage_max_chars = passage_max_chars
        self._session: Optional[requests.Session] = None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_session(self) -> requests.Session:
        if self._session is None:
            if not self._api_key:
                raise RuntimeError(
                    "GEMINI_API_KEY is not set. Add it to your .env file."
                )
            self._session = requests.Session()
            self._session.headers.update(
                {"Content-Type": "application/json", "Accept-Encoding": "identity"}
            )
        return self._session

    def _score_one(self, query: str, passage: str) -> float:
        """Ask Gemini to score a single (query, passage) pair.

        Returns a float in [0, 10]; defaults to 0.0 on error.
        Retries up to 3 times on 429 rate-limit responses.
        """
        truncated = passage[: self._passage_max_chars]
        prompt = _SCORE_PROMPT.format(query=query, passage=truncated)

        session = self._get_session()
        url = (
            f"{self._BASE}/models/{self._model}:generateContent"
            f"?key={self._api_key}"
        )
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 32,
            },
        }

        wait_secs = 15
        for attempt in range(1, 4):   # up to 3 attempts
            try:
                resp = session.post(url, json=body, timeout=15)

                if resp.status_code == 429:
                    if attempt < 3:
                        logger.warning(
                            "Reranker rate-limited (429) - waiting %ds (retry %d/3)",
                            wait_secs, attempt,
                        )
                        time.sleep(wait_secs)
                        wait_secs *= 2
                        continue
                    logger.debug("Reranker 429 after all retries, score=0.0")
                    return 0.0

                if not resp.ok:
                    logger.debug("Reranker API error %s: %s", resp.status_code, resp.text[:200])
                    return 0.0

                raw_text = (
                    resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                    .strip()
                )
                raw_text = re.sub(r"```(?:json)?", "", raw_text).strip().strip("`")
                data = json.loads(raw_text)
                return float(data.get("score", 0))

            except Exception as exc:
                logger.debug("Reranker scoring failed: %s", exc)
                return 0.0

        return 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def rerank(
        self, query: str, candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Rerank *candidates* by Gemini relevance score.

        Args:
            query: The original user question.
            candidates: List of chunk dicts from the hybrid retriever
                (each must have a ``"content"`` key).

        Returns:
            Top-K chunk dicts sorted by descending relevance score.
            Each dict gains a ``"rerank_score"`` key.
        """
        if not candidates:
            return []

        logger.info(
            "Reranking %d candidates for query: '%s'",
            len(candidates),
            query[:60],
        )

        scored: List[Dict[str, Any]] = []
        for idx, chunk in enumerate(candidates):
            passage = chunk.get("content", "")
            score = self._score_one(query, passage)
            scored.append({**chunk, "rerank_score": score})
            logger.debug(
                "  [%d/%d] chunk_id=%s  rerank_score=%.1f",
                idx + 1,
                len(candidates),
                chunk.get("chunk_id", "?"),
                score,
            )

        scored.sort(key=lambda c: c["rerank_score"], reverse=True)
        top = scored[: self.top_k]
        logger.info(
            "Reranking complete — kept top %d (scores: %s)",
            len(top),
            [f"{c['rerank_score']:.1f}" for c in top],
        )
        return top

"""Query rewriting module for NexusRAG.

Uses Gemini to expand a single user query into multiple semantically
varied variants.  Searching with all variants and fusing the results
(via RRF) consistently improves recall by 15-25 % compared with using
only the original query.

Technique: Multi-Query Retrieval
Reference: LangChain MultiQueryRetriever / RAG-Fusion
"""

import json
import logging
import re
import time
from typing import List, Optional

import requests

from src.config import config

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an expert at reformulating search queries for an enterprise \
knowledge base.

Given a user question, generate {n} alternative search queries that \
capture different phrasings, perspectives, and keyword combinations to \
maximise retrieval recall.  The queries should:
- Cover different terminology (formal/informal, acronyms, synonyms)
- Focus on different facets of the question when relevant
- Stay factually faithful — do NOT change the intent

Return ONLY a JSON array of strings, no explanation.
Example output: ["query 1", "query 2", "query 3"]
"""


class QueryRewriter:
    """Generates multi-query expansions using the Gemini LLM.

    Args:
        n_variants: Number of alternative queries to generate (default 3).
        model: Gemini model name (defaults to ``config.GEMINI_MODEL``).
        api_key: Gemini API key (defaults to ``config.GEMINI_API_KEY``).
    """

    _BASE = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        n_variants: int = 3,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.n_variants = n_variants
        self._model = (model or config.GEMINI_MODEL).split("/")[-1]
        self._api_key = api_key or config.GEMINI_API_KEY
        self._session: Optional[requests.Session] = None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_session(self) -> requests.Session:
        if self._session is None:
            if not self._api_key:
                raise RuntimeError(
                    "GEMINI_API_KEY is not set. "
                    "Add it to your .env file: GEMINI_API_KEY=your-key"
                )
            self._session = requests.Session()
            self._session.headers.update(
                {"Content-Type": "application/json", "Accept-Encoding": "identity"}
            )
        return self._session

    def _call_gemini(self, prompt: str, max_retries: int = 3) -> str:
        """Send *prompt* to Gemini and return the raw text response.

        Retries up to *max_retries* times on 429 rate-limit responses
        using exponential backoff (15s -> 30s -> 60s).
        """
        session = self._get_session()
        url = f"{self._BASE}/models/{self._model}:generateContent?key={self._api_key}"
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 512,
            },
        }

        wait_secs = 15
        for attempt in range(1, max_retries + 1):
            resp = session.post(url, json=body, timeout=20)

            if resp.status_code == 429:
                if attempt < max_retries:
                    logger.warning(
                        "QueryRewriter rate-limited (429) - waiting %ds (retry %d/%d)",
                        wait_secs, attempt, max_retries,
                    )
                    time.sleep(wait_secs)
                    wait_secs *= 2
                    continue
                raise RuntimeError(
                    f"Gemini API error {resp.status_code}: {resp.text[:400]}"
                )

            if not resp.ok:
                raise RuntimeError(
                    f"Gemini API error {resp.status_code}: {resp.text[:400]}"
                )

            data = resp.json()
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError) as exc:
                raise RuntimeError(f"Unexpected Gemini response format: {data}") from exc

        raise RuntimeError("Gemini API failed after all retries.")

    @staticmethod
    def _parse_json_array(raw: str) -> List[str]:
        """Extract the JSON string array from an LLM response."""
        # Strip markdown code fences if present
        raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
        # Find the first [...] block
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
                if isinstance(result, list):
                    return [str(q) for q in result if str(q).strip()]
            except json.JSONDecodeError:
                pass
        # Fallback: split on newlines and clean up
        lines = [l.strip().strip('"-,') for l in raw.splitlines()]
        return [l for l in lines if len(l) > 5]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def rewrite(self, query: str) -> List[str]:
        """Generate query variants for *query*.

        Args:
            query: Original user question.

        Returns:
            List starting with the original query, followed by LLM-generated
            variants.  Falls back to ``[query]`` on any API error.
        """
        if not query.strip():
            return [query]

        prompt = (
            _SYSTEM_PROMPT.format(n=self.n_variants)
            + f"\n\nUser question: {query}"
        )

        try:
            raw = self._call_gemini(prompt)
            variants = self._parse_json_array(raw)
            logger.info(
                "QueryRewriter generated %d variants for query: '%s'",
                len(variants),
                query[:60],
            )
            # Always include the original at the front
            all_queries = [query] + [v for v in variants if v != query]
            return all_queries[: self.n_variants + 1]
        except Exception as exc:
            logger.warning("QueryRewriter failed (%s) — using original query.", exc)
            return [query]

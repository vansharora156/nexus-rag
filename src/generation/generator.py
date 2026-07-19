"""Answer generation module for NexusRAG.

Calls Gemini to produce a grounded, citation-aware answer from the
retrieved context.  Uses the lightweight ``requests``-only pattern
(no SDK import) to stay consistent with the embedder and avoid any
gRPC / protobuf memory overhead.

Prompt design
-------------
The system prompt instructs Gemini to:
1. Answer ONLY from the provided context.
2. Use inline ``[N]`` citation markers that match the numbered sources.
3. Indicate when the answer is not present in the context.
4. Keep the answer concise and factual.
"""

import logging
import time
from typing import Any, Dict, List, Optional

import requests

from src.config import config
from src.generation.citation_formatter import Citation, CitationFormatter

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an expert enterprise knowledge assistant for AskTheCompany.

Your task is to answer the user's question using ONLY the provided source \
passages below.  Rules:

1. Ground every claim in the context — cite sources with [N] inline.
2. If the answer spans multiple sources, cite all relevant ones: [1][3].
3. If the context does not contain the answer, say:
   "I could not find this information in the available documents."
4. Be concise, factual, and professional.
5. For tabular data, present it as a formatted table when helpful.
6. Do NOT fabricate information beyond what the context states.

--- CONTEXT ---
{context}
--- END CONTEXT ---

Question: {question}

Answer:"""


class GeminiGenerator:
    """Generates grounded answers using Gemini + retrieved context chunks.

    Args:
        model: Gemini model name (defaults to ``config.GEMINI_MODEL``).
        api_key: Gemini API key (defaults to ``config.GEMINI_API_KEY``).
        temperature: LLM temperature (0.0 for factual, deterministic answers).
        max_output_tokens: Max tokens for the generated answer.
    """

    _BASE = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.1,
        max_output_tokens: int = 1024,
    ):
        self._model = (model or config.GEMINI_MODEL).split("/")[-1]
        self._api_key = api_key or config.GEMINI_API_KEY
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens
        self._session: Optional[requests.Session] = None
        self._formatter = CitationFormatter()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(
                {"Content-Type": "application/json", "Accept-Encoding": "identity"}
            )
            logger.info("GeminiGenerator ready (model=%s)", self._model)
        return self._session

    def _call_gemini(self, prompt: str, max_retries: int = 3) -> str:
        """Send the assembled prompt to Gemini and return the answer text.

        Automatically retries on 429 rate-limit responses using exponential
        backoff (15s → 30s → 60s) so that bursts of questions don't fail
        on the free-tier 5 req/min quota.
        """
        if not self._api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. "
                "Add it to your .env file: GEMINI_API_KEY=your-key"
            )
        session = self._get_session()
        url = (
            f"{self._BASE}/models/{self._model}:generateContent"
            f"?key={self._api_key}"
        )
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self._temperature,
                "maxOutputTokens": self._max_output_tokens,
            },
        }

        wait_secs = 15
        for attempt in range(1, max_retries + 1):
            resp = session.post(url, json=body, timeout=30)

            if resp.status_code == 429:
                if attempt < max_retries:
                    logger.warning(
                        "Gemini rate-limited (429) — waiting %ds before retry %d/%d",
                        wait_secs, attempt, max_retries,
                    )
                    time.sleep(wait_secs)
                    wait_secs *= 2   # 15 → 30 → 60
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
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            except (KeyError, IndexError) as exc:
                raise RuntimeError(f"Unexpected Gemini response format: {data}") from exc

        raise RuntimeError("Gemini API failed after all retries.")

    def _call_groq(self, prompt: str, max_retries: int = 3) -> str:
        """Send the prompt to Groq Chat Completion API and return the answer.

        Retries on 429 rate-limits using exponential backoff.
        """
        session = self._get_session()
        api_key = config.GROQ_API_KEY
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to your .env file: GROQ_API_KEY=your-key"
            )
        model = config.GROQ_MODEL
        url = "https://api.groq.com/openai/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are an expert enterprise knowledge assistant for AskTheCompany."},
                {"role": "user", "content": prompt}
            ],
            "temperature": self._temperature,
            "max_tokens": self._max_output_tokens,
        }

        wait_secs = 5
        for attempt in range(1, max_retries + 1):
            try:
                resp = session.post(url, json=body, headers=headers, timeout=30)

                if resp.status_code == 429:
                    if attempt < max_retries:
                        logger.warning(
                            "Groq rate-limited (429) — waiting %ds before retry %d/%d",
                            wait_secs, attempt, max_retries
                        )
                        time.sleep(wait_secs)
                        wait_secs *= 2
                        continue
                    raise RuntimeError(f"Groq API error 429: {resp.text[:400]}")

                if not resp.ok:
                    raise RuntimeError(f"Groq API error {resp.status_code}: {resp.text[:400]}")

                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            except Exception as exc:
                if attempt == max_retries:
                    raise exc
                logger.warning("Groq API call attempt %d failed: %s. Retrying...", attempt, exc)
                time.sleep(wait_secs)
                wait_secs *= 2

        raise RuntimeError("Groq API failed after all retries.")

    def _call_llm(self, prompt: str, max_retries: int = 3) -> str:
        """Call the configured LLM backend (Gemini or Groq)."""
        backend = (config.LLM_BACKEND or "gemini").lower()
        if backend == "groq":
            return self._call_groq(prompt, max_retries)
        return self._call_gemini(prompt, max_retries)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate a grounded answer for *query* from the retrieved *chunks*.

        Args:
            query: Original user question.
            chunks: Reranked chunk dicts from :class:`HybridRetriever`.

        Returns:
            Dict with keys:
            - ``"answer"``        — the generated answer text (str)
            - ``"citations"``     — list of citation dicts
            - ``"context_block"`` — the context string sent to the LLM
            - ``"num_sources"``   — number of source chunks used
        """
        if not chunks:
            return {
                "answer": (
                    "I could not find any relevant documents to answer your question. "
                    "Please check that the knowledge base has been ingested."
                ),
                "citations": [],
                "context_block": "",
                "num_sources": 0,
            }

        # Build structured citations
        citations: List[Citation] = self._formatter.format(chunks)
        context_block = self._formatter.build_context_block(citations)

        # Assemble the full prompt
        prompt = _SYSTEM_PROMPT.format(
            context=context_block,
            question=query,
        )

        logger.info(
            "Generating answer for query '%s' with %d source(s) using backend '%s'.",
            query[:60],
            len(citations),
            config.LLM_BACKEND,
        )

        try:
            answer = self._call_llm(prompt)
        except Exception as exc:
            logger.error("Answer generation failed: %s", exc)
            answer = (
                "I encountered an error while generating the answer. "
                f"Detail: {exc}"
            )

        return {
            "answer": answer,
            "citations": [c.to_dict() for c in citations],
            "context_block": context_block,
            "num_sources": len(citations),
        }

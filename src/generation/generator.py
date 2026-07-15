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
            if not self._api_key:
                raise RuntimeError(
                    "GEMINI_API_KEY is not set. "
                    "Add it to your .env file: GEMINI_API_KEY=your-key"
                )
            self._session = requests.Session()
            self._session.headers.update(
                {"Content-Type": "application/json", "Accept-Encoding": "identity"}
            )
            logger.info("GeminiGenerator ready (model=%s)", self._model)
        return self._session

    def _call_gemini(self, prompt: str) -> str:
        """Send the assembled prompt to Gemini and return the answer text."""
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
        resp = session.post(url, json=body, timeout=30)
        if not resp.ok:
            raise RuntimeError(
                f"Gemini API error {resp.status_code}: {resp.text[:400]}"
            )
        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError) as exc:
            raise RuntimeError(f"Unexpected Gemini response format: {data}") from exc

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
            "Generating answer for query '%s' with %d source(s).",
            query[:60],
            len(citations),
        )

        try:
            answer = self._call_gemini(prompt)
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

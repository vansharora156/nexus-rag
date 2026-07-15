"""Query pipeline orchestrator for NexusRAG.

Ties together the retrieval and generation layers into a single
end-to-end ``QueryPipeline`` that can be called from the FastAPI routes
or from scripts.

Flow
----
User query + username
        ↓
  PermissionsManager  →  resolve user roles
        ↓
  HybridRetriever     →  multi-query RRF-fused dense+sparse retrieval
                         + ACL filtering + cross-encoder reranking
        ↓
  GeminiGenerator     →  grounded answer with numbered citations
        ↓
  Structured response dict
"""

import logging
import time
from typing import Any, Dict, Optional

from src.config import config
from src.indexing.embedder import Embedder
from src.indexing.vector_store import VectorStore
from src.indexing.bm25_index import BM25Index
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.query_rewriter import QueryRewriter
from src.retrieval.reranker import CrossEncoderReranker
from src.generation.generator import GeminiGenerator

logger = logging.getLogger(__name__)


class QueryPipeline:
    """End-to-end query orchestrator for AskTheCompany.

    Initialise once at application startup (all components are lazy-loaded
    internally) and call :meth:`query` for each incoming request.

    Args:
        use_reranker: Enable/disable the cross-encoder reranking step.
        use_query_rewriting: Enable/disable multi-query expansion.
        top_k: Final number of context chunks to pass to the generator.
    """

    def __init__(
        self,
        use_reranker: bool = True,
        use_query_rewriting: bool = True,
        top_k: Optional[int] = None,
    ):
        self._top_k = top_k or config.RERANK_TOP_K

        # Initialise all components
        logger.info("Initialising QueryPipeline components…")

        self.embedder = Embedder()
        self.vector_store = VectorStore()
        self.bm25_index = BM25Index()

        # Attempt to load the saved BM25 index from disk
        try:
            self.bm25_index.load()
            logger.info("BM25 index loaded from disk.")
        except Exception as exc:
            logger.warning(
                "Could not load BM25 index (%s). "
                "Sparse retrieval will be unavailable until ingest is run.",
                exc,
            )

        self.retriever = HybridRetriever(
            vector_store=self.vector_store,
            bm25_index=self.bm25_index,
            embedder=self.embedder,
            query_rewriter=QueryRewriter(),
            reranker=CrossEncoderReranker(top_k=self._top_k),
            use_reranker=use_reranker,
            use_query_rewriting=use_query_rewriting,
        )

        self.generator = GeminiGenerator()
        logger.info("QueryPipeline ready.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def query(
        self,
        question: str,
        username: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Answer *question* for *username* with grounded citations.

        Args:
            question: The natural-language question from the user.
            username: Authenticated username for ACL enforcement.
                Pass ``None`` to skip permission filtering (admin / dev mode).
            top_k: Number of source chunks to retrieve and cite
                (defaults to ``config.RERANK_TOP_K``).

        Returns:
            Dict with the following keys:

            ``answer``          str   — Generated answer with inline [N] citations.
            ``citations``       list  — Structured citation objects.
            ``query_variants``  list  — Queries searched (original + rewrites).
            ``num_sources``     int   — Number of chunks used.
            ``elapsed_ms``      float — End-to-end latency in milliseconds.
            ``username``        str   — The requesting user (or "anonymous").
        """
        t0 = time.perf_counter()
        effective_top_k = top_k or self._top_k

        logger.info(
            "QueryPipeline.query: user='%s' top_k=%d question='%s'",
            username or "anonymous",
            effective_top_k,
            question[:80],
        )

        # 1. Retrieval
        chunks, query_variants = self.retriever.retrieve(
            query=question,
            username=username,
            top_k=effective_top_k,
        )
        logger.info("Retrieved %d chunks after full retrieval pipeline.", len(chunks))

        # 2. Generation
        generation_result = self.generator.generate(
            query=question,
            chunks=chunks,
        )

        elapsed_ms = (time.perf_counter() - t0) * 1000

        return {
            "answer": generation_result["answer"],
            "citations": generation_result["citations"],
            "query_variants": query_variants,
            "num_sources": generation_result["num_sources"],
            "elapsed_ms": round(elapsed_ms, 1),
            "username": username or "anonymous",
        }

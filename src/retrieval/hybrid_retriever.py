"""Hybrid retrieval orchestrator for NexusRAG.

Implements the full multi-stage retrieval pipeline:

1. **Query rewriting** — generates N semantically diverse query variants
   using :class:`~src.retrieval.query_rewriter.QueryRewriter`.

2. **Dense retrieval** — Qdrant cosine-similarity search for each variant
   using the pre-built vector store.

3. **Sparse retrieval** — BM25 keyword search for each variant using the
   pre-built BM25 index.

4. **Reciprocal Rank Fusion (RRF)** — merges all ranked candidate lists
   into a single fused ranking that rewards consistent high placement.

5. **ACL filtering** — applies the user's permission roles to ensure
   only authorised documents are returned.

6. **Cross-encoder reranking** — final Gemini-scored pass over the top
   candidates to select the most relevant chunks.

Usage::

    retriever = HybridRetriever(vector_store, bm25_index, embedder)
    chunks = retriever.retrieve(query="vacation policy", username="alice")
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from src.config import config
from src.indexing.embedder import Embedder
from src.indexing.vector_store import VectorStore
from src.indexing.bm25_index import BM25Index
from src.retrieval.query_rewriter import QueryRewriter
from src.retrieval.reranker import CrossEncoderReranker
from src.retrieval.permission_filter import get_user_roles, filter_chunks_by_acl

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion
# ---------------------------------------------------------------------------

def reciprocal_rank_fusion(
    ranked_lists: List[List[Dict[str, Any]]],
    k: int = 60,
) -> List[Dict[str, Any]]:
    """Merge multiple ranked result lists using Reciprocal Rank Fusion.

    RRF score for a document ``d`` across lists ``L_1 … L_n``:

        RRF(d) = Σ_i  1 / (k + rank_i(d))

    Documents absent from a list receive no contribution for that list.
    The merged list is sorted by descending RRF score.

    Args:
        ranked_lists: List of ranked chunk dicts.  Each dict must have a
            ``"chunk_id"`` key.
        k: Smoothing constant (default 60 per the original RRF paper).

    Returns:
        Deduplicated list of chunk dicts, sorted by descending RRF score.
        Each dict gains a ``"rrf_score"`` key.
    """
    rrf_scores: Dict[str, float] = defaultdict(float)
    chunk_registry: Dict[str, Dict[str, Any]] = {}

    for ranked_list in ranked_lists:
        for rank_idx, chunk in enumerate(ranked_list, start=1):
            cid = chunk.get("chunk_id", "")
            if not cid:
                continue
            rrf_scores[cid] += 1.0 / (k + rank_idx)
            if cid not in chunk_registry:
                chunk_registry[cid] = chunk

    merged = []
    for cid, score in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True):
        entry = {**chunk_registry[cid], "rrf_score": score}
        merged.append(entry)

    return merged


# ---------------------------------------------------------------------------
# HybridRetriever
# ---------------------------------------------------------------------------

class HybridRetriever:
    """Orchestrates the full hybrid retrieval pipeline.

    Args:
        vector_store: Initialised :class:`VectorStore` instance.
        bm25_index: Initialised :class:`BM25Index` instance.
        embedder: Initialised :class:`Embedder` instance.
        query_rewriter: Optional :class:`QueryRewriter` (created with
            defaults when not provided).
        reranker: Optional :class:`CrossEncoderReranker` (created with
            defaults when not provided).
        retrieval_top_k: Candidate count from each retriever per query
            variant (default from config).
        rrf_k: RRF smoothing constant (default from config).
        use_reranker: Whether to apply cross-encoder reranking (default True).
        use_query_rewriting: Whether to expand the query (default True).
    """

    def __init__(
        self,
        vector_store: VectorStore,
        bm25_index: BM25Index,
        embedder: Embedder,
        query_rewriter: Optional[QueryRewriter] = None,
        reranker: Optional[CrossEncoderReranker] = None,
        retrieval_top_k: int = None,
        rrf_k: int = None,
        use_reranker: bool = True,
        use_query_rewriting: bool = True,
    ):
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        self.embedder = embedder
        self.query_rewriter = query_rewriter or QueryRewriter()
        self.reranker = reranker or CrossEncoderReranker()
        self.retrieval_top_k = retrieval_top_k or config.RETRIEVAL_TOP_K
        self.rrf_k = rrf_k or config.RRF_K
        self.use_reranker = use_reranker
        self.use_query_rewriting = use_query_rewriting

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _dense_search(
        self, query: str, active_roles: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Embed *query* and search Qdrant."""
        embedding = self.embedder.embed_query(query)
        return self.vector_store.search(
            query_embedding=embedding,
            top_k=self.retrieval_top_k,
            active_roles=active_roles,
        )

    def _sparse_search(
        self, query: str, active_roles: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """BM25 keyword search."""
        try:
            return self.bm25_index.search(
                query=query,
                top_k=self.retrieval_top_k,
                active_roles=active_roles,
            )
        except RuntimeError as exc:
            logger.warning("BM25 index not available (%s) — skipping sparse search.", exc)
            return []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        username: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Run the full hybrid retrieval pipeline.

        Args:
            query: Raw user question.
            username: Authenticated user (used to resolve ACL roles).
            top_k: Final number of chunks to return (defaults to
                ``config.RERANK_TOP_K``).

        Returns:
            Tuple of ``(chunks, query_variants)`` where:
            - ``chunks`` is the reranked list of chunk dicts.
            - ``query_variants`` is the list of queries that were searched.
        """
        final_top_k = top_k or config.RERANK_TOP_K

        # 1. Resolve user permissions
        active_roles: Optional[List[str]] = None
        if username:
            active_roles = get_user_roles(username)
            logger.info("User '%s' → roles: %s", username, active_roles)

        # 2. Query rewriting
        if self.use_query_rewriting:
            query_variants = self.query_rewriter.rewrite(query)
        else:
            query_variants = [query]

        logger.info(
            "Searching with %d query variant(s): %s",
            len(query_variants),
            [q[:50] for q in query_variants],
        )

        # 3. Collect ranked lists from dense + sparse for every variant
        all_ranked_lists: List[List[Dict[str, Any]]] = []

        for variant in query_variants:
            dense_results = self._dense_search(variant, active_roles=active_roles)
            sparse_results = self._sparse_search(variant, active_roles=active_roles)
            logger.debug(
                "  Variant '%s': dense=%d sparse=%d",
                variant[:40],
                len(dense_results),
                len(sparse_results),
            )
            if dense_results:
                all_ranked_lists.append(dense_results)
            if sparse_results:
                all_ranked_lists.append(sparse_results)

        if not all_ranked_lists:
            logger.warning("No results returned from any retriever.")
            return [], query_variants

        # 4. Reciprocal Rank Fusion
        fused = reciprocal_rank_fusion(all_ranked_lists, k=self.rrf_k)
        logger.info("RRF produced %d unique candidates.", len(fused))

        # 5. ACL safety-net filter (belt-and-suspenders, ACL already applied in retrieval)
        if username:
            fused = filter_chunks_by_acl(fused, username)
            logger.info("After ACL safety filter: %d candidates.", len(fused))

        # 6. Cross-encoder reranking
        if self.use_reranker and fused:
            # Send up to 2× final_top_k candidates to the reranker to limit API calls
            candidates = fused[: final_top_k * 2]
            reranked = self.reranker.rerank(query=query, candidates=candidates)
        else:
            reranked = fused[:final_top_k]

        return reranked[:final_top_k], query_variants

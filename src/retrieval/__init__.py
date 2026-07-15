"""NexusRAG retrieval layer.

Exports the primary retrieval components for use by the query pipeline.
"""

from src.retrieval.hybrid_retriever import HybridRetriever, reciprocal_rank_fusion
from src.retrieval.query_rewriter import QueryRewriter
from src.retrieval.reranker import CrossEncoderReranker
from src.retrieval.permission_filter import get_user_roles, filter_chunks_by_acl

__all__ = [
    "HybridRetriever",
    "reciprocal_rank_fusion",
    "QueryRewriter",
    "CrossEncoderReranker",
    "get_user_roles",
    "filter_chunks_by_acl",
]

"""Deduplication module using MinHash LSH for NexusRAG."""

from .minhash_dedup import MinHashDeduplicator

__all__ = [
    "MinHashDeduplicator",
]

"""NexusRAG pipeline orchestration layer.

Exports both pipeline orchestrators:
- IngestionPipeline: document parsing → chunking → dedup → embed → index
- QueryPipeline:     query rewrite → retrieve → rerank → generate
"""

from src.pipeline.ingest import IngestionPipeline
from src.pipeline.query import QueryPipeline

__all__ = ["IngestionPipeline", "QueryPipeline"]

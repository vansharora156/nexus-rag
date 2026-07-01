"""Hybrid chunking module for NexusRAG.

Combines structural-first chunking with semantic-second splitting.
"""

import logging
from typing import List

from src.config import config
from src.parsers.base import ParsedDocument
from .structural_chunker import StructuralChunker, Chunk
from .semantic_chunker import SemanticChunker

logger = logging.getLogger(__name__)


class HybridChunker:
    """Pipelines structural and semantic split engines.

    First preserves structural bounds (lists, pages, tables, threads) and then
    semantically splits any oversized blocks using sentence embeddings.
    """

    def __init__(self):
        self.structural = StructuralChunker(
            max_tokens=config.CHUNK_MAX_TOKENS,
            overlap_tokens=config.CHUNK_OVERLAP_TOKENS
        )
        self.semantic = SemanticChunker(
            embedding_model_name=config.EMBEDDING_MODEL,
            max_tokens=config.CHUNK_MAX_TOKENS
        )

    def chunk_documents(self, documents: List[ParsedDocument]) -> List[Chunk]:
        """Process a list of ParsedDocuments through the hybrid chunking pipeline.

        Args:
            documents: List of ParsedDocuments.

        Returns:
            A consolidated list of Chunk objects.
        """
        all_chunks: List[Chunk] = []

        for doc in documents:
            logger.info(f"Chunking document '{doc.title}' ({doc.source_type.value})")
            
            # Step 1: Structural layout chunking
            struct_chunks = self.structural.chunk_document(doc)
            
            # Step 2: Semantic refinement for large text blocks
            final_chunks = self.semantic.split_chunks(struct_chunks)
            
            all_chunks.extend(final_chunks)

        logger.info(f"Generated {len(all_chunks)} hybrid chunks from {len(documents)} parsed documents")
        return all_chunks

"""
Hybrid chunking module for NexusRAG.

Combines structural-first chunking with semantic-second splitting.

Pipeline
--------
ParsedDocument
      │
      ▼
StructuralChunker
      │
      ▼
SemanticChunker
      │
      ▼
Final Chunk List
"""

import logging
from typing import List

from src.config import config
from src.parsers.base import ParsedDocument
from .structural_chunker import StructuralChunker, Chunk
from .semantic_chunker import SemanticChunker

logger = logging.getLogger(__name__)


class HybridChunker:
    """
    Hybrid chunking pipeline.

    Workflow:
        1. Perform structure-aware chunking (pages, headings, tables, etc.).
        2. Further split oversized chunks semantically.
        3. Return retrieval-ready Chunk objects.
    """

    def __init__(self):
        """Initialize structural and semantic chunkers."""

        self.structural = StructuralChunker(
            max_tokens=config.CHUNK_MAX_TOKENS,
            overlap_tokens=config.CHUNK_OVERLAP_TOKENS,
        )

        self.semantic = SemanticChunker(
            embedding_model_name=config.EMBEDDING_MODEL,
            max_tokens=config.CHUNK_MAX_TOKENS,
        )

        logger.info("HybridChunker initialized successfully.")

    def chunk_documents(
        self,
        documents: List[ParsedDocument],
    ) -> List[Chunk]:
        """
        Chunk a collection of ParsedDocuments.

        Args:
            documents:
                List of ParsedDocument objects.

        Returns:
            List of final Chunk objects.
        """

        all_chunks: List[Chunk] = []

        logger.info(
            "Starting chunking for %d documents.",
            len(documents),
        )

        for doc in documents:

            # Skip empty documents
            if not doc.content.strip():

                logger.warning(
                    "Skipping empty document '%s'.",
                    doc.title,
                )

                continue

            logger.info(
                "Chunking document '%s' (%s).",
                doc.title,
                doc.source_type.value,
            )

            try:

                # -------------------------------
                # Step 1 : Structural Chunking
                # -------------------------------
                structural_chunks = self.structural.chunk_document(doc)

                logger.debug(
                    "Generated %d structural chunks.",
                    len(structural_chunks),
                )

                # -------------------------------
                # Step 2 : Semantic Chunking
                # -------------------------------
                final_chunks = self.semantic.split_chunks(
                    structural_chunks
                )

                logger.debug(
                    "Generated %d final chunks after semantic refinement.",
                    len(final_chunks),
                )

                all_chunks.extend(final_chunks)

            except Exception as exc:

                logger.exception(
                    "Failed while chunking '%s': %s",
                    doc.title,
                    exc,
                )

        logger.info(
            "Chunking completed successfully."
        )

        logger.info(
            "Generated %d chunks from %d documents.",
            len(all_chunks),
            len(documents),
        )

        return all_chunks
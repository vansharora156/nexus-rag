"""Ingestion pipeline orchestration module for NexusRAG.

Coordinates document parsing, chunking, deduplication, dense embedding generation,
and storage indexing.
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

from src.parsers.registry import ParserRegistry
from src.chunking.hybrid_chunker import HybridChunker
from src.dedup.minhash_dedup import MinHashDeduplicator
from src.indexing.embedder import Embedder
from src.indexing.vector_store import VectorStore
from src.indexing.bm25_index import BM25Index

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Orchestrator for the NexusRAG document ingestion flow.

    Processes directories of raw files and registers them into the search index.
    """

    def __init__(self):
        self.registry = ParserRegistry()
        self.chunker = HybridChunker()
        self.deduplicator = MinHashDeduplicator()
        self.embedder = Embedder()
        self.vector_store = VectorStore()
        self.bm25_index = BM25Index()

    def ingest_directory(
        self, 
        data_dir: Path, 
        recreate_collection: bool = True
    ) -> Dict[str, Any]:
        """Ingest all supported documents found in a directory recursively.

        Args:
            data_dir: Path to directory containing document files.
            recreate_collection: If True, resets the Qdrant database first.

        Returns:
            Dictionary containing run statistics (files, chunks, time, etc.).
        """
        start_time = time.time()
        data_path = Path(data_dir)
        
        if not data_path.exists():
            raise FileNotFoundError(f"Data directory not found: {data_path}")

        logger.info(f"Starting ingestion scan in: {data_path.resolve()}")

        # 1. Discover and parse files
        parsed_docs = []
        files_processed = 0
        
        # Walk directory
        for file_path in data_path.glob("**/*"):
            if file_path.is_file() and self.registry.can_parse(file_path):
                try:
                    parser = self.registry.get_parser(file_path)
                    docs = parser.parse(file_path)
                    parsed_docs.extend(docs)
                    files_processed += 1
                    logger.debug(f"Parsed file: {file_path.name}")
                except Exception as e:
                    logger.error(f"Error parsing file {file_path}: {e}", exc_info=True)

        if not parsed_docs:
            logger.warning("No supported files found to ingest.")
            return {
                "files_processed": 0,
                "chunks_generated": 0,
                "duplicates_flagged": 0,
                "elapsed_seconds": time.time() - start_time
            }

        # 2. Chunk documents
        logger.info(f"Chunking {len(parsed_docs)} parsed document structures...")
        chunks = self.chunker.chunk_documents(parsed_docs)
        logger.info(f"Generated {len(chunks)} raw chunks.")

        # 3. Deduplicate chunks
        logger.info("Executing MinHash LSH near-duplicate analysis...")
        processed_chunks = self.deduplicator.deduplicate(chunks)
        dedup_stats = self.deduplicator.get_dedup_stats()
        
        # 4. Generate embeddings for Qdrant (for ALL chunks, both canonical and duplicate)
        logger.info("Generating dense embeddings for vector store...")
        chunk_texts = [c.content for c in processed_chunks]
        embeddings = self.embedder.embed_texts(chunk_texts, show_progress=False)
        
        # 5. Populate Qdrant vector database
        if recreate_collection:
            self.vector_store.recreate_collection(dimension=self.embedder.dimension)
        
        logger.info("Upserting records into Qdrant database...")
        self.vector_store.add_chunks(processed_chunks, embeddings)

        # 6. Populate BM25 Index (lexical database)
        logger.info("Building BM25 sparse keyword index...")
        self.bm25_index.build_index(processed_chunks)
        self.bm25_index.save()

        elapsed_time = time.time() - start_time
        stats = {
            "files_processed": files_processed,
            "chunks_generated": len(chunks),
            "duplicates_flagged": dedup_stats["duplicate_count"],
            "canonical_count": dedup_stats["canonical_count"],
            "elapsed_seconds": round(elapsed_time, 2)
        }

        logger.info(
            f"Ingestion pipeline execution completed in {stats['elapsed_seconds']}s. "
            f"Processed {stats['files_processed']} files -> {stats['chunks_generated']} chunks "
            f"({stats['duplicates_flagged']} duplicates, {stats['canonical_count']} canonical)."
        )
        return stats

"""Embedding generation module for NexusRAG.

Wraps sentence-transformers to generate dense vector embeddings using models
like BAAI/bge-m3.
"""

import logging
from typing import List
import numpy as np

from src.config import config

logger = logging.getLogger(__name__)


class Embedder:
    """Generates dense vector embeddings using sentence-transformers.

    Provides batch encoding for document chunks and single-sentence encoding
    for incoming user search queries.
    """

    def __init__(self, model_name: str = None):
        self.model_name = model_name or config.EMBEDDING_MODEL
        self._model = None

    @property
    def model(self):
        """Lazy-load the SentenceTransformer model to optimize startup time."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading dense embedding model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
            except ImportError:
                logger.error("sentence-transformers not installed. Install requirements first.")
                raise
        return self._model

    def embed_texts(
        self, 
        texts: List[str], 
        batch_size: int = 32, 
        show_progress: bool = True
    ) -> List[List[float]]:
        """Generate dense embeddings for a list of text strings.

        Args:
            texts: List of text inputs to embed.
            batch_size: Batch size for model inference.
            show_progress: Whether to show a progress bar.

        Returns:
            A list of float lists representing the embeddings.
        """
        if not texts:
            return []

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        """Generate dense embedding for a single query string.

        Args:
            query: User search query.

        Returns:
            A list of floats representing the embedding vector.
        """
        embedding = self.model.encode(
            query,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return embedding.tolist()

    @property
    def dimension(self) -> int:
        """Return the embedding vector dimensions (e.g. 1024 for BGE-M3)."""
        # BGE-M3 base dimension is 1024
        try:
            return self.model.get_sentence_embedding_dimension()
        except Exception:
            return 1024

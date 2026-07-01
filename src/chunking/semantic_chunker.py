"""Semantic chunking module for NexusRAG.

Performs embedding-based splitting by evaluating cosine similarity between
consecutive sentences to find topic shift boundaries.
"""

import logging
from typing import List, Optional
import numpy as np

from src.config import config
from .structural_chunker import Chunk

logger = logging.getLogger(__name__)


class SemanticChunker:
    """Semantic chunker using embedding similarity.

    Splits large text chunks at points where the cosine similarity between
    adjacent sentences falls below a threshold, indicating a change in topic.
    """

    def __init__(
        self,
        embedding_model_name: str = None,
        similarity_threshold: float = 0.35,
        max_tokens: int = 512
    ):
        self._model_name = embedding_model_name or config.EMBEDDING_MODEL
        self.similarity_threshold = similarity_threshold
        self.max_tokens = max_tokens
        self.char_limit = max_tokens * 4
        self._model = None

    @property
    def model(self):
        """Lazy-load the SentenceTransformer model to save startup latency."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading embedding model for semantic chunker: {self._model_name}")
                self._model = SentenceTransformer(self._model_name)
            except ImportError:
                logger.error("sentence-transformers not installed. Semantic chunker falling back to text splits.")
                self._model = None
        return self._model

    def find_breakpoints(self, text: str) -> List[int]:
        """Find semantic breakpoints in a string of text.

        Returns:
            A list of character indices where splits should occur.
        """
        if not text.strip():
            return []

        # Split into sentences
        sentences = self._split_sentences(text)
        if len(sentences) <= 1:
            return []

        # If model is not available, we can't do embedding similarity; fallback
        model = self.model
        if model is None:
            return []

        try:
            # Embed all sentences
            embeddings = model.encode(sentences, show_progress_bar=False)
            
            # Compute cosine similarities between consecutive sentences
            similarities = []
            for i in range(len(embeddings) - 1):
                sim = self._cosine_similarity(embeddings[i], embeddings[i + 1])
                similarities.append(sim)

            # Find breakpoints where similarity is below threshold
            breakpoints = []
            char_accum = 0
            for i, sim in enumerate(similarities):
                char_accum += len(sentences[i]) + 1  # +1 for split character
                if sim < self.similarity_threshold:
                    breakpoints.append(char_accum)
            
            return breakpoints
        except Exception as e:
            logger.warning(f"Failed to calculate semantic breakpoints: {e}")
            return []

    def split_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        """Split any chunks that exceed token limits using semantic boundaries.

        Args:
            chunks: List of structural chunks.

        Returns:
            A list of chunks (some split semantically, others unchanged).
        """
        output_chunks: List[Chunk] = []

        for chunk in chunks:
            # Tables and code blocks are not split semantically to preserve format
            if chunk.is_table or "```" in chunk.content or len(chunk.content) <= self.char_limit:
                output_chunks.append(chunk)
                continue

            breakpoints = self.find_breakpoints(chunk.content)
            if not breakpoints:
                # If no semantic splits could be determined, fallback to normal character splits
                output_chunks.append(chunk)
                continue

            # Split the chunk content at character breakpoints
            last_idx = 0
            parts = []
            for bp in breakpoints:
                parts.append(chunk.content[last_idx:bp].strip())
                last_idx = bp
            parts.append(chunk.content[last_idx:].strip())

            # Filter empty splits and build new sub-chunks
            sub_chunks_content = [p for p in parts if p]
            if len(sub_chunks_content) <= 1:
                output_chunks.append(chunk)
                continue

            # Build sub-chunks
            logger.info(f"Semantically split chunk '{chunk.chunk_id}' into {len(sub_chunks_content)} parts")
            for sub_idx, sub_content in enumerate(sub_chunks_content):
                sub_chunk_id = f"{chunk.chunk_id}_s{sub_idx:02d}"
                sub_chunk = Chunk(
                    chunk_id=sub_chunk_id,
                    doc_id=chunk.doc_id,
                    content=sub_content,
                    source_type=chunk.source_type,
                    title=chunk.title,
                    heading_path=chunk.heading_path,
                    page_number=chunk.page_number,
                    row_range=chunk.row_range,
                    acl_tags=chunk.acl_tags,
                    source_path=chunk.source_path,
                    is_table=False,
                    metadata={**chunk.metadata, "semantic_split_idx": sub_idx}
                )
                output_chunks.append(sub_chunk)

        return output_chunks

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """Split paragraph block into individual sentences using simple regex."""
        import re
        sentence_end = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
        return [s.strip() for s in sentence_end.split(text) if s.strip()]

    @staticmethod
    def _cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
        """Compute cosine similarity between two 1D vectors."""
        dot = np.dot(v1, v2)
        n1 = np.linalg.norm(v1)
        n2 = np.linalg.norm(v2)
        if n1 == 0 or n2 == 0:
            return 0.0
        return float(dot / (n1 * n2))

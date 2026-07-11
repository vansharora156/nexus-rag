"""Production-ready MinHash deduplication module for NexusRAG.

Uses MinHash Locality Sensitive Hashing (LSH) to detect near-duplicate
chunks before indexing into the retrieval system.

Pipeline

Chunk
   ↓
Normalize Text
   ↓
Generate Word Shingles
   ↓
MinHash Signature
   ↓
LSH Candidate Search
   ↓
Best Similarity Match
   ↓
Duplicate Metadata
"""

import logging
import re
from typing import List, Dict, Set

from datasketch import MinHash, MinHashLSH

from src.config import config
from src.chunking.structural_chunker import Chunk

logger = logging.getLogger(__name__)


class MinHashDeduplicator:
    """Detect near-duplicate chunks using MinHash + LSH."""

    def __init__(
        self,
        threshold: float = None,
        num_perm: int = None,
        shingle_size: int = 3,
    ):
        self.threshold = threshold or config.DEDUP_THRESHOLD
        self.num_perm = num_perm or config.MINHASH_NUM_PERM
        self.shingle_size = shingle_size

        self.lsh = MinHashLSH(
            threshold=self.threshold,
            num_perm=self.num_perm,
        )

        self._minhashes: Dict[str, MinHash] = {}

        self.total_processed = 0
        self.duplicate_count = 0

    # ---------------------------------------------------------
    # Main Deduplication Pipeline
    # ---------------------------------------------------------

    def deduplicate(
        self,
        chunks: List[Chunk],
    ) -> List[Chunk]:
        """
        Detect near-duplicate chunks.

        Duplicate chunks are retained but marked with:

        - is_duplicate=True
        - duplicate_of=<canonical_chunk_id>

        Returns
        -------
        List[Chunk]
        """

        logger.info(
            "Running MinHash deduplication over %d chunks",
            len(chunks),
        )

        # Reset state for every run
        self.total_processed = 0
        self.duplicate_count = 0

        self._minhashes.clear()

        self.lsh = MinHashLSH(
            threshold=self.threshold,
            num_perm=self.num_perm,
        )

        canonical_chunks = []
        duplicate_chunks = []

        for chunk in chunks:

            self.total_processed += 1

            # -----------------------------------------
            # Ignore empty chunks
            # -----------------------------------------

            if not chunk.content.strip():

                chunk.is_duplicate = False
                chunk.duplicate_of = None

                canonical_chunks.append(chunk)
                continue

            # -----------------------------------------
            # Skip tables
            # -----------------------------------------

            if chunk.is_table:

                chunk.is_duplicate = False
                chunk.duplicate_of = None

                canonical_chunks.append(chunk)
                continue

            # -----------------------------------------
            # Compute MinHash signature
            # -----------------------------------------

            minhash = self._compute_minhash(
                chunk.content
            )

            candidates = self.lsh.query(minhash)

            # -----------------------------------------
            # No candidate found
            # -----------------------------------------

            if not candidates:

                self.lsh.insert(
                    chunk.chunk_id,
                    minhash,
                )

                self._minhashes[
                    chunk.chunk_id
                ] = minhash

                chunk.is_duplicate = False
                chunk.duplicate_of = None

                canonical_chunks.append(chunk)

                continue

            # -----------------------------------------
            # Choose best matching candidate
            # -----------------------------------------

            best_candidate = None
            best_similarity = 0.0

            for candidate in candidates:

                similarity = minhash.jaccard(
                    self._minhashes[candidate]
                )

                if similarity > best_similarity:

                    best_similarity = similarity
                    best_candidate = candidate

                            # -----------------------------------------
            # Duplicate Found
            # -----------------------------------------

            if (
                best_candidate is not None
                and best_similarity >= self.threshold
            ):

                chunk.is_duplicate = True
                chunk.duplicate_of = best_candidate

                # Store similarity in metadata
                if chunk.metadata is None:
                    chunk.metadata = {}

                chunk.metadata["dedup_similarity"] = round(
                    best_similarity,
                    3,
                )

                self.duplicate_count += 1

                logger.debug(
                    "Duplicate detected: %s -> %s (similarity=%.3f)",
                    chunk.chunk_id,
                    best_candidate,
                    best_similarity,
                )

                duplicate_chunks.append(chunk)

            # -----------------------------------------
            # New Canonical Chunk
            # -----------------------------------------

            else:

                self.lsh.insert(
                    chunk.chunk_id,
                    minhash,
                )

                self._minhashes[
                    chunk.chunk_id
                ] = minhash

                chunk.is_duplicate = False
                chunk.duplicate_of = None

                canonical_chunks.append(chunk)

        logger.info(
            "Deduplication complete: %d canonical, %d duplicate",
            len(canonical_chunks),
            len(duplicate_chunks),
        )

        # Canonical chunks first, duplicates later
        return canonical_chunks + duplicate_chunks

    # ---------------------------------------------------------
    # Statistics
    # ---------------------------------------------------------

    def get_dedup_stats(self) -> Dict[str, float]:
        """
        Return deduplication statistics.
        """

        canonical = (
            self.total_processed
            - self.duplicate_count
        )

        duplicate_ratio = (
            (
                self.duplicate_count
                / self.total_processed
            )
            if self.total_processed
            else 0
        )

        return {

            "total_processed": self.total_processed,

            "canonical_count": canonical,

            "duplicate_count": self.duplicate_count,

            "duplicate_ratio": round(
                duplicate_ratio * 100,
                2,
            ),

            "threshold": self.threshold,

            "num_perm": self.num_perm,

            "shingle_size": self.shingle_size,
        }

    # ---------------------------------------------------------
    # Text Normalization
    # ---------------------------------------------------------

    def _normalize_text(
        self,
        text: str,
    ) -> str:
        """
        Normalize text before hashing.
        """

        text = text.lower()

        text = re.sub(
            r"[^\w\s]",
            " ",
            text,
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    # ---------------------------------------------------------
    # Shingle Generation
    # ---------------------------------------------------------

    def _create_shingles(
        self,
        text: str,
    ) -> Set[str]:
        """
        Convert normalized text into
        word shingles.
        """

        normalized = self._normalize_text(text)

        words = normalized.split()

        if not words:
            return set()

        # Very short chunk
        if len(words) <= self.shingle_size:

            return {
                " ".join(words)
            }

        shingles = set()

        for i in range(
            len(words)
            - self.shingle_size
            + 1
        ):

            shingles.add(
                " ".join(
                    words[
                        i:i + self.shingle_size
                    ]
                )
            )

        return shingles
            # ---------------------------------------------------------
    # MinHash Generation
    # ---------------------------------------------------------

    def _compute_minhash(
        self,
        text: str,
    ) -> MinHash:
        """
        Compute MinHash signature from text.

        Parameters
        ----------
        text : str

        Returns
        -------
        MinHash
        """

        shingles = self._create_shingles(text)

        m = MinHash(
            num_perm=self.num_perm,
        )

        for shingle in shingles:

            m.update(
                shingle.encode("utf-8")
            )

        return m

    # ---------------------------------------------------------
    # Similarity API
    # ---------------------------------------------------------

    def compute_similarity(
        self,
        text1: str,
        text2: str,
    ) -> float:
        """
        Compute approximate Jaccard similarity
        between two text strings.

        Returns
        -------
        float
            Estimated similarity.
        """

        m1 = self._compute_minhash(text1)
        m2 = self._compute_minhash(text2)

        return m1.jaccard(m2)

    # ---------------------------------------------------------
    # Compare Existing Chunks
    # ---------------------------------------------------------

    def compare_chunks(
        self,
        chunk1: Chunk,
        chunk2: Chunk,
    ) -> float:
        """
        Compare two Chunk objects.

        Returns
        -------
        float
            Estimated similarity.
        """

        return self.compute_similarity(
            chunk1.content,
            chunk2.content,
        )

    # ---------------------------------------------------------
    # Reset
    # ---------------------------------------------------------

    def reset(self):
        """
        Reset internal LSH index and statistics.

        Useful for testing.
        """

        logger.info(
            "Resetting MinHash deduplicator."
        )

        self.total_processed = 0
        self.duplicate_count = 0

        self._minhashes.clear()

        self.lsh = MinHashLSH(
            threshold=self.threshold,
            num_perm=self.num_perm,
        )
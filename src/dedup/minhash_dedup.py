"""Near-duplicate detection using MinHash LSH.

This module uses `datasketch <https://ekzhu.com/datasketch/>`_ to detect
near-duplicate text chunks *before* they are indexed.  It computes Jaccard
similarity over **word n-gram shingles** and uses Locality-Sensitive Hashing
(LSH) to efficiently find candidate pairs without an O(n²) comparison.

The first occurrence of each content fingerprint is treated as the
**canonical** version.  Later duplicates have their ``is_duplicate`` flag
set and point to the canonical chunk via ``duplicate_of``.

Usage::

    from src.dedup.minhash_dedup import MinHashDeduplicator

    deduper = MinHashDeduplicator()
    chunks = deduper.deduplicate(chunks)
    non_dup = [c for c in chunks if not c.is_duplicate]
"""

import re
import logging
from typing import List, Dict, Set

from datasketch import MinHash, MinHashLSH

from src.chunking.structural_chunker import Chunk
from src.config import config

logger = logging.getLogger(__name__)


class MinHashDeduplicator:
    """Near-duplicate detection using MinHash LSH.

    Uses Jaccard similarity on word n-gram shingles to detect
    near-duplicate chunks across different sources.

    Args:
        threshold: Jaccard-similarity threshold above which two chunks
            are considered near-duplicates.  Defaults to
            ``config.DEDUP_THRESHOLD``.
        num_perm: Number of MinHash permutations (higher = more accurate,
            slower).  Defaults to ``config.MINHASH_NUM_PERM``.
        shingle_size: Number of consecutive words per shingle.
    """

    def __init__(
        self,
        threshold: float | None = None,
        num_perm: int | None = None,
        shingle_size: int = 3,
    ) -> None:
        self.threshold = threshold if threshold is not None else config.DEDUP_THRESHOLD
        self.num_perm = num_perm if num_perm is not None else config.MINHASH_NUM_PERM
        self.shingle_size = shingle_size

        self.lsh = MinHashLSH(
            threshold=self.threshold, num_perm=self.num_perm
        )
        self._minhashes: Dict[str, MinHash] = {}
        self._total_seen: int = 0
        self._total_duplicates: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def deduplicate(self, chunks: List[Chunk]) -> List[Chunk]:
        """Detect and mark near-duplicate chunks.

        Iterates through *chunks* in order.  For each chunk the MinHash
        signature is computed and the LSH index is queried.  If a
        near-duplicate already exists the chunk is marked; otherwise it is
        inserted as a new canonical entry.

        Args:
            chunks: Ordered list of :class:`Chunk` objects.

        Returns:
            The **same** list (mutated in-place) with ``is_duplicate`` and
            ``duplicate_of`` fields updated.
        """
        self._total_seen = len(chunks)
        self._total_duplicates = 0

        for chunk in chunks:
            content = chunk.content.strip()
            if not content:
                continue

            minhash = self._compute_minhash(content)

            # Query LSH for existing near-duplicates
            try:
                candidates = self.lsh.query(minhash)
            except ValueError:
                # Empty index – no candidates
                candidates = []

            if candidates:
                # Mark as duplicate of the first (canonical) candidate
                canonical_id = candidates[0]
                chunk.is_duplicate = True
                chunk.duplicate_of = canonical_id
                self._total_duplicates += 1
                logger.debug(
                    "Chunk %s is a near-duplicate of %s",
                    chunk.chunk_id,
                    canonical_id,
                )
            else:
                # New canonical chunk – insert into LSH
                try:
                    self.lsh.insert(chunk.chunk_id, minhash)
                    self._minhashes[chunk.chunk_id] = minhash
                except ValueError:
                    # Duplicate key – chunk_id already exists
                    logger.warning(
                        "Duplicate chunk_id '%s' encountered; skipping LSH "
                        "insertion",
                        chunk.chunk_id,
                    )

        stats = self.get_dedup_stats()
        logger.info(
            "Deduplication complete: %d total, %d canonical, %d duplicates "
            "(%.1f%% reduction)",
            stats["total"],
            stats["canonical"],
            stats["duplicates"],
            stats["reduction_pct"],
        )

        return chunks

    def get_dedup_stats(self) -> Dict[str, int | float]:
        """Return deduplication statistics.

        Returns:
            Dictionary with keys ``total``, ``canonical``, ``duplicates``,
            and ``reduction_pct``.
        """
        canonical = self._total_seen - self._total_duplicates
        reduction_pct = (
            (self._total_duplicates / self._total_seen * 100.0)
            if self._total_seen > 0
            else 0.0
        )
        return {
            "total": self._total_seen,
            "canonical": canonical,
            "duplicates": self._total_duplicates,
            "reduction_pct": round(reduction_pct, 2),
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _create_shingles(self, text: str) -> Set[str]:
        """Create word n-gram shingles from *text*.

        The text is normalised (lowercased, punctuation removed, whitespace
        collapsed) before shingling.

        Args:
            text: Raw input text.

        Returns:
            A set of space-joined word n-grams.
        """
        # Normalise
        normalised = text.lower()
        normalised = re.sub(r"[^\w\s]", " ", normalised)
        normalised = re.sub(r"\s+", " ", normalised).strip()

        words = normalised.split()

        if len(words) < self.shingle_size:
            # If text is shorter than shingle size, return the whole text
            # as a single shingle
            return {normalised} if normalised else set()

        shingles: Set[str] = set()
        for i in range(len(words) - self.shingle_size + 1):
            shingle = " ".join(words[i : i + self.shingle_size])
            shingles.add(shingle)

        return shingles

    def _compute_minhash(self, text: str) -> MinHash:
        """Compute MinHash signature for *text*.

        Args:
            text: Input text (will be shingled internally).

        Returns:
            A :class:`datasketch.MinHash` object.
        """
        m = MinHash(num_perm=self.num_perm)
        shingles = self._create_shingles(text)
        for shingle in shingles:
            m.update(shingle.encode("utf-8"))
        return m

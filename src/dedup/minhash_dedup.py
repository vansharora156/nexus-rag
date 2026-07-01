"""Deduplication module using MinHash LSH.

Identifies near-duplicate document chunks across repositories by evaluating
Jaccard similarity on word shingles.
"""

import logging
import re
from typing import List, Dict, Tuple, Set, Any
from datasketch import MinHash, MinHashLSH

from src.config import config
from src.chunking.structural_chunker import Chunk

logger = logging.getLogger(__name__)


class MinHashDeduplicator:
    """Near-duplicate detector using MinHash LSH.

    Groups similar documents based on overlap of word shingles, preventing
    redundant context chunks from flooding the retrieval index.
    """

    def __init__(self, threshold: float = None, num_perm: int = None, shingle_size: int = 3):
        self.threshold = threshold or config.DEDUP_THRESHOLD
        self.num_perm = num_perm or config.MINHASH_NUM_PERM
        self.shingle_size = shingle_size
        
        # Initialize LSH index
        self.lsh = MinHashLSH(threshold=self.threshold, num_perm=self.num_perm)
        self._minhashes: Dict[str, MinHash] = {}
        
        self.total_processed = 0
        self.duplicate_count = 0

    def deduplicate(self, chunks: List[Chunk]) -> List[Chunk]:
        """Detect and mark near-duplicate chunks.

        Updates the is_duplicate and duplicate_of fields of duplicate chunks,
        retaining the first parsed version as the canonical copy.

        Args:
            chunks: List of Chunk objects.

        Returns:
            The same list of chunks with duplicate status fields updated.
        """
        logger.info(f"Running MinHash deduplication over {len(chunks)} chunks (threshold={self.threshold})")

        for chunk in chunks:
            self.total_processed += 1
            
            # Skip tables from deduplication (they are structured and need to be distinct)
            if chunk.is_table:
                chunk.is_duplicate = False
                chunk.duplicate_of = None
                continue

            # Compute MinHash signature
            m = self._compute_minhash(chunk.content)
            
            # Query LSH for near-duplicates
            candidates = self.lsh.query(m)
            
            if candidates:
                # We found near-duplicates!
                # Mark the current chunk as duplicate, linking to the first candidate (canonical)
                canonical_id = sorted(candidates)[0]
                
                chunk.is_duplicate = True
                chunk.duplicate_of = canonical_id
                self.duplicate_count += 1
                
                logger.debug(f"Chunk '{chunk.chunk_id}' marked as duplicate of '{canonical_id}'")
            else:
                # No duplicates found, insert this as a new canonical chunk
                self.lsh.insert(chunk.chunk_id, m)
                self._minhashes[chunk.chunk_id] = m
                
                chunk.is_duplicate = False
                chunk.duplicate_of = None

        logger.info(f"Deduplication complete: {self.duplicate_count} duplicates flagged out of {self.total_processed} chunks.")
        return chunks

    def get_dedup_stats(self) -> Dict[str, int]:
        """Get deduplication run stats.

        Returns:
            Dictionary containing processing stats.
        """
        return {
            "total_processed": self.total_processed,
            "duplicate_count": self.duplicate_count,
            "canonical_count": self.total_processed - self.duplicate_count
        }

    def _create_shingles(self, text: str) -> Set[str]:
        """Tokenize text and generate word n-gram shingles."""
        # Normalize text: lowercase, remove non-alphanumeric, collapse space
        normalized = text.lower()
        normalized = re.sub(r"[^\w\s]", " ", normalized)
        words = [w.strip() for w in normalized.split() if w.strip()]
        
        shingles: Set[str] = set()
        if len(words) < self.shingle_size:
            # Fallback if text is too short: use single words
            return set(words)
            
        for i in range(len(words) - self.shingle_size + 1):
            shingle = "_".join(words[i:i + self.shingle_size])
            shingles.add(shingle)
            
        return shingles

    def _compute_minhash(self, text: str) -> MinHash:
        """Compute MinHash signature from text shingles."""
        m = MinHash(num_perm=self.num_perm)
        shingles = self._create_shingles(text)
        
        for shingle in shingles:
            m.update(shingle.encode("utf-8"))
            
        return m

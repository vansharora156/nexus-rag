"""BM25 sparse retrieval indexing module for NexusRAG.

Wraps the bm25s library to build, serialize, load, and search sparse lexical indexes,
with post-retrieval security ACL filtering.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

from src.config import config
from src.chunking.structural_chunker import Chunk

logger = logging.getLogger(__name__)


class BM25Index:
    """BM25 index manager utilizing bm25s.

    Executes rapid keyword search queries and applies role-based ACL gating
    to filter returned candidates.
    """

    def __init__(self, index_dir: str = None):
        self.index_dir = Path(index_dir or config.BM25_INDEX_DIR)
        self._retriever = None
        self._chunk_ids: List[str] = []
        self._chunk_contents: List[str] = []
        self._chunk_acls: List[List[str]] = []
        self._chunk_metadata: List[Dict[str, Any]] = []

    def build_index(self, chunks: List[Chunk]) -> None:
        """Tokenize text and construct the BM25 index from a list of chunks.

        Note: Excludes duplicate chunks to optimize index storage and relevancy.

        Args:
            chunks: List of Chunk objects.
        """
        import bm25s

        # Only index canonical (non-duplicate) chunks
        canonical_chunks = [c for c in chunks if not c.is_duplicate]
        if not canonical_chunks:
            logger.warning("No canonical chunks available to index.")
            return

        self._chunk_ids = [c.chunk_id for c in canonical_chunks]
        self._chunk_contents = [c.content for c in canonical_chunks]
        self._chunk_acls = [c.acl_tags for c in canonical_chunks]
        
        # Save structural details for metadata mapping
        self._chunk_metadata = []
        for c in canonical_chunks:
            self._chunk_metadata.append({
                "doc_id": c.doc_id,
                "title": c.title,
                "heading_path": c.heading_path,
                "source_type": c.source_type.value,
                "page_number": c.page_number,
                "row_range": c.row_range,
                "is_table": c.is_table,
                "is_duplicate": c.is_duplicate,
                "duplicate_of": c.duplicate_of
            })

        # Tokenize content using bm25s default tokenizer (removes standard English stopwords)
        tokenized_corpus = bm25s.tokenize(self._chunk_contents, stopwords="en")
        
        # Build index
        self._retriever = bm25s.BM25()
        self._retriever.index(tokenized_corpus)
        logger.info(f"Built BM25 index with {len(self._chunk_contents)} documents")

    def search(
        self, 
        query: str, 
        top_k: int = 20, 
        active_roles: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Search the sparse index and apply permission boundaries.

        Args:
            query: Lexical query string.
            top_k: Candidate matches limit.
            active_roles: Optional user security roles for access control.

        Returns:
            List of matching dictionaries containing scores and payloads.
        """
        import bm25s

        if self._retriever is None:
            raise RuntimeError("BM25 index not built or loaded. Call build_index() or load() first.")

        # Tokenize the query
        tokenized_query = bm25s.tokenize([query], stopwords="en")
        
        # Retrieve raw scores (returns indices and scores of shape [1, k])
        # Retrieve more candidates initially to compensate for post-filtering of unauthorized documents
        search_k = min(top_k * 4 if active_roles else top_k, len(self._chunk_ids))
        if search_k == 0:
            return []
            
        results, scores = self._retriever.retrieve(tokenized_query, k=search_k)
        
        output = []
        for doc_idx, score in zip(results[0], scores[0]):
            idx = int(doc_idx)
            
            # 1. Enforce post-retrieval ACL check
            acls = self._chunk_acls[idx]
            if active_roles:
                # User roles must intersect with document ACL tags, or document is open to 'all'
                query_roles = set(active_roles) | {"all"}
                if not any(role in acls for role in query_roles):
                    continue  # Filter out unauthorized chunk
            
            meta = self._chunk_metadata[idx]
            output.append({
                "chunk_id": self._chunk_ids[idx],
                "doc_id": meta["doc_id"],
                "content": self._chunk_contents[idx],
                "source_type": meta["source_type"],
                "acls": acls,
                "title": meta["title"],
                "heading_path": meta["heading_path"],
                "page_number": meta["page_number"],
                "row_range": meta["row_range"],
                "is_table": meta["is_table"],
                "is_duplicate": meta["is_duplicate"],
                "duplicate_of": meta["duplicate_of"],
                "score": float(score)
            })

            # Break when we have collected top_k matching chunks
            if len(output) >= top_k:
                break
                
        return output

    def save(self) -> None:
        """Serialize the index and metadata mapping to the target folder."""
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        # Save BM25 retriever using bm25s format
        if self._retriever:
            self._retriever.save(str(self.index_dir / "bm25_model"))
            
        # Save metadata mapping file
        metadata_payload = {
            "chunk_ids": self._chunk_ids,
            "chunk_contents": self._chunk_contents,
            "chunk_acls": self._chunk_acls,
            "chunk_metadata": self._chunk_metadata
        }
        
        meta_path = self.index_dir / "bm25_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata_payload, f, indent=2)
            
        logger.info(f"Saved BM25 index and metadata to: {self.index_dir}")

    def load(self) -> None:
        """Load the index and metadata mapping from disk."""
        import bm25s

        # Load retriever
        self._retriever = bm25s.BM25.load(str(self.index_dir / "bm25_model"), load_corpus=True)
        
        # Load metadata
        meta_path = self.index_dir / "bm25_metadata.json"
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
            
        self._chunk_ids = meta["chunk_ids"]
        self._chunk_contents = meta["chunk_contents"]
        self._chunk_acls = meta["chunk_acls"]
        self._chunk_metadata = meta["chunk_metadata"]
        
        logger.info(f"Loaded BM25 index from: {self.index_dir} ({len(self._chunk_ids)} chunks)")

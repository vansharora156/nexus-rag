"""Qdrant Vector Database integration module for NexusRAG.

Handles collection lifecycle management, document upserts, and metadata-filtered
vector similarity searches.
"""

import hashlib
import logging
from typing import List, Dict, Any, Optional
import qdrant_client
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchAny

from src.config import config
from src.chunking.structural_chunker import Chunk

logger = logging.getLogger(__name__)


class VectorStore:
    """Wrapper around Qdrant client for dense vector storage and retrieval.

    Supports local in-memory operation, persistent local storage directories,
    or remote Qdrant clusters.
    """

    def __init__(
        self, 
        url: str = None, 
        path: str = None, 
        collection_name: str = None
    ):
        self.url = url or config.QDRANT_URL
        self.path = path or config.QDRANT_PATH
        self.collection_name = collection_name or config.QDRANT_COLLECTION
        self._client = None

    @property
    def client(self) -> qdrant_client.QdrantClient:
        """Lazy-load the Qdrant client connection."""
        if self._client is None:
            # If QDRANT_URL is set, prioritize connecting to server
            # Otherwise, fallback to local path storage or :memory:
            if self.url and not self.path:
                logger.info(f"Connecting to remote Qdrant server at: {self.url}")
                self._client = qdrant_client.QdrantClient(url=self.url)
            else:
                logger.info(f"Initializing local Qdrant storage at path: {self.path}")
                self._client = qdrant_client.QdrantClient(path=self.path)
        return self._client

    def close(self) -> None:
        """Close the Qdrant client connection and release file locks."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception as e:
                logger.warning(f"Error closing Qdrant client: {e}")
            self._client = None

    def recreate_collection(self, dimension: int = 3072) -> None:
        """Delete and recreate the collection with correct dimensions and index payload fields."""
        client = self.client
        logger.info(f"Recreating collection '{self.collection_name}' (dimension={dimension})")

        # Delete existing collection if it exists
        if client.collection_exists(collection_name=self.collection_name):
            client.delete_collection(collection_name=self.collection_name)

        # Create new collection using Cosine distance
        client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=dimension, distance=Distance.COSINE)
        )

        # Set up payload indexes for rapid filtering
        # 1. Indexing on ACL tags (dynamic security gating)
        client.create_payload_index(
            collection_name=self.collection_name,
            field_name="acls",
            field_schema="keyword"
        )
        # 2. Indexing on Source Type
        client.create_payload_index(
            collection_name=self.collection_name,
            field_name="source_type",
            field_schema="keyword"
        )

    def add_chunks(self, chunks: List[Chunk], embeddings: List[List[float]]) -> None:
        """Upload chunks and their dense embeddings into Qdrant.

        Args:
            chunks: List of Chunk metadata structures.
            embeddings: List of embedding vectors matching chunks.
        """
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks and embeddings must match.")

        client = self.client
        points = []

        for idx, (chunk, vector) in enumerate(zip(chunks, embeddings)):
            payload = {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "content": chunk.content,
                "source_type": chunk.source_type.value,
                "acls": chunk.acl_tags,
                "title": chunk.title,
                "heading_path": chunk.heading_path,
                "page_number": chunk.page_number,
                "row_range": chunk.row_range,
                "is_table": chunk.is_table,
                "is_duplicate": chunk.is_duplicate,
                "duplicate_of": chunk.duplicate_of
            }
            
            # Use hash of chunk_id to create a valid integer or UUID point key
            # point_id must be int or UUID string
            point_id = hashlib_uuid(chunk.chunk_id)
            
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
            )

        # Batch upload to Qdrant
        logger.info(f"Upserting {len(points)} points into Qdrant collection '{self.collection_name}'")
        client.upsert(
            collection_name=self.collection_name,
            points=points
        )

    def search(
        self, 
        query_embedding: List[float], 
        top_k: int = 20, 
        active_roles: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Search the collection for similar vectors.

        Args:
            query_embedding: Query dense vector.
            top_k: Top candidate count.
            active_roles: Optional security roles to restrict access.

        Returns:
            List of matching dictionaries containing scores and payloads.
        """
        client = self.client
        
        # Build filter conditions
        search_filter = None
        if active_roles:
            # Expand active roles to always include "all" (public documents)
            query_roles = list(active_roles)
            if "all" not in query_roles:
                query_roles.append("all")
                
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="acls",
                        match=MatchAny(any=query_roles)
                    )
                ]
            )

        results = client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=top_k,
            query_filter=search_filter
        ).points

        output = []
        for res in results:
            output.append({
                "chunk_id": res.payload.get("chunk_id"),
                "doc_id": res.payload.get("doc_id"),
                "content": res.payload.get("content"),
                "source_type": res.payload.get("source_type"),
                "acls": res.payload.get("acls", []),
                "title": res.payload.get("title"),
                "heading_path": res.payload.get("heading_path"),
                "page_number": res.payload.get("page_number"),
                "row_range": res.payload.get("row_range"),
                "is_table": res.payload.get("is_table", False),
                "is_duplicate": res.payload.get("is_duplicate", False),
                "duplicate_of": res.payload.get("duplicate_of"),
                "score": res.score
            })
            
        return output

    def reset(self) -> None:
        """Deletes the Qdrant collection completely."""
        client = self.client
        if client.collection_exists(collection_name=self.collection_name):
            client.delete_collection(collection_name=self.collection_name)
            logger.info(f"Deleted Qdrant collection '{self.collection_name}'")

    @property
    def count(self) -> int:
        """Get the count of indexed points in the collection."""
        client = self.client
        if not client.collection_exists(collection_name=self.collection_name):
            return 0
        res = client.get_collection(collection_name=self.collection_name)
        return res.points_count


def hashlib_uuid(string_id: str) -> str:
    """Generate a stable UUID string from any string ID for Qdrant compatibility."""
    import uuid
    m = hashlib.md5()
    m.update(string_id.encode("utf-8"))
    return str(uuid.UUID(m.hexdigest()))

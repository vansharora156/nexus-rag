"""Central configuration module for the NexusRAG enterprise RAG system.

This module loads environment variables from a ``.env`` file (via
``python-dotenv``) and exposes them through a single ``Config`` dataclass
instance. Every pipeline component should import the singleton ``config``
object rather than reading ``os.environ`` directly so that configuration
stays consistent and testable.

Configuration groups
--------------------
- **Paths** – project root, data directory, index persistence directories.
- **LLM** – Google Gemini API key and model name.
- **Embeddings** – Sentence-Transformers model identifier (BAAI/bge-m3) used for dense vector creation.
- **Reranker** – Cross-Encoder model identifier (BAAI/bge-reranker-large) for Stage 2 reranking.
- **Qdrant** – collection name, URL, and local storage path for the dense vector store.
- **Retrieval** – top-K values for the initial retrieval stage, the re-ranker, and the Reciprocal Rank Fusion constant.
- **Chunking** – maximum token length and overlap for the sliding-window chunker.
- **Server** – host and port for the FastAPI application.
- **Permissions** – path to the JSON file that maps ACL tags to user roles.
- **Dedup** – MinHash-LSH similarity threshold and number of permutations for near-duplicate detection.

Usage
-----
>>> from src.config import config
>>> print(config.GEMINI_MODEL)
'gemini-2.5-flash'
"""

import os
from pathlib import Path
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Application-wide configuration backed by environment variables.

    Each field falls back to a sensible default when the corresponding
    environment variable is not set. Numeric variables are cast at
    construction time so that downstream code never has to parse strings.

    Attributes:
        PROJECT_ROOT: Absolute path to the repository root directory.
        DATA_DIR: Default directory for raw / processed documents.
        QDRANT_URL: Qdrant vector database URL (e.g., http://localhost:6333).
        QDRANT_PATH: On-disk path where Qdrant stores its data for local client runs.
        QDRANT_COLLECTION: Name of the Qdrant collection to use.
        BM25_INDEX_DIR: On-disk path for serialised BM25 indices.
        GEMINI_API_KEY: API key for the Google Gemini LLM provider.
        GEMINI_MODEL: Gemini model identifier.
        EMBEDDING_MODEL: HuggingFace model id for sentence-transformers.
        RERANKER_MODEL: Cross-Encoder model identifier for reranking.
        RETRIEVAL_TOP_K: Number of candidates returned by the first-stage
            retriever (dense + sparse).
        RERANK_TOP_K: Number of documents kept after cross-encoder
            re-ranking.
        RRF_K: Constant *k* in the Reciprocal Rank Fusion formula
            ``1 / (k + rank)``.
        CHUNK_MAX_TOKENS: Maximum token count for each text chunk.
        CHUNK_OVERLAP_TOKENS: Token overlap between consecutive chunks.
        API_HOST: Network interface the FastAPI server binds to.
        API_PORT: TCP port the FastAPI server listens on.
        PERMISSIONS_FILE: Path to the ACL permissions JSON file.
        DEDUP_THRESHOLD: Jaccard-similarity threshold above which two
            chunks are considered near-duplicates.
        MINHASH_NUM_PERM: Number of permutations used by the MinHash
            algorithm (higher => more accurate but slower).
        OCR_ENGINE: OCR engine identifier (e.g., PaddleOCR).
    """

    # -- Paths ----------------------------------------------------------------
    PROJECT_ROOT: Path = field(
        default_factory=lambda: Path(__file__).parent.parent
    )
    DATA_DIR: Path = field(
        default_factory=lambda: Path(__file__).parent.parent / "data"
    )
    BM25_INDEX_DIR: str = os.getenv("BM25_INDEX_DIR", "./bm25_index")

    # -- Qdrant ---------------------------------------------------------------
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_PATH: str = os.getenv("QDRANT_PATH", "./qdrant_storage")
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "enterprise_docs")

    # -- LLM ------------------------------------------------------------------
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # -- Embeddings & Reranking -----------------------------------------------
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    RERANKER_MODEL: str = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-large")

    # -- Retrieval ------------------------------------------------------------
    RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "20"))
    RERANK_TOP_K: int = int(os.getenv("RERANK_TOP_K", "5"))
    RRF_K: int = int(os.getenv("RRF_K", "60"))

    # -- Chunking -------------------------------------------------------------
    CHUNK_MAX_TOKENS: int = int(os.getenv("CHUNK_MAX_TOKENS", "512"))
    CHUNK_OVERLAP_TOKENS: int = int(os.getenv("CHUNK_OVERLAP_TOKENS", "50"))

    # -- Server ---------------------------------------------------------------
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # -- Permissions ----------------------------------------------------------
    PERMISSIONS_FILE: Path = field(
        default_factory=lambda: Path(__file__).parent.parent
        / "data"
        / "permissions.json"
    )

    # -- Dedup ----------------------------------------------------------------
    DEDUP_THRESHOLD: float = float(os.getenv("DEDUP_THRESHOLD", "0.7"))
    MINHASH_NUM_PERM: int = int(os.getenv("MINHASH_NUM_PERM", "128"))

    # -- OCR ------------------------------------------------------------------
    OCR_ENGINE: str = os.getenv("OCR_ENGINE", "PaddleOCR")


# Singleton config instance – import this from anywhere in the project.
config = Config()

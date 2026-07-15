"""Pydantic request/response models for the NexusRAG FastAPI application."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared / nested models
# ---------------------------------------------------------------------------

class CitationModel(BaseModel):
    """A single source citation."""
    index: int = Field(..., description="1-based citation number matching [N] in the answer.")
    source_type: str = Field(..., description="Document type: pdf, markdown, excel, slack.")
    icon: str = Field(..., description="Source-type emoji icon.")
    title: str = Field(..., description="Document or page title.")
    heading_path: Optional[str] = Field(None, description="Heading breadcrumb within the document.")
    page_number: Optional[int] = Field(None, description="PDF page number (if applicable).")
    row_range: Optional[str] = Field(None, description="Excel/CSV row range (if applicable).")
    chunk_id: str = Field(..., description="Unique chunk identifier.")
    doc_id: str = Field(..., description="Parent document identifier.")
    acls: List[str] = Field(default_factory=list, description="Access control tags on this document.")
    score: float = Field(..., description="Retrieval relevance score (RRF or dense).")
    rerank_score: Optional[float] = Field(None, description="Cross-encoder reranking score (0–10).")
    content_snippet: str = Field(..., description="Up to 300 characters of the source passage.")
    is_table: bool = Field(False, description="True if this chunk is tabular data.")
    label: str = Field(..., description="Formatted citation label, e.g. '[1] 📄 Q4 Report (page 3)'.")


# ---------------------------------------------------------------------------
# Query endpoint
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    """POST /query request body."""
    query: str = Field(..., min_length=1, description="The user's natural-language question.")
    username: Optional[str] = Field(
        None,
        description=(
            "Authenticated username for ACL permission enforcement. "
            "Omit to disable permission filtering (open/dev mode)."
        ),
    )
    top_k: int = Field(5, ge=1, le=20, description="Number of source chunks to retrieve.")


class QueryResponse(BaseModel):
    """POST /query response body."""
    answer: str = Field(..., description="Gemini-generated answer with inline [N] citation markers.")
    citations: List[CitationModel] = Field(
        default_factory=list, description="Ordered list of sources cited in the answer."
    )
    query_variants: List[str] = Field(
        default_factory=list,
        description="Original query plus LLM-generated variants searched for wider recall.",
    )
    num_sources: int = Field(..., description="Number of source chunks used to generate the answer.")
    elapsed_ms: float = Field(..., description="End-to-end latency in milliseconds.")
    username: str = Field(..., description="Username the query was executed for.")


# ---------------------------------------------------------------------------
# Ingest endpoint
# ---------------------------------------------------------------------------

class IngestRequest(BaseModel):
    """POST /ingest request body."""
    data_dir: str = Field(
        "./data",
        description="Path to the directory of documents to ingest (relative to project root).",
    )
    recreate_collection: bool = Field(
        True,
        description="If True, wipes the existing Qdrant collection before re-ingesting.",
    )


class IngestResponse(BaseModel):
    """POST /ingest response body."""
    status: str = Field(..., description="'ok' or 'error'.")
    files_processed: int = Field(0, description="Number of files successfully parsed.")
    chunks_generated: int = Field(0, description="Total chunks created.")
    duplicates_flagged: int = Field(0, description="Near-duplicate chunks detected.")
    canonical_count: int = Field(0, description="Non-duplicate chunks indexed.")
    elapsed_seconds: float = Field(0.0, description="Ingestion wall-clock time in seconds.")
    message: Optional[str] = Field(None, description="Error message if status is 'error'.")


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """GET /health response body."""
    status: str = Field("ok", description="Service health: 'ok' or 'degraded'.")
    qdrant_collection: str = Field(..., description="Qdrant collection name.")
    qdrant_points: int = Field(..., description="Number of vectors currently indexed.")
    bm25_index_dir: str = Field(..., description="BM25 index directory path.")
    embedding_backend: str = Field(..., description="Active embedding backend ('gemini' or 'local').")
    embedding_model: str = Field(..., description="Embedding model identifier.")
    gemini_model: str = Field(..., description="Generative model identifier.")
    details: Dict[str, Any] = Field(default_factory=dict)

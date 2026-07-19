"""FastAPI route handlers for the AskTheCompany RAG API.

Endpoints
---------
POST /query    — Ask a question and get a grounded answer with citations.
POST /ingest   — Ingest a directory of documents into the knowledge base.
GET  /health   — Service health check with index statistics.
"""

import asyncio
import logging
from pathlib import Path
from functools import partial

from fastapi import APIRouter, HTTPException, Request

from api.models import (
    QueryRequest, QueryResponse,
    IngestRequest, IngestResponse,
    HealthResponse,
)
from src.config import config

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Helper: access the shared QueryPipeline stored in app.state
# ---------------------------------------------------------------------------

def _pipeline(request: Request):
    """Retrieve the QueryPipeline singleton from FastAPI app state."""
    pipeline = getattr(request.app.state, "query_pipeline", None)
    if pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="Query pipeline is not initialised. Run ingest first.",
        )
    return pipeline


# ---------------------------------------------------------------------------
# POST /query
# ---------------------------------------------------------------------------

@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Ask the company anything",
    description=(
        "Submit a natural-language question. The system retrieves the most "
        "relevant passages from the enterprise knowledge base (with ACL enforcement) "
        "and returns a grounded Gemini-generated answer with inline citations."
    ),
    tags=["RAG"],
)
async def query_endpoint(body: QueryRequest, request: Request) -> QueryResponse:
    pipeline = _pipeline(request)
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            partial(
                pipeline.query,
                question=body.query,
                username=body.username,
                top_k=body.top_k,
            ),
        )
    except Exception as exc:
        logger.exception("Error in /query handler")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return QueryResponse(**result)


# ---------------------------------------------------------------------------
# POST /ingest
# ---------------------------------------------------------------------------

@router.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Ingest documents into the knowledge base",
    description=(
        "Parses all supported files in the specified directory "
        "(PDF, Markdown, Excel, Slack JSON), chunks, deduplicates, "
        "embeds, and indexes them into Qdrant + BM25."
    ),
    tags=["Admin"],
)
async def ingest_endpoint(body: IngestRequest, request: Request) -> IngestResponse:
    from src.pipeline.ingest import IngestionPipeline

    data_dir = Path(body.data_dir)
    if not data_dir.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Directory not found: {data_dir.resolve()}",
        )

    try:
        def _run_ingest():
            pipeline = IngestionPipeline()
            return pipeline.ingest_directory(
                data_dir=data_dir,
                recreate_collection=body.recreate_collection,
            )
        loop = asyncio.get_event_loop()
        stats = await loop.run_in_executor(None, _run_ingest)
    except Exception as exc:
        logger.exception("Error in /ingest handler")
        return IngestResponse(status="error", message=str(exc))

    # Reload BM25 index in the query pipeline so it can serve sparse results
    qp = getattr(request.app.state, "query_pipeline", None)
    if qp is not None:
        try:
            await loop.run_in_executor(None, qp.bm25_index.load)
            logger.info("BM25 index reloaded into QueryPipeline after ingest.")
        except Exception as exc:
            logger.warning("Could not reload BM25 after ingest: %s", exc)

    return IngestResponse(
        status="ok",
        files_processed=stats.get("files_processed", 0),
        chunks_generated=stats.get("chunks_generated", 0),
        duplicates_flagged=stats.get("duplicates_flagged", 0),
        canonical_count=stats.get("canonical_count", 0),
        elapsed_seconds=stats.get("elapsed_seconds", 0.0),
    )


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
    description="Returns index statistics and configuration details.",
    tags=["Admin"],
)
async def health_endpoint(request: Request) -> HealthResponse:
    from src.indexing.vector_store import VectorStore
    from src.indexing.embedder import Embedder

    details: dict = {}
    qdrant_points = 0
    status = "ok"

    # Check Qdrant
    try:
        vs = VectorStore()
        qdrant_points = vs.count
        details["qdrant"] = "connected"
    except Exception as exc:
        details["qdrant"] = f"error: {exc}"
        status = "degraded"

    # Check BM25
    bm25_dir = Path(config.BM25_INDEX_DIR)
    details["bm25_index_exists"] = bm25_dir.exists()

    # Embedder info
    try:
        emb = Embedder()
        details["embedder_dimension"] = emb.dimension
    except Exception as exc:
        details["embedder"] = f"error: {exc}"
        status = "degraded"

    return HealthResponse(
        status=status,
        qdrant_collection=config.QDRANT_COLLECTION,
        qdrant_points=qdrant_points,
        bm25_index_dir=str(bm25_dir.resolve()),
        embedding_backend=config.EMBEDDING_BACKEND,
        embedding_model=(
            config.GEMINI_EMBEDDING_MODEL
            if config.EMBEDDING_BACKEND == "gemini"
            else config.EMBEDDING_MODEL
        ),
        gemini_model=config.GEMINI_MODEL,
        details=details,
    )

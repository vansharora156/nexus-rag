"""FastAPI application factory for AskTheCompany.

Creates and configures the FastAPI ``app`` instance:
- Registers the API router with a ``/api/v1`` prefix
- Adds CORS middleware for development convenience
- Initialises the :class:`QueryPipeline` singleton on startup
- Exposes Swagger UI at ``/docs`` and ReDoc at ``/redoc``

Usage (development)::

    uvicorn api.app:app --reload --port 8000

Usage (production)::

    uvicorn api.app:app --host 0.0.0.0 --port 8000 --workers 2
"""

import logging
import sys

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise shared singletons on startup and clean up on shutdown."""
    logger.info("=" * 60)
    logger.info("  AskTheCompany — NexusRAG Enterprise RAG System")
    logger.info("=" * 60)

    # Initialise the QueryPipeline once and attach to app.state
    logger.info("Loading QueryPipeline…")
    try:
        from src.pipeline.query import QueryPipeline
        app.state.query_pipeline = QueryPipeline()
        logger.info("QueryPipeline loaded successfully.")
    except Exception as exc:
        logger.error("Failed to load QueryPipeline: %s", exc)
        logger.warning(
            "Server will start but /query will return 503 until the issue is resolved."
        )
        app.state.query_pipeline = None

    logger.info("Server ready. Docs: http://localhost:8000/docs")
    yield

    # Shutdown cleanup (nothing persistent to close for now)
    logger.info("Server shutting down.")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="AskTheCompany — NexusRAG",
        description=(
            "Enterprise RAG system with multi-source ingestion (PDF, Markdown, "
            "Excel, Slack), hybrid BM25+dense retrieval, cross-encoder reranking, "
            "ACL-based permission enforcement, and Gemini-powered answer generation."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS — allow all origins in development; tighten for production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes under /api/v1
    app.include_router(router, prefix="/api/v1")

    # Root redirect to docs
    @app.get("/", include_in_schema=False)
    async def root():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/docs")

    return app


# Module-level app instance (used by uvicorn)
app = create_app()

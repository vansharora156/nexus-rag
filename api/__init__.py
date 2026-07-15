"""FastAPI application package for AskTheCompany.

This package exposes HTTP endpoints for document ingestion, querying,
and health checks.  It delegates all business logic to the ``src``
pipeline modules.

Main exports:
- ``app``: The FastAPI application instance (for uvicorn).
- ``router``: The APIRouter with all endpoint definitions.
"""

from api.app import app
from api.routes import router

__all__ = ["app", "router"]

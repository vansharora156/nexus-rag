"""Server entry point for AskTheCompany.

Run from the project root::

    python server/main.py

Or via uvicorn directly::

    uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
"""

import sys
from pathlib import Path

# Ensure project root is on the import path when running as a script
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uvicorn
from src.config import config


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  AskTheCompany — NexusRAG Server")
    print("=" * 60)
    print(f"  Host : {config.API_HOST}")
    print(f"  Port : {config.API_PORT}")
    print(f"  Docs : http://localhost:{config.API_PORT}/docs")
    print("=" * 60 + "\n")

    uvicorn.run(
        "api.app:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True,          # Hot-reload for development
        log_level="info",
    )

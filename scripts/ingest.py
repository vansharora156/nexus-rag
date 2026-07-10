"""Script to execute the end-to-end document ingestion pipeline.

Parses, chunks, deduplicates, embeds, and indexes all files in the data directory.
"""

import sys
import logging
from pathlib import Path

# Add project root to sys path
sys.path.append(str(Path(__file__).parent.parent.resolve()))

from src.pipeline.ingest import IngestionPipeline

def main():
    # Set up basic logging to console
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    logger = logging.getLogger("ingest_script")
    
    # Ingestion directories
    project_root = Path(__file__).parent.parent.resolve()
    data_dir = project_root / "data"
    
    logger.info("Initializing NexusRAG Ingestion Orchestrator...")
    pipeline = IngestionPipeline()
    
    try:
        stats = pipeline.ingest_directory(data_dir, recreate_collection=True)
        print("\n" + "=" * 50)
        print("🎉 INGESTION PIPELINE SUMMARY")
        print("=" * 50)
        print(f"📁 Files parsed and processed: {stats['files_processed']}")
        print(f"🧩 Text chunks generated:      {stats['chunks_generated']}")
        print(f"🔍 Near-duplicates flagged:    {stats['duplicates_flagged']}")
        print(f"✅ Canonical chunks indexed:   {stats['canonical_count']}")
        print(f"⏱️ Ingestion time elapsed:     {stats['elapsed_seconds']} seconds")
        print("=" * 50 + "\n")
        
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

"""
Test script for the NexusRAG Embedder.

Run:
    python -m scripts.test_embedder
"""

import sys
import time
import traceback
from pathlib import Path

# Ensure UTF-8 output on Windows terminals (avoids UnicodeEncodeError with emoji)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.parsers.registry import ParserRegistry
from src.chunking.hybrid_chunker import HybridChunker
from src.dedup.minhash_dedup import MinHashDeduplicator
from src.indexing.embedder import Embedder


def main():

    print("=" * 70)
    print("🚀 EMBEDDER TEST")
    print("=" * 70)

    data_dir = Path("data")

    if not data_dir.exists():
        print("❌ Data directory not found.")
        return

    registry = ParserRegistry()
    chunker = HybridChunker()
    deduplicator = MinHashDeduplicator()
    embedder = Embedder()

    parsed_documents = []

    try:

        # -------------------------------------------------------
        # Parse Documents
        # -------------------------------------------------------

        print("\n📄 Parsing Documents")

        for file_path in sorted(data_dir.glob("**/*")):

            if not file_path.is_file():
                continue

            if not registry.can_parse(file_path):
                continue

            print(f"   • {file_path.name}")

            parser = registry.get_parser(file_path)

            docs = parser.parse(file_path)

            parsed_documents.extend(docs)

        print(f"\n✅ Parsed Documents : {len(parsed_documents)}")

        # -------------------------------------------------------
        # Chunk Documents
        # -------------------------------------------------------

        print("\n🧩 Chunking Documents")

        chunks = chunker.chunk_documents(parsed_documents)

        print(f"✅ Generated Chunks : {len(chunks)}")

        # -------------------------------------------------------
        # Deduplicate
        # -------------------------------------------------------

        print("\n🔍 Deduplicating Chunks")

        processed_chunks = deduplicator.deduplicate(chunks)

        canonical_chunks = [
            c for c in processed_chunks
            if not c.is_duplicate
        ]

        stats = deduplicator.get_dedup_stats()

        print(f"Canonical Chunks : {stats['canonical_count']}")
        print(f"Duplicate Chunks : {stats['duplicate_count']}")

        # -------------------------------------------------------
        # Embed
        # -------------------------------------------------------

        print("\n🧠 Loading Embedding Model")

        start = time.time()

        embeddings = embedder.embed_chunks(
            canonical_chunks,
            show_progress=True,
        )

        elapsed = time.time() - start

        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)

        print(f"Model Name          : {embedder.model_name}")
        print(f"Embedding Dimension : {embedder.dimension}")
        print(f"Embeddings Created  : {len(embeddings)}")
        print(f"Embedding Time      : {elapsed:.2f} sec")

        # -------------------------------------------------------
        # Sample Embedding
        # -------------------------------------------------------

        if embeddings:

            vector = embeddings[0]

            print("\nSample Vector")

            print("-" * 70)

            print(f"Vector Length : {len(vector)}")

            print("First 10 Values")

            for value in vector[:10]:
                print(f"{value:.6f}")

        # -------------------------------------------------------
        # Sample Chunk
        # -------------------------------------------------------

        if canonical_chunks:

            chunk = canonical_chunks[0]

            print("\nSample Chunk")

            print("-" * 70)

            print(f"Title      : {chunk.title}")
            print(f"Heading    : {chunk.heading_path}")
            print(f"Characters : {len(chunk.content)}")

            print("\nPreview")

            preview = chunk.content[:300]

            print(preview)

        print("\n🎉 Embedder Test Completed Successfully!")

    except Exception:

        print("\n❌ Embedder Test Failed!\n")

        traceback.print_exc()


if __name__ == "__main__":
    main()
"""
Test script for MinHash Deduplicator.

Run:
    python -m scripts.test_minhash_dedup
"""

from pathlib import Path
import traceback

from src.parsers.registry import ParserRegistry
from src.chunking.hybrid_chunker import HybridChunker
from src.dedup.minhash_dedup import MinHashDeduplicator


def main():
    print("=" * 70)
    print("🚀 MINHASH DEDUPLICATION TEST")
    print("=" * 70)

    data_dir = Path("data")

    if not data_dir.exists():
        print("❌ Data directory not found.")
        return

    registry = ParserRegistry()
    chunker = HybridChunker()
    deduplicator = MinHashDeduplicator()

    parsed_documents = []

    print("\n📄 Parsing Documents")

    try:
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

        print("\n🧩 Chunking Documents")

        chunks = chunker.chunk_documents(parsed_documents)

        print(f"✅ Generated Chunks : {len(chunks)}")

        print("\n🔍 Running MinHash Deduplication")

        processed_chunks = deduplicator.deduplicate(chunks)

        stats = deduplicator.get_dedup_stats()

        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)

        print(f"Total Chunks       : {stats['total_processed']}")
        print(f"Canonical Chunks   : {stats['canonical_count']}")
        print(f"Duplicate Chunks   : {stats['duplicate_count']}")
        print(f"Duplicate Ratio    : {stats['duplicate_ratio']}%")
        print(f"Threshold          : {stats['threshold']}")
        print(f"Num Permutations   : {stats['num_perm']}")
        print(f"Shingle Size       : {stats['shingle_size']}")

        print("\nDuplicate Chunks")

        duplicate_found = False

        for chunk in processed_chunks:

            if not chunk.is_duplicate:
                continue

            duplicate_found = True

            print("-" * 60)
            print(f"Chunk ID       : {chunk.chunk_id}")
            print(f"Duplicate Of   : {chunk.duplicate_of}")

            similarity = chunk.metadata.get(
                "dedup_similarity",
                "N/A",
            )

            print(f"Similarity     : {similarity}")

            print("\nPreview")

            preview = chunk.content[:200].replace("\n", " ")

            print(preview)

        if not duplicate_found:
            print("No duplicate chunks detected.")

        print("\nCanonical Chunks")

        shown = 0

        for chunk in processed_chunks:

            if chunk.is_duplicate:
                continue

            print("-" * 60)
            print(f"Chunk ID     : {chunk.chunk_id}")
            print(f"Title        : {chunk.title}")
            print(f"Heading      : {chunk.heading_path}")
            print(f"Characters   : {len(chunk.content)}")

            shown += 1

            if shown >= 5:
                break

        print("\n🎉 MinHash Deduplication Test Completed Successfully!")

    except Exception:
        print("\n❌ Test Failed!\n")
        traceback.print_exc()


if __name__ == "__main__":
    main()
"""
Test script for Hybrid Chunker.

Run:

    python -m scripts.test_chunker
"""

from pathlib import Path
import traceback

from src.parsers.registry import ParserRegistry
from src.chunking.hybrid_chunker import HybridChunker


def main():

    print("=" * 70)
    print("🚀 HYBRID CHUNKER TEST")
    print("=" * 70)

    registry = ParserRegistry()
    chunker = HybridChunker()

    data_dir = Path("data")

    parsed_documents = []

    print("\n📂 Scanning data directory...")

    for file in sorted(data_dir.rglob("*")):

        if not file.is_file():
            continue

        if file.name == "permissions.json":
            continue

        if not registry.can_parse(file):
            continue

        print(f"\n📄 Parsing: {file.name}")

        try:

            parser = registry.get_parser(file)

            docs = parser.parse(file)

            parsed_documents.extend(docs)

            print(f"   ✅ Parsed {len(docs)} document(s)")

        except Exception:

            print(f"   ❌ Failed to parse {file.name}")

            traceback.print_exc()

    print("\n" + "=" * 70)
    print("PARSING SUMMARY")
    print("=" * 70)

    print(f"Documents Parsed : {len(parsed_documents)}")

    if not parsed_documents:

        print("\n❌ No documents were parsed.")

        return

    print("\n🚀 Running Hybrid Chunker...")

    try:

        chunks = chunker.chunk_documents(parsed_documents)

    except Exception:

        traceback.print_exc()

        return

    print("\n" + "=" * 70)
    print("CHUNKING SUMMARY")
    print("=" * 70)

    print(f"Chunks Generated : {len(chunks)}")

    if not chunks:

        print("\n❌ No chunks generated.")

        return

    print("\nShowing first 10 chunks...\n")

    for i, chunk in enumerate(chunks[:10], start=1):

        print("-" * 70)

        print(f"Chunk #{i}")

        print("-" * 70)

        print(f"Chunk ID      : {chunk.chunk_id}")

        print(f"Document ID   : {chunk.doc_id}")

        print(f"Title         : {chunk.title}")

        print(f"Source Type   : {chunk.source_type.value}")

        print(f"Heading       : {chunk.heading}")

        print(f"Heading Path  : {chunk.heading_path}")

        print(f"Page Number   : {chunk.page_number}")

        print(f"Row Range     : {chunk.row_range}")

        print(f"Is Table      : {chunk.is_table}")

        print(f"ACL Tags      : {chunk.acl_tags}")

        print(f"Characters    : {len(chunk.content)}")

        print("\nMetadata")

        print(chunk.metadata)

        print("\nContent Preview")

        print("-" * 40)

        print(chunk.content[:300])

        print()

    print("=" * 70)
    print("FINAL STATISTICS")
    print("=" * 70)

    pdf_chunks = sum(
        1 for c in chunks if c.source_type.value == "pdf"
    )

    markdown_chunks = sum(
        1 for c in chunks if c.source_type.value == "confluence"
    )

    excel_chunks = sum(
        1 for c in chunks if c.source_type.value == "excel"
    )

    slack_chunks = sum(
        1 for c in chunks if c.source_type.value == "slack"
    )

    table_chunks = sum(
        1 for c in chunks if c.is_table
    )

    print(f"PDF Chunks        : {pdf_chunks}")

    print(f"Markdown Chunks   : {markdown_chunks}")

    print(f"Excel Chunks      : {excel_chunks}")

    print(f"Slack Chunks      : {slack_chunks}")

    print(f"Table Chunks      : {table_chunks}")

    print(f"Total Chunks      : {len(chunks)}")

    print("\n🎉 Hybrid Chunker Test Completed Successfully!")


if __name__ == "__main__":
    main()
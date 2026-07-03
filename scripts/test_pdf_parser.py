"""
Test script for PDF Parser.

Run:

    python scripts/test_pdf_parser.py

This script checks:
1. PDF exists
2. Parser initialization
3. PDF parsing
4. ParsedDocument contents
"""

from pathlib import Path
import traceback

from src.parsers.pdf_parser import PDFParser


def main():
    print("=" * 70)
    print("🚀 PDF PARSER DEBUG TEST")
    print("=" * 70)

    # ------------------------------------------------------------------
    # Locate PDF
    # ------------------------------------------------------------------
    pdf_path = Path("data/pdf/employee-handbook.pdf")

    print(f"\n📂 Looking for PDF:")
    print(pdf_path.resolve())

    if not pdf_path.exists():
        print("\n❌ ERROR: PDF file not found!")
        return

    print("✅ PDF exists")

    # ------------------------------------------------------------------
    # Create parser
    # ------------------------------------------------------------------
    print("\n🔧 Creating PDFParser...")

    try:
        parser = PDFParser()
        print("✅ PDFParser created successfully")

    except Exception as e:
        print("❌ Failed to create PDFParser")
        traceback.print_exc()
        return

    # ------------------------------------------------------------------
    # Parse PDF
    # ------------------------------------------------------------------
    print("\n📖 Parsing PDF...")

    try:
        documents = parser.parse(pdf_path)

    except Exception as e:
        print("❌ Parser crashed!")
        traceback.print_exc()
        return

    print("✅ Parsing completed")

    # ------------------------------------------------------------------
    # Print results
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    print(f"Documents Returned : {len(documents)}")

    for i, doc in enumerate(documents, start=1):

        print("\n" + "-" * 60)
        print(f"Document #{i}")
        print("-" * 60)

        print(f"Title        : {doc.title}")
        print(f"Document ID  : {doc.doc_id}")
        print(f"Source Type  : {doc.source_type}")
        print(f"Source Path  : {doc.source_path}")
        print(f"Scanned PDF  : {doc.is_scanned}")

        print("\nMetadata")
        print(doc.metadata)

        print("\nACL Tags")
        print(doc.acl_tags)

        print("\nSections")
        print(f"Total Sections : {len(doc.sections)}")

        for section in doc.sections:
            print(
                f"  • Page {section.page_number} | {section.heading}"
            )

        print("\nTables")
        print(f"Tables Found : {len(doc.tables)}")

        print("\nContent Preview")
        print("-" * 60)
        print(doc.content[:500])
        print("-" * 60)

    print("\n🎉 PDF Parser Test Completed Successfully!")


if __name__ == "__main__":
    try:
        main()

    except Exception:
        print("\n❌ Unexpected Fatal Error\n")
        traceback.print_exc()
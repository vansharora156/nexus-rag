"""
Test script for Excel Parser.

Run:

python -m scripts.test_excel_parser
"""

from pathlib import Path
import traceback

from src.parsers.excel_parser import ExcelParser


def main():

    print("=" * 70)
    print("🚀 EXCEL PARSER TEST")
    print("=" * 70)

    excel_dir = Path("data/excel")

    files = []

    files.extend(excel_dir.glob("*.xlsx"))
    files.extend(excel_dir.glob("*.xls"))
    files.extend(excel_dir.glob("*.csv"))

    if not files:

        print("❌ No spreadsheet files found.")
        return

    excel_path = files[0]

    print(f"\n📂 Using Spreadsheet:")
    print(excel_path.resolve())

    try:

        parser = ExcelParser()

        print("\n✅ ExcelParser created")

        documents = parser.parse(excel_path)

        print("\n✅ Parsing completed")

        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)

        print(f"Documents Returned : {len(documents)}")

        for doc in documents:

            print("\nTitle")
            print(doc.title)

            print("\nDocument ID")
            print(doc.doc_id)

            print("\nMetadata")
            print(doc.metadata)

            print("\nACL Tags")
            print(doc.acl_tags)

            print("\nTables")
            print(len(doc.tables))

            print("\nSections")
            print(len(doc.sections))

            for section in doc.sections:

                print("-" * 40)

                print("Heading :", section.heading)

                print("Row Range :", section.row_range)

                print("Heading Path :", section.heading_path)

                print("\nPreview")

                print(section.content[:200])

            print("\nDocument Preview")

            print(doc.content[:500])

    except Exception:

        traceback.print_exc()


if __name__ == "__main__":
    main()
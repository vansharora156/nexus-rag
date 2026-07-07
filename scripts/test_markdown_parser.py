print("SCRIPT STARTED")
"""
Test script for Markdown Parser.

Run:
    python -m scripts.test_markdown_parser
"""

from pathlib import Path
import traceback

from src.parsers.markdown_parser import MarkdownParser


def main():
    print("=" * 70)
    print("🚀 MARKDOWN PARSER DEBUG TEST")
    print("=" * 70)

    markdown_dir = Path("data/markdown")

    md_files = list(markdown_dir.glob("*.md"))

    if not md_files:
        print("❌ No markdown files found.")
        return

    md_path = md_files[0]

    print(f"\n📂 Using Markdown File:")
    print(md_path.resolve())

    try:
        parser = MarkdownParser()
        print("\n✅ MarkdownParser created")

        documents = parser.parse(md_path)

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
            print(f"Total Sections : {len(doc.sections)}")

            for section in doc.sections:

                print("-" * 40)
                print(f"Heading      : {section.heading}")
                print(f"Level        : {section.heading_level}")
                print(f"Heading Path : {section.heading_path}")
                print("\nContent Preview")
                print(section.content[:150])

            print("\nContent Preview")
            print("-" * 60)
            print(doc.content[:500])

    except Exception:
        traceback.print_exc()


if __name__ == "__main__":
    main()
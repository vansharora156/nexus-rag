"""
Test script for Slack Parser.

Run:

python -m scripts.test_slack_parser
"""

from pathlib import Path
import traceback

from src.parsers.slack_parser import SlackParser


def main():

    print("=" * 70)
    print("🚀 SLACK PARSER TEST")
    print("=" * 70)

    slack_dir = Path("data/slack")

    files = list(slack_dir.glob("*.json"))

    if not files:

        print("❌ No Slack JSON files found.")
        return

    slack_path = files[0]

    print("\n📂 Using Slack Export:")
    print(slack_path.resolve())

    try:

        parser = SlackParser()

        print("\n✅ SlackParser created")

        documents = parser.parse(slack_path)

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

            print("\nSections")
            print(f"Total Sections : {len(doc.sections)}")

            for section in doc.sections:

                print("-" * 40)

                print("Heading :", section.heading)

                print("Heading Path :", section.heading_path)

                print("\nPreview")

                print(section.content[:250])

            print("\nDocument Preview")
            print("-" * 60)

            print(doc.content[:700])

    except Exception:
        traceback.print_exc()


if __name__ == "__main__":
    main()
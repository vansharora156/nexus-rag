"""End-to-end query test script for AskTheCompany.

Fires a set of representative enterprise questions directly through the
QueryPipeline (no HTTP server required) and prints the results.

Run from the project root::

    python scripts/test_query.py

Prerequisites:
- Data must have been ingested: ``python scripts/ingest.py``
- GEMINI_API_KEY must be set in .env
"""

import sys
import time
from pathlib import Path

# Ensure project root is importable
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import logging
logging.basicConfig(
    level=logging.WARNING,  # Suppress verbose pipeline logs during the test
    format="%(levelname)s — %(message)s",
)

from src.pipeline.query import QueryPipeline  # noqa: E402

# ---------------------------------------------------------------------------
# Test questions (covers factual, table-lookup, multi-source, permission)
# ---------------------------------------------------------------------------

TEST_CASES = [
    {
        "question": "What is the company's vacation policy?",
        "username": "alice",
        "description": "Factual — HR policy document",
    },
    {
        "question": "What were the Q4 revenue figures and how do they compare to Q3?",
        "username": "alice",
        "description": "Table lookup — financial report",
    },
    {
        "question": "What engineering tools and frameworks does the team use?",
        "username": "bob",
        "description": "Multi-source — Slack + markdown",
    },
    {
        "question": "Summarise the key decisions from the last engineering team discussion.",
        "username": "bob",
        "description": "Slack thread synthesis",
    },
    {
        "question": "What is the process for requesting a software licence?",
        "username": "alice",
        "description": "Factual — policy document",
    },
]


def separator(title: str) -> None:
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)


def print_result(result: dict, description: str) -> None:
    print(f"\n📋 Test: {description}")
    print(f"👤 User : {result['username']}")
    print(f"❓ Q    : {result.get('question', '')}")
    print(f"⏱  Time : {result['elapsed_ms']:.0f} ms")
    print(f"📚 Sources used: {result['num_sources']}")

    if result["query_variants"]:
        print(f"🔁 Query variants searched: {len(result['query_variants'])}")
        for i, v in enumerate(result["query_variants"], 1):
            print(f"   [{i}] {v[:70]}")

    print(f"\n💡 Answer:\n{result['answer']}")

    if result["citations"]:
        print(f"\n📎 Citations ({len(result['citations'])}):")
        for c in result["citations"]:
            print(f"  {c['label']}")
            print(f"    Score: retrieval={c['score']:.3f}", end="")
            if c.get("rerank_score") is not None:
                print(f"  rerank={c['rerank_score']:.1f}/10", end="")
            print()


def main() -> None:
    separator("AskTheCompany — End-to-End Query Test")

    print("\nInitialising QueryPipeline…")
    t0 = time.perf_counter()
    try:
        pipeline = QueryPipeline()
    except Exception as exc:
        print(f"\n❌ Failed to initialise pipeline: {exc}")
        print("   Make sure you have run: python scripts/ingest.py")
        sys.exit(1)

    init_ms = (time.perf_counter() - t0) * 1000
    print(f"Pipeline ready in {init_ms:.0f} ms.\n")

    passed = 0
    failed = 0

    for i, tc in enumerate(TEST_CASES, start=1):
        separator(f"Test {i}/{len(TEST_CASES)}: {tc['description']}")
        try:
            result = pipeline.query(
                question=tc["question"],
                username=tc["username"],
                top_k=5,
            )
            result["question"] = tc["question"]
            print_result(result, tc["description"])
            passed += 1
        except Exception as exc:
            print(f"\n❌ Query failed: {exc}")
            import traceback
            traceback.print_exc()
            failed += 1

    separator("Summary")
    print(f"✅ Passed : {passed}")
    print(f"❌ Failed : {failed}")
    print(f"Total  : {len(TEST_CASES)}")


if __name__ == "__main__":
    main()

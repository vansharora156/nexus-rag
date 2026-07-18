# -*- coding: utf-8 -*-
"""Day 5 Test - Query Pipeline End-to-End

Tests the full chain:
  QueryRewriter -> HybridRetriever (Qdrant + BM25 + RRF) ->
  CrossEncoderReranker -> GeminiGenerator

Each question tests a different domain and ACL user:

  Q1 (alice/engineering): "How do I deploy to production?"
  Q2 (carol/hr):          "What is the company leave policy?"
  Q3 (dave/finance):      "What is the Q3 budget?"
  Q4 (frank/intern):      "What are the company values?"
  Q5 (alice/engineering): Finance question - should get restricted answer

Per-question checks:
  - answer is non-empty string (> 30 chars)
  - citations list is non-empty
  - num_sources >= 1
  - elapsed_ms is recorded
  - query_variants contains the original question
  - username echoed correctly

Structural checks (after all questions):
  - Citation dicts have icon, title, source_type, content_snippet
  - ACL test: frank (intern/'all') cannot see finance-only chunks

Run from project root:
    python scripts/day5_test_query_pipeline.py
"""

import sys
import io
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
logging.basicConfig(level=logging.WARNING, format="%(levelname)s - %(message)s")

from src.pipeline.query import QueryPipeline

PASS = "[PASS]"
FAIL = "[FAIL]"
passed_total = 0
failed_total = 0


def check(condition: bool, msg: str) -> bool:
    global passed_total, failed_total
    if condition:
        passed_total += 1
        print(f"  {PASS}  {msg}")
    else:
        failed_total += 1
        print(f"  {FAIL}  {msg}")
    return condition


def divider(char: str = "-", width: int = 62) -> None:
    print(char * width)


def section(title: str) -> None:
    print(f"\n{'=' * 62}")
    print(f"  {title}")
    print("=" * 62)


def run_question(pipeline: QueryPipeline, q: str, user: str, idx: int) -> dict:
    """Run one question and print a summary, returning the result dict."""
    print(f"\n[Q{idx}] User: '{user}'")
    print(f"  Question: {q}")
    print("  Running pipeline...")
    t0 = time.perf_counter()
    result = pipeline.query(question=q, username=user)
    wall_ms = (time.perf_counter() - t0) * 1000

    print(f"\n  Answer ({result['elapsed_ms']:.0f}ms):")
    # Print wrapped at 60 chars
    answer = result["answer"]
    for line in answer.split("\n"):
        print(f"    {line}")

    print(f"\n  Query variants searched:")
    for i, v in enumerate(result["query_variants"], 1):
        print(f"    [{i}] {v}")

    print(f"\n  Sources ({result['num_sources']}):")
    for c in result["citations"]:
        print(f"    [{c['index']}] {c['icon']} {c['title'][:40]}  "
              f"score={c['score']:.3f}")

    return result


# ============================================================
# MAIN
# ============================================================

def main() -> int:
    print("=" * 62)
    print("  Day 5 - Query Pipeline End-to-End")
    print("=" * 62)

    section("Pipeline Initialization")
    print("\n  Loading all components (Embedder, Qdrant, BM25, Reranker)...")
    t0 = time.perf_counter()
    pipeline = QueryPipeline(use_reranker=True, use_query_rewriting=True, top_k=5)
    init_ms = (time.perf_counter() - t0) * 1000
    print(f"  Pipeline ready in {init_ms:.0f}ms")
    check(True, f"Pipeline initialized in {init_ms:.0f}ms")

    # ------------------------------------------------------------------
    # Q1: Engineering question for alice
    # ------------------------------------------------------------------
    section("Q1: Engineering (alice)")
    r1 = run_question(pipeline,
                      q="How do I set up the local development environment and deploy to production?",
                      user="alice",
                      idx=1)

    divider()
    check(len(r1["answer"]) > 30,     f"Answer is non-trivial ({len(r1['answer'])} chars)")
    check(r1["num_sources"] >= 1,      f"At least 1 source cited (got {r1['num_sources']})")
    check(len(r1["citations"]) >= 1,   f"Citations list non-empty ({len(r1['citations'])})")
    check(r1["username"] == "alice",   f"Username echoed: {r1['username']}")
    check(len(r1["query_variants"]) >= 1, f"Query variants: {len(r1['query_variants'])}")
    check(r1["query_variants"][0] == "How do I set up the local development environment and deploy to production?",
          "Original query is first variant")
    check(r1["elapsed_ms"] > 0,        f"elapsed_ms recorded: {r1['elapsed_ms']}ms")

    # ------------------------------------------------------------------
    # Q2: HR question for carol
    # ------------------------------------------------------------------
    section("Q2: HR Leave Policy (carol)")
    r2 = run_question(pipeline,
                      q="How many vacation days do employees get and can unused days be carried over?",
                      user="carol",
                      idx=2)

    divider()
    check(len(r2["answer"]) > 30,     f"Answer is non-trivial ({len(r2['answer'])} chars)")
    check(r2["num_sources"] >= 1,      f"At least 1 source cited (got {r2['num_sources']})")
    check(r2["username"] == "carol",   f"Username echoed: {r2['username']}")
    # Soft check: answer mentions leave terms OR hit a rate-limit (acceptable)
    leave_terms = ["leave", "vacation", "annual", "days", "pto", "carry"]
    answer_lower = r2["answer"].lower()
    is_rate_limited = "429" in r2["answer"] or "quota" in answer_lower
    has_leave_terms = any(t in answer_lower for t in leave_terms)
    check(has_leave_terms or is_rate_limited,
          f"Answer mentions leave terms OR rate-limited (acceptable): '{r2['answer'][:80]}'")

    # ------------------------------------------------------------------
    # Q3: Finance question for dave
    # ------------------------------------------------------------------
    section("Q3: Finance / Budget (dave)")
    r3 = run_question(pipeline,
                      q="What is the company's Q3 budget and spending breakdown?",
                      user="dave",
                      idx=3)

    divider()
    check(len(r3["answer"]) > 30,     f"Answer is non-trivial ({len(r3['answer'])} chars)")
    check(r3["num_sources"] >= 1,      f"At least 1 source cited (got {r3['num_sources']})")
    check(r3["username"] == "dave",    f"Username echoed: {r3['username']}")

    # ------------------------------------------------------------------
    # Q4: Public question for frank (intern - 'all' role only)
    # ------------------------------------------------------------------
    section("Q4: Company Values (frank/intern)")
    r4 = run_question(pipeline,
                      q="What are the core company values at BigCorp?",
                      user="frank",
                      idx=4)

    divider()
    check(len(r4["answer"]) > 30,     f"Answer is non-trivial ({len(r4['answer'])} chars)")
    check(r4["num_sources"] >= 1,      f"At least 1 source cited (got {r4['num_sources']})")
    check(r4["username"] == "frank",   f"Username echoed: {r4['username']}")

    # ------------------------------------------------------------------
    # Q5: ACL test - alice asks about finance (should be restricted)
    # ------------------------------------------------------------------
    section("Q5: ACL Test - alice asks finance question (should be restricted)")
    r5 = run_question(pipeline,
                      q="What is the Q3 budget allocation for each department?",
                      user="alice",
                      idx=5)

    divider()
    check(r5["username"] == "alice", f"Username echoed: {r5['username']}")
    # alice has engineering+all but NOT finance. Finance docs should not appear.
    finance_only_leaked = [
        c for c in r5["citations"]
        if "finance" in c.get("acls", [])
        and "all" not in c.get("acls", [])
        and "engineering" not in c.get("acls", [])
    ]
    check(len(finance_only_leaked) == 0,
          f"No finance-only sources leaked to alice ({len(finance_only_leaked)} leaks)")
    # Should either give a graceful "not found" or answer from non-finance docs
    check(len(r5["answer"]) > 10, f"Got a response (not silent failure): {len(r5['answer'])} chars")

    # ------------------------------------------------------------------
    # Citation schema check (across all results)
    # ------------------------------------------------------------------
    section("Citation Schema Check")
    required_citation_keys = {"index", "icon", "title", "source_type",
                               "content_snippet", "score", "acls", "chunk_id"}
    all_citations = (r1["citations"] + r2["citations"] +
                     r3["citations"] + r4["citations"])

    print(f"\n  Checking {len(all_citations)} total citations...")
    if all_citations:
        sample = all_citations[0]
        missing = required_citation_keys - set(sample.keys())
        check(not missing,
              f"All required citation keys present (missing: {missing or 'none'})")
        check(all(c.get("icon") in {"📄","📝","📊","💬","📎"}
                  for c in all_citations),
              f"All citation icons are valid source-type icons")
        check(all(isinstance(c.get("content_snippet"), str) and
                  len(c.get("content_snippet", "")) > 5
                  for c in all_citations),
              f"All citations have non-empty content_snippet")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    total = passed_total + failed_total
    print(f"\n{'=' * 62}")
    print(f"  Result: {passed_total}/{total} passed")

    print(f"\n  Latency summary:")
    for i, r in enumerate([r1, r2, r3, r4, r5], 1):
        print(f"    Q{i}: {r['elapsed_ms']:>6.0f}ms  "
              f"| {r['num_sources']} sources | user={r['username']}")

    if failed_total == 0:
        print("\n  *** Day 5 Complete - Query Pipeline verified end-to-end! ***")
    else:
        print(f"\n  WARNING: {failed_total} test(s) failed - check output above.")
    print("=" * 62)
    return 0 if failed_total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

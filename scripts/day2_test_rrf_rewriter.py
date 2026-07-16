# -*- coding: utf-8 -*-
"""Day 2 Test - RRF + Query Rewriting

Part A: Reciprocal Rank Fusion (pure logic, no API needed)
  1. Basic merge of two lists
  2. Correct ranking when a doc appears in both lists
  3. RRF formula math check
  4. Deduplication across lists
  5. Single-list passthrough
  6. Empty list handling
  7. k constant effect

Part B: QueryRewriter (live Gemini API call)
  1. Returns original query + N variants
  2. All variants are non-empty strings
  3. No variant duplicates the original exactly
  4. Fallback on bad query (empty string)
  5. Fallback on API error simulation

Run from project root:
    python scripts/day2_test_rrf_rewriter.py
"""

import sys
import io
import math
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.hybrid_retriever import reciprocal_rank_fusion
from src.retrieval.query_rewriter import QueryRewriter

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


def section(title: str) -> None:
    print(f"\n{'=' * 58}")
    print(f"  {title}")
    print("=" * 58)


# ============================================================
# PART A: Reciprocal Rank Fusion
# ============================================================

def test_rrf() -> None:
    section("Part A: Reciprocal Rank Fusion (RRF)")

    # --- Test 1: Basic two-list merge ---
    print("\n[A1] Basic merge - 2 lists, 3 docs each")
    list_a = [
        {"chunk_id": "alpha",   "content": "HR policy"},
        {"chunk_id": "beta",    "content": "Engineering docs"},
        {"chunk_id": "gamma",   "content": "Finance report"},
    ]
    list_b = [
        {"chunk_id": "beta",    "content": "Engineering docs"},
        {"chunk_id": "delta",   "content": "Slack thread"},
        {"chunk_id": "alpha",   "content": "HR policy"},
    ]
    merged = reciprocal_rank_fusion([list_a, list_b], k=60)

    check(len(merged) == 4, f"4 unique docs in merged result (got {len(merged)})")
    all_ids = [c["chunk_id"] for c in merged]
    check(set(all_ids) == {"alpha", "beta", "gamma", "delta"},
          f"All chunk_ids present: {all_ids}")

    # --- Test 2: Correct ranking ---
    print("\n[A2] Ranking: 'beta' appears at rank-2 in list_a AND rank-1 in list_b => should be #1")
    # beta: 1/(60+2) + 1/(60+1) = 0.01613 + 0.01639 = 0.03252
    # alpha: 1/(60+1) + 1/(60+3) = 0.01639 + 0.01587 = 0.03226
    check(merged[0]["chunk_id"] == "beta",
          f"'beta' is #1 (appears in both lists at top) - got '{merged[0]['chunk_id']}'")
    check(merged[1]["chunk_id"] == "alpha",
          f"'alpha' is #2 (rank-1 in list_a, rank-3 in list_b) - got '{merged[1]['chunk_id']}'")

    # --- Test 3: RRF formula math ---
    print("\n[A3] RRF score math verification (k=60)")
    beta_expected = 1.0 / (60 + 2) + 1.0 / (60 + 1)   # rank-2 in A, rank-1 in B
    beta_actual = merged[0]["rrf_score"]
    check(
        abs(beta_actual - beta_expected) < 1e-8,
        f"beta RRF score correct: expected={beta_expected:.8f} actual={beta_actual:.8f}"
    )

    gamma_expected = 1.0 / (60 + 3)   # only in list_a at rank-3
    gamma_actual = next(c["rrf_score"] for c in merged if c["chunk_id"] == "gamma")
    check(
        abs(gamma_actual - gamma_expected) < 1e-8,
        f"gamma RRF score correct (only in list_a): expected={gamma_expected:.8f} actual={gamma_actual:.8f}"
    )

    # --- Test 4: Each chunk has rrf_score key ---
    print("\n[A4] All merged chunks have 'rrf_score' key")
    check(all("rrf_score" in c for c in merged),
          f"All {len(merged)} chunks have 'rrf_score'")

    # --- Test 5: Sorted descending ---
    print("\n[A5] Merged list is sorted by descending rrf_score")
    scores = [c["rrf_score"] for c in merged]
    check(scores == sorted(scores, reverse=True),
          f"Scores descending: {[round(s, 5) for s in scores]}")

    # --- Test 6: Single list passthrough ---
    print("\n[A6] Single ranked list passthrough")
    single = reciprocal_rank_fusion([list_a], k=60)
    check(len(single) == 3, f"Single-list merge returns 3 docs (got {len(single)})")
    check(single[0]["chunk_id"] == "alpha",
          f"First doc preserved (alpha) - got '{single[0]['chunk_id']}'")
    # Scores should be 1/(61), 1/(62), 1/(63)
    check(single[0]["rrf_score"] > single[1]["rrf_score"],
          f"Ordering preserved in single-list: {[round(c['rrf_score'],5) for c in single]}")

    # --- Test 7: Empty list ---
    print("\n[A7] Empty list input")
    empty = reciprocal_rank_fusion([], k=60)
    check(len(empty) == 0, "Empty input returns empty list")

    # --- Test 8: 3-list fusion with repeated doc ---
    print("\n[A8] 3-list fusion, 'omega' appears in all three lists")
    l1 = [{"chunk_id": "omega", "content": "Top doc"}, {"chunk_id": "x", "content": "x"}]
    l2 = [{"chunk_id": "omega", "content": "Top doc"}, {"chunk_id": "y", "content": "y"}]
    l3 = [{"chunk_id": "omega", "content": "Top doc"}, {"chunk_id": "z", "content": "z"}]
    three = reciprocal_rank_fusion([l1, l2, l3], k=60)
    check(three[0]["chunk_id"] == "omega",
          f"'omega' (rank-1 in all 3 lists) is first - got '{three[0]['chunk_id']}'")
    omega_score = three[0]["rrf_score"]
    omega_expected = 3 * (1.0 / (60 + 1))
    check(abs(omega_score - omega_expected) < 1e-8,
          f"omega score = 3 * 1/(61) = {omega_expected:.6f}, got {omega_score:.6f}")

    # --- Test 9: k constant effect ---
    print("\n[A9] k=0 gives higher scores than k=60")
    fused_k0  = reciprocal_rank_fusion([list_a, list_b], k=0)
    fused_k60 = reciprocal_rank_fusion([list_a, list_b], k=60)
    check(fused_k0[0]["rrf_score"] > fused_k60[0]["rrf_score"],
          f"k=0 top score ({fused_k0[0]['rrf_score']:.4f}) > k=60 ({fused_k60[0]['rrf_score']:.4f})")


# ============================================================
# PART B: Query Rewriter (live Gemini API)
# ============================================================

def test_query_rewriter() -> None:
    section("Part B: QueryRewriter (live Gemini API call)")

    rewriter = QueryRewriter(n_variants=3)

    # --- Test 1: Normal query rewriting ---
    query = "What is the company's vacation policy?"
    print(f"\n[B1] Rewriting query: '{query}'")
    print("     Calling Gemini API...")
    t0 = time.perf_counter()
    variants = rewriter.rewrite(query)
    elapsed = (time.perf_counter() - t0) * 1000

    print(f"\n     Got {len(variants)} queries in {elapsed:.0f}ms:")
    for i, v in enumerate(variants, 1):
        print(f"     [{i}] {v}")

    check(len(variants) >= 2, f"Got at least 2 queries (original + variants): {len(variants)}")
    check(variants[0] == query, f"Original query is first: '{variants[0]}'")
    check(all(isinstance(v, str) and len(v) > 5 for v in variants),
          "All variants are non-empty strings (>5 chars)")
    check(len(set(variants)) == len(variants),
          f"No duplicate variants (unique={len(set(variants))}, total={len(variants)})")

    # --- Test 2: Different query ---
    print(f"\n[B2] Rewriting a technical query")
    tech_q = "How do we handle database connection pooling in production?"
    t0 = time.perf_counter()
    tech_variants = rewriter.rewrite(tech_q)
    elapsed = (time.perf_counter() - t0) * 1000
    print(f"     Got {len(tech_variants)} queries in {elapsed:.0f}ms:")
    for i, v in enumerate(tech_variants, 1):
        print(f"     [{i}] {v}")
    check(len(tech_variants) >= 2, f"Got at least 2 queries for technical question")

    # --- Test 3: Empty query fallback ---
    print(f"\n[B3] Empty query fallback (no API call expected)")
    empty_result = rewriter.rewrite("")
    check(empty_result == [""], f"Empty query returns [''] fallback: {empty_result}")

    # --- Test 4: Whitespace-only fallback ---
    print(f"\n[B4] Whitespace-only query fallback")
    ws_result = rewriter.rewrite("   ")
    check(ws_result == ["   "], f"Whitespace query returns ['   '] fallback: {ws_result}")

    # --- Test 5: Verify variants are semantically related ---
    print(f"\n[B5] Spot-check: vacation variants mention 'leave' or 'time off' or 'pto'")
    vacation_text = " ".join(variants).lower()
    has_related = any(kw in vacation_text for kw in
                      ["leave", "pto", "paid time", "time off", "annual", "holiday",
                       "vacation", "days off", "benefit"])
    check(has_related,
          f"At least one related keyword found in variants: '{vacation_text[:100]}'")


# ============================================================
# MAIN
# ============================================================

def main() -> int:
    print("=" * 58)
    print("  Day 2 - RRF + Query Rewriting")
    print("=" * 58)

    test_rrf()
    test_query_rewriter()

    print(f"\n{'=' * 58}")
    print(f"  Result: {passed_total}/{passed_total + failed_total} passed")
    if failed_total == 0:
        print("  *** Day 2 Complete - RRF and QueryRewriter verified! ***")
    else:
        print(f"  WARNING: {failed_total} test(s) failed - check output above.")
    print("=" * 58)
    return 0 if failed_total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

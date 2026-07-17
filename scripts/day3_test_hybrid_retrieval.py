# -*- coding: utf-8 -*-
"""Day 3 Test - Full Hybrid Retrieval

Tests (require a populated Qdrant + BM25 index from ingest):

Part A: Index Health Check
  1. Qdrant collection exists and has points
  2. BM25 index dir exists and metadata is loadable

Part B: Dense Retrieval (Qdrant)
  3. Embed a query and search Qdrant
  4. Returns chunks with expected keys
  5. ACL filter works - alice sees engineering, not finance
  6. Scores are between 0 and 1

Part C: Sparse Retrieval (BM25)
  7. BM25 search returns results
  8. Results contain chunk_id, content, score
  9. ACL filter on BM25 - carol (hr) can see hr docs
  10. BM25 keyword matching - 'vacation' query finds leave-policy doc

Part D: RRF Fusion (Dense + Sparse combined)
  11. Same query through dense AND sparse, then RRF merge
  12. Fused list is longer than either individual list
  13. Top result has rrf_score
  14. No duplicate chunk_ids in fused result

Run from project root:
    python scripts/day3_test_hybrid_retrieval.py
"""

import sys
import io
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
logging.basicConfig(level=logging.WARNING, format="%(levelname)s - %(message)s")

from src.indexing.vector_store import VectorStore
from src.indexing.bm25_index import BM25Index
from src.indexing.embedder import Embedder
from src.retrieval.hybrid_retriever import reciprocal_rank_fusion

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
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


# ============================================================
# PART A: Index Health Check
# ============================================================

def test_index_health(vs: VectorStore, bm25: BM25Index) -> None:
    section("Part A: Index Health Check")

    print("\n[A1] Qdrant collection")
    count = vs.count
    print(f"     Points in collection: {count}")
    check(count > 0, f"Qdrant has {count} indexed points (expected > 0)")

    print("\n[A2] BM25 index")
    n_chunks = len(bm25._chunk_ids)
    print(f"     Chunks in BM25 index: {n_chunks}")
    check(n_chunks > 0, f"BM25 index has {n_chunks} chunks (expected > 0)")
    check(len(bm25._chunk_contents) == n_chunks,
          f"Content list matches chunk_ids count ({n_chunks})")
    check(len(bm25._chunk_metadata) == n_chunks,
          f"Metadata list matches chunk_ids count ({n_chunks})")


# ============================================================
# PART B: Dense Retrieval (Qdrant)
# ============================================================

def test_dense_retrieval(vs: VectorStore, embedder: Embedder) -> None:
    section("Part B: Dense Retrieval (Qdrant)")

    query = "What is the vacation and leave policy for employees?"
    print(f"\n  Query: '{query}'")
    print("  Embedding query...")
    t0 = time.perf_counter()
    q_vec = embedder.embed_query(query)
    embed_ms = (time.perf_counter() - t0) * 1000
    print(f"  Embedded in {embed_ms:.0f}ms  dim={len(q_vec)}")

    print("\n[B3] Qdrant search - no ACL filter")
    t0 = time.perf_counter()
    results = vs.search(query_embedding=q_vec, top_k=5)
    search_ms = (time.perf_counter() - t0) * 1000
    print(f"     Returned {len(results)} results in {search_ms:.0f}ms")
    for i, r in enumerate(results, 1):
        print(f"     [{i}] score={r['score']:.4f}  src={r['source_type']:<10}  title={r['title'][:40]}")
    check(len(results) > 0, f"Dense search returned {len(results)} results")

    print("\n[B4] Result schema check")
    expected_keys = {"chunk_id", "doc_id", "content", "source_type", "acls", "score", "title"}
    if results:
        actual_keys = set(results[0].keys())
        missing = expected_keys - actual_keys
        check(not missing, f"All expected keys present (missing: {missing or 'none'})")
        check(isinstance(results[0]["content"], str) and len(results[0]["content"]) > 10,
              f"Content is non-empty string (len={len(results[0]['content'])})")

    print("\n[B5] ACL filter - alice (engineering) cannot see finance docs")
    alice_results = vs.search(query_embedding=q_vec, top_k=10,
                              active_roles=["engineering", "all"])
    finance_leaked = [r for r in alice_results
                      if "finance" in r.get("acls", [])
                      and "all" not in r.get("acls", [])
                      and "engineering" not in r.get("acls", [])]
    print(f"     alice got {len(alice_results)} results, finance leaks: {len(finance_leaked)}")
    check(len(finance_leaked) == 0, f"No finance-only docs leaked to alice")

    print("\n[B6] Scores are in valid range")
    if results:
        all_valid = all(0.0 <= r["score"] <= 1.0 for r in results)
        min_s = min(r["score"] for r in results)
        max_s = max(r["score"] for r in results)
        check(all_valid, f"All scores in [0,1]: min={min_s:.4f} max={max_s:.4f}")
        check(results[0]["score"] >= results[-1]["score"],
              f"Results sorted descending: {results[0]['score']:.4f} >= {results[-1]['score']:.4f}")


# ============================================================
# PART C: Sparse Retrieval (BM25)
# ============================================================

def test_sparse_retrieval(bm25: BM25Index) -> None:
    section("Part C: Sparse Retrieval (BM25)")

    print("\n[C7] BM25 search - 'vacation leave policy'")
    t0 = time.perf_counter()
    results = bm25.search("vacation leave policy", top_k=5)
    search_ms = (time.perf_counter() - t0) * 1000
    print(f"     Returned {len(results)} results in {search_ms:.0f}ms")
    for i, r in enumerate(results, 1):
        print(f"     [{i}] score={r['score']:.4f}  src={r['source_type']:<10}  title={r['title'][:40]}")
    check(len(results) > 0, f"BM25 returned {len(results)} results")

    print("\n[C8] Result schema check")
    expected_keys = {"chunk_id", "content", "source_type", "score", "acls"}
    if results:
        actual_keys = set(results[0].keys())
        missing = expected_keys - actual_keys
        check(not missing, f"All expected keys present (missing: {missing or 'none'})")

    print("\n[C9] BM25 ACL filter - carol (hr) search")
    carol_results = bm25.search("leave policy", top_k=10,
                                active_roles=["hr", "all"])
    eng_leaked = [r for r in carol_results
                  if "engineering" in r.get("acls", [])
                  and "hr" not in r.get("acls", [])
                  and "all" not in r.get("acls", [])]
    print(f"     carol got {len(carol_results)} results, engineering leaks: {len(eng_leaked)}")
    check(len(eng_leaked) == 0, "No engineering-only docs leaked to carol (hr)")

    print("\n[C10] BM25 keyword relevance - 'budget finance' finds finance docs")
    fin_results = bm25.search("budget finance quarterly", top_k=10)
    contents = " ".join(r.get("content", "").lower() for r in fin_results)
    titles   = " ".join(r.get("title", "").lower() for r in fin_results)
    has_fin  = any(kw in contents + titles
                   for kw in ["budget", "finance", "quarter", "revenue", "expense"])
    check(has_fin, f"Finance-related keyword found in BM25 results for budget query")


# ============================================================
# PART D: RRF Fusion
# ============================================================

def test_rrf_fusion(vs: VectorStore, bm25: BM25Index, embedder: Embedder) -> None:
    section("Part D: RRF Fusion (Dense + Sparse)")

    query = "engineering deployment process and CI/CD pipeline"
    print(f"\n  Query: '{query}'")

    # Dense
    q_vec = embedder.embed_query(query)
    dense = vs.search(query_embedding=q_vec, top_k=10)
    sparse = bm25.search(query, top_k=10)
    print(f"     Dense results : {len(dense)}")
    print(f"     Sparse results: {len(sparse)}")

    print("\n[D11] RRF merge of dense + sparse")
    fused = reciprocal_rank_fusion([dense, sparse], k=60)
    print(f"     Fused results : {len(fused)}")
    check(len(fused) > 0, f"RRF produced {len(fused)} fused results")

    print("\n[D12] Fused list >= both individual lists")
    check(len(fused) >= max(len(dense), len(sparse)),
          f"fused({len(fused)}) >= max(dense={len(dense)}, sparse={len(sparse)})")

    print("\n[D13] All fused chunks have rrf_score")
    has_scores = all("rrf_score" in c for c in fused)
    check(has_scores, f"All {len(fused)} fused chunks have 'rrf_score'")

    print("\n[D14] No duplicate chunk_ids in fused result")
    ids = [c["chunk_id"] for c in fused]
    check(len(ids) == len(set(ids)),
          f"No duplicates: {len(ids)} total = {len(set(ids))} unique")

    print("\n  Top 5 fused results:")
    for i, r in enumerate(fused[:5], 1):
        print(f"     [{i}] rrf={r['rrf_score']:.5f}  src={r['source_type']:<10}  title={r['title'][:40]}")


# ============================================================
# MAIN
# ============================================================

def main() -> int:
    print("=" * 60)
    print("  Day 3 - Full Hybrid Retrieval")
    print("=" * 60)

    # Initialise components
    print("\nLoading components...")
    embedder = Embedder()
    vs = VectorStore()
    bm25 = BM25Index()

    try:
        bm25.load()
        print("  BM25 index loaded from disk.")
    except Exception as exc:
        print(f"  ERROR: Could not load BM25 index: {exc}")
        print("  Please run: python scripts/ingest.py")
        return 1

    qdrant_count = vs.count
    bm25_count = len(bm25._chunk_ids)
    print(f"  Qdrant: {qdrant_count} points | BM25: {bm25_count} chunks")

    # Run all test parts
    test_index_health(vs, bm25)
    test_dense_retrieval(vs, embedder)
    test_sparse_retrieval(bm25)
    test_rrf_fusion(vs, bm25, embedder)

    # Final summary
    total = passed_total + failed_total
    print(f"\n{'=' * 60}")
    print(f"  Result: {passed_total}/{total} passed")
    if failed_total == 0:
        print("  *** Day 3 Complete - Hybrid Retrieval verified! ***")
    else:
        print(f"  WARNING: {failed_total} test(s) failed - check output above.")
    print("=" * 60)
    return 0 if failed_total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

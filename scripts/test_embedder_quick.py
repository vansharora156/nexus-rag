"""
Quick terminal test for the NexusRAG Embedder.

Bypasses all parsing and OCR — tests only the Gemini embedding backend.
Completes in ~60 seconds.

Run:
    python -m scripts.test_embedder_quick
"""

import sys
import time
import logging

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")

from dotenv import load_dotenv
load_dotenv()

from src.indexing.embedder import Embedder


SAMPLE_TEXTS = [
    "Employees are entitled to 18 days of paid annual leave per year.",
    "Q3 revenue was $4.2M, up 18% YoY driven by enterprise subscriptions.",
    "The API rate limit is 1000 requests per minute per API key.",
    "New engineers should complete onboarding within their first two weeks.",
    "Vendor evaluation criteria include cost, support SLA, and security posture.",
    "The incident runbook requires an immediate Slack alert to #incidents.",
    "Company values: integrity, innovation, collaboration, and customer focus.",
    "Architecture decision: use Qdrant for dense vector storage over FAISS.",
    "Product roadmap Q4: launch multi-tenant support and SSO integration.",
    "Budget 2024: engineering headcount grows from 12 to 18 FTEs.",
]


def main():
    print("=" * 60)
    print("  EMBEDDER QUICK TEST")
    print("=" * 60)

    embedder = Embedder()

    print(f"\nBackend   : {embedder._backend_name}")
    print(f"Model     : {embedder.model_name}")
    print(f"Dimension : {embedder.dimension}")
    print(f"Loaded    : {embedder.is_loaded()}")

    # -------------------------------------------------------
    # Test 1: embed_texts
    # -------------------------------------------------------
    print("\n[1/3] embed_texts() with 10 texts ...")
    t0 = time.time()
    embeddings = embedder.embed_texts(SAMPLE_TEXTS, show_progress=False)
    elapsed = time.time() - t0

    assert len(embeddings) == 10, "Wrong number of embeddings"
    assert len(embeddings[0]) == embedder.dimension, "Wrong dimension"
    print(f"      OK  {len(embeddings)} vectors | dim={len(embeddings[0])} | {elapsed:.1f}s")

    # -------------------------------------------------------
    # Test 2: embed_query
    # -------------------------------------------------------
    print("\n[2/3] embed_query() ...")
    t0 = time.time()
    q_vec = embedder.embed_query("What is the leave policy for employees?")
    elapsed = time.time() - t0

    assert len(q_vec) == embedder.dimension, "Query vector wrong dimension"
    print(f"      OK  dim={len(q_vec)} | {elapsed:.1f}s")
    print(f"      Sample values: {[round(v, 5) for v in q_vec[:5]]}")

    # -------------------------------------------------------
    # Test 3: empty input / validation
    # -------------------------------------------------------
    print("\n[3/3] Edge cases ...")

    # Empty list
    result = embedder.embed_texts([])
    assert result == [], "Empty list should return []"

    # Blank strings filtered out
    result = embedder.embed_texts(["   ", ""])
    assert result == [], "All-blank list should return []"

    # Empty query raises ValueError
    try:
        embedder.embed_query("   ")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

    print("      OK  empty list -> [] | blank strings -> [] | empty query -> ValueError")

    # -------------------------------------------------------
    # Summary
    # -------------------------------------------------------
    print("\n" + "=" * 60)
    print("  RESULTS")
    print("=" * 60)
    print(f"  Model        : {embedder.model_name}")
    print(f"  Dimension    : {embedder.dimension}")
    print(f"  10 texts in  : {elapsed:.2f}s")
    print(f"  Per chunk    : {elapsed / 1:.2f}s")
    print(f"  Info         : {embedder.info}")
    print()
    print("  All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()

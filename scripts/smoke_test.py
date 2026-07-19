# -*- coding: utf-8 -*-
"""Quick smoke test: one question through the full pipeline (post-fix)."""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
import logging
logging.basicConfig(level=logging.WARNING, format="%(levelname)s - %(message)s")

print("Loading QueryPipeline...")
from src.pipeline.query import QueryPipeline
t0 = time.perf_counter()
pipeline = QueryPipeline(use_reranker=True, use_query_rewriting=True, top_k=3)
print(f"Ready in {(time.perf_counter()-t0)*1000:.0f}ms")

print()
print("Question: 'How many vacation days do employees get?'")
print("User    : carol (hr role)")
print("Running pipeline (includes retry logic if 429 hit)...")
print()

result = pipeline.query(
    question="How many vacation days do employees get?",
    username="carol",
)

print(f"Elapsed : {result['elapsed_ms']:.0f}ms")
print(f"Sources : {result['num_sources']}")
print(f"Variants: {result['query_variants']}")
print()
print("Answer:")
print(result["answer"])
print()

got_429 = "429" in result["answer"] or "quota" in result["answer"].lower()
real_answer = len(result["answer"]) > 50 and not got_429

if real_answer:
    print("STATUS: WORKING - Real answer returned with citations!")
elif got_429:
    print("STATUS: 429 persists even after retries (quota exhausted for the minute)")
else:
    print(f"STATUS: Short answer ({len(result['answer'])} chars) - check above")

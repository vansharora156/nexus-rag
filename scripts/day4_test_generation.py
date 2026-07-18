# -*- coding: utf-8 -*-
"""Day 4 Test - Generation Layer (CitationFormatter + GeminiGenerator)

Part A: CitationFormatter (pure logic, no API)
  1. PDF chunk -> correct icon (document icon)
  2. Markdown chunk -> correct icon
  3. Excel chunk -> correct icon
  4. Slack chunk -> correct icon
  5. Unknown source type -> default icon
  6. label() format with page_number
  7. label() format with heading_path
  8. label() format with row_range
  9. snippet truncation at 300 chars
  10. to_dict() includes all expected keys
  11. build_context_block() produces numbered [N] lines
  12. Empty chunks list returns empty context

Part B: GeminiGenerator - live Gemini API call with real chunks
  13. Empty chunks returns fallback answer
  14. Real answer generated from retrieved chunks
  15. Answer contains inline [N] citation markers
  16. Result dict has required keys (answer, citations, context_block, num_sources)
  17. citations list length matches num_sources
  18. Answer is non-trivially long (> 50 chars)
  19. Context block contains chunk content snippets

Run from project root:
    python scripts/day4_test_generation.py
"""

import sys
import io
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
logging.basicConfig(level=logging.WARNING, format="%(levelname)s - %(message)s")

from src.generation.citation_formatter import Citation, CitationFormatter
from src.generation.generator import GeminiGenerator

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
    print(f"\n{'=' * 62}")
    print(f"  {title}")
    print("=" * 62)


# ------------------------------------------------------------------
# Sample chunks (mock retrieved results - no API needed for Part A)
# ------------------------------------------------------------------

SAMPLE_CHUNKS = [
    {
        "chunk_id":    "c001",
        "doc_id":      "doc_hr_policy",
        "source_type": "pdf",
        "title":       "BigCorp Employee Handbook",
        "heading_path": None,
        "page_number": 3,
        "row_range":   None,
        "acls":        ["all"],
        "score":       0.91,
        "rrf_score":   0.033,
        "rerank_score": 8.5,
        "is_table":    False,
        "content": (
            "BigCorp employees are entitled to 20 days of paid annual leave "
            "per calendar year. Leave must be approved by your direct manager "
            "at least two weeks in advance. Unused leave can be carried forward "
            "for up to 12 months."
        ),
    },
    {
        "chunk_id":    "c002",
        "doc_id":      "doc_hr_leave",
        "source_type": "markdown",
        "title":       "HR Leave Policy",
        "heading_path": "Leave Policy > Annual Leave",
        "page_number": None,
        "row_range":   None,
        "acls":        ["all"],
        "score":       0.87,
        "rrf_score":   0.031,
        "rerank_score": 7.8,
        "is_table":    False,
        "content": (
            "## Annual Leave\n\n"
            "All full-time employees receive 20 days of paid vacation annually. "
            "Part-time employees receive leave on a pro-rata basis. "
            "Sick leave is separate and not included in the 20-day allowance."
        ),
    },
    {
        "chunk_id":    "c003",
        "doc_id":      "doc_budget",
        "source_type": "excel",
        "title":       "Q3 Budget Tracker",
        "heading_path": None,
        "page_number": None,
        "row_range":   "2-8",
        "acls":        ["finance", "exec"],
        "score":       0.75,
        "rrf_score":   0.025,
        "rerank_score": 6.1,
        "is_table":    True,
        "content": "| Dept | Q1 | Q2 | Q3 |\n|---|---|---|---|\n| Eng | 120k | 135k | 142k |",
    },
    {
        "chunk_id":    "c004",
        "doc_id":      "doc_slack_general",
        "source_type": "slack",
        "title":       "#engineering-general",
        "heading_path": None,
        "page_number": None,
        "row_range":   None,
        "acls":        ["engineering"],
        "score":       0.71,
        "rrf_score":   0.022,
        "rerank_score": 5.4,
        "is_table":    False,
        "content": (
            "Thread: leave policy question\n"
            "alice: Hey, can we carry over unused vacation days?\n"
            "carol: Yes, up to 12 months as per the handbook."
        ),
    },
    {
        "chunk_id":    "c005",
        "doc_id":      "doc_unknown",
        "source_type": "confluence",
        "title":       "Internal Wiki Page",
        "heading_path": "HR > Benefits",
        "page_number": None,
        "row_range":   None,
        "acls":        ["all"],
        "score":       0.65,
        "rrf_score":   0.019,
        "rerank_score": 4.2,
        "is_table":    False,
        "content": "Employees may take unpaid leave for personal reasons with manager approval.",
    },
]


# ============================================================
# PART A: CitationFormatter
# ============================================================

def test_citation_formatter() -> None:
    section("Part A: CitationFormatter (pure logic)")

    formatter = CitationFormatter()
    citations = formatter.format(SAMPLE_CHUNKS)

    print(f"\n  Formatted {len(citations)} citations:")
    for c in citations:
        print(f"    {c.label()}")

    # 1-5: Source type icons
    print("\n[A1-A5] Source type icon mapping")
    check(citations[0].icon == "📄",  f"PDF    -> 📄  got '{citations[0].icon}'")
    check(citations[1].icon == "📝",  f"Markdown -> 📝  got '{citations[1].icon}'")
    check(citations[2].icon == "📊",  f"Excel  -> 📊  got '{citations[2].icon}'")
    check(citations[3].icon == "💬",  f"Slack  -> 💬  got '{citations[3].icon}'")
    check(citations[4].icon == "📎",  f"Unknown -> 📎 (default) got '{citations[4].icon}'")

    # 6-8: label() formats
    print("\n[A6-A8] label() with different location hints")
    label_pdf = citations[0].label()
    check("page 3" in label_pdf,
          f"PDF label has page number: '{label_pdf}'")

    label_md = citations[1].label()
    check("Annual Leave" in label_md,
          f"Markdown label has heading_path: '{label_md}'")

    label_excel = citations[2].label()
    check("rows 2-8" in label_excel,
          f"Excel label has row_range: '{label_excel}'")

    # 9: Snippet truncation
    print("\n[A9] Snippet truncation at 300 chars")
    long_content = "word " * 200   # 1000 chars
    from src.generation.citation_formatter import _SNIPPET_CHARS
    short = formatter._snippet(long_content)
    check(len(short) <= _SNIPPET_CHARS + 5,
          f"Long content truncated to ~{_SNIPPET_CHARS} chars (got {len(short)})")
    check(short.endswith("...") or short.endswith("…"),
          f"Truncated snippet ends with ellipsis: '{short[-5:]}'")

    # 10: to_dict() keys
    print("\n[A10] to_dict() includes all required keys")
    required_keys = {
        "index", "source_type", "icon", "title", "heading_path",
        "page_number", "row_range", "chunk_id", "doc_id", "acls",
        "score", "rerank_score", "content_snippet", "is_table", "label",
    }
    actual_keys = set(citations[0].to_dict().keys())
    missing = required_keys - actual_keys
    check(not missing, f"All required keys present (missing: {missing or 'none'})")

    # 11: build_context_block()
    print("\n[A11] build_context_block() produces numbered [N] format")
    context = formatter.build_context_block(citations)
    check("[1]" in context, "Context block contains [1]")
    check("[2]" in context, "Context block contains [2]")
    check("[3]" in context, "Context block contains [3]")
    check("📄" in context, "Context block contains PDF icon")
    check("📝" in context, "Context block contains Markdown icon")
    print("\n  Context block preview (first 400 chars):")
    print("  " + context[:400].replace("\n", "\n  "))

    # 12: Empty chunks
    print("\n[A12] Empty chunks list")
    empty_citations = formatter.format([])
    empty_context = formatter.build_context_block(empty_citations)
    check(len(empty_citations) == 0, "Empty input -> 0 citations")
    check(empty_context == "", f"Empty citations -> empty context block: '{empty_context}'")


# ============================================================
# PART B: GeminiGenerator (live API)
# ============================================================

def test_generator() -> None:
    section("Part B: GeminiGenerator (live Gemini API)")

    gen = GeminiGenerator(temperature=0.1, max_output_tokens=512)

    # 13: Empty chunks fallback
    print("\n[B13] Empty chunks -> fallback answer (no API call)")
    result = gen.generate("What is the vacation policy?", chunks=[])
    check(len(result["answer"]) > 20, f"Fallback answer returned: '{result['answer'][:60]}...'")
    check(result["num_sources"] == 0, "num_sources = 0 for empty chunks")
    check(result["citations"] == [], "citations = [] for empty chunks")

    # 14-19: Real Gemini generation
    query = "How many vacation days do employees get and can they be carried over?"
    print(f"\n[B14] Live generation for query: '{query}'")
    print("  Using top 3 chunks from SAMPLE_CHUNKS...")
    print("  Calling Gemini API...")

    t0 = time.perf_counter()
    result = gen.generate(query, chunks=SAMPLE_CHUNKS[:3])
    elapsed_ms = (time.perf_counter() - t0) * 1000

    print(f"\n  --- GENERATED ANSWER ({elapsed_ms:.0f}ms) ---")
    print(f"  {result['answer']}")
    print(f"  --- END ANSWER ---")
    print(f"\n  Sources used: {result['num_sources']}")

    check(elapsed_ms < 30000, f"Response within 30s: {elapsed_ms:.0f}ms")

    print("\n[B15] Answer contains inline [N] citation markers")
    answer = result["answer"]
    has_citation = any(f"[{i}]" in answer for i in range(1, 6))
    check(has_citation, f"Answer has at least one [N] marker: '{answer[:80]}...'")

    print("\n[B16] Result dict has all required keys")
    required = {"answer", "citations", "context_block", "num_sources"}
    check(required.issubset(result.keys()),
          f"Keys present: {set(result.keys())}")

    print("\n[B17] citations list length matches num_sources")
    check(len(result["citations"]) == result["num_sources"],
          f"len(citations)={len(result['citations'])} == num_sources={result['num_sources']}")

    print("\n[B18] Answer is non-trivially long (> 50 chars)")
    check(len(answer) > 50, f"Answer length: {len(answer)} chars")

    print("\n[B19] Context block contains chunk content")
    ctx = result["context_block"]
    check(len(ctx) > 100, f"Context block is non-empty: {len(ctx)} chars")
    check("BigCorp" in ctx or "leave" in ctx.lower() or "vacation" in ctx.lower(),
          f"Context block mentions key terms: '{ctx[:80]}'")

    print("\n  Citation cards:")
    for c in result["citations"]:
        print(f"    [{c['index']}] {c['icon']} {c['title']}"
              f"  |  score={c['score']:.3f}")


# ============================================================
# MAIN
# ============================================================

def main() -> int:
    print("=" * 62)
    print("  Day 4 - Generation Layer")
    print("=" * 62)

    test_citation_formatter()
    test_generator()

    total = passed_total + failed_total
    print(f"\n{'=' * 62}")
    print(f"  Result: {passed_total}/{total} passed")
    if failed_total == 0:
        print("  *** Day 4 Complete - Generation Layer verified! ***")
    else:
        print(f"  WARNING: {failed_total} test(s) failed - check output above.")
    print("=" * 62)
    return 0 if failed_total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

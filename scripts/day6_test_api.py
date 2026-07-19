# -*- coding: utf-8 -*-
"""Day 6 Test - FastAPI Server

Tests all endpoints against the live server at http://localhost:8000

Part A: GET /health
  1.  Status code 200
  2.  status field is 'ok' or 'degraded' (not error)
  3.  qdrant_points > 0
  4.  bm25_index_exists = True
  5.  All required response fields present

Part B: POST /query (simple question, no user)
  6.  Status code 200
  7.  answer field is non-empty (> 30 chars)
  8.  citations is a list
  9.  num_sources >= 1
  10. elapsed_ms > 0
  11. username = 'anonymous' when not provided

Part C: POST /query (with ACL user)
  12. Status code 200
  13. username = 'carol'
  14. answer is non-empty
  15. citations have correct schema (icon, title, source_type, score)

Part D: POST /query (invalid input)
  16. Empty query -> 422 Unprocessable Entity

Part E: GET /docs (Swagger UI)
  17. Status 200
  18. Returns HTML page

Run from project root (server must already be running on :8000):
    python scripts/day6_test_api.py
"""

import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests")
    sys.exit(1)

BASE = "http://localhost:8000"
API  = f"{BASE}/api/v1"

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


# ============================================================
# PART A: /health
# ============================================================

def test_health() -> None:
    section("Part A: GET /api/v1/health")
    resp = requests.get(f"{API}/health", timeout=15)

    print(f"\n  Status : {resp.status_code}")
    if resp.ok:
        data = resp.json()
        print(f"  Body   : {data}")

    check(resp.status_code == 200, f"Status 200 (got {resp.status_code})")

    if not resp.ok:
        return

    data = resp.json()
    check(data.get("status") in ("ok", "degraded"),
          f"status is 'ok' or 'degraded' (got '{data.get('status')}')")
    check(data.get("qdrant_points", 0) > 0,
          f"qdrant_points > 0 (got {data.get('qdrant_points')})")
    check(data.get("details", {}).get("bm25_index_exists") is True,
          f"bm25_index_exists = True")

    required_keys = {"status", "qdrant_collection", "qdrant_points",
                     "bm25_index_dir", "embedding_backend",
                     "embedding_model", "gemini_model", "details"}
    missing = required_keys - set(data.keys())
    check(not missing, f"All required fields present (missing: {missing or 'none'})")


# ============================================================
# PART B: /query - anonymous (no username)
# ============================================================

def test_query_anonymous() -> None:
    section("Part B: POST /api/v1/query (anonymous user)")

    body = {
        "query": "What is the company leave policy?",
        "top_k": 3,
    }

    print(f"\n  Query  : {body['query']}")
    print("  User   : anonymous (not set)")
    print("  Calling API...")

    t0 = time.perf_counter()
    resp = requests.post(f"{API}/query", json=body, timeout=180)
    wall_ms = (time.perf_counter() - t0) * 1000

    print(f"\n  Status  : {resp.status_code}")
    check(resp.status_code == 200, f"Status 200 (got {resp.status_code})")

    if not resp.ok:
        print(f"  Error: {resp.text[:300]}")
        return

    data = resp.json()
    print(f"\n  Answer ({wall_ms:.0f}ms wall):")
    print(f"  {data.get('answer', '')}")
    print(f"\n  num_sources : {data.get('num_sources')}")
    print(f"  elapsed_ms  : {data.get('elapsed_ms')}")
    print(f"  username    : {data.get('username')}")

    check(len(data.get("answer", "")) > 30,
          f"answer non-empty ({len(data.get('answer',''))} chars)")
    check(isinstance(data.get("citations"), list),
          f"citations is a list (len={len(data.get('citations',[]))})")
    check(data.get("num_sources", 0) >= 1,
          f"num_sources >= 1 (got {data.get('num_sources')})")
    check(data.get("elapsed_ms", 0) > 0,
          f"elapsed_ms > 0 (got {data.get('elapsed_ms')})")
    check(data.get("username") == "anonymous",
          f"username = 'anonymous' (got '{data.get('username')}')")


# ============================================================
# PART C: /query - authenticated user (carol/hr)
# ============================================================

def test_query_authenticated() -> None:
    section("Part C: POST /api/v1/query (carol / hr role)")

    body = {
        "query": "How many vacation days do full-time employees get?",
        "username": "carol",
        "top_k": 3,
    }

    print(f"\n  Query  : {body['query']}")
    print(f"  User   : {body['username']}")
    print("  Calling API...")

    resp = requests.post(f"{API}/query", json=body, timeout=180)

    print(f"\n  Status : {resp.status_code}")
    check(resp.status_code == 200, f"Status 200 (got {resp.status_code})")

    if not resp.ok:
        print(f"  Error: {resp.text[:300]}")
        return

    data = resp.json()
    print(f"\n  Answer : {data.get('answer', '')}")
    print(f"\n  Citations:")
    for c in data.get("citations", []):
        print(f"    [{c['index']}] {c.get('icon','')} {c.get('title','')}  "
              f"score={c.get('score',0):.3f}")

    check(data.get("username") == "carol",
          f"username echoed correctly (got '{data.get('username')}')")
    check(len(data.get("answer", "")) > 30,
          f"answer non-empty ({len(data.get('answer',''))} chars)")

    # Citation schema
    citations = data.get("citations", [])
    if citations:
        c = citations[0]
        required = {"index", "icon", "title", "source_type",
                    "score", "content_snippet", "chunk_id", "label"}
        missing = required - set(c.keys())
        check(not missing,
              f"Citation has all required keys (missing: {missing or 'none'})")
        check(c.get("icon") in {"📄","📝","📊","💬","📎"},
              f"Citation icon is valid: '{c.get('icon')}'")


# ============================================================
# PART D: /query - invalid input
# ============================================================

def test_query_validation() -> None:
    section("Part D: POST /api/v1/query (validation errors)")

    print("\n[D16] Empty query string -> 422 Unprocessable Entity")
    resp = requests.post(f"{API}/query", json={"query": "", "top_k": 3}, timeout=10)
    print(f"  Status: {resp.status_code}")
    check(resp.status_code == 422,
          f"Empty query returns 422 (got {resp.status_code})")


# ============================================================
# PART E: Swagger UI
# ============================================================

def test_swagger() -> None:
    section("Part E: GET /docs (Swagger UI)")

    resp = requests.get(f"{BASE}/docs", timeout=10)
    print(f"\n  Status : {resp.status_code}")
    print(f"  Content-Type: {resp.headers.get('content-type','')}")

    check(resp.status_code == 200, f"Swagger /docs returns 200")
    check("text/html" in resp.headers.get("content-type", ""),
          f"Response is HTML (content-type: {resp.headers.get('content-type','')})")
    check("swagger" in resp.text.lower() or "openapi" in resp.text.lower(),
          "Page contains Swagger/OpenAPI UI content")


# ============================================================
# MAIN
# ============================================================

def main() -> int:
    print("=" * 62)
    print("  Day 6 - FastAPI Server")
    print(f"  Base URL: {BASE}")
    print("=" * 62)

    # Quick connectivity check
    print("\n  Checking server connectivity...")
    try:
        r = requests.get(f"{BASE}/docs", timeout=5)
        print(f"  Server reachable: {r.status_code}")
    except Exception as exc:
        print(f"\n  ERROR: Cannot reach server at {BASE}")
        print(f"  Detail: {exc}")
        print("  Make sure the server is running:")
        print("    uvicorn api.app:app --port 8000")
        return 1

    test_health()
    test_query_anonymous()
    test_query_authenticated()
    test_query_validation()
    test_swagger()

    total = passed_total + failed_total
    print(f"\n{'=' * 62}")
    print(f"  Result: {passed_total}/{total} passed")
    if failed_total == 0:
        print("  *** Day 6 Complete - FastAPI Server verified! ***")
    else:
        print(f"  WARNING: {failed_total} test(s) failed.")
    print("=" * 62)

    return 0 if failed_total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""Day 1 Test - ACL Layer (PermissionsManager)

Tests:
  1. File loading and user count
  2. get_roles() for known users
  3. Always includes 'all' role
  4. can_access() enforcement — allow & deny cases
  5. get_document_roles() for document ACL lookup
  6. Unknown user fallback
  7. list_users()

Run from project root:
    python scripts/day1_test_acl.py
"""

import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.acl.permissions import PermissionsManager

PASS = "[PASS]"
FAIL = "[FAIL]"

def check(condition: bool, msg: str) -> bool:
    print(f"  {PASS if condition else FAIL}  {msg}")
    return condition


def main():
    print("=" * 55)
    print("  Day 1 — ACL Layer Test")
    print("=" * 55)

    mgr = PermissionsManager()

    results = []

    print("\n[1] File loaded & users found")
    users = mgr.list_users()
    results.append(check(len(users) >= 3, f"Found {len(users)} users: {users}"))

    print("\n[2] get_roles() for known users")
    alice_roles = mgr.get_roles("alice")
    results.append(check("engineering" in alice_roles, f"alice has 'engineering': {alice_roles}"))
    results.append(check("all" in alice_roles,         f"alice always has 'all': {alice_roles}"))

    bob_roles = mgr.get_roles("bob")
    results.append(check("product" in bob_roles, f"bob has 'product': {bob_roles}"))
    results.append(check("exec" in bob_roles,    f"bob has 'exec': {bob_roles}"))

    carol_roles = mgr.get_roles("carol")
    results.append(check("hr" in carol_roles, f"carol has 'hr': {carol_roles}"))

    print("\n[3] Unknown user fallback")
    unknown = mgr.get_roles("nobody")
    results.append(check("all" in unknown, f"Unknown user still gets 'all': {unknown}"))
    results.append(check(len(unknown) == 1, f"Unknown user only gets 'all' (no extra roles): {unknown}"))

    print("\n[4] can_access() — allow cases")
    results.append(check(
        mgr.can_access("alice", ["engineering"]),
        "alice CAN access ['engineering'] doc"
    ))
    results.append(check(
        mgr.can_access("alice", ["engineering", "exec"]),
        "alice CAN access ['engineering','exec'] doc (she has engineering)"
    ))
    results.append(check(
        mgr.can_access("alice", ["all"]),
        "alice CAN access ['all'] public doc"
    ))
    results.append(check(
        mgr.can_access("frank", ["all"]),
        "frank (intern) CAN access ['all'] public doc"
    ))

    print("\n[5] can_access() — deny cases")
    results.append(check(
        not mgr.can_access("alice", ["finance"]),
        "alice CANNOT access ['finance'] doc"
    ))
    results.append(check(
        not mgr.can_access("alice", ["hr"]),
        "alice CANNOT access ['hr'] doc"
    ))
    results.append(check(
        not mgr.can_access("frank", ["engineering"]),
        "frank (intern/'all' only) CANNOT access ['engineering'] doc"
    ))

    print("\n[6] get_document_roles()")
    hr_roles = mgr.get_document_roles("hr-leave-policy.md")
    results.append(check("all" in hr_roles, f"hr-leave-policy.md roles: {hr_roles}"))

    qr_roles = mgr.get_document_roles("quarterly-report-q3.pdf")
    results.append(check("finance" in qr_roles, f"quarterly-report-q3.pdf roles: {qr_roles}"))
    results.append(check("all" not in qr_roles, f"quarterly-report-q3.pdf NOT public: {qr_roles}"))

    unknown_doc = mgr.get_document_roles("some-unknown-file.txt")
    results.append(check(unknown_doc == ["all"], f"Unknown doc defaults to ['all']: {unknown_doc}"))

    print("\n[7] user_info()")
    alice_info = mgr.user_info("alice")
    results.append(check(alice_info.get("name") == "Alice Chen", f"alice name: {alice_info.get('name')}"))
    results.append(check(alice_info.get("title") == "Senior Engineer", f"alice title: {alice_info.get('title')}"))

    # Summary
    passed = sum(results)
    total = len(results)
    print("\n" + "=" * 55)
    print(f"  Result: {passed}/{total} passed")
    if passed == total:
        print("  *** Day 1 Complete - ACL Layer is working correctly! ***")
    else:
        print(f"  WARNING: {total - passed} test(s) failed - check output above.")
    print("=" * 55)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

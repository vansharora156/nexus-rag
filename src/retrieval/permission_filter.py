"""Permission filter helper for NexusRAG retrieval.

Bridges the ACL permissions system with the retrieval layer by providing
a thin utility to extract active user roles for use in Qdrant pre-filters
and BM25 post-filters.
"""

from typing import List, Optional
from src.acl.permissions import PermissionsManager

# Module-level singleton — avoids re-parsing permissions.json on every call
_manager: Optional[PermissionsManager] = None


def get_permissions_manager() -> PermissionsManager:
    """Return the singleton PermissionsManager, initialising it on first call."""
    global _manager
    if _manager is None:
        _manager = PermissionsManager()
    return _manager


def get_user_roles(username: str) -> List[str]:
    """Resolve the security roles for *username*.

    Args:
        username: Authenticated user making the query.

    Returns:
        List of role strings (always contains ``"all"`` for public docs).
    """
    return get_permissions_manager().get_roles(username)


def filter_chunks_by_acl(chunks: list, username: str) -> list:
    """Post-hoc ACL filter for any list of chunk dicts.

    Useful as a safety net after retrieval if per-chunk access validation
    is needed outside the normal Qdrant/BM25 filter path.

    Args:
        chunks: List of chunk dicts, each with an ``"acls"`` key.
        username: Authenticated user.

    Returns:
        Filtered list containing only chunks the user may access.
    """
    mgr = get_permissions_manager()
    return [c for c in chunks if mgr.can_access(username, c.get("acls", []))]

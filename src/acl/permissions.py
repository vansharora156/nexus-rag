"""Access Control List (ACL) module for NexusRAG.

Loads and parses the ``permissions.json`` file, which maps users to roles
and documents to their allowed roles.

permissions.json schema (actual format used in this project)
------------------------------------------------------------
{
    "roles": ["engineering", "hr", "finance", "exec", "all"],
    "documents": {
        "hr-leave-policy.md": ["all"],
        "quarterly-report.pdf": ["finance", "exec"],
        ...
    },
    "users": {
        "alice": {"roles": ["engineering"], "name": "Alice Chen"},
        "bob":   {"roles": ["product", "exec"], "name": "Bob Martinez"},
        ...
    }
}

ACL logic
---------
A chunk tagged with ``acl_tags: ["hr", "exec"]`` is visible to a user
whose role list contains at least one of those tags.
The special role ``"all"`` means the document is publicly accessible to
every authenticated user.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

from src.config import config

logger = logging.getLogger(__name__)


class PermissionsManager:
    """Resolves user roles from the permissions file and enforces ACL checks.

    Designed to be instantiated once at application startup and shared
    across request handlers.  Call :meth:`reload` to hot-reload from disk.
    """

    def __init__(self, permissions_file: Optional[Path] = None):
        self._file = Path(permissions_file or config.PERMISSIONS_FILE)
        self._users: dict = {}      # username → {roles: [...], name: ...}
        self._documents: dict = {}  # filename → [allowed_roles]
        self._load()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Parse the permissions JSON file into memory."""
        if not self._file.exists():
            logger.warning(
                "Permissions file not found at '%s'. "
                "All users will be treated as having the 'all' role only.",
                self._file,
            )
            self._users = {}
            self._documents = {}
            return

        with self._file.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)

        # Support both flat {username: [...]} and nested {users: {username: {...}}} formats
        if "users" in raw:
            self._users = raw["users"]
        else:
            self._users = raw  # Flat format fallback

        self._documents = raw.get("documents", {})

        logger.info(
            "Loaded permissions: %d users, %d documents from '%s'.",
            len(self._users),
            len(self._documents),
            self._file,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reload(self) -> None:
        """Re-read the permissions file from disk (hot-reload)."""
        self._load()

    def get_roles(self, username: str) -> List[str]:
        """Return the role list for *username*.

        Always includes ``"all"`` so publicly accessible documents
        (tagged ``"all"``) are visible to every authenticated user.

        Args:
            username: The authenticated user identifier.

        Returns:
            Deduplicated list of role strings, guaranteed to contain ``"all"``.
        """
        user_entry = self._users.get(username, {})

        if isinstance(user_entry, dict):
            # Nested format: {"alice": {"roles": ["engineering"], "name": "Alice"}}
            roles = list(user_entry.get("roles", []))
        elif isinstance(user_entry, list):
            # Flat list format: {"alice": ["engineering", "all"]}
            roles = list(user_entry)
        else:
            roles = []

        if "all" not in roles:
            roles.append("all")

        return roles

    def can_access(self, username: str, acl_tags: List[str]) -> bool:
        """Return True if *username* is permitted to see a document with *acl_tags*.

        Args:
            username: Authenticated user identifier.
            acl_tags: The document's ACL tag list (e.g. ``["hr", "exec"]``).

        Returns:
            True when the user's roles intersect with the document's ACL tags.
        """
        if not acl_tags:
            # No restrictions — publicly accessible
            return True

        user_roles = set(self.get_roles(username))
        return bool(user_roles & set(acl_tags))

    def get_document_roles(self, filename: str) -> List[str]:
        """Return the allowed roles for a document by filename.

        Useful during ingestion to look up ACL tags from the permissions file
        rather than embedding them in the document itself.

        Args:
            filename: The document filename (e.g. ``"hr-leave-policy.md"``).

        Returns:
            List of allowed role strings, or ``["all"]`` if not found.
        """
        return self._documents.get(filename, ["all"])

    def list_users(self) -> List[str]:
        """Return all known usernames in the permissions file."""
        return list(self._users.keys())

    def user_info(self, username: str) -> dict:
        """Return full user metadata dict (name, title, roles) or empty dict."""
        return self._users.get(username, {})

    @property
    def permissions_file(self) -> Path:
        """Path to the loaded permissions JSON file."""
        return self._file

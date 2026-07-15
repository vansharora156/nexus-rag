"""NexusRAG ACL module.

Exports the PermissionsManager for role-based access control enforcement.
"""

from src.acl.permissions import PermissionsManager

__all__ = ["PermissionsManager"]

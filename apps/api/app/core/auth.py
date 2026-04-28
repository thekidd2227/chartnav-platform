"""Compatibility shim: re-export auth helpers from app.auth / app.authz."""
from typing import Union
from app.auth import resolve_caller_from_bearer as get_current_user
from app.authz import require_roles as _require_roles

def require_roles(roles: Union[list, str], *extra: str):
    """Adapter: accept require_roles(['admin','lead']) or require_roles('admin','lead')."""
    if isinstance(roles, list):
        return _require_roles(*roles)
    return _require_roles(roles, *extra)

__all__ = ["get_current_user", "require_roles"]

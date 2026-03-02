from __future__ import annotations

from backend.infrastructure.storage import azure_storage as _impl

globals().update(
    {
        name: value
        for name, value in vars(_impl).items()
        if not name.startswith("__")
    }
)

if hasattr(_impl, "__all__"):
    __all__ = _impl.__all__

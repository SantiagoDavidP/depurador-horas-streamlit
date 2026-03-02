from __future__ import annotations

from typing import Dict, Optional

from fastapi import Depends

from api.serializers import sanitize_payload
from api.services import get_profile_catalog

from api.presentation.dependencies import auth_provider


def health() -> Dict[str, str]:
    return {"status": "ok"}


def list_profiles(user: Optional[Dict[str, object]] = Depends(auth_provider.require_user)) -> Dict[str, object]:
    profiles = get_profile_catalog()
    payload = []
    for profile in profiles.values():
        payload.append(
            {
                "client_id": profile.client_id,
                "name": profile.name,
                "mapping": profile.mapping,
                "settings": profile.settings,
                "keywords": profile.keywords,
                "company_aliases": profile.company_aliases,
            }
        )
    return sanitize_payload({"profiles": payload})


def get_me(user: Optional[Dict[str, object]] = Depends(auth_provider.require_user)) -> Dict[str, object]:
    return sanitize_payload({"user": user})


__all__ = ["health", "list_profiles", "get_me"]

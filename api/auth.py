from __future__ import annotations

import logging
from typing import Dict, Optional

import requests
from fastapi import Header, HTTPException

from config.settings import get_settings

logger = logging.getLogger(__name__)


def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    if not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip()


def _fetch_graph_me(access_token: str) -> Optional[Dict[str, object]]:
    try:
        resp = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        logger.error("Graph /me error: %s - %s", resp.status_code, resp.text)
    except Exception as exc:
        logger.error("Graph /me failed: %s", exc)
    return None


def _check_group_membership(access_token: str, group_id: str) -> bool:
    try:
        resp = requests.get(
            "https://graph.microsoft.com/v1.0/me/memberOf",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.error("Graph /memberOf error: %s - %s", resp.status_code, resp.text)
            return False
        groups = resp.json().get("value", [])
        group_ids = [g.get("id") for g in groups if g.get("id")]
        return group_id in group_ids
    except Exception as exc:
        logger.error("Group check failed: %s", exc)
        return False


def require_user(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, object]]:
    settings = get_settings()
    if not settings.azure_ad.enabled:
        return None

    token = _extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    user_info = _fetch_graph_me(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")

    if settings.azure_ad.allowed_group_id:
        if not _check_group_membership(token, settings.azure_ad.allowed_group_id):
            raise HTTPException(status_code=403, detail="User not in allowed group")

    return user_info

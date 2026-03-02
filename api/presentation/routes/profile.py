from __future__ import annotations

from fastapi import APIRouter

from api.presentation import handlers

router = APIRouter()

router.add_api_route("/api/profiles", handlers.list_profiles, methods=["GET"])
router.add_api_route("/api/me", handlers.get_me, methods=["GET"])

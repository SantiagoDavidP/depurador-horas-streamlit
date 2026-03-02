from __future__ import annotations

from fastapi import APIRouter

from api.presentation import handlers

router = APIRouter()

router.add_api_route("/api/download/{file_id}", handlers.download, methods=["GET"])

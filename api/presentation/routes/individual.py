from __future__ import annotations

from fastapi import APIRouter

from api.presentation import handlers

router = APIRouter()

router.add_api_route("/api/individual/analyze", handlers.analyze_individual, methods=["POST"])
router.add_api_route("/api/individual/process", handlers.process_individual, methods=["POST"])

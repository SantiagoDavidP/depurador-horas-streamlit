from __future__ import annotations

from fastapi import APIRouter

from api.presentation import handlers

router = APIRouter()

router.add_api_route("/api/batch/analyze", handlers.analyze_batch, methods=["POST"])
router.add_api_route("/api/batch/process", handlers.process_batch, methods=["POST"])
router.add_api_route("/api/batch/consolidate", handlers.consolidate_batch, methods=["POST"])
router.add_api_route("/api/batch/baninter-zip", handlers.baninter_zip, methods=["POST"])

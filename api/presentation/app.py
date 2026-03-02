from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.presentation.routes.batch import router as batch_router
from api.presentation.routes.download import router as download_router
from api.presentation.routes.health import router as health_router
from api.presentation.routes.individual import router as individual_router
from api.presentation.routes.profile import router as profile_router

app = FastAPI(title="Nova Timesheet API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(profile_router)
app.include_router(batch_router)
app.include_router(individual_router)
app.include_router(download_router)

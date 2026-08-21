"""SwaraSetu FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import analytics, channels, phcs, sync, triage


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Offline-first voice-native triage API for rural India. "
        "Clinical decisions come from a deterministic WHO IMCI engine — "
        "no LLM in the decision path."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(triage.router)
app.include_router(phcs.router)
app.include_router(analytics.router)
app.include_router(sync.router)
app.include_router(channels.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name}

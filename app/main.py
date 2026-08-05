"""Voice Transcription Service — FastAPI application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.transcriptions import router as transcriptions_router
from app.api.webhooks import router as webhooks_router
from app.config import settings
from app.database import close_pool

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_pool()


app = FastAPI(
    title="Voice Transcription Service",
    description="Speech-to-text with speaker diarization via Soniox API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks_router, tags=["Webhooks"])
app.include_router(transcriptions_router, tags=["Transcriptions"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "voice-transcription"}

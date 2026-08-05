"""Transcription listing endpoint."""

from fastapi import APIRouter, Query

from app.database import get_transcriptions

router = APIRouter()


@router.get("/api/v1/transcriptions")
async def list_transcriptions(
    user_id: int | None = Query(None),
    limit: int = Query(50, le=200),
):
    return await get_transcriptions(user_id=user_id, limit=limit)

"""Webhook endpoints: audio upload, Soniox callback, user management."""

import logging

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.config import settings
from app.database import (
    count_user_transcriptions,
    deactivate_user,
    get_user_by_id,
    save_transcription,
)
from app.services.email import send_deactivation_email
from app.services.soniox import SonioxService, parse_transcription

logger = logging.getLogger(__name__)
router = APIRouter()


class UploadPayload(BaseModel):
    filename: str
    url: str
    base64: str = ""
    duration: float = 0
    mimeType: str = "audio/mpeg"
    userId: int | None = None
    source: str = "voice-recorder"


@router.post("/webhook/upload")
async def upload_audio(payload: UploadPayload):
    """Accept audio file, start Soniox transcription."""
    user_id = payload.userId
    filename = payload.filename

    if user_id:
        # Check exemption list
        user = await get_user_by_id(user_id)
        if user and user.get("email", "").lower() in settings.exempt_emails_list:
            logger.info(
                "User %s exempt from limits", user["email"],
                extra={"event": "limit_exempt", "user_id": user_id, "email": user["email"]},
            )
        else:
            count = await count_user_transcriptions(user_id)
            logger.info(
                "User %s: %s/%s transcriptions",
                user_id, count, settings.transcription_limit,
                extra={"event": "user_count", "user_id": user_id, "count": count},
            )
            if count >= settings.transcription_limit:
                logger.warning(
                    "User %s limit exceeded: %s/%s",
                    user_id, count, settings.transcription_limit,
                    extra={"event": "limit_exceeded", "user_id": user_id, "count": count},
                )
                return {"success": False, "error": "limit_exceeded", "count": count}

    soniox = SonioxService()
    try:
        uid_param = f"?user_id={user_id}" if user_id else ""
        callback_url = (
            f"{settings.soniox_webhook_base.rstrip('/')}"
            f"/webhook/soniox-callback/{filename}{uid_param}"
        )
        logger.info(
            "Starting transcription: %s, user=%s", filename, user_id,
            extra={"event": "soniox_start", "filename": filename, "user_id": user_id},
        )
        result = await soniox.start_transcription(
            audio_url=payload.url, webhook_url=callback_url,
        )
        return {
            "success": True,
            "transcription_id": result.get("id"),
            "filename": filename,
        }
    finally:
        await soniox.close()


@router.post("/webhook/soniox-callback/{filename}")
async def soniox_callback(
    filename: str,
    payload: dict,
    user_id: str | None = Query(None, alias="user_id"),
):
    """Receive Soniox transcription result, save to database."""
    uid = int(user_id) if user_id else None
    logger.info(
        "Callback: %s, uid=%s", filename, uid,
        extra={"event": "soniox_callback", "filename": filename, "user_id": uid},
    )
    transcription_id = payload.get("id")

    if payload.get("status") == "error":
        logger.error(
            "Soniox error: %s", payload.get("error_message", "?"),
            extra={"event": "soniox_error", "filename": filename},
        )
        return {"success": False}

    try:
        soniox = SonioxService()
        result = await soniox.get_transcript(transcription_id)
        parsed = parse_transcription(result)

        if parsed["full_text"]:
            await save_transcription(parsed["full_text"], uid)
            logger.info(
                "Saved uid=%s: %s chars", uid, len(parsed["full_text"]),
                extra={
                    "event": "transcription_saved",
                    "user_id": uid,
                    "chars": len(parsed["full_text"]),
                    "replicas": parsed["total_replicas"],
                },
            )

            if uid:
                user = await get_user_by_id(uid)
                if user and user.get("email", "").lower() not in settings.exempt_emails_list:
                    count = await count_user_transcriptions(uid)
                    if count >= settings.transcription_limit:
                        await deactivate_user(uid)
                        logger.warning(
                            "User %s deactivated after %s transcriptions",
                            uid, count,
                            extra={"event": "user_deactivated", "user_id": uid, "count": count},
                        )
                        # Send email notification
                        if settings.smtp_host and user.get("email"):
                            try:
                                await send_deactivation_email(
                                    to_email=settings.notification_email,
                                    user_email=user["email"],
                                    user_id=uid,
                                    count=count,
                                )
                            except Exception as e:
                                logger.error("Failed to send deactivation email: %s", e)

        return {"success": True, "replicas": parsed["total_replicas"]}

    except Exception as e:
        logger.error(
            "Error in callback: %s", e, exc_info=True,
            extra={"event": "callback_error", "filename": filename},
        )
        return {"success": False}
    finally:
        await soniox.close()

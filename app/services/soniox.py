"""Soniox speech-to-text service integration."""

import httpx
from app.config import settings


class SonioxService:
    BASE_URL = "https://api.soniox.com/v1"

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {settings.soniox_api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def start_transcription(
        self, audio_url: str, webhook_url: str, model: str = "stt-async-preview-v1",
    ) -> dict:
        payload = {
            "audio_url": audio_url,
            "model": model,
            "enable_speaker_diarization": "true",
            "enable_paragraphs": "true",
            "webhook_url": webhook_url,
        }
        resp = await self.client.post("/transcriptions", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def get_transcript(self, transcription_id: str) -> dict:
        resp = await self.client.get(f"/transcriptions/{transcription_id}/transcript")
        resp.raise_for_status()
        return resp.json()

    async def close(self):
        await self.client.aclose()


def parse_transcription(soniox_result: dict) -> dict:
    """Parse Soniox tokens into speaker-labeled dialogue."""
    tokens = soniox_result.get("tokens", [])
    replicas = []
    current = None

    for token in tokens:
        if token.get("is_audio_event") or not token.get("speaker"):
            continue
        speaker = token["speaker"]
        text = token.get("text", "")
        start_ms = token.get("start_ms", 0) or 0
        end_ms = token.get("end_ms", start_ms) or start_ms

        if not current or current["speaker"] != speaker:
            if current:
                current["text"] = current["text"].strip()
                replicas.append(current)
            current = {
                "speaker": speaker, "text": text,
                "start_ms": start_ms, "end_ms": end_ms,
            }
        else:
            current["text"] += text
            current["end_ms"] = end_ms

    if current:
        current["text"] = current["text"].strip()
        replicas.append(current)

    def ms_to_str(ms):
        s = ms // 1000
        return f"{s // 60}:{str(s % 60).zfill(2)}"

    dialogue = [
        {
            "speaker": r["speaker"],
            "text": r["text"],
            "start_time": ms_to_str(r["start_ms"]),
            "end_time": ms_to_str(r["end_ms"]),
        }
        for r in replicas
    ]

    full_text = "\n".join(f"[{d['speaker']}] {d['text']}" for d in dialogue)

    return {
        "dialog": dialogue,
        "full_text": full_text,
        "total_replicas": len(dialogue),
    }

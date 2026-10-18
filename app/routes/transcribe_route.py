from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, HttpUrl

from app.services.whisper_service import (
    get_runtime_config,
    get_whisper_model,
    transcribe_audio_from_url,
    transcribe_uploaded_file,
)

router = APIRouter(
    prefix="/api/transcribe",
    tags=["Transcription"],
)


class AudioURLRequest(BaseModel):
    audio_url: HttpUrl


@router.get("/status")
def status():
    return {
        "ok": True,
        "runtime": get_runtime_config(),
        "model_loaded": False,
        "note": "The model is lazy-loaded on the first transcription request.",
    }


@router.post("/warmup")
def warmup():
    try:
        get_whisper_model()
        return {
            "ok": True,
            "runtime": get_runtime_config(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/file")
def transcribe_file(audio: UploadFile = File(...)):
    try:
        suffix = Path(audio.filename or "audio").suffix or ".audio"

        result = transcribe_uploaded_file(
            audio.file,
            suffix=suffix,
        )

        return {
            "success": True,
            "filename": audio.filename,
            **result,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/url")
def transcribe_url(payload: AudioURLRequest):
    try:
        result = transcribe_audio_from_url(str(payload.audio_url))

        return {
            "success": True,
            **result,
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

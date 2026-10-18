from fastapi import FastAPI

from app.routes.transcribe_route import router as transcribe_router
from app.services.whisper_service import get_runtime_config

app = FastAPI(
    title="Voice Transcription Service",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "voice-to-text",
        "runtime": get_runtime_config(),
    }


app.include_router(transcribe_router)

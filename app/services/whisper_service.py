from __future__ import annotations

import ipaddress
import os
import socket
import tempfile
import threading
from pathlib import Path
from typing import BinaryIO
from urllib.parse import urlparse

import requests
from faster_whisper import WhisperModel


_model: WhisperModel | None = None
_model_lock = threading.Lock()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def get_runtime_config() -> dict:
    return {
        "model": os.getenv("WHISPER_MODEL", "small"),
        "device": os.getenv("WHISPER_DEVICE", "cpu"),
        "compute_type": os.getenv("WHISPER_COMPUTE_TYPE", "int8"),
        "beam_size": int(os.getenv("WHISPER_BEAM_SIZE", "5")),
        "vad_filter": _env_bool("WHISPER_VAD_FILTER", True),
    }


def get_whisper_model() -> WhisperModel:
    global _model

    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:
            return _model

        config = get_runtime_config()

        print(
            "Loading Whisper model:",
            f"model={config['model']}",
            f"device={config['device']}",
            f"compute_type={config['compute_type']}",
            flush=True,
        )

        _model = WhisperModel(
            config["model"],
            device=config["device"],
            compute_type=config["compute_type"],
        )

        print("Whisper model loaded.", flush=True)
        return _model


def _transcribe_path(path: str) -> dict:
    model = get_whisper_model()
    config = get_runtime_config()

    segments, info = model.transcribe(
        path,
        beam_size=config["beam_size"],
        vad_filter=True,
        vad_parameters={
            "min_silence_duration_ms": 700,
        },
        task="translate",

        # Prevent Whisper getting stuck repeating text
        condition_on_previous_text=False,
        repetition_penalty=1.1,
        no_repeat_ngram_size=3,

        no_speech_threshold=0.6,
    )   

    text = " ".join(
        segment.text.strip()
        for segment in segments
        if segment.text and segment.text.strip()
    ).strip()

    return {
        "text": text,
        "detected_language": info.language,
        "language_probability": getattr(
            info,
            "language_probability",
            None,
        ),
        "model": config["model"],
        "device": config["device"],
    }


def transcribe_uploaded_file(file_obj: BinaryIO, suffix: str = ".audio") -> dict:
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            while True:
                chunk = file_obj.read(1024 * 1024)
                if not chunk:
                    break
                tmp.write(chunk)
            temp_path = tmp.name

        return _transcribe_path(temp_path)

    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)


def _validate_public_http_url(audio_url: str) -> None:
    parsed = urlparse(audio_url)

    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http/https audio URLs are allowed.")

    if not parsed.hostname:
        raise ValueError("Audio URL does not contain a hostname.")

    # Basic SSRF protection for the local URL test endpoint.
    # Production integration should not accept a user-supplied URL at all.
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443)
    except socket.gaierror as exc:
        raise ValueError("Audio URL hostname could not be resolved.") from exc

    for result in addresses:
        ip = ipaddress.ip_address(result[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise ValueError("Private/internal audio URLs are not allowed.")


def transcribe_audio_from_url(audio_url: str) -> dict:
    if not _env_bool("ALLOW_URL_TRANSCRIPTION", False):
        raise ValueError("URL transcription is disabled.")

    _validate_public_http_url(audio_url)

    timeout = int(os.getenv("AUDIO_DOWNLOAD_TIMEOUT_SECONDS", "60"))
    max_bytes = int(os.getenv("MAX_AUDIO_BYTES", str(50 * 1024 * 1024)))

    temp_path = None

    try:
        with requests.get(
            audio_url,
            timeout=timeout,
            stream=True,
            allow_redirects=True,
        ) as response:
            response.raise_for_status()

            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > max_bytes:
                raise ValueError("Audio file is larger than the configured limit.")

            suffix = Path(urlparse(str(response.url)).path).suffix or ".audio"

            downloaded = 0
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue

                    downloaded += len(chunk)
                    if downloaded > max_bytes:
                        raise ValueError("Audio file is larger than the configured limit.")

                    tmp.write(chunk)

                temp_path = tmp.name

        return _transcribe_path(temp_path)

    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)

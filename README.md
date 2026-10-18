# Voice to text Service - Local Windows Docker Test

This project is a safe standalone test service for the voice-to-text feature.

- Ubuntu 22.04
- NVIDIA CUDA 12.4.1 runtime image family
- Python 3.11.9
- FastAPI + Uvicorn
- `faster-whisper`
- lazy Whisper model loading
- same container port style: 8000 internally

For the first Windows test it runs Whisper on CPU, so Docker Desktop does not need NVIDIA GPU passthrough.

## Folder

Copy/extract the project anywhere, for example:

```text
C:\project\voice-to-text
```

Open PowerShell in that directory.

## 1. Prerequisite

Install/start Docker Desktop and make sure it is using Linux containers / WSL2.

Check:

```powershell
docker version
docker compose version
```

## 2. Create local environment file

```powershell
Copy-Item .env.local.example .env.local
```

The initial values are:

```env
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
WHISPER_MODEL=small
```

`small` is intentionally used for the first local test because `large-v3` is much larger and much slower on CPU.

After the pipeline works, change:

```env
WHISPER_MODEL=large-v3
```

to test the same model used by the original script.

## 3. Build

```powershell
docker compose --env-file .env.local -f docker-compose.local.yml build
```

## 4. Start

```powershell
docker compose --env-file .env.local -f docker-compose.local.yml up -d
```

Check:

```powershell
docker ps
docker logs -f voice-to-text
```

## 5. Health test

Open:

```text
http://localhost:8010/health
```

or:

```powershell
Invoke-RestMethod http://localhost:8010/health
```

Expected shape:

```json
{
  "ok": true,
  "service": "voice-to-text",
  "runtime": {
    "model": "small",
    "device": "cpu",
    "compute_type": "int8",
    "beam_size": 5,
    "vad_filter": true
  }
}
```

## 6. Load the model

The model is lazy-loaded. The backend starts without loading Whisper.

Run:

```powershell
Invoke-RestMethod -Method Post http://localhost:8010/api/transcribe/warmup
```

The first call downloads the selected Whisper model and stores it in the Docker volume `whisper_model_cache`.

Watch:

```powershell
docker logs -f voice-to-text
```

## 7. Transcribe a local voice file

For example:

```powershell
curl.exe -X POST "http://localhost:8010/api/transcribe/file" `
  -F "audio=@C:\Users\DELL\Desktop\voice.ogg"
```

Expected result:

```json
{
  "success": true,
  "filename": "voice.ogg",
  "text": "Hello, I want to know my booking status.",
  "language": "en",
  "model": "small",
  "device": "cpu"
}
```

This is the best endpoint for the local test because it does not depend on Chatwoot or any public audio URL.

## 8. Optional URL test

Local-only endpoint:

```powershell
$body = @{
  audio_url = "https://example.com/audio.ogg"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8010/api/transcribe/url" `
  -ContentType "application/json" `
  -Body $body
```

## 9. Switch to large-v3 locally

Edit `.env.local`:

```env
WHISPER_MODEL=large-v3
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

Restart:

```powershell
docker compose --env-file .env.local -f docker-compose.local.yml up -d --force-recreate
```

Then warm it:

```powershell
Invoke-RestMethod -Method Post http://localhost:8010/api/transcribe/warmup
```

`large-v3` on CPU can be slow. That is okay for validating behavior.

## 10. Local NVIDIA GPU test

Only do this if Docker Desktop + WSL2 can already see your NVIDIA GPU.

Check:

```powershell
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

If that works:

```powershell
docker compose `
  --env-file .env.local `
  -f docker-compose.local.yml `
  -f docker-compose.gpu.yml `
  up -d --build
```

The GPU override uses:

```env
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
WHISPER_MODEL=large-v3
```

## 11. Stop

```powershell
docker compose --env-file .env.local -f docker-compose.local.yml down
```

This removes the container/network but keeps the model cache volume.

To also delete the downloaded models:

```powershell
docker compose --env-file .env.local -f docker-compose.local.yml down -v
```

Do not put `large-v3` model initialization directly at import time in the main FastAPI backend. This service lazy-loads it and isolates its resource usage.

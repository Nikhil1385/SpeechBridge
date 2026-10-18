# SpeechBridge

**A Dockerized multilingual speech transcription and English translation API powered by Faster-Whisper.**

SpeechBridge converts audio into text and supports translating speech from different languages into English. It provides a standalone FastAPI service that runs locally in Docker and can use NVIDIA GPU acceleration.

## Features

- **Multilingual speech recognition** — transcribe supported languages.
- **English translation** — translate supported non-English speech into English.
- **FastAPI REST API** — interact with transcription endpoints over HTTP.
- **Faster-Whisper** — speech recognition powered by CTranslate2.
- **NVIDIA GPU acceleration** — run inference on a compatible GPU.
- **Lazy model loading** — load the Whisper model when needed rather than during application import.
- **Docker Compose** — consistent local deployment.
- **Local audio and URL endpoints** — submit an audio file or a supported audio URL.

## Technology Stack

- Ubuntu 22.04
- NVIDIA CUDA 12.4.1 runtime image family
- Python 3.11.9
- FastAPI
- Uvicorn
- Faster-Whisper
- Docker and Docker Compose

## Project Structure

```text
SpeechBridge/
├── app/
│   ├── main.py
│   ├── routes/
│   │   └── transcribe_route.py
│   └── services/
│       └── whisper_service.py
├── .dockerignore
├── .env.local.example
├── .gitignore
├── DockerFile.voice
├── docker-compose.local.yml
├── docker-compose.gpu.yml
├── requirements.txt
├── test-local.ps1
└── README.md
```

*The structure above reflects the expected project layout; adjust it if your actual files differ.*

## Prerequisites

- Windows 10/11
- Docker Desktop configured to use Linux containers with the WSL2 backend
- NVIDIA GPU and compatible drivers for GPU inference
- Internet access for downloading the Whisper model on first use

Verify your Docker installation in PowerShell:

```powershell
docker version
docker compose version
```

For GPU support, verify that Docker can access your NVIDIA GPU:

```powershell
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

If this command fails, troubleshoot Docker Desktop, WSL2, NVIDIA drivers, and GPU container support before starting the GPU configuration.

## Configuration

SpeechBridge uses two Compose files:

- `docker-compose.local.yml` defines the application service and local container configuration.
- `docker-compose.gpu.yml` overrides the configuration for NVIDIA GPU inference.

The GPU configuration uses these settings:

```env
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
WHISPER_MODEL=large-v3
```

The application also supports a CPU configuration, which is useful when GPU passthrough is unavailable or when testing on a machine without a compatible GPU.

**Keep local environment files and credentials private.** Commit `.env.local.example` as a configuration template, not `.env.local`.

## Build and Run — NVIDIA GPU

Run the following commands from the project root.

### 1. Build the image

```powershell
docker compose -f docker-compose.local.yml -f docker-compose.gpu.yml build
```

### 2. Start the service

```powershell
docker compose -f docker-compose.local.yml -f docker-compose.gpu.yml up -d
```

### 3. Check the container

```powershell
docker ps
docker logs -f voice-to-text
```

The container should start the FastAPI application on port `8000` internally, mapped to port `8010` on your Windows host.

## Health Check

Open the following URL in your browser:

**http://localhost:8010/health**

Or run:

```powershell
Invoke-RestMethod -Uri "http://localhost:8010/health"
```

An example response is:

```json
{
  "ok": true,
  "service": "voice-to-text",
  "runtime": {
    "model": "large-v3",
    "device": "cuda",
    "compute_type": "float16",
    "beam_size": 5,
    "vad_filter": true
  }
}
```

The actual response depends on your application's health endpoint and active configuration.

## Load the Whisper Model

SpeechBridge uses lazy model loading. The service can start before the Whisper model is loaded.

Warm up the model using the API:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8010/api/transcribe/warmup"
```

The first model load may take time because the model must be downloaded if it is not already cached. Downloaded model files are stored in the Docker volume `whisper_model_cache`, provided the volume is configured in your Compose files.

Follow the logs while the model loads:

```powershell
docker logs -f voice-to-text
```

## Transcribe an Audio File

Use the file transcription endpoint to upload an audio file directly from Windows.

Example:

```powershell
curl.exe --max-time 300 `
  -X POST "http://localhost:8010/api/transcribe/file" `
  -F "audio=@C:\Users\YOUR_USERNAME\Desktop\voice.ogg"
```

Replace the sample path with the location of your audio file.

An example response is:

```json
{
  "success": true,
  "filename": "voice.ogg",
  "text": "Hello, I want to know my booking status.",
  "language": "en",
  "model": "large-v3",
  "device": "cuda"
}
```

The response fields and format depend on the implementation in your transcription route.

### Translation Behavior

For supported non-English input, Faster-Whisper can perform speech-to-English translation when the application requests the `translate` task. For transcription in the original language, the application should use the `transcribe` task.

The selected task determines whether the output remains in the spoken language or is translated into English.

## Optional: Transcribe Audio from a URL

If URL transcription is enabled in your application, submit a JSON request:

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

Replace the example URL with a valid, publicly accessible audio URL. The endpoint must be enabled in the application, and the server must be able to access the URL.

Only use trusted URLs. If URL fetching is enabled, restrict permitted destinations to help prevent server-side request forgery (SSRF).

## Optional: Run on CPU

CPU mode is useful for testing without GPU passthrough. It can be slower, particularly with larger models.

Configure your environment for CPU inference:

```env
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
WHISPER_MODEL=small
```

Use the local Compose configuration:

```powershell
docker compose -f docker-compose.local.yml build
docker compose -f docker-compose.local.yml up -d
```

Then warm up the model:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8010/api/transcribe/warmup"
```

If your CPU settings are supplied through `.env.local`, create that file from `.env.local.example` and pass `--env-file .env.local` to the local Compose commands. The GPU override does not automatically make every setting in that file unnecessary.

## Switch Models or Change Configuration

To change the model or inference settings, update the relevant environment configuration.

For GPU inference:

```env
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
WHISPER_MODEL=large-v3
```

For CPU inference:

```env
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
WHISPER_MODEL=small
```

Recreate the container after changing configuration:

```powershell
docker compose -f docker-compose.local.yml -f docker-compose.gpu.yml up -d --force-recreate
```

If you change the Compose files or Docker image definition, rebuild as well:

```powershell
docker compose -f docker-compose.local.yml -f docker-compose.gpu.yml up -d --build
```

**Performance note:** `large-v3` needs substantially more memory and compute than `small`. Choose the model based on available system resources and the accuracy and latency you need.

## Stop the Service

Stop and remove the container and Compose network while preserving the model cache:

```powershell
docker compose -f docker-compose.local.yml -f docker-compose.gpu.yml down
```

To also remove the Compose-managed model cache volume:

```powershell
docker compose -f docker-compose.local.yml -f docker-compose.gpu.yml down -v
```

**Warning:** The `-v` option deletes the associated Compose-managed volumes, including cached model files. Those files may need to be downloaded again.

## Security Notes

- Never commit `.env.local`, API keys, tokens, or credentials.
- Keep `.env.local.example` free of real secrets.
- Do not expose the service publicly without appropriate authentication, request limits, and network restrictions.
- Validate audio uploads and limit file size and processing time.
- Restrict URL transcription to trusted destinations if it is enabled.
- Avoid committing private audio samples or generated model files.

## Troubleshooting

**The health endpoint is unavailable**

```powershell
docker ps
docker logs --tail 200 voice-to-text
```

Check that the container is running and port `8010` is available.

**Docker cannot access the NVIDIA GPU**

```powershell
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

If the test fails, resolve the GPU container configuration before using the GPU Compose override.

**Model loading or transcription is slow**

- Try `small` for initial testing.
- Check container logs for model-download or inference errors.
- Verify available GPU memory and CPU/RAM usage.
- Remember that the first model load can take longer than subsequent requests.

**Transcription returns an error**

- Verify the audio file exists and is supported.
- Check the endpoint path and request field name.
- Inspect the application logs.
- Confirm the selected model has finished loading.


**SpeechBridge — Bridging spoken languages through AI.**
By Nikhil
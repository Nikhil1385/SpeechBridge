$ErrorActionPreference = "Stop"

Write-Host "Checking service..."
Invoke-RestMethod -Method Get -Uri "http://localhost:8010/health" |
    ConvertTo-Json -Depth 5

Write-Host ""
Write-Host "Warming model..."
Invoke-RestMethod -Method Post -Uri "http://localhost:8010/api/transcribe/warmup" |
    ConvertTo-Json -Depth 5

Write-Host ""
Write-Host "To test an audio file, run:"
Write-Host 'curl.exe -X POST "http://localhost:8010/api/transcribe/file" -F "audio=@C:\path\to\voice.ogg"'

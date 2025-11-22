# Quick Start Guide: MLX Whisper Transcribe API

**Feature**: 001-transcribe-api
**Last Updated**: 2025-11-22

## Overview

This guide helps you quickly get started with the MLX Whisper Transcribe API. The API is compatible with OpenAI's Whisper API, so you can use existing OpenAI client libraries with minimal configuration changes.

## What You'll Learn

- How to set up the server
- How to transcribe an audio file
- How to use existing OpenAI client libraries
- Common use cases and examples
- Error handling

## Prerequisites

- Python 3.12 or later
- macOS (for MLX support) or Linux
- 8GB+ RAM recommended
- 2GB+ free disk space for models

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd simple-mlx-whisper-server
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `fastapi`: HTTP server framework
- `uvicorn`: ASGI server
- `mlx-whisper`: MLX-Whisper for transcription
- `pydantic`: Data validation
- `pyyaml`: Configuration management
- `python-multipart`: Multipart form data handling

### 3. Configure the Server

Edit `config/config.yaml`:

```yaml
server:
  host: "0.0.0.0"
  port: 8000
  workers: 2  # Adjust based on your CPU cores

transcription:
  max_file_size: 26214400  # 25MB in bytes
  max_duration: 1500       # 25 minutes in seconds
  allowed_formats: ["mp3", "wav", "m4a", "mp4", "mpeg", "webm"]
  model: "mlx-community/whisper-small"

logging:
  level: "INFO"
  format: "json"
```

### 4. Start the Server

```bash
python -m src.main
# or
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

The server will start on `http://localhost:8000`

Check health:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "workers": {
    "total": 2,
    "active": 0,
    "available": 2
  },
  "model_loaded": true,
  "uptime_seconds": 10
}
```

## Quick Start Examples

### Example 1: Basic Transcription (curl)

```bash
curl -X POST "http://localhost:8000/v1/audio/transcriptions" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/your/audio.mp3" \
  -F "model=mlx-community/whisper-small" \
  -F "language=en"
```

Response:
```json
{
  "text": "Transcribed text from your audio file",
  "language": "en",
  "duration": 120.5,
  "task": "transcribe"
}
```

### Example 2: Using OpenAI Python SDK

```python
from openai import OpenAI

# Initialize client pointing to your server
client = OpenAI(
    api_key="not-needed",  # API accepts anonymous requests
    base_url="http://localhost:8000/v1"
)

# Transcribe audio file
with open("audio.mp3", "rb") as audio_file:
    transcript = client.audio.transcriptions.create(
        model="mlx-community/whisper-small",
        file=audio_file,
        language="en"
    )

print(transcript.text)
```

### Example 3: Different Response Formats

#### JSON (default)
```bash
curl -X POST "http://localhost:8000/v1/audio/transcriptions" \
  -F "file=@audio.mp3" \
  -F "response_format=json"
```

#### Text only
```bash
curl -X POST "http://localhost:8000/v1/audio/transcriptions" \
  -F "file=@audio.mp3" \
  -F "response_format=text"
```

Returns plain text response (no JSON)

#### Verbose JSON (with timestamps)
```bash
curl -X POST "http://localhost:8000/v1/audio/transcriptions" \
  -F "file=@audio.mp3" \
  -F "response_format=verbose_json"
```

Returns segments with timestamps:
```json
{
  "text": "Hello world, this is a test.",
  "language": "en",
  "duration": 120.5,
  "task": "transcribe",
  "segments": [
    {
      "id": 0,
      "seek": 0,
      "start": 0.0,
      "end": 2.5,
      "text": "Hello world,",
      "temperature": 0,
      "avg_logprob": -0.5,
      "compression_ratio": 0.8,
      "no_speech_prob": 0.01
    },
    {
      "id": 1,
      "seek": 250,
      "start": 2.5,
      "end": 4.5,
      "text": " this is a test.",
      "temperature": 0,
      "avg_logprob": -0.5,
      "compression_ratio": 0.8,
      "no_speech_prob": 0.01
    }
  ]
}
```

### Example 4: Language Detection

```python
# Auto-detect language (don't specify 'language' parameter)
transcript = client.audio.transcriptions.create(
    model="mlx-community/whisper-small",
    file=audio_file
)

print(f"Detected language: {transcript.language}")
```

### Example 5: Python Requests Library

```python
import requests

url = "http://localhost:8000/v1/audio/transcriptions"

with open("audio.mp3", "rb") as f:
    files = {"file": f}
    data = {
        "model": "mlx-community/whisper-small",
        "language": "en",
        "response_format": "json"
    }

    response = requests.post(url, files=files, data=data)

if response.status_code == 200:
    result = response.json()
    print(result["text"])
else:
    print(f"Error: {response.status_code}")
    print(response.json())
```

## Supported Audio Formats

| Format | Extension | MIME Type | Notes |
|--------|-----------|-----------|-------|
| MP3 | .mp3 | audio/mpeg | Most common |
| WAV | .wav | audio/wav | Uncompressed |
| M4A | .m4a | audio/mp4 | Apple format |
| MP4 | .mp4 | audio/mp4 | Video with audio |
| MPEG | .mpeg | video/mpeg | Video with audio |
| WEBM | .webm | audio/webm | Web format |

**Maximum file size**: 25MB
**Maximum duration**: 25 minutes (1500 seconds)

## Error Handling

### Common Error Codes

#### 400 Bad Request
```json
{
  "error": {
    "message": "Unsupported file format. Allowed: mp3, wav, m4a, mp4, mpeg, webm",
    "type": "invalid_file_format",
    "code": "400"
  }
}
```
**Cause**: File format not supported
**Solution**: Convert to supported format

#### 413 Payload Too Large
```json
{
  "error": {
    "message": "Audio file too large: 30MB (max: 25MB)",
    "type": "file_too_large",
    "code": "413"
  }
}
```
**Cause**: File exceeds 25MB size limit
**Solution**: Split audio or compress

```json
{
  "error": {
    "message": "Audio file too long: 30 minutes (max: 25 minutes)",
    "type": "file_too_long",
    "code": "413"
  }
}
```
**Cause**: File exceeds 25-minute duration
**Solution**: Split audio into shorter segments

#### 422 Unprocessable Entity
```json
{
  "error": {
    "message": "Invalid audio file: unable to read audio data",
    "type": "invalid_audio_file",
    "code": "422"
  }
}
```
**Cause**: Corrupted or invalid audio file
**Solution**: Verify audio file is valid and not corrupted

#### 503 Service Unavailable
```json
{
  "error": {
    "message": "Server busy. Maximum 10 concurrent requests.",
    "type": "server_busy",
    "code": "503"
  }
}
```
**Cause**: Too many concurrent requests (limit: 10)
**Solution**: Implement client-side rate limiting and retry

### Error Handling Best Practices

```python
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def transcribe_with_retry(file_path, max_retries=3, backoff_factor=1):
    url = "http://localhost:8000/v1/audio/transcriptions"
    session = requests.Session()

    # Configure retry strategy
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    with open(file_path, "rb") as f:
        files = {"file": f}
        data = {"model": "mlx-community/whisper-small"}
        response = session.post(url, files=files, data=data)

    if response.status_code == 200:
        return response.json()
    elif response.status_code == 503:
        # Server busy, implement client-side backoff
        print("Server busy, consider implementing exponential backoff")
        raise Exception("Server overloaded")
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
        raise Exception("Transcription failed")

    return None
```

## Performance Tips

### 1. Concurrent Requests

The server supports up to 10 concurrent requests. Clients can:

```python
import asyncio
import aiohttp

async def transcribe_batch(file_paths):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for path in file_paths:
            with open(path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename='audio.mp3')
                data.add_field('model', 'mlx-community/whisper-small')

                task = session.post(
                    "http://localhost:8000/v1/audio/transcriptions",
                    data=data
                )
                tasks.append(task)

        responses = await asyncio.gather(*tasks, return_exceptions=True)
        return responses

# Run 10 transcriptions concurrently
files = ["audio1.mp3", "audio2.mp3", ...]
results = asyncio.run(transcribe_batch(files))
```

### 2. File Size Optimization

```bash
# Compress audio before sending
ffmpeg -i input.wav -b:a 128k output.mp3

# Check file size
ls -lh audio.mp3

# Check duration
ffprobe -v quiet -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 audio.mp3
```

### 3. Language Specification

Specify language to improve accuracy and speed:

```python
# Auto-detect (slower)
transcript = client.audio.transcriptions.create(
    model="mlx-community/whisper-small",
    file=audio_file
)

# Specify language (faster, better accuracy)
transcript = client.audio.transcriptions.create(
    model="mlx-community/whisper-small",
    file=audio_file,
    language="en"  # or "zh", "es", etc.
)
```

## Monitoring and Health Checks

### Health Endpoint

```bash
curl http://localhost:8000/health
```

Response includes:
- `status`: Server health (healthy, degraded, unhealthy)
- `workers`: Worker pool status
- `model_loaded`: Whether MLX model is loaded
- `uptime_seconds`: Server uptime

### Structured Logging

Logs are in JSON format for easy parsing:

```json
{
  "timestamp": "2025-11-22T10:30:00Z",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "event": "transcription_completed",
  "duration_ms": 5234,
  "file_size_bytes": 5242880,
  "audio_duration_seconds": 120.5,
  "status_code": 200
}
```

## Configuration Reference

### config/config.yaml

```yaml
server:
  host: "0.0.0.0"          # Server host address
  port: 8000               # Server port
  workers: 2               # Number of worker processes (default: 2)

transcription:
  max_file_size: 26214400  # Max file size in bytes (default: 25MB)
  max_duration: 1500       # Max duration in seconds (default: 25 min)
  model: "mlx-community/whisper-small"  # MLX model to use
  allowed_formats:         # Allowed audio formats
    - "mp3"
    - "wav"
    - "m4a"
    - "mp4"
    - "mpeg"
    - "webm"

logging:
  level: "INFO"            # Log level (DEBUG, INFO, WARNING, ERROR)
  format: "json"           # Log format (json, text)
```

### Environment Variables

You can override config via environment variables:

```bash
export SERVER_HOST="0.0.0.0"
export SERVER_PORT="8000"
export SERVER_WORKERS="4"
export TRANSCRIPTION_MAX_FILE_SIZE="52428800"  # 50MB
export LOGGING_LEVEL="DEBUG"
```

## Migration from OpenAI API

If you're currently using OpenAI's Whisper API:

### Before (OpenAI)
```python
from openai import OpenAI

client = OpenAI(
    api_key="your-api-key",
    base_url="https://api.openai.com/v1"
)

transcript = client.audio.transcriptions.create(
    model="whisper-1",
    file=audio_file
)
```

### After (MLX Whisper Server)
```python
from openai import OpenAI

client = OpenAI(
    api_key="not-needed",  # Optional for this server
    base_url="http://localhost:8000/v1"  # Your server URL
)

transcript = client.audio.transcriptions.create(
    model="mlx-community/whisper-small",  # Different model name
    file=audio_file
)
```

**Changes required**:
1. Update `base_url` to your server URL
2. Change `model` from "whisper-1" to "mlx-community/whisper-small"
3. Optional: Remove API key (or keep for future auth)

## Troubleshooting

### Server won't start

```bash
# Check Python version
python --version  # Should be 3.12+

# Check dependencies
pip list | grep fastapi

# Check port availability
lsof -i :8000

# Check logs
tail -f logs/server.log
```

### Out of memory

```yaml
# Reduce worker count in config/config.yaml
server:
  workers: 1  # Use 1 worker instead of 2
```

### Model download fails

```bash
# Manually download model
python -c "import mlx.core as mx; import mlx_whisper; mlx_whisper.load('mlx-community/whisper-small')"
```

### Transcription fails

```bash
# Check file format
file audio.mp3

# Check file size
ls -lh audio.mp3

# Check duration
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 audio.mp3
```

## Next Steps

- ✅ Server is running and healthy
- ✅ You can transcribe audio files
- ✅ Error handling is implemented
- ✅ You're ready for production!

### Production Deployment

1. Use a process manager (systemd, PM2)
2. Set up reverse proxy (nginx)
3. Configure SSL/TLS certificates
4. Set up log aggregation
5. Monitor with Prometheus/Grafana
6. Configure auto-scaling if needed

### Advanced Usage

- Implement client-side rate limiting
- Add caching for repeated requests
- Set up request queuing for batch processing
- Monitor performance metrics
- Implement request retries with backoff

## Support

- Check health endpoint: `GET /health`
- View logs: Structured JSON logs with correlation IDs
- OpenAPI spec: Available at `/docs`
- ReDoc spec: Available at `/redoc`

## Resources

- [MLX Framework Documentation](https://ml-explore.github.io/mlx/build/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenAI Whisper API Reference](https://platform.openai.com/docs/guides/speech-to-text)

---

**Ready to transcribe!** 🎉

You now have everything you need to start transcribing audio with the MLX Whisper API.

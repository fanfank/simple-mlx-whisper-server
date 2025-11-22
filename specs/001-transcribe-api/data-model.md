# Data Model: High-Performance HTTP Transcribe API

**Date**: 2025-11-22
**Feature**: 001-transcribe-api

## Overview

This document defines the data entities, validation rules, and relationships for the Transcribe API server. The data model follows OpenAI Whisper API specification for full compatibility.

## Core Entities

### 1. Audio File

**Purpose**: Represents an uploaded audio file for transcription

**Attributes**:
- `filename` (string): Original filename from client
- `content_type` (string): MIME type (audio/mpeg, audio/wav, etc.)
- `size_bytes` (integer): File size in bytes (max: 25MB)
- `duration_seconds` (float): Audio duration (max: 1500 seconds / 25 minutes)
- `format` (string): Audio format (mp3, wav, m4a, mp4, mpeg, webm)
- `checksum` (string, optional): SHA256 hash for integrity
- `temp_path` (string): Temporary file path during processing

**Validation Rules**:
- Size must be ≤ 25,214,400 bytes (25MB)
- Duration must be ≤ 1500 seconds (25 minutes)
- Format must be in allowed_formats list
- Content type must match file extension
- File must be readable and valid audio format

**State Transitions**:
```
UPLOADED → VALIDATED → PROCESSING → COMPLETED
                ↓
            VALIDATION_FAILED
                ↓
            PROCESSING_FAILED
```

**Constraints**:
- Must have valid audio headers (magic numbers)
- Must not be corrupted or truncated
- Temporary files automatically deleted after processing

---

### 2. Transcription Request

**Purpose**: Represents a transcription request received via HTTP

**Attributes**:
- `request_id` (UUID): Unique identifier for the request
- `correlation_id` (UUID): For request tracing across logs
- `audio_file` (Audio File): The audio file to transcribe
- `parameters` (Transcription Parameters): Request parameters
- `timestamp` (datetime): When request was received
- `client_info` (dict, optional): Client metadata (User-Agent, etc.)

**Validation Rules**:
- Request ID must be unique
- Audio file must be validated before processing
- Parameters must be within allowed ranges
- Timestamp must be recent (within SLA)

**State Transitions**:
```
RECEIVED → QUEUED → PROCESSING → COMPLETED
              ↓
          QUEUE_FULL (HTTP 503)
              ↓
          INVALID (HTTP 400/413/422)
```

**Constraints**:
- Maximum 10 concurrent requests across all workers
- Request queue managed by WorkerPool
- Requests beyond capacity rejected immediately

---

### 3. Transcription Parameters

**Purpose**: Parameters for controlling transcription behavior

**Attributes**:
- `model` (string, optional): Model identifier (default: "whisper-1")
- `language` (string, optional): Language code (e.g., "en", "zh")
- `response_format` (string, optional): Output format (json, text, srt, verbose_json)
- `temperature` (float, optional): Sampling temperature (0.0-2.0, default: 0.0)

**Validation Rules**:
- Model must be a supported MLX Whisper model
- Language must be ISO 639-1 code or None
- Response format must be: json, text, srt, or verbose_json
- Temperature must be between 0.0 and 2.0 (float)

**Defaults** (when not specified):
- model: "mlx-community/whisper-small"
- language: None (auto-detect)
- response_format: "json"
- temperature: 0.0

**Constraints**:
- Compatible with OpenAI Whisper API parameter names
- Parameters passed through to MLX Whisper where applicable

---

### 4. Transcription Result

**Purpose**: The output of audio transcription

**Attributes**:
- `text` (string): The transcribed text
- `language` (string, optional): Detected or specified language
- `duration` (float): Audio duration in seconds
- `task` (string, optional): Task type (default: "transcribe")
- `segments` (array, optional): Timestamped segments (if verbose_json)
- `processing_time_ms` (integer): Time spent processing

**Validation Rules**:
- Text must be valid UTF-8 string
- Language must be ISO 639-1 code or None
- Duration must match original audio duration
- Processing time must be positive

**State Transitions**:
```
GENERATED → FORMATTED → RETURNED
```

**Constraints**:
- Format must match OpenAI Whisper API response
- Text encoding must be UTF-8
- All metadata preserved for logging

**Example (JSON response_format)**:
```json
{
  "text": "Transcribed text goes here",
  "language": "en",
  "duration": 120.5,
  "task": "transcribe"
}
```

---

### 5. Error Response

**Purpose**: Error information returned to client

**Attributes**:
- `error` (Error Details): Error type and message
- `request_id` (UUID): For debugging and correlation

**Validation Rules**:
- Error must have valid error type
- Message must be human-readable
- Request ID must match original request

**Constraints**:
- HTTP status code appropriate for error type
- No sensitive information in error messages
- Error structure matches OpenAI API

**Error Types**:
- `invalid_request_error`: Invalid parameters (HTTP 400)
- `invalid_file_format`: Unsupported format (HTTP 400)
- `file_too_large`: Exceeds size limit (HTTP 413)
- `file_too_long`: Exceeds duration limit (HTTP 413)
- `invalid_audio_file`: Corrupted or unreadable (HTTP 422)
- `rate_limit_exceeded`: Too many concurrent requests (HTTP 503)
- `server_error`: Internal server error (HTTP 500)

**Example**:
```json
{
  "error": {
    "message": "Audio file too large: 30MB (max: 25MB)",
    "type": "file_too_large",
    "code": "413"
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### 6. Worker Pool Configuration

**Purpose**: Configuration for managing worker processes

**Attributes**:
- `worker_count` (integer): Number of worker processes (default: 2)
- `max_concurrent_requests` (integer): Maximum concurrent requests (default: 10)
- `request_queue_size` (integer): Maximum queue size
- `worker_timeout` (integer): Worker idle timeout (seconds)

**Validation Rules**:
- Worker count must be ≥ 1
- Max concurrent must be ≥ worker_count
- Queue size must accommodate peak load

**Constraints**:
- Workers started on server initialization
- Each worker loads MLX Whisper model independently
- Workers survive model processing errors

---

### 7. Server Configuration

**Purpose**: Server-wide configuration settings

**Attributes**:
- `host` (string): Server host address
- `port` (integer): Server port number
- `workers` (integer): Number of worker processes
- `max_file_size` (integer): Maximum upload size in bytes
- `max_duration` (integer): Maximum duration in seconds
- `allowed_formats` (array): Allowed audio formats
- `model_name` (string): MLX Whisper model identifier
- `log_level` (string): Logging level
- `log_format` (string): Log format (json, text)

**Validation Rules**:
- Host must be valid IP or hostname
- Port must be 1-65535
- All sizes and limits must be positive
- Log level must be valid (DEBUG, INFO, WARNING, ERROR)

**Defaults**:
- host: "0.0.0.0"
- port: 8000
- workers: 2
- max_file_size: 25,214,400 (25MB)
- max_duration: 1500 (25 minutes)
- allowed_formats: ["mp3", "wav", "m4a", "mp4", "mpeg", "webm"]
- model_name: "mlx-community/whisper-small"
- log_level: "INFO"
- log_format: "json"

---

### 8. Request Log Entry

**Purpose**: Structured log entry for request tracking

**Attributes**:
- `timestamp` (string): ISO 8601 timestamp
- `request_id` (UUID): Request identifier
- `correlation_id` (UUID): Correlation ID for tracing
- `level` (string): Log level (INFO, WARNING, ERROR)
- `event` (string): Event type (request_received, transcription_started, etc.)
- `duration_ms` (integer, optional): Request duration
- `file_size_bytes` (integer, optional): Uploaded file size
- `audio_duration_seconds` (float, optional): Audio duration
- `status_code` (integer, optional): HTTP response code
- `error_type` (string, optional): Error type if failed

**Constraints**:
- No audio content or sensitive data logged
- Only metadata for debugging and monitoring
- Correlation ID enables request chain tracing

**Example**:
```json
{
  "timestamp": "2025-11-22T10:30:00Z",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "correlation_id": "330e7500-f19b-52d5-b617-557766551111",
  "level": "INFO",
  "event": "transcription_completed",
  "duration_ms": 5234,
  "file_size_bytes": 5242880,
  "audio_duration_seconds": 120.5,
  "status_code": 200
}
```

---

## Relationships

### Request Flow
```
HTTP Request → Transcription Request → Audio File → Validation
                                                    ↓
Transcription Result ← Worker Pool ← Transcription Service ← Processing
                                                    ↓
                                            MLX Whisper Model
```

### Error Flow
```
Validation Error → Error Response (HTTP 4xx)
Processing Error → Error Response (HTTP 5xx)
Worker Error → Restart Worker → Error Response (HTTP 503)
```

### Logging Flow
```
Request Received → Log Entry (request_received)
Processing Started → Log Entry (transcription_started)
Processing Complete → Log Entry (transcription_completed)
Error Encountered → Log Entry (error_type)
```

---

## Data Integrity Rules

1. **File Uniqueness**: Each request receives unique request_id (UUID4)
2. **File Cleanup**: Temporary files deleted after successful or failed processing
3. **Memory Management**: Audio buffers freed after transcription
4. **Model Isolation**: Each worker maintains independent MLX model instance
5. **No Data Persistence**: No audio data stored after request completion

---

## Validation Functions

### validate_audio_file(file)
- Check file exists and is readable
- Verify file size ≤ max_file_size
- Verify file extension in allowed_formats
- Validate audio headers (magic numbers)
- Extract duration using audio metadata
- Verify duration ≤ max_duration
- Return AudioFile entity or ValidationError

### validate_transcription_parameters(params)
- Check model is supported MLX model
- Verify language is ISO 639-1 code or None
- Validate response_format is allowed value
- Verify temperature is float 0.0-2.0
- Return TranscriptionParameters entity or ValidationError

### enforce_concurrency_limit()
- Check current request count < max_concurrent_requests
- If at capacity, return RateLimitError (HTTP 503)
- Increment counter on successful validation
- Decrement counter on completion/failure

---

## Summary

The data model provides:
- ✅ Complete representation of all request/response data
- ✅ Validation rules for all inputs
- ✅ State transitions for request lifecycle
- ✅ Error handling with appropriate HTTP codes
- ✅ OpenAI API compatibility
- ✅ Observability through structured logging
- ✅ No sensitive data persistence

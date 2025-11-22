# Feature Specification: High-Performance HTTP Transcribe API

**Feature Branch**: `001-transcribe-api`
**Created**: 2025-11-22
**Status**: Draft
**Input**: User description: "做一个高性能 HTTP 服务器，核心接口是 transcribe，与 OpenAI 的 Whisper OpenAPI 接口的入参、返回兼容，不需要管其它的接口，只实现 transcribe 接口"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Transcribe Audio File via API (Priority: P1) 🎯 MVP

Developers can send audio files to the transcribe endpoint and receive accurate text transcriptions, using standard OpenAI Whisper client libraries without any code changes.

**Why this priority**: This is the core functionality - enables users to integrate the server as a drop-in replacement for OpenAI's Whisper API, providing immediate value with zero migration cost.

**Independent Test**: Send a valid audio file to the transcribe endpoint and verify the response matches OpenAI's API format and contains accurate transcription text. Can be fully tested with curl or any HTTP client.

**Acceptance Scenarios**:

1. **Given** a valid audio file (MP3, WAV, M4A, etc.), **When** sent to `/v1/audio/transcriptions` endpoint with proper headers and parameters, **Then** the server returns HTTP 200 with JSON containing the transcribed text in the `"text"` field.

2. **Given** an audio file that matches OpenAI Whisper API format, **When** sent with identical headers and body structure, **Then** the response format MUST match OpenAI's specification exactly (same field names, structure, and HTTP status codes).

3. **Given** a client using OpenAI's official Python/Node.js SDKs, **When** pointing to this server's endpoint, **Then** the client works without any code modifications.

---

### User Story 2 - Multiple Audio Format Support (Priority: P2)

The API accepts various common audio formats (MP3, MP4, MPEG, M4A, WAV, WEBM) without requiring format conversion, ensuring broad compatibility with user audio sources.

**Why this priority**: Expands the usable audio sources for users, reducing pre-processing steps and improving the overall experience. Different platforms produce different audio formats.

**Independent Test**: Submit the same audio content in different formats (MP3, WAV, M4A) and verify all produce accurate transcriptions with the same content.

**Acceptance Scenarios**:

1. **Given** audio content in MP3 format, **When** sent to the transcribe endpoint, **Then** the server processes and transcribes successfully.

2. **Given** identical audio content in different supported formats, **When** each is transcribed separately, **Then** the resulting text should be identical (or near-identical) across formats.

---

### User Story 3 - Error Handling & Edge Cases (Priority: P3)

The API handles invalid inputs gracefully with appropriate error messages and HTTP status codes, maintaining stability under various error conditions.

**Why this priority**: Ensures production reliability and good developer experience. Proper error handling helps users understand and fix issues quickly.

**Independent Test**: Send various invalid inputs (corrupt files, wrong format, missing parameters) and verify appropriate error responses.

**Acceptance Scenarios**:

1. **Given** an unsupported audio file format, **When** sent to the endpoint, **Then** the server returns HTTP 400 with a clear error message indicating unsupported format.

2. **Given** a corrupted or unreadable audio file, **When** sent to the endpoint, **Then** the server returns HTTP 422 with an appropriate error message.

3. **Given** a file that exceeds the maximum size limit, **When** sent to the endpoint, **Then** the server returns HTTP 413 with an error message.

---

### Edge Cases

- What happens when audio contains silence or very low audio levels? → MLX Whisper handles naturally, returns empty or partial text as appropriate.
- How does system handle audio files with multiple speakers? → MLX Whisper transcribes all speakers together in one text stream (no speaker separation).
- What happens when the same audio is sent simultaneously by multiple clients? → Each request processed independently; system validates concurrency limit per FR-010.
- How does the system handle extremely long audio files? → Reject files over 25MB or 25 minutes with HTTP 413 per FR-007.
- What happens when audio contains special characters or non-ASCII text? → MLX Whisper handles UTF-8 encoding; transcription preserves special characters.
- What happens when 10+ concurrent requests arrive? → Return HTTP 503 "Server Busy" for 11th+ requests per FR-010.
- What happens when file upload is corrupted during transmission? → Return HTTP 422 with appropriate error per FR-009.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a `/v1/audio/transcriptions` HTTP endpoint that accepts POST requests with multipart/form-data containing audio files.
- **FR-002**: System MUST accept the following audio formats: MP3, MP4, MPEG, M4A, WAV, WEBM.
- **FR-003**: System MUST respond with HTTP 200 and JSON containing a `"text"` field with the transcription result for valid requests.
- **FR-004**: API MUST accept standard Whisper API parameters including `model`, `language`, `response_format`, and `temperature`.
- **FR-005**: System MUST return identical request/response format as OpenAI Whisper API specification for full compatibility.
- **FR-006**: System MUST reject audio files exceeding 25MB with HTTP 413 (Payload Too Large).
- **FR-007**: System MUST reject audio files exceeding 25 minutes duration with HTTP 413 (Payload Too Large).
- **FR-008**: System MUST validate audio format and reject unsupported formats with HTTP 400.
- **FR-009**: System MUST handle corrupted or unreadable audio files with HTTP 422 (Unprocessable Entity).
- **FR-010**: System MUST reject requests beyond 10 concurrent limit with HTTP 503 (Service Unavailable).
- **FR-011**: System MUST log request metadata, response times, errors, and MLX inference metrics with structured logging.
- **FR-012**: System MUST NOT log audio file content in any logs (privacy protection).

### Key Entities

- **Audio File**: Binary data in various formats (MP3, WAV, M4A, etc.) submitted via HTTP upload
- **Transcription Request**: HTTP POST with multipart/form-data containing file and parameters
- **Transcription Result**: JSON response with text field containing converted speech-to-text output
- **Error Response**: JSON response with error code and human-readable message

### Performance Requirements

- **PR-001**: System MUST handle at least 10 concurrent transcription requests without degradation.
- **PR-002**: Transcription processing for files under 5 minutes MUST complete within 30 seconds for single requests.
- **PR-003**: System MUST maintain stable performance under continuous load (100 requests/hour).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: API clients using OpenAI Whisper SDKs can switch to this server by changing only the endpoint URL, with zero code modifications required.
- **SC-002**: 95% of valid audio file requests receive accurate transcriptions matching the audio content.
- **SC-003**: Server maintains 99.5% uptime and responds to requests within 2 seconds (excluding transcription processing time) under normal load.
- **SC-004**: Developers can integrate the API in under 5 minutes using existing OpenAI Whisper documentation.
- **SC-005**: System handles at least 10 simultaneous transcriptions without timeout or performance degradation.
- **SC-006**: 90% of developer integrations succeed on first attempt without requiring troubleshooting.

## Clarifications

### Session 2025-11-22

- ~~Q: Should the API require API key authentication? → A: API key required with validation - prevents abuse, enables usage tracking, and allows for rate limiting per key.~~ **UPDATED: No authentication required - public API access**
- Q: What is the maximum concurrent request limit? → A: System MUST handle minimum 10 concurrent requests, reject 11th+ with HTTP 503 "Server Busy" - defines clear capacity boundary for load testing and operations.
- Q: What is the maximum audio file size limit? → A: 25MB maximum file size - standard for cloud APIs, balances capability with performance.
- Q: What is the maximum audio duration? → A: 25MB or 25 minutes (whichever comes first) - prevents memory exhaustion while accommodating typical use cases.
- Q: What observability is required? → A: Log request/response metadata, response times, errors, and MLX inference metrics to structured logging system - enables debugging and performance monitoring.

## Technical Assumptions

- **Audio Processing**: Standard audio codecs and formats widely supported by MLX Whisper will be used.
- **Model Compatibility**: MLX Whisper model variants will be used that match OpenAI's model capabilities.
- **Authentication**: No authentication required - public API access (simplifies integration).
- **Response Format**: JSON response structure exactly matches OpenAI's Whisper API response format.
- **File Handling**: Audio files are temporarily stored during processing and cleaned up immediately after.
- **Security**: No sensitive data (audio content or metadata) logged, only operational metrics.

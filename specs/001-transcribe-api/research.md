# Research: High-Performance HTTP Transcribe API

**Date**: 2025-11-22
**Feature**: 001-transcribe-api

## Technology Decisions

### 1. HTTP Server Framework: FastAPI

**Decision**: Use FastAPI for the HTTP server layer

**Rationale**:
- Native async support for handling concurrent requests efficiently
- Automatic OpenAPI/Swagger documentation generation (matches OpenAI Whisper API spec)
- Type hints and pydantic models for request/response validation
- Built-in middleware for CORS, logging, and error handling
- High performance comparable to Node.js and Go frameworks
- Excellent Python ecosystem and community support

**Alternatives Considered**:
- Flask: Requires manual async handling, less native type validation
- Django: Overkill for single-endpoint API, slower startup
- Starlette: Lower-level than FastAPI, requires more boilerplate

---

### 2. ASGI Server: Uvicorn

**Decision**: Use Uvicorn with Uvicorn workers for server deployment

**Rationale**:
- Production-grade ASGI server
- Supports multiple worker processes for CPU-bound MLX operations
- Built-in logging and configuration options
- Easy integration with FastAPI
- Supports both single-process and multi-process deployment

**Worker Configuration**:
- Default: 2 workers (matches config.yaml default)
- Each worker runs MLX-Whisper model independently
- Worker pool manages request queue and concurrency limits
- 10 concurrent request limit enforced across all workers

---

### 3. MLX-Whisper Integration

**Decision**: Use mlx-whisper library for audio transcription

**Rationale**:
- Apple's MLX framework optimized for Apple Silicon
- Supports standard audio formats (MP3, WAV, M4A, etc.)
- Whisper models compatible with OpenAI API output
- Python bindings available for direct integration
- Memory-efficient model loading and inference

**Model Management**:
- Models loaded once per worker on startup
- Models cached in memory during worker lifetime
- Thread-safe model inference
- Graceful model cleanup on shutdown

---

### 4. Configuration Management: YAML + Python

**Decision**: YAML configuration file with Python config loader

**Rationale**:
- Human-readable configuration format
- Support for nested configuration structures
- Easy to modify without code changes
- Type-safe loading with Pydantic validation
- Environment variable interpolation support

**Config Structure**:
```yaml
server:
  host: "0.0.0.0"
  port: 8000
  workers: 2  # Configurable worker count

transcription:
  max_file_size: 26214400  # 25MB in bytes
  max_duration: 1500  # 25 minutes in seconds
  allowed_formats: ["mp3", "wav", "m4a", "mp4", "mpeg", "webm"]
  model: "mlx-community/whisper-small"  # MLX model identifier

logging:
  level: "INFO"
  format: "json"
```

---

### 5. Audio Format Support

**Decision**: Support MP3, WAV, M4A, MP4, MPEG, WEBM formats

**Rationale**:
- Matches OpenAI Whisper API format support
- Broad compatibility with common audio sources
- MLX-Whisper native support for these formats
- No conversion required - direct processing

**Validation Strategy**:
- File extension checking
- Magic number/file header validation
- Duration extraction via audio metadata
- File size checking before processing

---

### 6. Concurrency Model

**Decision**: Multi-worker process pool with request queuing

**Rationale**:
- MLX operations are CPU-intensive and benefit from multiple processes
- Process isolation prevents GIL limitations
- Each worker handles one request at a time
- Request queue manages 10 concurrent limit
- Simple and reliable concurrency model

**Worker Pool**:
- N workers configured via config.yaml (default: 2)
- Each worker initialized with MLX model
- Workers listen on shared request queue
- 11th+ request rejected with HTTP 503

---

### 7. Logging Strategy

**Decision**: Structured JSON logging with correlation IDs

**Rationale**:
- Machine-readable logs for production debugging
- Correlation IDs enable request tracing across logs
- Performance metrics logged automatically
- No sensitive audio data logged
- Compatible with log aggregation systems

**Log Fields**:
- Request ID (UUID)
- Correlation ID (for request chaining)
- Timestamp (ISO 8601)
- Request metadata (file size, duration)
- Performance metrics (processing time, memory usage)
- Error details (for failures)

---

### 8. Testing Strategy

**Decision**: pytest with unit, integration, and contract tests

**Rationale**:
- FastAPI has excellent pytest integration
- Contract tests verify OpenAI API compatibility
- Unit tests mock MLX dependencies for isolation
- Integration tests validate end-to-end flows
- Test fixtures provide consistent audio samples

**Test Categories**:
- **Unit Tests**: Individual components (config, validation, transcription service)
- **Integration Tests**: API endpoint with real FastAPI client
- **Contract Tests**: OpenAI API format compatibility
- **Performance Tests**: Load testing with concurrent requests

---

### 9. File Handling Strategy

**Decision**: Temporary file storage with automatic cleanup

**Rationale**:
- Audio files processed in-memory when possible
- Temporary files created only for large files
- Automatic cleanup after transcription
- No persistent storage needed
- Secure deletion to prevent data leaks

**File Lifecycle**:
1. Request received with audio file
2. File validated (size, format, duration)
3. Temporary file created if needed
4. MLX-Whisper processes audio
5. Result returned
6. Temporary files deleted
7. Memory freed

---

## Implementation Patterns

### Dependency Injection Pattern
- FastAPI dependency injection for services
- Clean separation between HTTP layer and business logic
- Easy testing with mocked dependencies
- Configuration injected as singletons

### Service Layer Pattern
- TranscriptionService handles business logic
- ValidationService handles input validation
- WorkerPool manages concurrency
- Clear responsibilities per service

### Error Handling Pattern
- Custom exception classes per error type
- Centralized error handling middleware
- HTTP status codes match OpenAI API
- Detailed error messages for debugging

### Middleware Pattern
- Logging middleware for all requests
- CORS middleware for cross-origin requests
- Rate limiting middleware (optional)
- Error handling middleware

---

## Performance Considerations

### Memory Management
- Models loaded once per worker
- File streaming for large audio files
- Garbage collection after each request
- Memory limits enforced

### CPU Optimization
- Multi-process workers utilize all CPU cores
- Async I/O for non-CPU operations
- Efficient audio format parsing
- Minimal data copying

### Latency Optimization
- Model warm-up on worker startup
- Minimal serialization/deserialization
- Efficient JSON response formatting
- HTTP keep-alive support

---

## Security Considerations

### Input Validation
- File size limits enforced
- File format validation
- Duration limits enforced
- MIME type checking

### Data Protection
- No audio data logged
- Temporary files securely deleted
- Memory cleared after processing
- No persistent storage of audio

### Server Security
- CORS configured appropriately
- Request timeout limits
- Rate limiting (if needed)
- Secure headers in responses

---

## Deployment Considerations

### Container Deployment
- Docker image with Python 3.12
- Multi-stage build for size optimization
- Non-root user for security
- Health check endpoint

### Configuration
- Environment variables for secrets
- YAML for static configuration
- Command-line overrides
- Hot-reload in development

### Monitoring
- Health check endpoint at `/health`
- Metrics endpoint at `/metrics` (optional)
- Structured logging to stdout
- Error tracking and alerting

---

## Conclusion

All technology decisions align with the project requirements:
- ✅ OpenAI API compatibility (FastAPI, standard HTTP patterns)
- ✅ High performance (async + multi-worker)
- ✅ Code quality (Clean Architecture, type hints, tests)
- ✅ Observability (structured logging, correlation IDs)
- ✅ Functional integrity (validation, error handling)

Ready for Phase 1: Design and Contracts.

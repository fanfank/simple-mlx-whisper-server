# Implementation Plan: High-Performance HTTP Transcribe API

**Branch**: `001-transcribe-api` | **Date**: 2025-11-22 | **Spec**: [link](../spec.md)
**Input**: Feature specification from `/specs/001-transcribe-api/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a high-performance HTTP server that provides `/v1/audio/transcriptions` endpoint compatible with OpenAI Whisper API. Server uses Python 3.12 with MLX-Whisper for audio transcription, configurable worker system (default 2 workers), and YAML-based configuration. Supports multiple audio formats (MP3, WAV, M4A, etc.) with 25MB/25min limits, handles 10 concurrent requests, and provides structured logging without sensitive data retention.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI (HTTP server), MLX-Whisper (transcription), PyYAML (config), uvicorn (ASGI server)
**Storage**: Temporary file storage during transcription, automatic cleanup post-processing
**Testing**: pytest (unit/integration), requests/testing utilities for API testing
**Target Platform**: Linux server (macOS compatible via MLX)
**Project Type**: Single-service HTTP API
**Performance Goals**: Handle 10 concurrent requests, 30s processing for <5min files, 99.5% uptime
**Constraints**: 25MB file size limit, 25-minute duration limit, 10 concurrent request limit
**Scale/Scope**: Single server instance with configurable worker pool (default 2 workers)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Required Gates

- [x] **I. OpenAI API Compatibility**: `/v1/audio/transcriptions` endpoint matches OpenAI spec exactly - OpenAPI contract defines identical request/response format
- [x] **II. Test-First Development**: TDD approach with 80%+ code coverage - Test structure defined for unit/integration/contract tests
- [x] **III. Functional Integrity**: Audio validation, edge case handling, thread-safe MLX operations - Data model defines validation rules, WorkerPool manages concurrency
- [x] **IV. HTTP Server Best Practices**: Proper status codes, logging, graceful shutdown, connection pooling - FastAPI + Uvicorn workers, structured JSON logging
- [x] **V. Code Quality & Modularity**: Clean architecture, type hints, <10 complexity, minimized dependencies - src/api/, src/services/, src/mlx/ separation, Pydantic models
- [x] **VI. Observability**: Structured logging, correlation IDs, performance metrics, health checks - Log schema defined, /health endpoint, request tracking

**Status**: ✅ All gates pass - Ready for implementation

## Project Structure

### Documentation (this feature)

```text
specs/001-transcribe-api/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── api/                 # HTTP layer (FastAPI routes, handlers)
│   ├── routes.py        # Endpoint definitions
│   ├── middleware.py    # CORS, logging, rate limiting
│   └── models.py        # Request/response models
├── core/                # Configuration and utilities
│   ├── config.py        # YAML config loader
│   ├── logging.py       # Structured logging setup
│   └── exceptions.py    # Custom exception classes
├── services/            # Business logic layer
│   ├── transcription.py # Transcription service
│   ├── validation.py    # File validation
│   └── workers.py       # Worker pool management
├── mlx/                 # MLX integration
│   ├── whisper.py       # MLX Whisper wrapper
│   └── model_manager.py # Model loading/unloading
└── main.py              # Application entry point

config/
├── config.yaml          # Server configuration (worker count, etc.)
└── .env.example         # Environment variable template

tests/
├── unit/                # Unit tests for individual components
│   ├── test_config.py
│   ├── test_validation.py
│   ├── test_transcription.py
│   └── test_whisper.py
├── integration/         # End-to-end API tests
│   └── test_api.py
├── contract/            # OpenAI API compatibility tests
│   └── test_compatibility.py
└── fixtures/            # Test audio files

scripts/
├── start.sh             # Server startup script
└── run_tests.sh         # Test runner

Dockerfile              # Container definition
requirements.txt        # Python dependencies
pyproject.toml          # Python project config
README.md               # Project documentation
```

**Structure Decision**: Single project structure with clear separation: HTTP API layer (api/), business logic (services/), MLX integration (mlx/), and configuration (core/). Follows Clean Architecture pattern with dependency inversion.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| No violations | N/A | N/A |

All design decisions align with simpler alternatives. No complexity violations to justify.

**Justifications**:
- **Multi-worker design**: Required for MLX CPU-bound operations and concurrency limits
- **Separate service layers**: Standard Clean Architecture, enables testability and maintainability
- **Structured logging**: Industry standard for production APIs, minimal overhead
- **YAML configuration**: Standard practice, enables configuration without code changes

**Simpler alternatives rejected**:
- Single worker: Cannot meet 10 concurrent request requirement
- No service separation: Violates constitution Principle V (Code Quality)
- Basic logging: Violates constitution Principle VI (Observability)
- Hard-coded config: Poor operational flexibility

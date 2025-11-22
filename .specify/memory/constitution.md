<!--
Sync Impact Report - Constitution v1.0.0
========================================

Version Change: 0.1.0 → 1.0.0 (MAJOR - Initial ratification)
- New constitution for Simple MLX Whisper Server project

Modified Principles:
- N/A - Initial creation

Added Sections:
- Core Principles (6 principles total):
  I. OpenAI API Compatibility (NON-NEGOTIABLE)
  II. Test-First Development (NON-NEGOTIABLE)
  III. Functional Integrity
  IV. HTTP Server Best Practices
  V. Code Quality & Modularity
  VI. Observability & Monitoring
- Testing Standards (Unit, Integration, Contract, Performance)
- Code Quality Standards (Architecture, Error Handling, Security, Documentation)
- Development Workflow (Feature development, Code review, Quality gates)
- Governance (Amendment process, compliance requirements)

Removed Sections:
- N/A - Initial creation

Templates Updated:
✅ .specify/templates/plan-template.md - No changes needed
✅ .specify/templates/spec-template.md - No changes needed
✅ .specify/templates/tasks-template.md - No changes needed
✅ .specify/templates/checklist-template.md - No changes needed

Follow-up TODOs:
- None - All placeholders filled

Ratification: 2025-11-22 (initial adoption)
-->

# Simple MLX Whisper Server Constitution
<!-- A RESTful HTTP server implementing OpenAI Whisper API compatibility using MLX framework -->

## Core Principles

### I. OpenAI API Compatibility (NON-NEGOTIABLE)
All HTTP endpoints MUST match OpenAI Whisper API specification exactly. The `/v1/audio/transcriptions` endpoint MUST accept identical request/response formats, including multipart form data, HTTP headers, and JSON response structure. No deviations permitted unless explicitly adding OpenAI-compatible extensions.

**Rationale**: Ensures drop-in compatibility with existing OpenAI Whisper clients and tooling, enabling zero-code migration for users.

### II. Test-First Development (NON-NEGOTIABLE)
TDD mandatory: Unit tests written → API contracts defined → Tests fail → Implementation → Tests pass → Refactor. Minimum 80% code coverage required. All features and bug fixes MUST have corresponding tests before implementation.

**Rationale**: Guarantees functional integrity and enables confident refactoring. MLX integration requires careful testing due to hardware-specific behavior.

### III. Functional Integrity
All transcription operations MUST produce deterministic results for identical inputs. Audio processing MUST validate file formats, handle edge cases (corrupt files, unsupported codecs), and fail gracefully with meaningful error messages. Model loading and inference MUST be thread-safe and resource-managed.

**Rationale**: MLX Whisper requires strict input validation and proper resource management to prevent system instability and ensure reliable transcription quality.

### IV. HTTP Server Best Practices
RESTful design with proper HTTP status codes, idempotency where applicable, request/response logging with correlation IDs, graceful shutdown handling, and connection pooling. Middleware for authentication, rate limiting, and request validation MUST be intercept-based and testable.

**Rationale**: Ensures production-ready reliability, observability, and scalability. HTTP server patterns enable horizontal scaling and monitoring.

### V. Code Quality & Modularity
Clean Architecture enforced: clear separation between HTTP layer, service layer, and MLX integration. Type hints required for all public APIs. Documentation strings for all modules, classes, and functions. Cyclomatic complexity MUST NOT exceed 10 per function. Dependencies minimized and explicitly version-constrained.

**Rationale**: MLX integration is complex; modular design enables testing individual components and swapping implementations. Type safety prevents runtime errors in MLX operations.

### VI. Observability & Monitoring
Structured logging with JSON format, correlation IDs for request tracing, performance metrics for inference timing and memory usage, health check endpoints for load balancers, and error tracking with stack traces. All logs MUST be debuggable in production.

**Rationale**: Audio transcription is compute-intensive; observability enables performance tuning, capacity planning, and rapid debugging of MLX-specific issues.

## Testing Standards

**Unit Testing**: Every module, class, and function MUST have corresponding unit tests. Mock MLX dependencies for isolation. Test audio file parsing, validation logic, and error handling independently.

**Integration Testing**: Required for end-to-end transcription pipeline, HTTP request/response handling, concurrent request processing, and file upload/download workflows. Use real audio samples for validation.

**Contract Testing**: API schema validation against OpenAI specification. Response format verification, status code compliance, and header validation. MUST include compatibility tests with OpenAI client libraries.

**Performance Testing**: Benchmark inference speed, memory usage, and throughput. Test with various audio lengths and formats. Establish baseline metrics and regression detection.

**Rationale**: MLX hardware acceleration requires thorough testing across different scenarios to ensure functional integrity under various conditions.

## Code Quality Standards

**Architecture**: Layered architecture with strict dependencies: HTTP handlers → Services → MLX Whisper integration. No circular dependencies. Dependency injection for testability.

**Error Handling**: All errors MUST be handled gracefully with appropriate HTTP status codes (400, 413, 422, 500, 503). Error responses MUST include machine-parseable error codes and human-readable messages.

**Security**: Input validation for all audio files (size limits, format verification). Rate limiting to prevent resource exhaustion. Secure headers in all responses. No sensitive data in logs.

**Documentation**: API documentation using OpenAPI/Swagger format. Architecture diagrams for system design. Inline comments only for complex MLX operations. README with setup, testing, and deployment instructions.

**Rationale**: HTTP servers face internet-facing security risks; strict validation and security practices prevent attacks while maintaining performance.

## Development Workflow

**Feature Development**: Create feature branch → Write tests → Implement → Run full test suite → Code review → Merge to main → Deploy to staging → Run integration tests → Deploy to production.

**Code Review**: All code MUST be reviewed by at least one other developer. Review checklist includes: test coverage, error handling, performance implications, security considerations, and code clarity.

**Quality Gates**: CI/CD pipeline MUST pass before merge: linting, type checking, unit tests (100% pass), coverage check (≥80%), integration tests, and security scan.

**Rationale**: Enforces discipline and catches issues early. MLX integration benefits from peer review to catch hardware-specific pitfalls.

## Governance

This constitution supersedes all other development practices. Amendments require:
1. Documented proposal with rationale
2. Impact analysis on existing code and tests
3. Version bump following semantic versioning (MAJOR.MINOR.PATCH)
4. Approval from project maintainers
5. Migration plan for breaking changes

All PRs and code reviews MUST verify compliance with these principles. Complex solutions MUST be justified with documented rationale and simpler alternatives rejected in writing.

**Version**: 1.0.0 | **Ratified**: 2025-11-22 | **Last Amended**: 2025-11-22

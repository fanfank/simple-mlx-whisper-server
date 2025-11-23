"""API routes for the MLX Whisper Server."""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse

from ..api.models import (
    TranscribeRequest,
    TranscribeResponse,
    VerboseTranscribeResponse,
    ErrorResponse,
    HealthResponse
)
from ..core.exceptions import (
    TranscribeError,
    FileTooLargeError,
    FileTooLongError,
    InvalidFileFormatError,
    CorruptedAudioFileError,
    ServerBusyError
)
from ..core.logging import get_logger
from ..core.config import config

logger = get_logger(__name__)

# Create router
router = APIRouter()


def _dump_audio_file(
    audio_data: bytes,
    original_filename: str | None,
    dump_audio_dir: str,
    request_id: str
) -> None:
    """Persist uploaded audio to a configured dump directory with timestamp prefix."""
    if not dump_audio_dir:
        return

    dump_dir_path = Path(dump_audio_dir)
    safe_filename = Path(original_filename or "audio.mp3").name or "audio.mp3"
    timestamp_prefix = datetime.now().strftime("%Y%m%d%H%M%S")
    dump_path = dump_dir_path / f"{timestamp_prefix}_{safe_filename}"

    try:
        dump_dir_path.mkdir(parents=True, exist_ok=True)
        dump_path.write_bytes(audio_data)
        logger.info(
            "Saved uploaded audio to dump directory",
            dump_path=str(dump_path),
            request_id=request_id
        )
    except Exception as e:
        logger.error(
            "Failed to save uploaded audio",
            dump_dir=str(dump_dir_path),
            error=str(e),
            request_id=request_id
        )
        error = TranscribeError("Failed to save uploaded audio", "server_error", 500, request_id)
        raise HTTPException(status_code=500, detail=error.to_dict())


@router.post(
    "/v1/audio/transcriptions",
    response_model=TranscribeResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        413: {"model": ErrorResponse, "description": "Payload too large"},
        422: {"model": ErrorResponse, "description": "Unprocessable entity"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        503: {"model": ErrorResponse, "description": "Service unavailable"}
    },
    tags=["Audio"]
)
async def transcribe_audio(
    request: Request,
    file: UploadFile = File(..., description="Audio file to transcribe"),
    model: str = "mlx-community/whisper-large-v3-mlx",
    language: str | None = None,
    response_format: str = "json",
    temperature: float = 0.0
) -> Dict[str, Any]:
    """Transcribe an audio file to text.

    Compatible with OpenAI Whisper API.
    """
    # Get request ID from logging context
    request_id = logger._context.get("request_id", "unknown")

    try:
        cfg = config.load()
        logger.info(
            "Received transcription request",
            filename=file.filename,
            content_type=file.content_type,
            model=model,
            language=language,
            response_format=response_format,
            request_id=request_id
        )

        # Read file content
        audio_data = await file.read()

        # Check if file is empty
        if not audio_data:
            raise InvalidFileFormatError("empty", cfg.transcription.allowed_formats, request_id)

        filename_for_processing = file.filename or "audio.mp3"
        _dump_audio_file(audio_data, filename_for_processing, cfg.transcription.dump_audio_dir, request_id)

        # Create parameters dict
        parameters = {
            "model": model,
            "language": language,
            "response_format": response_format,
            "temperature": temperature
        }

        # Import transcription service
        from ..services.validation import AudioValidator
        from ..mlx.model_manager import ModelManager
        from ..services.transcription import TranscriptionService

        # Create service instances
        validator = AudioValidator(
            cfg.transcription.max_file_size,
            cfg.transcription.max_duration,
            cfg.transcription.allowed_formats
        )
        model_manager = ModelManager(cfg.transcription.model, cfg.transcription.use_modelscope)
        transcription_service = TranscriptionService(validator, model_manager)

        # Run transcription
        result = await transcription_service.transcribe(
            audio_data,
            filename_for_processing,
            parameters,
            request_id
        )

        logger.info(
            "Transcription successful",
            text_length=len(result.get("text", "")),
            request_id=request_id
        )

        # Return based on response format
        if response_format == "text":
            return JSONResponse(content={"text": result.get("text", "")})

        return result

    except (FileTooLargeError, FileTooLongError, InvalidFileFormatError, CorruptedAudioFileError, ServerBusyError) as e:
        # Handle expected errors
        logger.warning(
            "Transcription request failed",
            error_type=e.error_type,
            status_code=e.status_code,
            request_id=request_id
        )
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())

    except TranscribeError as e:
        # Handle transcription errors
        logger.error(
            "Transcription error",
            error=str(e.message),
            request_id=request_id
        )
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        # Handle unexpected errors
        logger.error(
            "Unexpected error",
            error=str(e),
            exc_info=True,
            request_id=request_id
        )
        error = TranscribeError("Internal server error", "server_error", 500, request_id)
        raise HTTPException(status_code=500, detail=error.to_dict())


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"]
)
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    # This is a simplified health check
    # In a real implementation, you would check:
    # - Model loading status
    # - Worker pool status
    # - Memory usage
    # - etc.

    return {
        "status": "healthy",
        "workers": {
            "total": config.load().server.workers,
            "active": 0,
            "available": config.load().server.workers
        },
        "model_loaded": True,
        "uptime_seconds": 0  # Would calculate actual uptime
    }


@router.get(
    "/",
    summary="Root endpoint"
)
async def root():
    """Root endpoint with API information."""
    return {
        "name": "MLX Whisper Server",
        "version": "0.1.0",
        "description": "High-performance HTTP server for audio transcription using MLX-Whisper",
        "openai_compatible": True,
        "endpoints": {
            "transcribe": "/v1/audio/transcriptions",
            "health": "/health",
            "docs": "/docs",
            "openapi": "/openapi.json"
        }
    }

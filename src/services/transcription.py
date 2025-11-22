"""Transcription service for audio transcription."""

import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from mlx_whisper.whisper import Whisper

from ..core.exceptions import TranscriptionError
from ..core.logging import get_logger

logger = get_logger(__name__)


class TranscriptionService:
    """Service for handling audio transcription requests."""

    def __init__(self, validator: Any, model_manager: Any):
        """Initialize transcription service.

        Args:
            validator: File validator instance
            model_manager: Model manager instance
        """
        self.validator = validator
        self.model_manager = model_manager

    async def transcribe(
        self,
        audio_data: bytes,
        filename: str,
        parameters: Dict[str, Any],
        request_id: str
    ) -> Dict[str, Any]:
        """Transcribe audio data.

        Args:
            audio_data: Raw audio data
            filename: Original filename
            parameters: Transcription parameters
            request_id: Request ID for tracking

        Returns:
            Transcription result

        Raises:
            TranscriptionError: If transcription fails
        """
        logger.info(
            "Starting transcription request",
            filename=filename,
            size_bytes=len(audio_data),
            request_id=request_id
        )

        # Create temporary file
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp:
                tmp.write(audio_data)
                temp_path = tmp.name

            # Validate file
            logger.debug("Validating file", request_id=request_id)
            format, duration = self.validator.validate_file(temp_path, len(audio_data))
            logger.debug(
                "File validated",
                format=format,
                duration=duration,
                request_id=request_id
            )

            # Get model
            logger.debug("Loading model", request_id=request_id)
            model: Any = self.model_manager.get_model()

            # Run transcription
            logger.info("Running transcription", request_id=request_id)
            result = model.transcribe(
                temp_path,
                path_or_hf_repo=self.model_manager.get_model_name(),
                fp16=True,
                #language=parameters.get("language"),
                #response_format=parameters.get("response_format", "json"),
                #temperature=parameters.get("temperature", 0.0)
            )

            # Add duration from validation
            if isinstance(result, dict) and "duration" not in result:
                result["duration"] = duration

            logger.info(
                "Transcription completed",
                text_length=len(result.get("text", "")),
                request_id=request_id
            )

            return result

        except Exception as e:
            logger.error(
                "Transcription failed",
                filename=filename,
                error=str(e),
                request_id=request_id
            )
            raise TranscriptionError(str(e), request_id=request_id)

        finally:
            # Cleanup temporary file
            if temp_path and Path(temp_path).exists():
                try:
                    Path(temp_path).unlink()
                    logger.debug("Temporary file cleaned up", request_id=request_id)
                except Exception as e:
                    logger.warning(
                        "Failed to cleanup temporary file",
                        file_path=temp_path,
                        error=str(e),
                        request_id=request_id
                    )

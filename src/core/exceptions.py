"""Custom exceptions for the MLX Whisper Server."""

from typing import Any, Dict, Optional


class TranscribeError(Exception):
    """Base exception for transcription errors."""

    def __init__(
        self,
        message: str,
        error_type: str,
        status_code: int,
        request_id: Optional[str] = None
    ):
        """Initialize transcription error.

        Args:
            message: Human-readable error message
            error_type: Machine-readable error type
            status_code: HTTP status code to return
            request_id: Optional request ID for correlation
        """
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        self.request_id = request_id

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON response."""
        return {
            "error": {
                "message": self.message,
                "type": self.error_type,
                "code": str(self.status_code)
            },
            "request_id": self.request_id
        }


class FileTooLargeError(TranscribeError):
    """Raised when uploaded file exceeds size limit."""

    def __init__(self, file_size: int, max_size: int, request_id: Optional[str] = None):
        """Initialize file too large error.

        Args:
            file_size: Actual file size in bytes
            max_size: Maximum allowed size in bytes
            request_id: Optional request ID
        """
        from ..core.logging import get_logger
        logger = get_logger(__name__)
        logger.warning(
            "File too large",
            file_size=file_size,
            max_size=max_size,
            request_id=request_id
        )

        message = f"Audio file too large: {file_size / (1024*1024):.1f}MB (max: {max_size / (1024*1024):.1f}MB)"
        super().__init__(message, "file_too_large", 413, request_id)


class FileTooLongError(TranscribeError):
    """Raised when audio duration exceeds limit."""

    def __init__(self, duration: float, max_duration: float, request_id: Optional[str] = None):
        """Initialize file too long error.

        Args:
            duration: Actual audio duration in seconds
            max_duration: Maximum allowed duration in seconds
            request_id: Optional request ID
        """
        from ..core.logging import get_logger
        logger = get_logger(__name__)
        logger.warning(
            "Audio file too long",
            duration=duration,
            max_duration=max_duration,
            request_id=request_id
        )

        message = f"Audio file too long: {duration / 60:.1f} minutes (max: {max_duration / 60:.1f} minutes)"
        super().__init__(message, "file_too_long", 413, request_id)


class InvalidFileFormatError(TranscribeError):
    """Raised when file format is not supported."""

    def __init__(self, format: str, allowed_formats: list[str], request_id: Optional[str] = None):
        """Initialize invalid format error.

        Args:
            format: File format that was rejected
            allowed_formats: List of allowed formats
            request_id: Optional request ID
        """
        message = f"Unsupported file format: {format}. Allowed formats: {', '.join(allowed_formats)}"
        super().__init__(message, "invalid_file_format", 400, request_id)


class CorruptedAudioFileError(TranscribeError):
    """Raised when audio file is corrupted or unreadable."""

    def __init__(self, reason: str, request_id: Optional[str] = None):
        """Initialize corrupted file error.

        Args:
            reason: Why the file is considered corrupted
            request_id: Optional request ID
        """
        message = f"Invalid audio file: {reason}"
        super().__init__(message, "invalid_audio_file", 422, request_id)


class ServerBusyError(TranscribeError):
    """Raised when server is overloaded (too many concurrent requests)."""

    def __init__(self, max_concurrent: int, request_id: Optional[str] = None):
        """Initialize server busy error.

        Args:
            max_concurrent: Maximum concurrent requests
            request_id: Optional request ID
        """
        message = f"Server busy. Maximum {max_concurrent} concurrent requests."
        super().__init__(message, "server_busy", 503, request_id)


class TranscriptionError(TranscribeError):
    """Raised when transcription processing fails."""

    def __init__(self, reason: str, request_id: Optional[str] = None):
        """Initialize transcription error.

        Args:
            reason: Why transcription failed
            request_id: Optional request ID
        """
        message = f"Transcription failed: {reason}"
        super().__init__(message, "server_error", 500, request_id)


class ModelLoadError(TranscribeError):
    """Raised when MLX model fails to load."""

    def __init__(self, model_name: str, reason: str, request_id: Optional[str] = None):
        """Initialize model load error.

        Args:
            model_name: Name of model that failed to load
            reason: Why model loading failed
            request_id: Optional request ID
        """
        message = f"Failed to load model {model_name}: {reason}"
        super().__init__(message, "model_load_error", 500, request_id)


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""

    pass

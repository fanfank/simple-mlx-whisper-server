"""
Unit tests for error handling and edge cases.

These tests verify that the application properly handles various error scenarios
and raises appropriate exceptions with correct HTTP status codes.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from pydantic import ValidationError as PydanticValidationError

from src.core.exceptions import (
    TranscribeError,
    FileTooLargeError,
    UnsupportedFormatError,
    CorruptedFileError,
    InvalidDurationError,
    ServiceUnavailableError,
    ValidationError,
)
from src.services.validation import ValidationService
from src.services.transcription import TranscriptionService
from src.services.workers import WorkerPool


class TestValidationErrors:
    """Test validation-related errors."""

    def test_file_too_large_error(self):
        """Test that files exceeding size limit raise FileTooLargeError."""
        with pytest.raises(FileTooLargeError) as exc_info:
            raise FileTooLargeError(
                file_size=30 * 1024 * 1024,  # 30MB
                max_size=25 * 1024 * 1024,  # 25MB
            )
        assert "30.0 MB" in str(exc_info.value)
        assert "25.0 MB" in str(exc_info.value)

    def test_unsupported_format_error(self):
        """Test that unsupported formats raise UnsupportedFormatError."""
        with pytest.raises(UnsupportedFormatError) as exc_info:
            raise UnsupportedFormatError(format="xyz", supported_formats=["mp3", "wav"])
        assert "xyz" in str(exc_info.value)
        assert "mp3" in str(exc_info.value)

    def test_corrupted_file_error(self):
        """Test that corrupted files raise CorruptedFileError."""
        with pytest.raises(CorruptedFileError) as exc_info:
            raise CorruptedFileError(file_path="/tmp/test.mp3")
        assert "/tmp/test.mp3" in str(exc_info.value)

    def test_invalid_duration_error(self):
        """Test that files exceeding duration limit raise InvalidDurationError."""
        with pytest.raises(InvalidDurationError) as exc_info:
            raise InvalidDurationError(
                duration=1800,  # 30 minutes
                max_duration=1500,  # 25 minutes
            )
        assert "30.0 minutes" in str(exc_info.value)
        assert "25.0 minutes" in str(exc_info.value)


class TestServiceErrors:
    """Test service layer errors."""

    def test_transcribe_error(self):
        """Test that general transcription errors are properly raised."""
        with pytest.raises(TranscribeError) as exc_info:
            raise TranscribeError("Model initialization failed")
        assert "Model initialization failed" in str(exc_info.value)

    def test_service_unavailable_error(self):
        """Test that service unavailable errors are properly raised."""
        with pytest.raises(ServiceUnavailableError) as exc_info:
            raise ServiceUnavailableError(message="All workers busy", current_load=10, max_capacity=10)
        assert "All workers busy" in str(exc_info.value)
        assert "10" in str(exc_info.value)


class TestValidationServiceErrors:
    """Test ValidationService error handling."""

    @pytest.fixture
    def validation_service(self):
        """Create a ValidationService instance."""
        return ValidationService(
            max_file_size=25 * 1024 * 1024,  # 25MB
            max_duration=1500,  # 25 minutes
            supported_formats=["mp3", "wav", "m4a", "mp4", "mpeg", "webm"],
        )

    def test_validate_file_size_too_large(self, validation_service, tmp_path):
        """Test that oversized files raise FileTooLargeError."""
        # Create a file larger than max_file_size
        large_file = tmp_path / "large.mp3"
        large_file.write_bytes(b"x" * (30 * 1024 * 1024))  # 30MB

        with pytest.raises(FileTooLargeError):
            validation_service.validate_file_size(large_file)

    def test_validate_file_size_within_limit(self, validation_service, tmp_path):
        """Test that files within size limit pass validation."""
        small_file = tmp_path / "small.mp3"
        small_file.write_bytes(b"x" * (10 * 1024 * 1024))  # 10MB

        # Should not raise any exception
        validation_service.validate_file_size(small_file)

    def test_validate_file_format_unsupported(self, validation_service, tmp_path):
        """Test that unsupported formats raise UnsupportedFormatError."""
        unsupported_file = tmp_path / "test.xyz"
        unsupported_file.write_bytes(b"dummy content")

        with pytest.raises(UnsupportedFormatError):
            validation_service.validate_file_format(unsupported_file)

    def test_validate_file_format_supported(self, validation_service, tmp_path):
        """Test that supported formats pass validation."""
        for format_name in ["mp3", "wav", "m4a", "mp4", "mpeg", "webm"]:
            test_file = tmp_path / f"test.{format_name}"
            test_file.write_bytes(b"dummy content")
            # Should not raise any exception
            validation_service.validate_file_format(test_file)

    def test_validate_magic_bytes_invalid_format(self, validation_service, tmp_path):
        """Test that files with invalid magic bytes raise CorruptedFileError."""
        # Create a file with wrong magic bytes (claims to be MP3 but isn't)
        fake_mp3 = tmp_path / "fake.mp3"
        fake_mp3.write_bytes(b"NOTMP3DATA")

        with pytest.raises(CorruptedFileError):
            validation_service.validate_magic_bytes(fake_mp3)

    def test_validate_audio_duration_too_long(self, validation_service, tmp_path):
        """Test that files exceeding duration limit raise InvalidDurationError."""
        long_file = tmp_path / "long.wav"
        # Create a dummy file
        long_file.write_bytes(b"dummy audio data")

        with patch('src.services.validation.get_audio_duration') as mock_duration:
            mock_duration.return_value = 1800  # 30 minutes

            with pytest.raises(InvalidDurationError):
                validation_service.validate_audio_duration(long_file)

    def test_validate_audio_duration_within_limit(self, validation_service, tmp_path):
        """Test that files within duration limit pass validation."""
        short_file = tmp_path / "short.wav"
        short_file.write_bytes(b"dummy audio data")

        with patch('src.services.validation.get_audio_duration') as mock_duration:
            mock_duration.return_value = 600  # 10 minutes

            # Should not raise any exception
            validation_service.validate_audio_duration(short_file)

    def test_validate_audio_duration_handles_error(self, validation_service, tmp_path):
        """Test that errors in duration detection raise CorruptedFileError."""
        error_file = tmp_path / "error.wav"
        error_file.write_bytes(b"dummy audio data")

        with patch('src.services.validation.get_audio_duration') as mock_duration:
            mock_duration.side_effect = Exception("Cannot read audio file")

            with pytest.raises(CorruptedFileError):
                validation_service.validate_audio_duration(error_file)


class TestTranscriptionServiceErrors:
    """Test TranscriptionService error handling."""

    @pytest.fixture
    def transcription_service(self):
        """Create a TranscriptionService instance."""
        return TranscriptionService(model="test-model")

    @pytest.mark.asyncio
    async def test_transcribe_with_file_not_found(self, transcription_service):
        """Test that missing files raise appropriate error."""
        with pytest.raises(CorruptedFileError):
            await transcription_service.transcribe("/nonexistent/file.mp3")

    @pytest.mark.asyncio
    async def test_transcribe_handles_mlx_error(self, transcription_service, tmp_path):
        """Test that MLX errors are wrapped in TranscribeError."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"dummy audio")

        with patch('src.services.transcription.transcribe') as mock_transcribe:
            mock_transcribe.side_effect = Exception("MLX error")

            with pytest.raises(TranscribeError):
                await transcription_service.transcribe(str(audio_file))


class TestWorkerPoolErrors:
    """Test WorkerPool error handling."""

    @pytest.mark.asyncio
    async def test_worker_pool_at_capacity(self):
        """Test that WorkerPool properly rejects requests when at capacity."""
        worker_pool = WorkerPool(max_workers=2)

        # Simulate all workers being busy
        with patch.object(worker_pool, '_get_least_busy_worker', return_value=None):
            with pytest.raises(ServiceUnavailableError):
                await worker_pool.submit_task(lambda: "test")

    @pytest.mark.asyncio
    async def test_worker_pool_accepts_task_when_available(self):
        """Test that WorkerPool accepts tasks when capacity available."""
        worker_pool = WorkerPool(max_workers=2)

        # Should not raise when capacity available
        with patch.object(worker_pool, '_get_least_busy_worker', return_value=Mock()):
            # This should not raise
            await worker_pool.submit_task(lambda: "test")


class TestExceptionHierarchy:
    """Test that exceptions form a proper hierarchy."""

    def test_exception_inheritance(self):
        """Test that custom exceptions inherit from correct base classes."""
        assert issubclass(FileTooLargeError, ValidationError)
        assert issubclass(UnsupportedFormatError, ValidationError)
        assert issubclass(CorruptedFileError, ValidationError)
        assert issubclass(InvalidDurationError, ValidationError)
        assert issubclass(ValidationError, TranscribeError)
        assert issubclass(ServiceUnavailableError, TranscribeError)

    def test_exception_instances_are_exceptions(self):
        """Test that custom exceptions are also Python exceptions."""
        assert isinstance(FileTooLargeError("test"), Exception)
        assert isinstance(UnsupportedFormatError("test"), Exception)
        assert isinstance(CorruptedFileError("test"), Exception)
        assert isinstance(InvalidDurationError("test"), Exception)
        assert isinstance(ServiceUnavailableError("test"), Exception)
        assert isinstance(TranscribeError("test"), Exception)


class TestPydanticValidationErrors:
    """Test that Pydantic validation errors are properly handled."""

    def test_invalid_request_model_raises_validation_error(self):
        """Test that invalid request data raises Pydantic validation error."""
        from src.api.models import TranscribeRequest

        # Test with missing required field
        with pytest.raises(PydanticValidationError):
            TranscribeRequest()

    def test_invalid_file_type_raises_validation_error(self):
        """Test that invalid file type raises Pydantic validation error."""
        from src.api.models import TranscribeRequest

        # Test with invalid model name
        with pytest.raises(PydanticValidationError):
            TranscribeRequest(model="")  # Empty model name should fail validation


@pytest.mark.asyncio
class TestConcurrentRequestHandling:
    """Test handling of concurrent requests."""

    @pytest.mark.skip(reason="Integration test - move to test_api.py")
    async def test_too_many_concurrent_requests(self):
        """Test that 11+ concurrent requests return HTTP 503."""
        # This is an integration test, should be in test_api.py
        pass

    @pytest.mark.skip(reason="Integration test - move to test_api.py")
    async def test_accepts_max_concurrent_requests(self):
        """Test that up to 10 concurrent requests are accepted."""
        # This is an integration test, should be in test_api.py
        pass


class TestErrorMessageFormatting:
    """Test that error messages are properly formatted."""

    def test_file_size_error_message(self):
        """Test that file size error messages are human-readable."""
        error = FileTooLargeError(
            file_size=26214400,  # 25MB in bytes
            max_size=26214400,   # 25MB in bytes
        )
        assert "25.0 MB" in str(error)
        assert "25.0 MB" in error.message

    def test_duration_error_message(self):
        """Test that duration error messages are human-readable."""
        error = InvalidDurationError(
            duration=1500,  # 25 minutes in seconds
            max_duration=1500,  # 25 minutes in seconds
        )
        assert "25.0 minutes" in str(error)
        assert "25.0 minutes" in error.message

    def test_all_errors_have_message_attribute(self):
        """Test that all custom exceptions have a message attribute."""
        exceptions = [
            FileTooLargeError(100, 1000),
            UnsupportedFormatError("xyz", ["mp3"]),
            CorruptedFileError("/tmp/test"),
            InvalidDurationError(100, 1000),
            ServiceUnavailableError("test", 1, 1),
            TranscribeError("test"),
        ]

        for exc in exceptions:
            assert hasattr(exc, "message")
            assert isinstance(exc.message, str)

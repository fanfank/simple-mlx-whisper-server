"""Tests for TranscriptionService."""

import pytest
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch

from src.services.transcription import TranscriptionService
from src.core.exceptions import TranscriptionError


class TestTranscriptionService:
    """Test TranscriptionService class."""

    @pytest.fixture
    def mock_validator(self):
        """Create mock validator."""
        return MagicMock()

    @pytest.fixture
    def mock_model_manager(self):
        """Create mock model manager."""
        return MagicMock()

    @pytest.fixture
    def transcription_service(self, mock_validator, mock_model_manager):
        """Create transcription service."""
        return TranscriptionService(mock_validator, mock_model_manager)

    def test_init(self, transcription_service, mock_validator, mock_model_manager):
        """Test service initialization."""
        assert transcription_service.validator == mock_validator
        assert transcription_service.model_manager == mock_model_manager

    @pytest.mark.asyncio
    async def test_transcribe_success(self, transcription_service, mock_validator, mock_model_manager):
        """Test successful transcription."""
        # Setup mocks
        mock_validator.validate_file.return_value = ("mp3", 120.0)
        mock_model_manager.get_model.return_value = MagicMock()

        with patch("src.services.transcription.MLXWhisper") as mock_mlx:
            mock_whisper = MagicMock()
            mock_whisper.transcribe.return_value = {
                "text": "Test transcription",
                "language": "en",
                "duration": 120.0,
                "task": "transcribe"
            }
            mock_mlx.return_value = mock_whisper

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(b"test audio data")
                f.flush()

                result = await transcription_service.transcribe(
                    b"test audio data",
                    "test.mp3",
                    {"model": "test-model", "language": "en"},
                    "test-request-id"
                )

                assert result["text"] == "Test transcription"
                assert result["language"] == "en"
                assert result["duration"] == 120.0

        Path(f.name).unlink()

    @pytest.mark.asyncio
    async def test_transcribe_with_response_formats(self, transcription_service, mock_validator, mock_model_manager):
        """Test transcription with different response formats."""
        # Setup mocks
        mock_validator.validate_file.return_value = ("wav", 60.0)
        mock_model_manager.get_model.return_value = MagicMock()

        with patch("src.services.transcription.MLXWhisper") as mock_mlx:
            mock_whisper = MagicMock()
            mock_whisper.transcribe.return_value = {"text": "Transcribed text"}
            mock_mlx.return_value = mock_whisper

            # Test text format
            result = await transcription_service.transcribe(
                b"audio",
                "audio.wav",
                {"response_format": "text"},
                "req-id"
            )
            assert result == {"text": "Transcribed text"}

            # Test json format
            result = await transcription_service.transcribe(
                b"audio",
                "audio.wav",
                {"response_format": "json"},
                "req-id"
            )
            # Should add duration
            assert result["text"] == "Transcribed text"
            assert "duration" in result

        Path("audio.wav").unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_transcribe_failure(self, transcription_service, mock_validator, mock_model_manager):
        """Test transcription failure."""
        # Setup mocks to raise error
        mock_validator.validate_file.side_effect = Exception("Validation failed")

        with pytest.raises(TranscriptionError) as exc_info:
            await transcription_service.transcribe(
                b"audio",
                "audio.mp3",
                {},
                "req-id"
            )

        assert exc_info.value.status_code == 500

    def test_transcribe_cleanup_temp_file(self, transcription_service, mock_validator, mock_model_manager):
        """Test that temporary files are cleaned up."""
        # Setup mocks
        mock_validator.validate_file.return_value = ("mp3", 60.0)
        mock_model_manager.get_model.return_value = MagicMock()

        with patch("src.services.transcription.MLXWhisper"):
            with patch("src.services.transcription.MLXWhisper"):
                # Create a temp file that should be cleaned up
                import asyncio

                async def run_test():
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                        temp_path = f.name
                        f.write(b"test")

                    await transcription_service.transcribe(
                        b"test",
                        "test.mp3",
                        {},
                        "req-id"
                    )

                    # File should be deleted
                    assert not Path(temp_path).exists()

                asyncio.run(run_test())

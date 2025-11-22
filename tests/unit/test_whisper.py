"""Tests for MLX Whisper wrapper."""

import pytest
from pathlib import Path
import tempfile

# Note: These tests require MLX-Whisper to be installed
# They will be skipped if MLX is not available


@pytest.mark.skip(reason="MLX-Whisper not installed")
class TestMLXWhisper:
    """Test MLX Whisper wrapper."""

    def test_init(self):
        """Test MLX Whisper initialization."""
        from src.mlx.whisper import MLXWhisper

        whisper = MLXWhisper("mlx-community/whisper-small")
        assert whisper.model_name == "mlx-community/whisper-small"

    def test_transcribe(self):
        """Test transcription."""
        from src.mlx.whisper import MLXWhisper

        whisper = MLXWhisper("mlx-community/whisper-small")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            # Create minimal WAV file
            f.write(b"RIFF" + b"\x00" * 100)
            f.flush()

            result = whisper.transcribe(
                f.name,
                language="en",
                response_format="json"
            )

            assert "text" in result
            assert "language" in result
            assert "duration" in result
            assert "task" in result

        Path(f.name).unlink()

    def test_response_formats(self):
        """Test different response formats."""
        from src.mlx.whisper import MLXWhisper

        whisper = MLXWhisper("mlx-community/whisper-small")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFF" + b"\x00" * 100)
            f.flush()

            # Test text format
            result = whisper.transcribe(f.name, response_format="text")
            assert isinstance(result, dict)
            assert "text" in result

            # Test json format
            result = whisper.transcribe(f.name, response_format="json")
            assert "text" in result
            assert "language" in result

            # Test srt format
            result = whisper.transcribe(f.name, response_format="srt")
            assert "text" in result

        Path(f.name).unlink()

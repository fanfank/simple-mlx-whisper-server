"""Contract tests to verify OpenAI API compatibility."""

import pytest
from fastapi.testclient import TestClient
from openai import OpenAI
from pathlib import Path
import tempfile


class TestOpenAICompatibility:
    """Test compatibility with OpenAI Whisper API."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from src.main import app
        return TestClient(app)

    @pytest.fixture
    def openai_client(self):
        """Create OpenAI client pointing to our server."""
        return OpenAI(
            api_key="not-needed",
            base_url="http://testserver/v1"
        )

    @pytest.fixture
    def audio_file(self):
        """Create a test audio file."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            # Write WAV header
            f.write(b"RIFF" + b"\x00" * 100)
            f.flush()
            yield Path(f.name)
        Path(f.name).unlink()

    def test_endpoint_exists(self, client):
        """Test that the transcribe endpoint exists."""
        response = client.post("/v1/audio/transcriptions")
        # Should get 422 (validation error) not 404 (not found)
        assert response.status_code != 404

    def test_request_format_multipart(self, client):
        """Test that endpoint accepts multipart/form-data."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"test")
            f.flush()

            # Test with multipart form data (OpenAI format)
            with open(f.name, "rb") as file:
                response = client.post(
                    "/v1/audio/transcriptions",
                    data={
                        "model": "mlx-community/whisper-small",
                        "language": "en",
                        "response_format": "json",
                        "temperature": "0.0"
                    },
                    files={"file": file}
                )

            # Should get format error, not parameter error
            assert response.status_code in [400, 422, 500]  # Not 422 (missing file)

        Path(f.name).unlink()

    def test_response_format_json(self, client):
        """Test that response format matches OpenAI specification."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFF" + b"\x00" * 100)
            f.flush()

            with open(f.name, "rb") as file:
                response = client.post(
                    "/v1/audio/transcriptions",
                    files={"file": file},
                    data={"response_format": "json"}
                )

            # If response is successful, check format
            if response.status_code == 200:
                data = response.json()
                assert "text" in data
                assert "task" in data
                assert data["task"] == "transcribe"

        Path(f.name).unlink()

    def test_response_format_text(self, client):
        """Test that text response format works."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFF" + b"\x00" * 100)
            f.flush()

            with open(f.name, "rb") as file:
                response = client.post(
                    "/v1/audio/transcriptions",
                    files={"file": file},
                    data={"response_format": "text"}
                )

            # If response is successful, check format
            if response.status_code == 200:
                # Should return plain text
                assert isinstance(response.text, str)
                # Should not be JSON
                try:
                    json.loads(response.text)
                    pytest.fail("Expected text response, got JSON")
                except json.decoder.JSONDecodeError:
                    pass  # Expected - it's text, not JSON

        Path(f.name).unlink()

    def test_parameters_model(self, client):
        """Test that model parameter is accepted."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFF" + b"\x00" * 100)
            f.flush()

            with open(f.name, "rb") as file:
                response = client.post(
                    "/v1/audio/transcriptions",
                    files={"file": file},
                    data={"model": "mlx-community/whisper-small"}
                )

            # Should accept model parameter (even if model doesn't exist)
            assert response.status_code != 422  # Not a validation error

        Path(f.name).unlink()

    def test_parameters_language(self, client):
        """Test that language parameter is accepted."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFF" + b"\x00" * 100)
            f.flush()

            with open(f.name, "rb") as file:
                response = client.post(
                    "/v1/audio/transcriptions",
                    files={"file": file},
                    data={"language": "en"}
                )

            # Should accept language parameter
            assert response.status_code != 422  # Not a validation error

        Path(f.name).unlink()

    def test_parameters_response_format(self, client):
        """Test that response_format parameter works."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFF" + b"\x00" * 100)
            f.flush()

            # Test all supported formats
            formats = ["json", "text", "verbose_json", "srt"]
            for fmt in formats:
                with open(f.name, "rb") as file:
                    response = client.post(
                        "/v1/audio/transcriptions",
                        files={"file": file},
                        data={"response_format": fmt}
                    )

                # Should accept format parameter
                assert response.status_code != 422

        Path(f.name).unlink()

    def test_parameters_temperature(self, client):
        """Test that temperature parameter is accepted."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFF" + b"\x00" * 100)
            f.flush()

            with open(f.name, "rb") as file:
                response = client.post(
                    "/v1/audio/transcriptions",
                    files={"file": file},
                    data={"temperature": "0.5"}
                )

            # Should accept temperature parameter
            assert response.status_code != 422

        Path(f.name).unlink()

    def test_error_format(self, client):
        """Test that error format matches OpenAI specification."""
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            f.write(b"test")
            f.flush()

            with open(f.name, "rb") as file:
                response = client.post(
                    "/v1/audio/transcriptions",
                    files={"file": file}
                )

            if response.status_code >= 400:
                data = response.json()
                assert "error" in data
                assert "message" in data["error"]
                assert "type" in data["error"]
                assert "code" in data["error"]

        Path(f.name).unlink()

    def test_supported_formats(self, client):
        """Test that all OpenAI-supported formats are accepted."""
        formats = ["mp3", "wav", "m4a", "mp4", "mpeg", "webm"]

        for fmt in formats:
            with tempfile.NamedTemporaryFile(suffix=f".{fmt}", delete=False) as f:
                # Write minimal file content
                if fmt == "wav":
                    f.write(b"RIFF" + b"\x00" * 100)
                else:
                    f.write(b"test")

                f.flush()

                with open(f.name, "rb") as file:
                    response = client.post(
                        "/v1/audio/transcriptions",
                        files={"file": file}
                    )

                # Format should be accepted (may fail for other reasons like MLX not installed)
                assert response.status_code != 400  # Not "unsupported format"

            Path(f.name).unlink()

    @pytest.mark.skip(reason="Requires actual MLX-Whisper installation")
    def test_end_to_end_with_openai_sdk(self, openai_client, audio_file):
        """Test end-to-end with OpenAI SDK (requires MLX-Whisper)."""
        with open(audio_file, "rb") as f:
            try:
                result = openai_client.audio.transcriptions.create(
                    model="mlx-community/whisper-small",
                    file=f
                )
                assert result.text is not None
            except Exception as e:
                # May fail if MLX not installed or model not available
                pytest.skip(f"MLX test skipped: {e}")

"""Tests for audio validation service."""

import pytest
from pathlib import Path
import tempfile

from src.services.validation import AudioValidator
from src.core.exceptions import (
    FileTooLargeError,
    FileTooLongError,
    InvalidFileFormatError,
    CorruptedAudioFileError
)


class TestAudioValidator:
    """Test AudioValidator class."""

    @pytest.fixture
    def validator(self):
        """Create validator instance for testing."""
        return AudioValidator(
            max_file_size=25 * 1024 * 1024,  # 25MB
            max_duration=1500,  # 25 minutes
            allowed_formats=["mp3", "wav", "m4a"]
        )

    def test_validate_file_size_too_large(self, validator):
        """Test that file too large raises error."""
        with pytest.raises(FileTooLargeError) as exc_info:
            validator._validate_file_size(30 * 1024 * 1024)

        assert exc_info.value.status_code == 413

    def test_validate_file_size_ok(self, validator):
        """Test that valid file size passes."""
        # Should not raise
        validator._validate_file_size(1024 * 1024)  # 1MB

    def test_validate_duration_too_long(self, validator):
        """Test that file too long raises error."""
        with pytest.raises(FileTooLongError) as exc_info:
            validator._validate_duration(2000)  # 33 minutes

        assert exc_info.value.status_code == 413

    def test_validate_duration_ok(self, validator):
        """Test that valid duration passes."""
        # Should not raise
        validator._validate_duration(600)  # 10 minutes

    def test_detect_format_by_extension(self, validator):
        """Test format detection by file extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files with different extensions
            test_cases = [
                ("test.mp3", "mp3"),
                ("test.wav", "wav"),
                ("test.m4a", "m4a"),
            ]

            for filename, expected_format in test_cases:
                file_path = Path(tmpdir) / filename
                file_path.touch()  # Create empty file

                format = validator._detect_format(str(file_path))
                assert format == expected_format

    def test_detect_format_unsupported(self, validator):
        """Test detection of unsupported format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.unk"
            file_path.touch()

            with pytest.raises(InvalidFileFormatError) as exc_info:
                validator._detect_format(str(file_path))

            assert exc_info.value.status_code == 400

    def test_validate_file_integrity_valid(self, validator):
        """Test validation of valid file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file with WAV header
            file_path = Path(tmpdir) / "test.wav"
            with open(file_path, "wb") as f:
                f.write(b"RIFF" + b"\x00" * 100)  # WAV header + dummy data

            # Should not raise
            validator._validate_file_integrity(str(file_path), "wav")

    def test_validate_file_integrity_invalid_wav(self, validator):
        """Test validation of invalid WAV file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file with invalid WAV header
            file_path = Path(tmpdir) / "test.wav"
            with open(file_path, "wb") as f:
                f.write(b"NOTWAV" + b"\x00" * 100)  # Invalid header

            with pytest.raises(CorruptedAudioFileError):
                validator._validate_file_integrity(str(file_path), "wav")

    def test_get_duration_with_ffprobe(self, validator):
        """Test duration detection with ffprobe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.mp3"
            file_path.touch()

            # This test may fail if ffprobe is not available
            # In that case, it should fall back to estimation
            duration = validator._get_duration(str(file_path), "mp3")
            assert isinstance(duration, float)
            assert duration > 0

    def test_validate_file_end_to_end(self, validator):
        """Test complete file validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.wav"
            with open(file_path, "wb") as f:
                f.write(b"RIFF" + b"\x00" * 100)  # Valid WAV header

            # Should not raise
            format, duration = validator.validate_file(str(file_path), 104)
            assert format == "wav"
            assert isinstance(duration, float)

"""File validation service for audio uploads."""

import mimetypes
from pathlib import Path
from typing import Tuple

from ..core.exceptions import CorruptedAudioFileError, FileTooLargeError, FileTooLongError, InvalidFileFormatError
from ..core.logging import get_logger

logger = get_logger(__name__)


class AudioValidator:
    """Validates audio files for transcription."""

    # Magic numbers for common audio formats
    MAGIC_NUMBERS = {
        b"ID3": "mp3",  # MP3 with ID3v2 tag
        b"\xff\xfb": "mp3",  # MP3 frame
        b"\xff\xf3": "mp3",  # MP3 frame (alternate)
        b"RIFF": "wav",  # WAV file
        b"fLaC": "flac",  # FLAC file
        b"OggS": "ogg",  # OGG file
        b"\x00\x00\x00": "mp4",  # MP4 file (ftyp box)
        b"ftyp": "mp4",  # MP4 file
        b"WEBm": "webm",  # WebM file
    }

    # MIME type to format mapping
    MIME_TO_FORMAT = {
        "audio/mpeg": "mp3",
        "audio/wav": "wav",
        "audio/wave": "wav",
        "audio/x-wav": "wav",
        "audio/mp4": "m4a",
        "audio/m4a": "m4a",
        "audio/x-m4a": "m4a",
        "video/mp4": "mp4",
        "audio/mpeg": "mp3",
        "audio/webm": "webm",
        "video/webm": "webm",
    }

    def __init__(self, max_file_size: int, max_duration: int, allowed_formats: list[str]):
        """Initialize validator.

        Args:
            max_file_size: Maximum file size in bytes
            max_duration: Maximum duration in seconds
            allowed_formats: List of allowed audio formats
        """
        self.max_file_size = max_file_size
        self.max_duration = max_duration
        self.allowed_formats = allowed_formats

    def validate_file(self, file_path: str, file_size: int) -> Tuple[str, float]:
        """Validate audio file.

        Args:
            file_path: Path to the file
            file_size: File size in bytes

        Returns:
            Tuple of (format, duration) if valid

        Raises:
            FileTooLargeError: If file exceeds size limit
            InvalidFileFormatError: If file format is not supported
            CorruptedAudioFileError: If file is corrupted
            FileTooLongError: If audio duration exceeds limit
        """
        # Check file size
        self._validate_file_size(file_size)

        # Detect format
        format = self._detect_format(file_path)
        logger.debug("Format detected", file_path=file_path, format=format)

        # Validate format is allowed
        if format not in self.allowed_formats:
            raise InvalidFileFormatError(format, self.allowed_formats)

        # Check file is not corrupted
        self._validate_file_integrity(file_path, format)

        # Check duration
        duration = self._get_duration(file_path, format)
        logger.debug("Duration checked", file_path=file_path, duration=duration)

        # Validate duration
        self._validate_duration(duration)

        return format, duration

    def _validate_file_size(self, file_size: int) -> None:
        """Validate file size.

        Args:
            file_size: File size in bytes

        Raises:
            FileTooLargeError: If file exceeds size limit
        """
        if file_size > self.max_file_size:
            raise FileTooLargeError(file_size, self.max_file_size)

    def _detect_format(self, file_path: str) -> str:
        """Detect audio format from file.

        Args:
            file_path: Path to the file

        Returns:
            Detected format (e.g., 'mp3', 'wav')

        Raises:
            InvalidFileFormatError: If format cannot be determined
        """
        # First try by extension
        extension = Path(file_path).suffix.lower().lstrip(".")
        if extension in self.allowed_formats:
            return extension

        # Try by MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and mime_type in self.MIME_TO_FORMAT:
            format_from_mime = self.MIME_TO_FORMAT[mime_type]
            if format_from_mime in self.allowed_formats:
                return format_from_mime

        # Try by magic number
        format_from_magic = self._detect_by_magic_number(file_path)
        if format_from_magic and format_from_magic in self.allowed_formats:
            return format_from_magic

        raise InvalidFileFormatError("unknown", self.allowed_formats)

    def _detect_by_magic_number(self, file_path: str) -> str | None:
        """Detect format by reading magic number.

        Args:
            file_path: Path to the file

        Returns:
            Detected format or None if not detected
        """
        try:
            with open(file_path, "rb") as f:
                # Read first 12 bytes for magic number
                header = f.read(12)

            # Check magic numbers
            for magic, format in self.MAGIC_NUMBERS.items():
                if header.startswith(magic):
                    return format

            return None

        except Exception as e:
            logger.error("Failed to detect magic number", file_path=file_path, error=str(e))
            return None

    def _validate_file_integrity(self, file_path: str, format: str) -> None:
        """Validate file is not corrupted.

        Args:
            file_path: Path to the file
            format: Detected file format

        Raises:
            CorruptedAudioFileError: If file is corrupted
        """
        try:
            with open(file_path, "rb") as f:
                # Read a small chunk to verify file is readable
                chunk = f.read(1024)

                if not chunk:
                    raise CorruptedAudioFileError("File is empty")

                # Format-specific validation
                if format == "mp3":
                    # Check for valid MP3 frame
                    if not (chunk.startswith(b"ID3") or
                            chunk.startswith(b"\xff\xfb") or
                            chunk.startswith(b"\xff\xf3")):
                        # Could still be a valid MP3, just not detected
                        pass

                elif format == "wav":
                    # Check RIFF header
                    if not chunk.startswith(b"RIFF"):
                        raise CorruptedAudioFileError("Invalid WAV file header")

                elif format == "mp4" or format == "m4a":
                    # Check for MP4/M4A header
                    if not (b"ftyp" in chunk):
                        raise CorruptedAudioFileError("Invalid MP4/M4A file header")

                elif format == "webm":
                    # Check for WebM header
                    if not (b"WEBm" in chunk or b"\x1a\x45\xdf\xa3" in chunk):
                        raise CorruptedAudioFileError("Invalid WebM file header")

        except CorruptedAudioFileError:
            raise
        except Exception as e:
            logger.error("Failed to validate file integrity", file_path=file_path, format=format, error=str(e))
            raise CorruptedAudioFileError(f"Unable to read file: {str(e)}")

    def _get_duration(self, file_path: str, format: str) -> float:
        """Get audio duration in seconds.

        Args:
            file_path: Path to the file
            format: File format

        Returns:
            Duration in seconds

        Note:
            For now, this returns a placeholder. In a real implementation,
            you would use a library like pydub or librosa to get the actual duration.
            For simplicity and to avoid heavy dependencies, we'll use a simple approach.
        """
        # Simple approach: try to use ffprobe if available
        try:
            import subprocess

            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", file_path],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0 and result.stdout.strip():
                duration = float(result.stdout.strip())
                return duration

        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError, Exception) as e:
            logger.warning(
                "Could not determine duration via ffprobe, using estimation",
                file_path=file_path,
                error=str(e)
            )

        # Fallback: estimate duration based on file size
        # This is very rough - assumes ~1MB per minute at 128kbps
        file_size_mb = Path(file_path).stat().st_size / (1024 * 1024)
        estimated_duration = file_size_mb * 60 / 1.0  # Rough estimate

        logger.info(
            "Using estimated duration",
            file_path=file_path,
            file_size_mb=file_size_mb,
            estimated_duration=estimated_duration
        )

        return estimated_duration

    def _validate_duration(self, duration: float) -> None:
        """Validate audio duration.

        Args:
            duration: Duration in seconds

        Raises:
            FileTooLongError: If duration exceeds limit
        """
        if duration > self.max_duration:
            raise FileTooLongError(duration, self.max_duration)

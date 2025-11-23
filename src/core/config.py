"""Configuration loader for the MLX Whisper Server."""

import os
from pathlib import Path
from typing import Any, Dict

import yaml
from pydantic import BaseModel, Field, ConfigDict


class TranscriptionConfig(BaseModel):
    """Transcription service configuration."""
    model_config = ConfigDict(extra="forbid")

    max_file_size: int = Field(default=25 * 1024 * 1024, description="Maximum file size in bytes")
    max_duration: int = Field(default=1500, description="Maximum duration in seconds")
    allowed_formats: list[str] = Field(
        default=["mp3", "wav", "m4a", "mp4", "mpeg", "webm"],
        description="Allowed audio formats"
    )
    model: str = Field(description="MLX model name")
    use_modelscope: bool = Field(default=True, description="Whether to use modelscope instead of huggingface")
    dump_audio_dir: str = Field(default="", description="Directory to dump uploaded audio files")


class ServerConfig(BaseModel):
    """Server configuration."""
    model_config = ConfigDict(extra="forbid")

    host: str = Field(default="0.0.0.0", description="Server host address")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=2, description="Number of worker processes")


class LoggingConfig(BaseModel):
    """Logging configuration."""
    model_config = ConfigDict(extra="forbid")

    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="text", description="Log format")


class AppConfig(BaseModel):
    """Main application configuration."""
    model_config = ConfigDict(extra="forbid")

    server: ServerConfig = Field(default_factory=ServerConfig)
    transcription: TranscriptionConfig = Field(default_factory=TranscriptionConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


class Config:
    """Configuration manager for the application."""

    def __init__(self, config_path: str | None = None):
        """Initialize configuration loader.

        Args:
            config_path: Optional path to config file. Defaults to config/config.yaml
        """
        self.config_path = config_path or self._find_config_file()
        self._config: AppConfig | None = None

    def _find_config_file(self) -> str:
        """Find configuration file in standard locations."""
        # Check current directory
        if Path("config/config.yaml.local").exists():
            return "config/config.yaml.local"

        # Check parent directory
        if Path("../config/config.yaml.local").exists():
            return "../config/config.yaml.local"

        # Fallback path
        return "../config/config.yaml"

    def load(self) -> AppConfig:
        """Load configuration from file and environment.

        Returns:
            Loaded configuration object
        """
        if self._config is not None:
            return self._config

        # Load from YAML file if exists
        config_data: Dict[str, Any] = {}
        if Path(self.config_path).exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}

        # Create configuration with environment variable overrides
        self._config = AppConfig(**config_data)
        return self._config

    def reload(self) -> AppConfig:
        """Reload configuration from file.

        Returns:
            Reloaded configuration object
        """
        self._config = None
        return self.load()

    @property
    def config(self) -> AppConfig:
        """Get current configuration (loads if not loaded)."""
        return self._config or self.load()


# Global configuration instance
config = Config()

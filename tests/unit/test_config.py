"""Tests for configuration loader."""

import pytest
from pathlib import Path
import tempfile
import yaml

from src.core.config import AppConfig, Config, ServerConfig, TranscriptionConfig, LoggingConfig


class TestServerConfig:
    """Test ServerConfig model."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ServerConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.workers == 2

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ServerConfig(host="127.0.0.1", port=9000, workers=4)
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.workers == 4


class TestTranscriptionConfig:
    """Test TranscriptionConfig model."""

    def test_default_values(self):
        """Test default transcription configuration."""
        config = TranscriptionConfig()
        assert config.max_file_size == 25 * 1024 * 1024
        assert config.max_duration == 1500
        assert config.allowed_formats == ["mp3", "wav", "m4a", "mp4", "mpeg", "webm"]
        assert config.model == "mlx-community/whisper-small"

    def test_custom_values(self):
        """Test custom transcription configuration."""
        config = TranscriptionConfig(
            max_file_size=50 * 1024 * 1024,
            max_duration=3000,
            model="mlx-community/whisper-medium"
        )
        assert config.max_file_size == 50 * 1024 * 1024
        assert config.max_duration == 3000
        assert config.model == "mlx-community/whisper-medium"


class TestLoggingConfig:
    """Test LoggingConfig model."""

    def test_default_values(self):
        """Test default logging configuration."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.format == "json"

    def test_custom_values(self):
        """Test custom logging configuration."""
        config = LoggingConfig(level="DEBUG", format="text")
        assert config.level == "DEBUG"
        assert config.format == "text"


class TestAppConfig:
    """Test AppConfig model."""

    def test_load_from_dict(self):
        """Test loading configuration from dictionary."""
        config_data = {
            "server": {"host": "127.0.0.1", "port": 9000},
            "transcription": {"model": "test-model"},
            "logging": {"level": "DEBUG"}
        }
        config = AppConfig(**config_data)
        assert config.server.host == "127.0.0.1"
        assert config.server.port == 9000
        assert config.transcription.model == "test-model"
        assert config.logging.level == "DEBUG"


class TestConfig:
    """Test Config class."""

    def test_find_config_file_default(self):
        """Test finding config file in default location."""
        config = Config()
        assert config.config_path == "config/config.yaml"

    def test_load_config(self):
        """Test loading configuration from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config file
            config_path = Path(tmpdir) / "test_config.yaml"
            config_data = {
                "server": {"host": "127.0.0.1", "port": 9000},
                "transcription": {"model": "test-model"}
            }
            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            # Load configuration
            config = Config(str(config_path))
            cfg = config.load()

            assert cfg.server.host == "127.0.0.1"
            assert cfg.server.port == 9000
            assert cfg.transcription.model == "test-model"

    def test_config_property(self):
        """Test config property getter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.yaml"
            with open(config_path, "w") as f:
                yaml.dump({}, f)

            config = Config(str(config_path))
            cfg = config.config  # Access property

            assert isinstance(cfg, AppConfig)

    def test_reload_config(self):
        """Test reloading configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.yaml"
            config_data = {"server": {"port": 9000}}
            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            config = Config(str(config_path))
            cfg1 = config.load()
            assert cfg1.server.port == 9000

            # Update config file
            config_data = {"server": {"port": 9500}}
            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            # Reload
            cfg2 = config.reload()
            assert cfg2.server.port == 9500

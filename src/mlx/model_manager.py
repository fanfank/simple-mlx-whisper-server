"""Model manager for MLX Whisper."""

import threading
from typing import Any, Dict, Optional

import mlx_whisper
from mlx_whisper.load_models import load_model
from mlx_whisper.whisper import Whisper
import mlx.core as mx

from ..core.exceptions import ModelLoadError
from ..core.logging import get_logger

logger = get_logger(__name__)


class ModelManager:
    """Manager for MLX Whisper model lifecycle."""

    def __init__(self, model_name: str, use_modelscope: bool):
        """Initialize model manager.

        Args:
            model_name: Name of the model to manage
            use_modelscope: Whether to use modelscope
        """
        self.model_name = model_name
        if use_modelscope:
            from modelscope import snapshot_download
            self.model_name = snapshot_download(model_name)
        self._model: Optional[Any] = None
        self._lock = threading.Lock()
        self._load_count = 0

    def get_model_name(self) -> str:
        return self.model_name

    def get_model(self) -> Any:
        """Get the loaded model, loading it if necessary.

        Returns:
            Loaded MLX model

        Raises:
            ModelLoadError: If model loading fails
        """
        with self._lock:
            if self._model is None:
                logger.info("Model not loaded, loading...", model_name=self.model_name)
                self._load_model()
                self._load_count += 1
                logger.info(
                    "Model loaded successfully",
                    model_name=self.model_name,
                    load_count=self._load_count
                )
            return self._model

    def _load_model(self) -> None:
        """Load the MLX model.

        Raises:
            ModelLoadError: If model loading fails
        """
        try:
            self._model = mlx_whisper #load_model(self.model_name, dtype=mx.float16)
        except Exception as e:
            logger.error("Failed to load model", model_name=self.model_name, error=str(e))
            raise ModelLoadError(self.model_name, str(e))

    def is_loaded(self) -> bool:
        """Check if model is loaded.

        Returns:
            True if model is loaded, False otherwise
        """
        with self._lock:
            return self._model is not None

    def unload_model(self) -> None:
        """Unload the model to free resources."""
        with self._lock:
            if self._model is not None:
                logger.info("Unloading model", model_name=self.model_name)
                self._model = None

    def get_status(self) -> Dict[str, Any]:
        """Get model manager status.

        Returns:
            Dictionary with status information
        """
        with self._lock:
            return {
                "model_name": self.model_name,
                "loaded": self._model is not None,
                "load_count": self._load_count,
            }

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.unload_model()

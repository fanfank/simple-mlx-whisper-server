"""API request/response models for the transcribe endpoint."""

from typing import Optional

from pydantic import BaseModel, Field


class TranscribeRequest(BaseModel):
    """Request model for audio transcription."""
    model_config = {"extra": "forbid"}

    language: Optional[str] = Field(default=None, description="Language code (auto-detect if None)")
    response_format: str = Field(
        default="json",
        description="Output format: json, text, srt, verbose_json"
    )
    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0 to 2.0)"
    )


class TranscribeResponse(BaseModel):
    """Response model for successful transcription."""
    text: str = Field(description="Transcribed text")
    language: Optional[str] = Field(default=None, description="Detected or specified language")
    duration: float = Field(default=0.0, description="Audio duration in seconds")
    task: str = Field(default="transcribe", description="Task type")


class VerboseTranscribeResponse(TranscribeResponse):
    """Response model for verbose JSON transcription."""
    segments: list[dict] = Field(default_factory=list, description="Timestamped segments")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: dict = Field(description="Error details")
    request_id: Optional[str] = Field(default=None, description="Request ID for debugging")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(description="Server status")
    workers: dict = Field(description="Worker pool status")
    model_loaded: bool = Field(description="Whether MLX model is loaded")
    uptime_seconds: int = Field(description="Server uptime in seconds")

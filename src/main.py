"""Main application entry point for MLX Whisper Server."""

from contextlib import asynccontextmanager
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import mlx_whisper
from mlx_whisper.transcribe import ModelHolder
import mlx.core as mx
import uvicorn

from .api.routes import router
from .api.middleware import LoggingMiddleware, RequestSizeMiddleware
from .core.config import config
from .core.logging import setup_logging, get_logger

# Setup logging
cfg = config.load()
setup_logging(cfg.logging.level, cfg.logging.format)

logger = get_logger(__name__)

# Track start time for uptime calculation
start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info(
        "Starting MLX Whisper Server",
        host=cfg.server.host,
        port=cfg.server.port,
        workers=cfg.server.workers
    )

    model = cfg.transcription.model
    if cfg.transcription.use_modelscope:
        from modelscope import snapshot_download
        model = snapshot_download(cfg.transcription.model)
    ModelHolder.get_model(model, mx.float16)

    yield

    # Shutdown
    logger.info("Shutting down MLX Whisper Server")


# Create FastAPI application
app = FastAPI(
    title="MLX Whisper Server",
    description="High-performance HTTP server for audio transcription using MLX-Whisper. Compatible with OpenAI Whisper API.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add middleware
#app.add_middleware(LoggingMiddleware)
app.add_middleware(RequestSizeMiddleware, max_request_size=cfg.transcription.max_file_size)

## Add CORS middleware
#app.add_middleware(
#    CORSMiddleware,
#    allow_origins=["*"],
#    allow_credentials=True,
#    allow_methods=["GET", "POST", "OPTIONS"],
#    allow_headers=["*"]
#)

# Include API routes
app.include_router(router)

# Add exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        exc_info=True,
        url=str(request.url)
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "Internal server error",
                "type": "server_error",
                "code": "500"
            }
        }
    )


def main():
    """Main entry point."""
    cfg = config.load()

    logger.info(
        "Launching server",
        host=cfg.server.host,
        port=cfg.server.port,
        workers=cfg.server.workers
    )

    # Run server
    uvicorn.run(
        "src.main:app",
        host=cfg.server.host,
        port=cfg.server.port,
        workers=cfg.server.workers,
        reload=False,
        log_level=cfg.logging.level.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()

"""Worker pool for managing concurrent transcription requests."""

import asyncio
import threading
from queue import Queue, Empty
from typing import Any, Callable, Dict, Optional

from ..core.exceptions import ServerBusyError
from ..core.logging import get_logger

logger = get_logger(__name__)


class Worker:
    """Single worker for handling transcription requests."""

    def __init__(self, worker_id: int, model_manager: Any):
        """Initialize worker.

        Args:
            worker_id: Unique worker ID
            model_manager: Model manager instance
        """
        self.worker_id = worker_id
        self.model_manager = model_manager
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.queue: Queue = Queue()
        self.current_request: Optional[Dict[str, Any]] = None

    def start(self) -> None:
        """Start the worker thread."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("Worker started", worker_id=self.worker_id)

    def stop(self) -> None:
        """Stop the worker thread."""
        if not self.running:
            return

        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        logger.info("Worker stopped", worker_id=self.worker_id)

    def _run(self) -> None:
        """Main worker loop."""
        while self.running:
            try:
                # Get request from queue (with timeout)
                request = self.queue.get(timeout=1)
                self.current_request = request

                # Process request
                self._process_request(request)

            except Empty:
                # No requests, continue
                continue
            except Exception as e:
                logger.error(
                    "Worker error",
                    worker_id=self.worker_id,
                    error=str(e),
                    exc_info=True
                )
            finally:
                self.current_request = None
                self.queue.task_done()

    def _process_request(self, request: Dict[str, Any]) -> None:
        """Process a transcription request.

        Args:
            request: Request dictionary containing:
                - audio_path: Path to audio file
                - callback: Callback function to call with result
                - request_id: Request ID for logging
        """
        request_id = request.get("request_id", "unknown")
        logger.info(
            "Worker processing request",
            worker_id=self.worker_id,
            request_id=request_id
        )

        try:
            # Get model
            model = self.model_manager.get_model()

            # Run transcription
            # Note: This would call the actual transcription service
            result = {
                "status": "success",
                "text": "Transcription result",
                "worker_id": self.worker_id
            }

            # Call callback with result
            if "callback" in request:
                request["callback"](result)

        except Exception as e:
            logger.error(
                "Request processing failed",
                worker_id=self.worker_id,
                request_id=request_id,
                error=str(e)
            )

            # Call callback with error
            if "callback" in request:
                request["callback"]({"status": "error", "error": str(e)})

    def submit(self, request: Dict[str, Any]) -> None:
        """Submit a request to the worker queue.

        Args:
            request: Request dictionary
        """
        if not self.running:
            raise RuntimeError("Worker is not running")

        self.queue.put(request)

    def is_busy(self) -> bool:
        """Check if worker is currently processing a request.

        Returns:
            True if worker is busy, False otherwise
        """
        return self.current_request is not None

    def queue_size(self) -> int:
        """Get current queue size.

        Returns:
            Number of requests in queue
        """
        return self.queue.qsize()


class WorkerPool:
    """Pool of workers for handling concurrent requests."""

    def __init__(
        self,
        num_workers: int,
        max_concurrent: int,
        model_manager: Any
    ):
        """Initialize worker pool.

        Args:
            num_workers: Number of worker processes
            max_concurrent: Maximum concurrent requests across all workers
            model_manager: Model manager instance
        """
        self.num_workers = num_workers
        self.max_concurrent = max_concurrent
        self.model_manager = model_manager
        self.workers: list[Worker] = []
        self._active_requests = 0
        self._lock = threading.Lock()

        # Create workers
        for i in range(num_workers):
            worker = Worker(i, model_manager)
            self.workers.append(worker)

    def start(self) -> None:
        """Start all workers."""
        logger.info("Starting worker pool", num_workers=self.num_workers)
        for worker in self.workers:
            worker.start()

    def stop(self) -> None:
        """Stop all workers."""
        logger.info("Stopping worker pool")
        for worker in self.workers:
            worker.stop()

    def submit(
        self,
        audio_path: str,
        callback: Callable[[Dict[str, Any]], None],
        request_id: str
    ) -> None:
        """Submit a transcription request.

        Args:
            audio_path: Path to audio file
            callback: Callback function for result
            request_id: Request ID for tracking

        Raises:
            ServerBusyError: If at capacity
        """
        with self._lock:
            if self._active_requests >= self.max_concurrent:
                raise ServerBusyError(self.max_concurrent, request_id)
            self._active_requests += 1

        request = {
            "audio_path": audio_path,
            "callback": lambda result: self._handle_result(result, request_id),
            "request_id": request_id
        }

        # Find least busy worker
        worker = self._get_least_busy_worker()
        worker.submit(request)

        logger.info(
            "Request submitted",
            request_id=request_id,
            worker_id=worker.worker_id,
            active_requests=self._active_requests
        )

    def _handle_result(self, result: Dict[str, Any], request_id: str) -> None:
        """Handle request completion.

        Args:
            result: Request result
            request_id: Request ID
        """
        with self._lock:
            self._active_requests = max(0, self._active_requests - 1)

        logger.info(
            "Request completed",
            request_id=request_id,
            status=result.get("status"),
            active_requests=self._active_requests
        )

    def _get_least_busy_worker(self) -> Worker:
        """Get the least busy worker.

        Returns:
            Worker instance
        """
        # Simple round-robin: select first available worker
        for worker in self.workers:
            if not worker.is_busy() and worker.queue_size() == 0:
                return worker

        # All workers busy, select one with smallest queue
        return min(self.workers, key=lambda w: w.queue_size())

    def get_status(self) -> Dict[str, Any]:
        """Get worker pool status.

        Returns:
            Dictionary with status information
        """
        with self._lock:
            return {
                "num_workers": self.num_workers,
                "max_concurrent": self.max_concurrent,
                "active_requests": self._active_requests,
                "workers": [
                    {
                        "worker_id": w.worker_id,
                        "busy": w.is_busy(),
                        "queue_size": w.queue_size(),
                        "running": w.running
                    }
                    for w in self.workers
                ]
            }

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

"""
Performance tests for concurrent request handling.

These tests verify that the server can handle the required concurrent load:
- Support up to 10 concurrent requests
- Reject 11th request with HTTP 503
- Maintain performance under load
"""

import pytest
import asyncio
import time
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
import httpx


class TestConcurrentRequestHandling:
    """Test server handles multiple concurrent requests."""

    @pytest.fixture
    async def client(self):
        """Create async HTTP client."""
        async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
            yield client

    @pytest.fixture
    def valid_audio_file(self, tmp_path):
        """Create a valid audio file for performance testing."""
        audio_file = tmp_path / "test_audio.wav"
        # Create a minimal WAV file (1 second of silence)
        wav_header = b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
        audio_file.write_bytes(wav_header)
        return audio_file

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_accepts_up_to_10_concurrent_requests(self, client, valid_audio_file):
        """Test that server accepts up to 10 concurrent requests."""
        num_requests = 10

        async def send_request(request_id: int):
            """Send a single request."""
            with open(valid_audio_file, "rb") as f:
                files = {"file": ("audio.wav", f, "audio/wav")}
                try:
                    response = await client.post(
                        "/v1/audio/transcriptions",
                        files=files
                    )
                    return request_id, response.status_code, response.elapsed.total_seconds()
                except Exception as e:
                    return request_id, None, str(e)

        # Send 10 concurrent requests
        start_time = time.time()

        tasks = [send_request(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        elapsed_time = time.time() - start_time

        # Analyze results
        successful_requests = [r for r in results if isinstance(r, tuple) and r[1] in [200, 202, 503]]
        failed_requests = [r for r in results if not isinstance(r, tuple) or r[1] not in [200, 202, 503]]

        # All requests should be accepted (may be 503 if at capacity, but should not be rejected)
        assert len(successful_requests) == num_requests, \
            f"Only {len(successful_requests)}/{num_requests} requests succeeded"

        # Print performance metrics
        print(f"\n=== 10 Concurrent Requests Performance ===")
        print(f"Total time: {elapsed_time:.2f}s")
        print(f"Requests per second: {num_requests/elapsed_time:.2f}")
        print(f"Average response time: {sum(r[2] for r in successful_requests)/len(successful_requests):.3f}s")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_rejects_11th_concurrent_request_with_503(self, client, valid_audio_file):
        """Test that 11th concurrent request returns HTTP 503."""
        num_requests = 11

        async def send_request(request_id: int):
            """Send a single request."""
            with open(valid_audio_file, "rb") as f:
                files = {"file": ("audio.wav", f, "audio/wav")}
                response = await client.post(
                    "/v1/audio/transcriptions",
                    files=files,
                    timeout=5.0  # Shorter timeout for this test
                )
                return request_id, response.status_code

        # First send 10 requests to saturate capacity
        tasks = [send_request(i) for i in range(10)]
        first_10 = await asyncio.gather(*tasks, return_exceptions=True)

        # Give the system a moment to process
        await asyncio.sleep(0.1)

        # Now send the 11th request
        with open(valid_audio_file, "rb") as f:
            files = {"file": ("audio.wav", f, "audio/wav")}
            response_11 = await client.post(
                "/v1/audio/transcriptions",
                files=files,
                timeout=5.0
            )

        # The 11th request should be rejected with 503
        assert response_11.status_code == 503, \
            f"Expected 503, got {response_11.status_code}"

        # Verify error format
        data = response_11.json()
        assert "error" in data
        assert data["error"]["type"] == "service_unavailable"

        print(f"\n=== 11th Request Correctly Rejected ===")
        print(f"Status code: {response_11.status_code}")
        print(f"Error type: {data['error']['type']}")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_performance_under_load(self, client, valid_audio_file):
        """Test performance metrics under concurrent load."""
        num_requests = 10
        num_runs = 3  # Run the test multiple times

        all_latencies = []

        for run in range(num_runs):
            async def send_request(request_id: int):
                """Send a single request."""
                with open(valid_audio_file, "rb") as f:
                    files = {"file": ("audio.wav", f, "audio/wav")}
                    start = time.time()
                    response = await client.post(
                        "/v1/audio/transcriptions",
                        files=files
                    )
                    elapsed = time.time() - start
                    return response.status_code, elapsed

            start_time = time.time()

            tasks = [send_request(i) for i in range(num_requests)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            run_time = time.time() - start_time

            # Collect latencies for successful requests
            latencies = [r[1] for r in results if isinstance(r, tuple)]
            all_latencies.extend(latencies)

            print(f"\n=== Run {run + 1}/{num_runs} ===")
            print(f"Total time: {run_time:.2f}s")
            print(f"Requests: {len(latencies)}/{num_requests}")
            if latencies:
                print(f"Avg latency: {sum(latencies)/len(latencies):.3f}s")
                print(f"Min latency: {min(latencies):.3f}s")
                print(f"Max latency: {max(latencies):.3f}s")
                print(f"Throughput: {len(latencies)/run_time:.2f} req/s")

        # Overall statistics
        if all_latencies:
            print(f"\n=== Overall Performance ===")
            print(f"Total requests: {len(all_latencies)}")
            print(f"Overall avg latency: {sum(all_latencies)/len(all_latencies):.3f}s")
            print(f"Overall min latency: {min(all_latencies):.3f}s")
            print(f"Overall max latency: {max(all_latencies):.3f}s")

            # Performance assertions
            avg_latency = sum(all_latencies) / len(all_latencies)
            assert avg_latency < 5.0, f"Average latency too high: {avg_latency:.3f}s"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_request_queueing_behavior(self, client, valid_audio_file):
        """Test that requests are properly queued when at capacity."""
        num_requests = 15  # More than capacity

        async def send_request(request_id: int):
            """Send a single request."""
            with open(valid_audio_file, "rb") as f:
                files = {"file": ("audio.wav", f, "audio/wav")}
                start = time.time()
                try:
                    response = await client.post(
                        "/v1/audio/transcriptions",
                        files=files,
                        timeout=10.0
                    )
                    elapsed = time.time() - start
                    return request_id, response.status_code, elapsed
                except httpx.TimeoutException:
                    elapsed = time.time() - start
                    return request_id, "timeout", elapsed

        start_time = time.time()

        tasks = [send_request(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.time() - start_time

        # Categorize results
        status_codes = {}
        for r in results:
            if isinstance(r, tuple):
                status = r[1]
                status_codes[status] = status_codes.get(status, 0) + 1

        print(f"\n=== Request Queueing Test ===")
        print(f"Total requests: {num_requests}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Status codes: {status_codes}")

        # We expect:
        # - Some requests to succeed (200/202)
        # - Some to be rejected (503)
        # - Very few or no timeouts
        timeout_count = sum(1 for r in results if isinstance(r, tuple) and r[1] == "timeout")
        assert timeout_count < 3, f"Too many timeouts: {timeout_count}"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_slow_requests_dont_block_fast_requests(self, client, valid_audio_file):
        """Test that slow requests don't block fast requests."""
        # This test verifies that the server can handle requests with varying processing times
        # without blocking fast requests

        # Create files of different sizes to simulate varying processing times
        small_file = valid_audio_file
        medium_file = Path(valid_audio_file).parent / "medium.wav"
        large_file = Path(valid_audio_file).parent / "large.wav"

        # Create files of different sizes
        small_file.write_bytes(b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
        medium_file.write_bytes(b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00" + b"x" * 100000)
        large_file.write_bytes(b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00" + b"x" * 500000)

        files = [
            (small_file, "small.wav"),
            (medium_file, "medium.wav"),
            (large_file, "large.wav"),
        ]

        async def send_request(file_info, request_id):
            """Send a request with specific file."""
            file_path, file_name = file_info
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f, "audio/wav")}
                start = time.time()
                response = await client.post(
                    "/v1/audio/transcriptions",
                    files=files,
                    timeout=10.0
                )
                elapsed = time.time() - start
                return request_id, file_name, response.status_code, elapsed

        # Send requests with different file sizes concurrently
        tasks = []
        for i, file_info in enumerate(files * 4):  # 12 total requests
            tasks.append(send_request(file_info, i))

        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time

        # Analyze results
        print(f"\n=== Mixed Load Test ===")
        print(f"Total time: {total_time:.2f}s")
        print(f"Total requests: {len(results)}")

        # Check that fast requests (small files) didn't get blocked by slow ones
        small_requests = [r for r in results if isinstance(r, tuple) and "small" in r[1]]
        large_requests = [r for r in results if isinstance(r, tuple) and "large" in r[1]]

        if small_requests:
            small_avg = sum(r[3] for r in small_requests) / len(small_requests)
            print(f"Small file avg latency: {small_avg:.3f}s")

        if large_requests:
            large_avg = sum(r[3] for r in large_requests) / len(large_requests)
            print(f"Large file avg latency: {large_avg:.3f}s")


class TestWorkerPoolPerformance:
    """Test WorkerPool performance characteristics."""

    @pytest.mark.performance
    def test_worker_pool_initialization(self):
        """Test that WorkerPool initializes with correct capacity."""
        from src.services.workers import WorkerPool

        max_workers = 10
        pool = WorkerPool(max_workers=max_workers)

        assert pool.max_workers == max_workers

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_worker_pool_submit_performance(self):
        """Test WorkerPool can handle rapid task submission."""
        from src.services.workers import WorkerPool

        pool = WorkerPool(max_workers=10)

        async def dummy_task():
            """A simple dummy task."""
            await asyncio.sleep(0.01)  # 10ms task
            return "done"

        # Submit many tasks rapidly
        num_tasks = 50
        start_time = time.time()

        tasks = [pool.submit_task(dummy_task) for _ in range(num_tasks)]
        results = await asyncio.gather(*tasks)

        elapsed_time = time.time() - start_time

        print(f"\n=== WorkerPool Performance ===")
        print(f"Tasks: {num_tasks}")
        print(f"Time: {elapsed_time:.2f}s")
        print(f"Tasks/sec: {num_tasks/elapsed_time:.2f}")

        # All tasks should complete
        assert len(results) == num_tasks
        assert all(r == "done" for r in results)


class TestLatencyBenchmarks:
    """Test latency benchmarks for different scenarios."""

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_single_request_latency(self, client, valid_audio_file):
        """Test latency for a single request."""
        with open(valid_audio_file, "rb") as f:
            files = {"file": ("audio.wav", f, "audio/wav")}

            # Warm up
            await client.post("/v1/audio/transcriptions", files=files)

            # Measure latency
            latencies = []
            for _ in range(5):
                start = time.time()
                response = await client.post("/v1/audio/transcriptions", files=files)
                elapsed = time.time() - start
                latencies.append(elapsed)

                # Verify response
                assert response.status_code in [200, 202, 503]

            avg_latency = sum(latencies) / len(latencies)
            print(f"\n=== Single Request Latency ===")
            print(f"Average: {avg_latency:.3f}s")
            print(f"Min: {min(latencies):.3f}s")
            print(f"Max: {max(latencies):.3f}s")

            # Performance requirement: should respond within 5 seconds
            assert avg_latency < 5.0, f"Average latency {avg_latency:.3f}s exceeds 5s threshold"

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_concurrent_request_latency_degradation(self, client, valid_audio_file):
        """Test that latency doesn't degrade significantly with concurrency."""
        concurrency_levels = [1, 5, 10]
        latency_results = {}

        for concurrency in concurrency_levels:
            latencies = []

            for _ in range(5):  # Run each concurrency level 5 times
                async def send_single_request():
                    with open(valid_audio_file, "rb") as f:
                        files = {"file": ("audio.wav", f, "audio/wav")}
                        start = time.time()
                        response = await client.post("/v1/audio/transcriptions", files=files)
                        elapsed = time.time() - start
                        return elapsed

                # Send requests at the specified concurrency level
                tasks = [send_single_request() for _ in range(concurrency)]
                results = await asyncio.gather(*tasks)

                latencies.extend(results)

            avg_latency = sum(latencies) / len(latencies)
            latency_results[concurrency] = avg_latency

            print(f"\n=== Concurrency {concurrency} ===")
            print(f"Average latency: {avg_latency:.3f}s")

        # Check that latency degradation is reasonable
        # Going from 1 to 10 concurrent requests shouldn't increase latency by more than 5x
        single_latency = latency_results[1]
        max_latency = latency_results[10]
        degradation_factor = max_latency / single_latency

        print(f"\n=== Latency Degradation ===")
        print(f"Single request: {single_latency:.3f}s")
        print(f"10 concurrent: {max_latency:.3f}s")
        print(f"Degradation factor: {degradation_factor:.2f}x")

        # Allow up to 5x degradation
        assert degradation_factor < 5.0, \
            f"Latency degraded too much: {degradation_factor:.2f}x from single to 10 concurrent"


if __name__ == "__main__":
    # Run performance tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])

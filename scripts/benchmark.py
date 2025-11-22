#!/usr/bin/env python
"""
Performance benchmarking script for MLX Whisper Server.

This script runs various performance tests to measure:
- Latency under different loads
- Throughput (requests per second)
- Resource utilization
- Concurrent request handling

Usage:
    python scripts/benchmark.py --url http://localhost:8000 --duration 60
    python scripts/benchmark.py --url http://localhost:8000 --test latency
    python scripts/benchmark.py --url http://localhost:8000 --test concurrent
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Any
import tempfile

import httpx
import pandas as pd


class BenchmarkRunner:
    """Run performance benchmarks against the server."""

    def __init__(self, base_url: str, duration: int = 60):
        """Initialize benchmark runner.

        Args:
            base_url: Base URL of the server (e.g., http://localhost:8000)
            duration: Test duration in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.duration = duration
        self.results: Dict[str, Any] = {}

    async def create_test_audio(self) -> Path:
        """Create a test audio file for benchmarking.

        Returns:
            Path to temporary audio file
        """
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            # Create minimal WAV file (1 second of silence)
            wav_header = (
                b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
                b"D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
            )
            f.write(wav_header)
            return Path(f.name)

    async def test_latency(self) -> Dict[str, Any]:
        """Test single-request latency.

        Returns:
            Latency statistics
        """
        print("\n=== Latency Test ===")
        print(f"Running for {self.duration} seconds...\n")

        audio_file = await self.create_test_audio()

        latencies = []
        start_time = time.time()
        request_count = 0

        async with httpx.AsyncClient(timeout=30.0) as client:
            while time.time() - start_time < self.duration:
                try:
                    with open(audio_file, "rb") as f:
                        files = {"file": ("test.wav", f, "audio/wav")}
                        req_start = time.time()
                        response = await client.post(
                            f"{self.base_url}/v1/audio/transcriptions",
                            files=files
                        )
                        req_time = time.time() - req_start

                    latencies.append(req_time)
                    request_count += 1

                    # Progress update
                    if request_count % 10 == 0:
                        print(f"Requests: {request_count}, Latest latency: {req_time:.3f}s")

                except Exception as e:
                    print(f"Error: {e}")

        # Cleanup
        audio_file.unlink()

        # Calculate statistics
        if latencies:
            stats = {
                "total_requests": len(latencies),
                "avg_latency": sum(latencies) / len(latencies),
                "min_latency": min(latencies),
                "max_latency": max(latencies),
                "p50_latency": sorted(latencies)[len(latencies) // 2],
                "p95_latency": sorted(latencies)[int(len(latencies) * 0.95)],
                "p99_latency": sorted(latencies)[int(len(latencies) * 0.99)],
            }

            print("\nLatency Statistics:")
            for key, value in stats.items():
                print(f"  {key}: {value:.3f}s")

            return stats
        else:
            print("\nNo successful requests!")
            return {}

    async def test_concurrent_requests(self, concurrency_levels: List[int]) -> Dict[str, Any]:
        """Test concurrent request handling.

        Args:
            concurrency_levels: List of concurrency levels to test

        Returns:
            Concurrency test results
        """
        print("\n=== Concurrent Requests Test ===")
        print(f"Testing concurrency levels: {concurrency_levels}\n")

        audio_file = await self.create_test_audio()
        results = {}

        for concurrency in concurrency_levels:
            print(f"\nTesting with concurrency={concurrency}...")

            latencies = []
            start_time = time.time()

            async def send_request(semaphore: asyncio.Semaphore):
                async with semaphore:
                    try:
                        with open(audio_file, "rb") as f:
                            files = {"file": ("test.wav", f, "audio/wav")}
                            req_start = time.time()
                            async with httpx.AsyncClient(timeout=30.0) as client:
                                response = await client.post(
                                    f"{self.base_url}/v1/audio/transcriptions",
                                    files=files
                                )
                            req_time = time.time() - req_start
                            return req_time
                    except Exception as e:
                        print(f"Error: {e}")
                        return None

            # Create semaphore and run concurrent requests
            semaphore = asyncio.Semaphore(concurrency)
            tasks = [send_request(semaphore) for _ in range(concurrency * 2)]

            completed = 0
            for result in await asyncio.gather(*tasks):
                if result:
                    latencies.append(result)
                    completed += 1

            test_duration = time.time() - start_time

            if latencies:
                stats = {
                    "concurrency": concurrency,
                    "total_requests": len(latencies),
                    "successful_requests": completed,
                    "test_duration": test_duration,
                    "avg_latency": sum(latencies) / len(latencies),
                    "min_latency": min(latencies),
                    "max_latency": max(latencies),
                    "throughput": len(latencies) / test_duration,
                }

                print(f"  Completed: {completed}/{concurrency * 2} requests")
                print(f"  Avg latency: {stats['avg_latency']:.3f}s")
                print(f"  Throughput: {stats['throughput']:.2f} req/s")

                results[concurrency] = stats

        # Cleanup
        audio_file.unlink()

        return results

    async def test_throughput(self, target_rps: int) -> Dict[str, Any]:
        """Test maximum throughput.

        Args:
            target_rps: Target requests per second

        Returns:
            Throughput test results
        """
        print(f"\n=== Throughput Test ===")
        print(f"Target: {target_rps} RPS for {self.duration} seconds\n")

        audio_file = await self.create_test_audio()
        request_interval = 1.0 / target_rps

        latencies = []
        request_times = []
        start_time = time.time()

        async def send_request():
            try:
                with open(audio_file, "rb") as f:
                    files = {"file": ("test.wav", f, "audio/wav")}
                    req_start = time.time()
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(
                            f"{self.base_url}/v1/audio/transcriptions",
                            files=files
                        )
                    req_time = time.time() - req_start
                    return req_time, req_start
            except Exception as e:
                print(f"Error: {e}")
                return None, None

        # Send requests at target RPS
        while time.time() - start_time < self.duration:
            req_start = time.time()

            result = await send_request()
            if result[0]:
                latencies.append(result[0])
                request_times.append(req_start)

            # Wait to maintain target RPS
            elapsed = time.time() - req_start
            if elapsed < request_interval:
                await asyncio.sleep(request_interval - elapsed)

        test_duration = time.time() - start_time

        # Cleanup
        audio_file.unlink()

        # Calculate statistics
        if latencies:
            stats = {
                "target_rps": target_rps,
                "actual_rps": len(latencies) / test_duration,
                "total_requests": len(latencies),
                "avg_latency": sum(latencies) / len(latencies),
                "min_latency": min(latencies),
                "max_latency": max(latencies),
            }

            print(f"Target RPS: {target_rps}")
            print(f"Actual RPS: {stats['actual_rps']:.2f}")
            print(f"Total requests: {len(latencies)}")
            print(f"Avg latency: {stats['avg_latency']:.3f}s")

            return stats
        else:
            print("\nNo successful requests!")
            return {}

    async def test_error_rates(self) -> Dict[str, Any]:
        """Test error rates under load.

        Returns:
            Error rate statistics
        """
        print("\n=== Error Rate Test ===")
        print("Testing with oversized file, invalid format, etc.\n")

        results = {
            "file_too_large": None,
            "invalid_format": None,
            "corrupted_file": None,
        }

        # Test 1: File too large
        print("Testing file too large (30MB)...")
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"x" * (30 * 1024 * 1024))
            large_file = Path(f.name)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                with open(large_file, "rb") as f:
                    files = {"file": ("large.mp3", f, "audio/mpeg")}
                    response = await client.post(
                        f"{self.base_url}/v1/audio/transcriptions",
                        files=files
                    )
                results["file_too_large"] = {
                    "status_code": response.status_code,
                    "expected_413": response.status_code == 413
                }
                print(f"  Status: {response.status_code} (expected 413)")
        finally:
            large_file.unlink()

        # Test 2: Invalid format
        print("Testing invalid format...")
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            f.write(b"invalid data")
            invalid_file = Path(f.name)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                with open(invalid_file, "rb") as f:
                    files = {"file": ("invalid.xyz", f, "application/octet-stream")}
                    response = await client.post(
                        f"{self.base_url}/v1/audio/transcriptions",
                        files=files
                    )
                results["invalid_format"] = {
                    "status_code": response.status_code,
                    "expected_400": response.status_code == 400
                }
                print(f"  Status: {response.status_code} (expected 400)")
        finally:
            invalid_file.unlink()

        # Test 3: Corrupted file
        print("Testing corrupted file...")
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"NOTMP3DATA")
            corrupted_file = Path(f.name)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                with open(corrupted_file, "rb") as f:
                    files = {"file": ("corrupted.mp3", f, "audio/mpeg")}
                    response = await client.post(
                        f"{self.base_url}/v1/audio/transcriptions",
                        files=files
                    )
                results["corrupted_file"] = {
                    "status_code": response.status_code,
                    "expected_422": response.status_code == 422
                }
                print(f"  Status: {response.status_code} (expected 422)")
        finally:
            corrupted_file.unlink()

        return results

    async def run_all_tests(self, test_types: List[str]) -> Dict[str, Any]:
        """Run all specified tests.

        Args:
            test_types: List of test types to run

        Returns:
            Combined test results
        """
        print("=" * 60)
        print("MLX Whisper Server - Performance Benchmark")
        print("=" * 60)

        # Health check
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                print(f"\n✅ Server is healthy: {response.status_code}")
        except Exception as e:
            print(f"\n❌ Server is not accessible: {e}")
            return {}

        results = {"timestamp": time.time()}

        # Run requested tests
        if "latency" in test_types:
            results["latency"] = await self.test_latency()

        if "concurrent" in test_types:
            results["concurrent"] = await self.test_concurrent_requests([1, 5, 10, 15, 20])

        if "throughput" in test_types:
            results["throughput"] = await self.test_throughput(target_rps=5)

        if "error_rates" in test_types:
            results["error_rates"] = await self.test_error_rates()

        return results

    def save_results(self, results: Dict[str, Any], output_file: str):
        """Save results to JSON file.

        Args:
            results: Test results
            output_file: Output file path
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

        print(f"\n📊 Results saved to: {output_path}")

    def print_summary(self, results: Dict[str, Any]):
        """Print summary of all test results.

        Args:
            results: Test results
        """
        print("\n" + "=" * 60)
        print("Benchmark Summary")
        print("=" * 60)

        if "latency" in results:
            lat = results["latency"]
            print(f"\nLatency (avg): {lat.get('avg_latency', 0):.3f}s")
            print(f"Latency (p95): {lat.get('p95_latency', 0):.3f}s")

        if "concurrent" in results:
            print(f"\nConcurrent Request Handling:")
            for concurrency, stats in results["concurrent"].items():
                print(f"  Concurrency {concurrency}: {stats['throughput']:.2f} req/s, "
                      f"avg latency {stats['avg_latency']:.3f}s")

        if "throughput" in results:
            thr = results["throughput"]
            print(f"\nThroughput: {thr.get('actual_rps', 0):.2f} req/s "
                  f"(target: {thr.get('target_rps', 0)})")

        if "error_rates" in results:
            print(f"\nError Handling:")
            for test_name, result in results["error_rates"].items():
                status = "✅" if result["expected_413"] or result["expected_400"] or result["expected_422"] else "❌"
                print(f"  {status} {test_name}: {result['status_code']}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Performance Benchmark for MLX Whisper Server")
    parser.add_argument("--url", default="http://localhost:8000", help="Server URL")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--test", choices=["latency", "concurrent", "throughput", "error_rates", "all"],
                       default="all", help="Test type to run")
    parser.add_argument("--output", default="results/benchmark_results.json", help="Output file")
    parser.add_argument("--rps", type=int, default=5, help="Target RPS for throughput test")

    args = parser.parse_args()

    # Determine test types
    if args.test == "all":
        test_types = ["latency", "concurrent", "throughput", "error_rates"]
    else:
        test_types = [args.test]

    # Run benchmarks
    runner = BenchmarkRunner(args.url, args.duration)

    if args.test == "throughput":
        results = await runner.run_all_tests(["throughput"])
    else:
        results = await runner.run_all_tests(test_types)

    if results:
        # Print summary
        runner.print_summary(results)

        # Save results
        runner.save_results(results, args.output)

        print("\n✅ Benchmark completed successfully!")
        return 0
    else:
        print("\n❌ Benchmark failed!")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

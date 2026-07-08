"""
Load test script for benchmarking API endpoints (RPS + latency percentiles).

Why this matters for your CV claims:
    A benchmark like "5,200 RPS, <0.85ms p99 latency" is only credible if you can say
    exactly HOW it was measured. This script produces real, reproducible numbers and
    separates "gateway only" (routing, no LLM call) from "full pipeline" (includes LLM
    inference) so you don't accidentally conflate the two on your CV.

Usage:
    pip install aiohttp --break-system-packages
    python load_test.py --url http://localhost:8000/health --concurrency 50 --duration 15
    python load_test.py --url http://localhost:8000/gateway/ai_agent --concurrency 1 --duration 120 --payload '{"text":"test"}'

Run it once against a lightweight endpoint (e.g. /health or a route with no LLM call)
to get your "gateway" numbers, and once against your real RAG/chat endpoint to get your
"full pipeline" numbers. Report both separately.
"""

import argparse
import asyncio
import time
import statistics
import json
import aiohttp


async def worker(session, url, method, payload, latencies, errors, stop_time):
    while time.monotonic() < stop_time:
        start = time.monotonic()
        try:
            if method == "GET":
                async with session.get(url) as resp:
                    await resp.read()
                    if resp.status >= 400:
                        errors[0] += 1
            else:
                async with session.post(url, json=payload) as resp:
                    await resp.read()
                    if resp.status >= 400:
                        errors[0] += 1
        except Exception:
            errors[0] += 1
        else:
            latencies.append(time.monotonic() - start)


async def run_load_test(url, concurrency, duration, payload):
    method = "POST" if payload else "GET"
    latencies = []
    errors = [0]
    stop_time = time.monotonic() + duration

    connector = aiohttp.TCPConnector(limit=concurrency)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            worker(session, url, method, payload, latencies, errors, stop_time)
            for _ in range(concurrency)
        ]
        await asyncio.gather(*tasks)

    return latencies, errors[0]


def percentile(data, pct):
    if not data:
        return float("nan")
    data_sorted = sorted(data)
    k = (len(data_sorted) - 1) * (pct / 100)
    f = int(k)
    c = min(f + 1, len(data_sorted) - 1)
    if f == c:
        return data_sorted[f]
    return data_sorted[f] + (data_sorted[c] - data_sorted[f]) * (k - f)


def main():
    parser = argparse.ArgumentParser(description="Simple async load tester")
    parser.add_argument("--url", required=True, help="Endpoint to hit")
    parser.add_argument("--concurrency", type=int, default=20, help="Concurrent workers")
    parser.add_argument("--duration", type=int, default=15, help="Test duration in seconds")
    parser.add_argument("--payload", type=str, default=None, help="JSON payload for POST requests")
    args = parser.parse_args()

    payload = json.loads(args.payload) if args.payload else None

    print(f"Running load test: {args.url}")
    print(f"Concurrency: {args.concurrency}, Duration: {args.duration}s")
    print("-" * 50)

    start = time.monotonic()
    latencies, errors = asyncio.run(
        run_load_test(args.url, args.concurrency, args.duration, payload)
    )
    elapsed = time.monotonic() - start

    total_requests = len(latencies) + errors
    rps = total_requests / elapsed if elapsed > 0 else 0

    print(f"Total requests:   {total_requests}")
    print(f"Successful:       {len(latencies)}")
    print(f"Errors:           {errors}")
    print(f"RPS:              {rps:.1f}")
    if latencies:
        print(f"Latency p50:      {statistics.median(latencies) * 1000:.2f} ms")
        print(f"Latency p95:      {percentile(latencies, 95) * 1000:.2f} ms")
        print(f"Latency p99:      {percentile(latencies, 99) * 1000:.2f} ms")
        print(f"Latency max:      {max(latencies) * 1000:.2f} ms")
    print("-" * 50)
    print("Record: hardware, endpoint tested (gateway-only vs full pipeline)")


if __name__ == "__main__":
    main()

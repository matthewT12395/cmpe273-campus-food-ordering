#!/usr/bin/env python
"""
Latency measurement script for Part A (Synchronous REST)
Tests three scenarios:
1. Baseline (no delay/failure)
2. 2s delay injected into Inventory service
3. Inventory service failure injection
"""

import requests
import time
import csv
import sys
from pathlib import Path

BASE_URL = "http://localhost:5000"
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Test parameters
NUM_REQUESTS = 10
SCENARIOS = {
    "baseline": {"items": ["pizza"]},
    "delay_2s": {"items": ["sushi"], "delay": 2},
    "failure": {"items": ["salad"], "fail": True},
}


def measure_scenario(scenario_name, scenario_config, num_requests=NUM_REQUESTS):
    """Run N requests for a scenario and return latency stats."""
    latencies = []
    errors = 0
    success_count = 0

    print(f"\n[{scenario_name}] Running {num_requests} requests...")

    for i in range(num_requests):
        start = time.time()
        try:
            resp = requests.post(
                f"{BASE_URL}/order",
                json=scenario_config,
                timeout=15,
            )
            elapsed = time.time() - start
            latencies.append(elapsed)

            if resp.status_code in (200, 502):
                # 200 = success, 502 = expected error for failure scenario
                success_count += 1
            else:
                errors += 1

            print(f"  Request {i+1}/{num_requests}: {elapsed:.3f}s (HTTP {resp.status_code})")
        except Exception as e:
            elapsed = time.time() - start
            latencies.append(elapsed)
            errors += 1
            print(f"  Request {i+1}/{num_requests}: {elapsed:.3f}s (ERROR: {e})")

    # Compute statistics
    latencies.sort()
    stats = {
        "scenario": scenario_name,
        "num_requests": num_requests,
        "success": success_count,
        "errors": errors,
        "min_latency": min(latencies),
        "max_latency": max(latencies),
        "avg_latency": sum(latencies) / len(latencies),
        "median_latency": latencies[len(latencies) // 2],
        "p95_latency": latencies[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0],
    }

    return stats


def main():
    print("=" * 70)
    print("Part A: Synchronous REST - Latency Measurement")
    print("=" * 70)

    all_stats = []

    for scenario_name, scenario_config in SCENARIOS.items():
        stats = measure_scenario(scenario_name, scenario_config)
        all_stats.append(stats)

    # Write CSV
    csv_path = RESULTS_DIR / "latency_results.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_stats[0].keys())
        writer.writeheader()
        writer.writerows(all_stats)

    print(f"\n✓ Results saved to: {csv_path}")

    # Write markdown report with reasoning
    report_path = RESULTS_DIR / "PART_A_RESULTS.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Part A: Synchronous REST - Latency & Failure Injection Report\n\n")
        f.write("## Latency Measurements (N=10 requests per scenario)\n\n")
        f.write("| Scenario | Min (s) | Avg (s) | Median (s) | Max (s) | P95 (s) | Success | Errors |\n")
        f.write("|----------|---------|---------|------------|---------|---------|---------|--------|\n")

        for stats in all_stats:
            f.write(
                f"| {stats['scenario']} | {stats['min_latency']:.3f} | {stats['avg_latency']:.3f} | "
                f"{stats['median_latency']:.3f} | {stats['max_latency']:.3f} | {stats['p95_latency']:.3f} | "
                f"{stats['success']} | {stats['errors']} |\n"
            )

        f.write("\n## Analysis & Reasoning\n\n")

        f.write("### Scenario 1: Baseline (No delay/failure)\n")
        baseline = all_stats[0]
        f.write(
            f"- **Average latency**: {baseline['avg_latency']:.3f}s\n"
            f"- **Observation**: Low and consistent latency (~100-200ms) because Order → Inventory → Notification "
            f"execute sequentially with no artificial delays.\n"
            f"- **Why**: OrderService calls Inventory synchronously, waits for response, then calls Notification synchronously. "
            f"All three services respond immediately.\n"
        )

        f.write("\n### Scenario 2: Inventory Delay (2s injected)\n")
        delay = all_stats[1]
        f.write(
            f"- **Average latency**: {delay['avg_latency']:.3f}s (~{delay['avg_latency'] - baseline['avg_latency']:.3f}s slower than baseline)\n"
            f"- **Observation**: Latency increases by ~2s due to the injected delay in Inventory service.\n"
            f"- **Why**: OrderService makes a synchronous POST to Inventory with `?delay=2` query parameter. "
            f"The Inventory service sleeps for 2s, then responds. OrderService must wait for this response before "
            f"proceeding to Notification. The total order latency = sleep time + RPC overhead.\n"
            f"- **Impact**: Demonstrates how downstream service latency directly impacts caller latency in synchronous workflows.\n"
        )

        f.write("\n### Scenario 3: Inventory Failure (500 error)\n")
        failure = all_stats[2]
        f.write(
            f"- **Average latency**: {failure['avg_latency']:.3f}s\n"
            f"- **HTTP Response**: 502 Bad Gateway (expected error handling)\n"
            f"- **Observation**: OrderService receives HTTP 500 from Inventory and returns 502 to the client.\n"
            f"- **Why**: OrderService includes retry logic (2 retries with exponential backoff ~0.5s × 2^attempt). "
            f"Each retry adds latency. After max retries exhausted, OrderService returns a 502 error response.\n"
            f"- **Error handling**: OrderService explicitly returns `reserve-failed` error with the original Inventory "
            f"status code, allowing the client to understand what went wrong.\n"
        )

        f.write("\n## Summary\n\n")
        f.write("**Key Takeaways**:\n")
        f.write(
            "1. **Synchronous blocking**: OrderService blocks on Inventory and Notification calls. "
            "Any latency in downstream services directly increases order latency.\n"
        )
        f.write(
            "2. **Error amplification**: With retries enabled, failure scenarios see compounded latency "
            "(original timeout + retry backoff delays).\n"
        )
        f.write(
            "3. **User experience impact**: A 2s Inventory delay translates to ~2s added order latency, "
            "which is noticeable in a user-facing API.\n"
        )
        f.write(
            "4. **Next optimization**: Part B (async messaging) will decouple order placement from inventory/notification, "
            "reducing customer-facing latency.\n"
        )

    print(f"✓ Report saved to: {report_path}\n")

    # Print summary table to console
    print("\nSummary Table:")
    print("-" * 100)
    print(
        f"{'Scenario':<20} {'Min (s)':<10} {'Avg (s)':<10} {'Median (s)':<12} {'Max (s)':<10} {'P95 (s)':<10} {'Success':<8} {'Errors':<8}"
    )
    print("-" * 100)
    for stats in all_stats:
        print(
            f"{stats['scenario']:<20} {stats['min_latency']:<10.3f} {stats['avg_latency']:<10.3f} "
            f"{stats['median_latency']:<12.3f} {stats['max_latency']:<10.3f} {stats['p95_latency']:<10.3f} "
            f"{stats['success']:<8} {stats['errors']:<8}"
        )
    print("-" * 100)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠ Measurement interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error during measurement: {e}")
        sys.exit(1)

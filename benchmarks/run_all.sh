#!/usr/bin/env bash
# Run all Semantic FS benchmark scripts sequentially.
#
# Usage:
#   ./benchmarks/run_all.sh
#   STRICT_PREFLIGHT=true ./benchmarks/run_all.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting Semantic FS benchmark suite..."
echo ""

echo "1/4 Latency (Задержка)..."
"${SCRIPT_DIR}/latency.sh"

echo ""
echo "2/4 Throughput (Пропускная способность)..."
"${SCRIPT_DIR}/throughput.sh"

echo ""
echo "3/4 Error Rate (Уровень ошибок)..."
"${SCRIPT_DIR}/error_rate.sh"

echo ""
echo "4/4 Circuit Breaker Trips..."
"${SCRIPT_DIR}/circuit_breaker.sh"

echo ""
echo "All benchmarks completed. See benchmarks/results/ for output files."

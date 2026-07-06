#!/usr/bin/env bash
# Latency benchmark (Задержка): per-service response time on /health endpoints.
#
# Usage:
#   ./benchmarks/latency.sh
#   REQUESTS=200 ./benchmarks/latency.sh
#
# Env:
#   REQUESTS          — samples per service (default: 100)
#   STRICT_PREFLIGHT  — exit if any service is down (default: false)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

STRICT_PREFLIGHT="${STRICT_PREFLIGHT:-false}"
RUN_ID="$(timestamp)"
OUTPUT_FILE="${RESULTS_DIR}/latency_${RUN_ID}.txt"

require_curl
ensure_results_dir
print_banner "Latency Benchmark (Задержка)"
preflight_services "$STRICT_PREFLIGHT"

measure_service_latency() {
  local name="$1"
  local url
  url="$(service_health_url "$name")"
  local i
  local tmp
  tmp="$(mktemp)"

  echo "Measuring ${name} (${REQUESTS} requests)..."
  for ((i = 1; i <= REQUESTS; i++)); do
    curl -s -o /dev/null -w "%{time_total}\n" --connect-timeout 5 --max-time 10 "$url" >>"$tmp" || echo "0" >>"$tmp"
  done

  local stats
  stats="$(calc_latency_stats <"$tmp")"
  rm -f "$tmp"

  echo "  ${stats}"
  echo "service=${name} url=${url} ${stats}" >>"$OUTPUT_FILE"
}

{
  echo "# Latency benchmark — ${RUN_ID}"
  echo "# requests_per_service=${REQUESTS}"
  echo ""
} >"$OUTPUT_FILE"

for name in "${SERVICE_NAMES[@]}"; do
  measure_service_latency "$name"
done

echo ""
echo "Latency summary saved to: ${OUTPUT_FILE}"

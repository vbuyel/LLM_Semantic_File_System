#!/usr/bin/env bash
# Throughput benchmark (Пропускная способность): sustained RPS per service.
#
# Uses Apache Bench (ab) when available; falls back to parallel curl workers.
#
# Usage:
#   ./benchmarks/throughput.sh
#   REQUESTS=5000 CONCURRENCY=50 ./benchmarks/throughput.sh
#
# Env:
#   REQUESTS     — total requests per service (default: 1000)
#   CONCURRENCY  — parallel workers (default: 20)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

STRICT_PREFLIGHT="${STRICT_PREFLIGHT:-false}"
RUN_ID="$(timestamp)"
OUTPUT_FILE="${RESULTS_DIR}/throughput_${RUN_ID}.txt"

require_curl
ensure_results_dir
print_banner "Throughput Benchmark (Пропускная способность)"
preflight_services "$STRICT_PREFLIGHT"

run_ab_throughput() {
  local name="$1"
  local url="$2"
  local ab_out
  ab_out="$(mktemp)"

  if ! ab -n "$REQUESTS" -c "$CONCURRENCY" -q "$url" >"$ab_out" 2>&1; then
    rm -f "$ab_out"
    return 1
  fi

  local rps failed
  rps="$(awk '/Requests per second/ { print $4 }' "$ab_out")"
  failed="$(awk '/Failed requests/ { print $3 }' "$ab_out")"
  rm -f "$ab_out"

  echo "  tool=ab rps=${rps} failed=${failed:-0}"
  echo "service=${name} url=${url} tool=ab requests=${REQUESTS} concurrency=${CONCURRENCY} rps=${rps} failed=${failed:-0}" >>"$OUTPUT_FILE"
}

run_curl_throughput() {
  local name="$1"
  local url="$2"
  local tmp_dir success_file start end elapsed rps

  tmp_dir="$(mktemp -d)"
  success_file="${tmp_dir}/success"
  : >"$success_file"

  echo "  tool=curl (ab not available or failed)"

  start="$(python3 -c 'import time; print(time.time())')"
  seq 1 "$REQUESTS" | xargs -P "$CONCURRENCY" -I{} bash -c '
    code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "'"$url"'")
    if [[ "$code" == "200" ]]; then
      echo 1 >> "'"$success_file"'"
    fi
  '
  end="$(python3 -c 'import time; print(time.time())')"

  local success_count
  success_count="$(wc -l <"$success_file" | tr -d ' ')"
  elapsed="$(awk -v s="$start" -v e="$end" 'BEGIN { printf "%.4f", e - s }')"
  rps="$(awk -v n="$success_count" -v t="$elapsed" 'BEGIN { if (t > 0) printf "%.2f", n / t; else print "0.00" }')"
  local failed=$((REQUESTS - success_count))

  rm -rf "$tmp_dir"

  echo "  rps=${rps} success=${success_count} failed=${failed} duration_sec=${elapsed}"
  echo "service=${name} url=${url} tool=curl requests=${REQUESTS} concurrency=${CONCURRENCY} rps=${rps} success=${success_count} failed=${failed} duration_sec=${elapsed}" >>"$OUTPUT_FILE"
}

measure_service_throughput() {
  local name="$1"
  local url
  url="$(service_health_url "$name")"

  echo "Measuring ${name} (${REQUESTS} requests, concurrency=${CONCURRENCY})..."
  if command -v ab >/dev/null 2>&1; then
    if run_ab_throughput "$name" "$url"; then
      return 0
    fi
    echo "  ab failed for ${name}, falling back to curl..."
  fi
  run_curl_throughput "$name" "$url"
}

{
  echo "# Throughput benchmark — ${RUN_ID}"
  echo "# requests=${REQUESTS} concurrency=${CONCURRENCY}"
  echo ""
} >"$OUTPUT_FILE"

for name in "${SERVICE_NAMES[@]}"; do
  measure_service_throughput "$name"
done

echo ""
echo "Throughput summary saved to: ${OUTPUT_FILE}"

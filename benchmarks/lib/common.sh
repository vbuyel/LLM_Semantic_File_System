#!/usr/bin/env bash
# Shared configuration and helpers for Semantic FS benchmark scripts.

set -euo pipefail

BENCHMARK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "${BENCHMARK_ROOT}/.." && pwd)"
RESULTS_DIR="${BENCHMARK_RESULTS_DIR:-${BENCHMARK_ROOT}/results}"

# Service hosts (override via env). Use 127.0.0.1 — macOS ab fails on "localhost".
GATEWAY_HOST="${GATEWAY_HOST:-http://127.0.0.1:8000}"
LLM_HOST="${LLM_HOST:-http://127.0.0.1:8001}"
FILE_OPS_HOST="${FILE_OPS_HOST:-http://127.0.0.1:8002}"
EVENT_DB_HOST="${EVENT_DB_HOST:-http://127.0.0.1:8003}"
VECTOR_DB_HOST="${VECTOR_DB_HOST:-http://127.0.0.1:8004}"

# Default benchmark parameters
REQUESTS="${REQUESTS:-1000}"
PROXY_REQUESTS="${PROXY_REQUESTS:-10}"
CONCURRENCY="${CONCURRENCY:-10}"
DURATION_SEC="${DURATION_SEC:-30}"
POLL_INTERVAL_SEC="${POLL_INTERVAL_SEC:-2}"
PROXY_MAX_TIME="${PROXY_MAX_TIME:-15}"

# Benchmark identity headers for file_ops / gateway routes
BENCH_OWNER="${BENCH_OWNER:-benchmark@local.test}"
BENCH_AUTH_PROVIDER="${BENCH_AUTH_PROVIDER:-local}"
BENCH_STORAGE_SOURCE="${BENCH_STORAGE_SOURCE:-gcs}"

declare -a SERVICE_NAMES=(
  "gateway"
  "llm"
  "file_ops"
  "event_db"
  "vector_db"
)

service_url() {
  local name="$1"
  case "$name" in
    gateway)   echo "${GATEWAY_HOST}" ;;
    llm)       echo "${LLM_HOST}" ;;
    file_ops)  echo "${FILE_OPS_HOST}" ;;
    event_db)  echo "${EVENT_DB_HOST}" ;;
    vector_db) echo "${VECTOR_DB_HOST}" ;;
    *) echo "Unknown service: $name" >&2; return 1 ;;
  esac
}

service_health_url() {
  echo "$(service_url "$1")/health"
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command not found: $cmd" >&2
    exit 1
  fi
}

require_curl() {
  require_cmd curl
}

timestamp() {
  date +"%Y%m%d_%H%M%S"
}

ensure_results_dir() {
  mkdir -p "$RESULTS_DIR"
}

print_banner() {
  local title="$1"
  echo ""
  echo "============================================================"
  echo " $title"
  echo "============================================================"
  echo "Timestamp : $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "Results   : ${RESULTS_DIR}"
  echo ""
}

check_service_reachable() {
  local name="$1"
  local url
  url="$(service_health_url "$name")"
  local code
  code="$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 --max-time 5 "$url" || echo "000")"
  if [[ "$code" == "200" ]]; then
    echo "  [OK]   ${name} (${url})"
    return 0
  fi
  echo "  [FAIL] ${name} (${url}) — HTTP ${code}" >&2
  return 1
}

preflight_services() {
  local strict="${1:-false}"
  local failed=0
  echo "Preflight: checking service health endpoints..."
  for name in "${SERVICE_NAMES[@]}"; do
    if ! check_service_reachable "$name"; then
      failed=$((failed + 1))
    fi
  done
  if [[ "$failed" -gt 0 && "$strict" == "true" ]]; then
    echo ""
    echo "ERROR: ${failed} service(s) unreachable. Start the stack before benchmarking." >&2
    exit 1
  fi
  echo ""
}

# Reads latency samples (seconds, one per line) from stdin; prints summary stats.
calc_latency_stats() {
  awk '
    NF == 0 { next }
    {
      values[NR] = $1
      sum += $1
    }
    END {
      if (NR == 0) {
        print "count=0"
        exit
      }
      n = NR
      for (i = 1; i <= n; i++) {
        for (j = i + 1; j <= n; j++) {
          if (values[i] > values[j]) {
            tmp = values[i]; values[i] = values[j]; values[j] = tmp
          }
        }
      }
      p50_idx = int(0.50 * n); if (p50_idx < 1) p50_idx = 1
      p95_idx = int(0.95 * n); if (p95_idx < 1) p95_idx = 1
      p99_idx = int(0.99 * n); if (p99_idx < 1) p99_idx = 1
      printf "count=%d min_ms=%.2f avg_ms=%.2f p50_ms=%.2f p95_ms=%.2f p99_ms=%.2f max_ms=%.2f\n",
        n,
        values[1] * 1000,
        (sum / n) * 1000,
        values[p50_idx] * 1000,
        values[p95_idx] * 1000,
        values[p99_idx] * 1000,
        values[n] * 1000
    }
  '
}

ms_from_seconds() {
  awk -v s="$1" 'BEGIN { printf "%.2f", s * 1000 }'
}

http_status_code() {
  local method="$1"
  local url="$2"
  shift 2
  curl -s -o /dev/null -w "%{http_code}" -X "$method" --connect-timeout 5 --max-time 30 "$url" "$@"
}

http_time_total_sec() {
  local url="$1"
  shift
  curl -s -o /dev/null -w "%{time_total}" --connect-timeout 5 --max-time 30 "$url" "$@"
}

gateway_file_headers() {
  echo "-H" "X-Owner: ${BENCH_OWNER}"
  echo "-H" "X-Auth-Provider: ${BENCH_AUTH_PROVIDER}"
  echo "-H" "X-Storage-Source: ${BENCH_STORAGE_SOURCE}"
}

#!/usr/bin/env bash
# Error rate benchmark (Уровень ошибок): HTTP 5xx ratio and Kafka queue health.
#
# Measures:
#   1. Percentage of HTTP responses with status >= 500 per service.
#   2. Kafka consumer queue health via event_db / vector_db health payloads.
#
# Usage:
#   ./benchmarks/error_rate.sh
#   REQUESTS=500 ./benchmarks/error_rate.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

STRICT_PREFLIGHT="${STRICT_PREFLIGHT:-false}"
RUN_ID="$(timestamp)"
OUTPUT_FILE="${RESULTS_DIR}/error_rate_${RUN_ID}.txt"

require_curl
ensure_results_dir
print_banner "Error Rate Benchmark (Уровень ошибок)"
preflight_services "$STRICT_PREFLIGHT"

measure_http_error_rate() {
  local name="$1"
  local url
  url="$(service_health_url "$name")"
  local i code
  local total=0 errors_5xx=0 errors_other=0

  for ((i = 1; i <= REQUESTS; i++)); do
    code="$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "$url" || echo "000")"
    total=$((total + 1))
    if [[ "$code" =~ ^5 ]]; then
      errors_5xx=$((errors_5xx + 1))
    elif [[ "$code" != "200" ]]; then
      errors_other=$((errors_other + 1))
    fi
  done

  local error_rate_pct
  error_rate_pct="$(awk -v e="$errors_5xx" -v t="$total" 'BEGIN { if (t > 0) printf "%.2f", (e / t) * 100; else print "0.00" }')"

  echo "  http_5xx=${errors_5xx}/${total} (${error_rate_pct}%) non_2xx_other=${errors_other}"
  echo "service=${name} url=${url} total=${total} http_5xx=${errors_5xx} error_rate_pct=${error_rate_pct} non_2xx_other=${errors_other}" >>"$OUTPUT_FILE"
}

check_kafka_consumer_health() {
  local name="$1"
  local url body alive dead=0 total=0

  url="$(service_health_url "$name")"
  echo "Checking Kafka consumer health for ${name} (${REQUESTS} polls)..."

  for ((i = 1; i <= REQUESTS; i++)); do
    body="$(curl -s --connect-timeout 5 --max-time 10 "$url" || echo '{}')"
    total=$((total + 1))
    alive="$(echo "$body" | awk -F'"consumer_alive":' 'NF>1 { gsub(/[^a-z]/, "", $2); print $2 }')"
    if [[ "$alive" != "true" ]]; then
      dead=$((dead + 1))
    fi
  done

  local queue_fail_pct
  queue_fail_pct="$(awk -v d="$dead" -v t="$total" 'BEGIN { if (t > 0) printf "%.2f", (d / t) * 100; else print "0.00" }')"

  echo "  consumer_dead=${dead}/${total} queue_fail_pct=${queue_fail_pct}%"
  echo "service=${name} kafka_consumer_dead=${dead} kafka_polls=${total} queue_fail_pct=${queue_fail_pct}" >>"$OUTPUT_FILE"
}

measure_gateway_proxy_error_rate() {
  local endpoints=(
    "POST|${GATEWAY_HOST}/gateway/ai_agent|{\"text\":\"benchmark ping\",\"owner\":\"${BENCH_OWNER}\",\"correlation_id\":\"bench-$(uuidgen 2>/dev/null || echo test)\"}"
    "GET|${GATEWAY_HOST}/gateway/get_objects?path=|"
  )
  local entry method url payload code total=0 errors_5xx=0

  echo "Measuring gateway proxy error rate (${PROXY_REQUESTS} requests per route)..."

  for entry in "${endpoints[@]}"; do
    IFS='|' read -r method url payload <<<"$entry"
    local route_errors=0

    for ((i = 1; i <= PROXY_REQUESTS; i++)); do
      if [[ "$method" == "POST" ]]; then
        code="$(curl -s -o /dev/null -w "%{http_code}" -X POST \
          -H "Content-Type: application/json" \
          -H "X-Owner: ${BENCH_OWNER}" \
          -d "$payload" \
          --connect-timeout 5 --max-time "${PROXY_MAX_TIME}" "$url" || echo "000")"
      else
        code="$(curl -s -o /dev/null -w "%{http_code}" -X GET \
          -H "X-Owner: ${BENCH_OWNER}" \
          -H "X-Auth-Provider: ${BENCH_AUTH_PROVIDER}" \
          -H "X-Storage-Source: ${BENCH_STORAGE_SOURCE}" \
          --connect-timeout 5 --max-time "${PROXY_MAX_TIME}" "$url" || echo "000")"
      fi
      total=$((total + 1))
      if [[ "$code" =~ ^5 ]]; then
        errors_5xx=$((errors_5xx + 1))
        route_errors=$((route_errors + 1))
      fi
    done

    echo "  route=${url} http_5xx=${route_errors}/${PROXY_REQUESTS}"
    echo "route=${url} total=${PROXY_REQUESTS} http_5xx=${route_errors}" >>"$OUTPUT_FILE"
  done

  local proxy_error_pct
  proxy_error_pct="$(awk -v e="$errors_5xx" -v t="$total" 'BEGIN { if (t > 0) printf "%.2f", (e / t) * 100; else print "0.00" }')"
  echo "  gateway_proxy_total_5xx=${errors_5xx}/${total} (${proxy_error_pct}%)"
  echo "gateway_proxy_total=${total} gateway_proxy_5xx=${errors_5xx} gateway_proxy_error_pct=${proxy_error_pct}" >>"$OUTPUT_FILE"
}

{
  echo "# Error rate benchmark — ${RUN_ID}"
  echo "# requests=${REQUESTS}"
  echo ""
} >"$OUTPUT_FILE"

echo "=== HTTP 5xx on /health ==="
for name in "${SERVICE_NAMES[@]}"; do
  echo "Service: ${name}"
  measure_http_error_rate "$name"
done

echo ""
echo "=== Kafka queue health (consumer_alive) ==="
for name in event_db vector_db; do
  check_kafka_consumer_health "$name"
done

echo ""
echo "=== Gateway proxy routes (may include upstream failures) ==="
measure_gateway_proxy_error_rate

echo ""
echo "Error rate summary saved to: ${OUTPUT_FILE}"

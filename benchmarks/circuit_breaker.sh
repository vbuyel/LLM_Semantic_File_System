#!/usr/bin/env bash
# Circuit breaker trips benchmark: frequency of dependency-failure responses.
#
# Semantic FS does not expose a dedicated circuit-breaker metric endpoint yet.
# This script treats gateway 503/504 responses and Kafka consumer restarts as
# circuit-breaker-like trips — the same failure modes the system isolates on.
#
# Usage:
#   ./benchmarks/circuit_breaker.sh
#   DURATION_SEC=60 POLL_INTERVAL_SEC=1 ./benchmarks/circuit_breaker.sh
#
# Chaos mode (stop a dependency first, then run):
#   # e.g. stop LLM service on port 8001, then:
#   CHAOS_TARGET=llm ./benchmarks/circuit_breaker.sh
#
# Env:
#   DURATION_SEC        — observation window (default: 30)
#   POLL_INTERVAL_SEC   — seconds between probe rounds (default: 2)
#   CHAOS_TARGET        — optional: gateway|llm|file_ops|event_db|vector_db

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

RUN_ID="$(timestamp)"
OUTPUT_FILE="${RESULTS_DIR}/circuit_breaker_${RUN_ID}.txt"

require_curl
ensure_results_dir
print_banner "Circuit Breaker Trips Benchmark"

if [[ -n "${CHAOS_TARGET:-}" ]]; then
  echo "CHAOS_TARGET=${CHAOS_TARGET} — expecting elevated 503/504 from dependent routes."
  echo ""
fi

probe_gateway_route() {
  local route="$1"
  local method="$2"
  local url="$3"
  local payload="${4:-}"
  local code

  if [[ "$method" == "POST" ]]; then
    code="$(curl -s -o /dev/null -w "%{http_code}" -X POST \
      -H "Content-Type: application/json" \
      -H "X-Owner: ${BENCH_OWNER}" \
      -d "$payload" \
      --connect-timeout 3 --max-time "${PROXY_MAX_TIME}" "$url" || echo "000")"
  else
    code="$(curl -s -o /dev/null -w "%{http_code}" -X GET \
      -H "X-Owner: ${BENCH_OWNER}" \
      -H "X-Auth-Provider: ${BENCH_AUTH_PROVIDER}" \
      -H "X-Storage-Source: ${BENCH_STORAGE_SOURCE}" \
      --connect-timeout 3 --max-time "${PROXY_MAX_TIME}" "$url" || echo "000")"
  fi

  case "$code" in
    503|504)
      echo "trip"
      ;;
    *)
      echo "ok"
      ;;
  esac
}

probe_kafka_consumer() {
  local name="$1"
  local body alive

  body="$(curl -s --connect-timeout 3 --max-time 5 "$(service_health_url "$name")" || echo '{}')"
  alive="$(echo "$body" | awk -F'"consumer_alive":' 'NF>1 { gsub(/[^a-z]/, "", $2); print $2 }')"
  if [[ "$alive" == "true" ]]; then
    echo "ok"
  else
    echo "trip"
  fi
}

{
  echo "# Circuit breaker benchmark — ${RUN_ID}"
  echo "# duration_sec=${DURATION_SEC} poll_interval_sec=${POLL_INTERVAL_SEC}"
  echo "# chaos_target=${CHAOS_TARGET:-none}"
  echo ""
} >"$OUTPUT_FILE"

trips_gateway_ai_agent=0
trips_gateway_get_objects=0
trips_event_db_consumer=0
trips_vector_db_consumer=0

rounds=0
end_epoch=$(( $(date +%s) + DURATION_SEC ))

echo "Probing for ${DURATION_SEC}s (interval=${POLL_INTERVAL_SEC}s)..."
echo ""

while [[ $(date +%s) -lt $end_epoch ]]; do
  rounds=$((rounds + 1))

  if [[ "$(probe_gateway_route "ai_agent" "POST" "${GATEWAY_HOST}/gateway/ai_agent" "{\"text\":\"cb probe\",\"owner\":\"${BENCH_OWNER}\",\"correlation_id\":\"cb-${rounds}\"}")" == "trip" ]]; then
    trips_gateway_ai_agent=$((trips_gateway_ai_agent + 1))
  fi

  if [[ "$(probe_gateway_route "get_objects" "GET" "${GATEWAY_HOST}/gateway/get_objects?path=")" == "trip" ]]; then
    trips_gateway_get_objects=$((trips_gateway_get_objects + 1))
  fi

  if [[ "$(probe_kafka_consumer event_db)" == "trip" ]]; then
    trips_event_db_consumer=$((trips_event_db_consumer + 1))
  fi

  if [[ "$(probe_kafka_consumer vector_db)" == "trip" ]]; then
    trips_vector_db_consumer=$((trips_vector_db_consumer + 1))
  fi

  sleep "$POLL_INTERVAL_SEC"
done

total_trips=$((trips_gateway_ai_agent + trips_gateway_get_objects + trips_event_db_consumer + trips_vector_db_consumer))

trips_per_min="$(awk -v t="$total_trips" -v d="$DURATION_SEC" 'BEGIN { if (d > 0) printf "%.2f", (t / d) * 60; else print "0.00" }')"

echo "Results (${rounds} probe rounds):"
printf "  %-24s %s trips\n" "gateway/ai_agent" "${trips_gateway_ai_agent}"
printf "  %-24s %s trips\n" "gateway/get_objects" "${trips_gateway_get_objects}"
printf "  %-24s %s trips\n" "event_db consumer" "${trips_event_db_consumer}"
printf "  %-24s %s trips\n" "vector_db consumer" "${trips_vector_db_consumer}"
echo ""
echo "  total_trips=${total_trips}"
echo "  trips_per_min=${trips_per_min}"

{
  echo "rounds=${rounds} duration_sec=${DURATION_SEC}"
  echo "gateway_ai_agent_trips=${trips_gateway_ai_agent}"
  echo "gateway_get_objects_trips=${trips_gateway_get_objects}"
  echo "event_db_consumer_trips=${trips_event_db_consumer}"
  echo "vector_db_consumer_trips=${trips_vector_db_consumer}"
  echo "total_trips=${total_trips}"
  echo "trips_per_min=${trips_per_min}"
} >>"$OUTPUT_FILE"

echo ""
echo "Circuit breaker summary saved to: ${OUTPUT_FILE}"
echo ""
echo "Tip: stop a downstream service (e.g. LLM on :8001) and rerun with CHAOS_TARGET=llm"
echo "     to measure trip frequency under dependency failure."

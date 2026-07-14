#!/usr/bin/env bash
# Replay benchmarks/test_cases.json queries against the LLM agent so Langfuse
# records real ai-agent-turn traces.
#
# Prerequisites: LLM service on LLM_URL (default http://localhost:8001), Ollama up.
#
# Usage:
#   ./run_agent_traces.sh
#   ./run_agent_traces.sh --limit 5
#   LLM_URL=http://localhost:8001 OWNER=vladbuyel@gmail.com ./run_agent_traces.sh --limit 10 --delay 1
#
# Direct LLM service (recommended for tracing):
#   POST $LLM_URL/get_response  {"text","owner","correlation_id"}
#
# Via gateway instead:
#   ./run_agent_traces.sh --via-gateway
#   GATEWAY_URL=http://localhost:8000 ./run_agent_traces.sh --via-gateway --limit 3

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT="${SCRIPT_DIR}/test_cases.json"
LLM_URL="${LLM_URL:-http://localhost:8001}"
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000}"
OWNER="${OWNER:-vladbuyel@gmail.com}"
LIMIT=""
DELAY="${DELAY:-0}"
VIA_GATEWAY=0
TIMEOUT="${TIMEOUT:-120}"

usage() {
  sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input) INPUT="$2"; shift 2 ;;
    --limit) LIMIT="$2"; shift 2 ;;
    --delay) DELAY="$2"; shift 2 ;;
    --owner) OWNER="$2"; shift 2 ;;
    --via-gateway) VIA_GATEWAY=1; shift ;;
    -h|--help) usage 0 ;;
    *) echo "Unknown option: $1" >&2; usage 1 ;;
  esac
done

if [[ ! -f "$INPUT" ]]; then
  echo "Input not found: $INPUT" >&2
  exit 1
fi

if ! command -v python3 >/dev/null; then
  echo "python3 is required to parse JSON and build curl payloads" >&2
  exit 1
fi

TOTAL="$(python3 -c "import json; print(len(json.load(open('$INPUT'))))")"
N="$TOTAL"
if [[ -n "$LIMIT" ]]; then
  N="$LIMIT"
  if (( N > TOTAL )); then N="$TOTAL"; fi
fi

if (( VIA_GATEWAY )); then
  ENDPOINT="${GATEWAY_URL%/}/gateway/ai_agent"
  echo "Target: gateway $ENDPOINT"
else
  ENDPOINT="${LLM_URL%/}/get_response"
  echo "Target: LLM $ENDPOINT"
fi
echo "Owner:  $OWNER"
echo "Cases:  $N / $TOTAL from $INPUT"
echo

ok=0
fail=0

for ((i = 0; i < N; i++)); do
  corr_id="bench-$(date +%s)-$(printf '%03d' "$i")"

  # Build request body / headers via python (handles Unicode + JSON escaping)
  eval "$(python3 - "$INPUT" "$i" "$OWNER" "$corr_id" "$VIA_GATEWAY" <<'PY'
import json, shlex, sys
path, idx, owner, corr, via_gw = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5] == "1"
case = json.load(open(path))[idx]
query = case["query"]
preview = query.replace("\n", " ")[:90]
if via_gw:
    body = json.dumps({"text": query}, ensure_ascii=False)
else:
    body = json.dumps(
        {"text": query, "owner": owner, "correlation_id": corr},
        ensure_ascii=False,
    )
print(f"QUERY={shlex.quote(preview)}")
print(f"BODY={shlex.quote(body)}")
print(f"CORR={shlex.quote(corr)}")
PY
)"

  printf "[%d/%d] %s…\n" "$((i + 1))" "$N" "$QUERY"

  tmp="$(mktemp)"
  http_code=0
  if (( VIA_GATEWAY )); then
    http_code="$(curl -sS -o "$tmp" -w "%{http_code}" \
      --max-time "$TIMEOUT" \
      -X POST "$ENDPOINT" \
      -H "Content-Type: application/json" \
      -H "X-Owner: $OWNER" \
      -H "X-Correlation-ID: $CORR" \
      -d "$BODY" || true)"
  else
    http_code="$(curl -sS -o "$tmp" -w "%{http_code}" \
      --max-time "$TIMEOUT" \
      -X POST "$ENDPOINT" \
      -H "Content-Type: application/json" \
      -d "$BODY" || true)"
  fi

  if [[ "$http_code" == "200" ]]; then
    snippet="$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); t=d.get('text',''); print((t[:120]+'…') if len(t)>120 else t)" "$tmp" 2>/dev/null || head -c 120 "$tmp")"
    echo "  OK ($http_code) corr=$CORR — $snippet"
    ok=$((ok + 1))
  else
    echo "  FAIL (HTTP $http_code) corr=$CORR — $(head -c 200 "$tmp")"
    fail=$((fail + 1))
  fi
  rm -f "$tmp"

  if [[ "$DELAY" != "0" && "$DELAY" != "0.0" ]]; then
    sleep "$DELAY"
  fi
done

echo
echo "Done: $ok ok, $fail failed. Check Langfuse Traces (session_id = correlation_id)."

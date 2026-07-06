#!/usr/bin/env bash
# Run all LLM quality benchmarks (TTFT + RAG evaluation scores).
#
# Usage:
#   ./benchmarks/run_llm_benchmarks.sh
#   LLM_EVAL_OWNER=vladbuyel@gmail.com ./benchmarks/run_llm_benchmarks.sh
#
# Defaults to 50 cases from benchmarks/llm/dataset_50.json

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ensure_results_dir
print_banner "LLM Quality Benchmark Suite (${LLM_MIN_CASES} cases)"
preflight_services "true"

run_llm_eval all

echo ""
echo "LLM quality benchmarks completed. See ${RESULTS_DIR} for JSON output."

#!/usr/bin/env bash
# Generation latency benchmark (TTFT — Time to First Token).
#
# Measures streaming generation latency after RAG context retrieval.
#
# Usage:
#   ./benchmarks/generation_latency.sh
#   LLM_DATASET=benchmarks/llm/my_cases.json ./benchmarks/generation_latency.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ensure_results_dir
print_banner "Generation Latency (TTFT)"
preflight_services "true"

run_llm_eval ttft

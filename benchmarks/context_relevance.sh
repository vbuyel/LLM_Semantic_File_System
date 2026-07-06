#!/usr/bin/env bash
# Context relevance benchmark: retrieved documents vs user query.
#
# Usage:
#   ./benchmarks/context_relevance.sh
#   LLM_EVAL_OWNER=user@example.com ./benchmarks/context_relevance.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ensure_results_dir
print_banner "Context Relevance"
preflight_services "true"

run_llm_eval context_relevance

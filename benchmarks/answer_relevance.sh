#!/usr/bin/env bash
# Answer relevance benchmark: final answer vs user problem.
#
# Usage:
#   ./benchmarks/answer_relevance.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ensure_results_dir
print_banner "Answer Relevance"
preflight_services "true"

run_llm_eval answer_relevance

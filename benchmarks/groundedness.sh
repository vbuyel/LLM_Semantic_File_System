#!/usr/bin/env bash
# Groundedness / faithfulness benchmark: answer supported by retrieved context.
#
# Usage:
#   ./benchmarks/groundedness.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ensure_results_dir
print_banner "Groundedness (Faithfulness)"
preflight_services "true"

run_llm_eval groundedness

#!/bin/bash
# run_tests.sh
# Run pytest for all microservices in their respective virtual environments to avoid PYTHONPATH conflicts.

# Exit on first failure
set -e

# Get workspace root
WORKSPACE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting all microservice test suites..."

echo ""
echo "1/5 Running gateway_auth tests..."
cd "$WORKSPACE_ROOT/src/gateway_auth" && ./.venv/bin/pytest -v
cd "$WORKSPACE_ROOT"

echo ""
echo "2/5 Running llm tests..."
cd "$WORKSPACE_ROOT/src/llm" && ./.venv/bin/pytest -v
cd "$WORKSPACE_ROOT"

echo ""
echo "3/5 Running file_ops tests..."
cd "$WORKSPACE_ROOT/src/file_ops" && ./.venv/bin/pytest -v
cd "$WORKSPACE_ROOT"

echo ""
echo "4/5 Running event_db tests..."
cd "$WORKSPACE_ROOT/src/event_db" && ./.venv/bin/pytest -v
cd "$WORKSPACE_ROOT"

echo ""
echo "5/5 Running vector_db tests..."
cd "$WORKSPACE_ROOT/src/vector_db" && ./.venv/bin/pytest -v
cd "$WORKSPACE_ROOT"

echo ""
echo "All microservice test suites completed successfully!"

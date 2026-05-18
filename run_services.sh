#!/bin/bash
# run_services.sh
# Orchestrates starting all microservices in the background, including infrastructure, and stops them gracefully on Ctrl+C.

WORKSPACE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$WORKSPACE_ROOT/logs"
mkdir -p "$LOG_DIR"

echo "Starting LLM Semantic File System services..."

# PIDs list to kill on exit
declare -a PIDS=()

# Cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down all services..."
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            wait "$pid" 2>/dev/null
        fi
    done
    echo "All services stopped successfully!"
    exit 0
}

# Bind cleanup to SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM

# 1. Start Kafka Docker Container
echo "1. Starting Kafka infrastructure..."
cd "$WORKSPACE_ROOT/src/kafka"
docker-compose up -d
cd "$WORKSPACE_ROOT"

echo "Waiting for Kafka broker to start..."
sleep 5

# 2. Setup Kafka Topics
echo "2. Setting up Kafka topics..."
"$WORKSPACE_ROOT/src/file_ops/.venv/bin/python" "$WORKSPACE_ROOT/src/kafka/broker.py"

# 3. Start Python microservices in the background
echo "3. Starting LLM service on port 8001..."
cd "$WORKSPACE_ROOT/src/llm"
./.venv/bin/uvicorn v1.main:app --port 8001 > "$LOG_DIR/llm.log" 2>&1 &
PIDS+=($!)

echo "4. Starting File Operations service on port 8002..."
cd "$WORKSPACE_ROOT/src/file_ops"
./.venv/bin/uvicorn v1.main:app --port 8002 > "$LOG_DIR/file_ops.log" 2>&1 &
PIDS+=($!)

echo "5. Starting Event DB service on port 8003..."
cd "$WORKSPACE_ROOT/src/event_db"
./.venv/bin/uvicorn v1.main:app --port 8003 > "$LOG_DIR/event_db.log" 2>&1 &
PIDS+=($!)

echo "6. Starting Vector DB service on port 8004..."
cd "$WORKSPACE_ROOT/src/vector_db"
./.venv/bin/uvicorn v1.main:app --port 8004 > "$LOG_DIR/vector_db.log" 2>&1 &
PIDS+=($!)

echo "7. Starting Authentication & Gateway service on port 8000..."
cd "$WORKSPACE_ROOT/src/gateway_auth"
./.venv/bin/uvicorn v1.main:app --port 8000 > "$LOG_DIR/gateway_auth.log" 2>&1 &
PIDS+=($!)

# 4. Start UI static server
echo "8. Starting Frontend UI on port 5500..."
cd "$WORKSPACE_ROOT/ui"
npx serve -s . -p 5500 > "$LOG_DIR/ui.log" 2>&1 &
PIDS+=($!)

echo ""
echo "All services have been started!"
echo "----------------------------------------"
echo "Gateway (API): http://localhost:8000"
echo "Frontend UI:    http://localhost:5500"
echo "Logs saved to:  $LOG_DIR/"
echo "----------------------------------------"
echo "Press [Ctrl+C] to stop all services..."

# Keep the script running to keep trapping Ctrl+C
while true; do
    sleep 1
done

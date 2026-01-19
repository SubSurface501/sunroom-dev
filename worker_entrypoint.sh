#!/bin/bash
# DEBUG MODE: HTTP Server Only
set +e

PORT="${PORT:-8080}"
echo "--- DEBUG ENTRYPOINT STARTING (PYTHON 3.11 FULL) ---"
echo "--- PORT: $PORT ---"

# 1. Start HTTP Server
echo "--- STARTING HTTP SERVER ---"
python -u -m http.server "$PORT" &
HTTP_PID=$!
echo "--- HTTP SERVER PID: $HTTP_PID ---"

# 2. Monitor Loop
while true; do
    if ! kill -0 $HTTP_PID > /dev/null 2>&1; then
        echo "CRITICAL: HTTP Server died!"
        exit 1
    fi
    sleep 5
    echo "Server alive..."
done

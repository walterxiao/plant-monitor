#!/bin/bash
# Launch the Plant Monitor dashboard web server.
# Regenerates the dashboard page first so it always shows fresh data.
set -e
cd "$(dirname "$0")"
python3 dashboard.py
echo "Dashboard at http://localhost:8000/dashboard/  (Ctrl+C to stop)"
python3 serve.py

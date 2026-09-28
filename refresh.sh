#!/bin/bash
# Refresh everything: analyze new photos -> check alerts ->
# rebuild timelapse videos -> regenerate the dashboard page.
# (One command per line, not && chains: with set -e, a failed && list
# does NOT stop the script, but a failed simple command does.)
set -e
cd "$(dirname "$0")"
python3 analyze.py
python3 alerts.py
python3 timelapse.py
python3 dashboard.py
echo "Refreshed."

#!/bin/bash
# Refresh everything: analyze new photos -> check alerts ->
# rebuild timelapse videos -> regenerate the dashboard page.
cd "$(dirname "$0")"
python3 analyze.py && python3 alerts.py && python3 timelapse.py && python3 dashboard.py
echo "Refreshed."

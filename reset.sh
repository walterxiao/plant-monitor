#!/bin/bash
# Reset derived data (dashboard, videos, analysis) and rebuild from photos.
# Photos in data/photos/ are NEVER touched.
cd "$(dirname "$0")"

echo "This will DELETE and rebuild:"
echo "  - dashboard page ..... data/dashboard/"
echo "  - videos ............. data/videos/, data/frames/, videos_manifest.json"
echo "  - analysis data ...... data/metrics.jsonl"
echo "  - alert history ...... data/alerts.jsonl, data/state.json"
echo "Photos in data/photos/ are NOT touched."
echo
read -r -p "Type 'yes' to continue: " answer
if [ "$answer" != "yes" ]; then
    echo "Cancelled — nothing was deleted."
    exit 0
fi

rm -rf data/dashboard data/videos data/frames \
       data/metrics.jsonl data/videos_manifest.json \
       data/alerts.jsonl data/state.json
echo "Cleared. Rebuilding everything from photos (videos take a few minutes)..."
./refresh.sh

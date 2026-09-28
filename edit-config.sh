#!/bin/bash
# Open config.yaml for editing, then restart the capture service so the
# changes take effect. (The capture loop reads the config once at startup.)
cd "$(dirname "$0")"
"${EDITOR:-nano}" config.yaml
echo "Restarting capture service..."
sudo systemctl restart plant-capture.service
echo "Done — new settings are live."

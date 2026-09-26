#!/bin/bash
# Plant Monitor installer — run on the Raspberry Pi.
set -euo pipefail
cd "$(dirname "$0")"

echo "== system packages =="
sudo apt update
sudo apt install -y ffmpeg python3-pip python3-picamera2

echo "== python packages =="
pip3 install --break-system-packages -q \
  opencv-python numpy pyyaml astral matplotlib pillow

echo "== data directories =="
mkdir -p data/photos data/videos data/dashboard

echo "== systemd units =="
sudo cp systemd/plant-capture.service systemd/plant-daily.service \
        systemd/plant-daily.timer /etc/systemd/system/
# point the units at this checkout
sudo sed -i "s|/home/pi/plant-monitor|$(pwd)|g" \
  /etc/systemd/system/plant-capture.service \
  /etc/systemd/system/plant-daily.service
sudo systemctl daemon-reload
sudo systemctl enable --now plant-capture.service
sudo systemctl enable --now plant-daily.timer

echo
echo "Done. Capture loop is running; daily pipeline (analyze -> alerts ->"
echo "timelapse -> dashboard) runs at 22:30. Check status with:"
echo "  systemctl status plant-capture.service"
echo "  systemctl status plant-daily.timer"
echo "Serve the dashboard with:  python3 -m http.server 8000 --directory data/dashboard"

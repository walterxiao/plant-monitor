# Setup Guide — Plant Monitor on Raspberry Pi

Step-by-step from unboxing to your first timelapse. Assumes Raspberry Pi OS
(Bookworm) 64-bit. Total time: about 30 minutes plus one calibration day.

## 1. Assemble the hardware

1. Seat the Camera Module 3 ribbon cable into the Pi's CSI port (blue side
   facing the Ethernet port on a Pi 5, pull the connector latch first).
2. Mount the Pi + camera so the camera faces the plant, ~30–60 cm away, with
   the whole plant in frame. A small tripod or gooseneck mount works well.
3. Insert the flashed microSD card, connect power, and boot.

Tip: keep the camera position fixed from now on. The growth metrics measure
pixel changes, so bumping the camera looks like "growth."

## 2. Flash Raspberry Pi OS

1. Install [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on
   your computer.
2. Choose **Raspberry Pi OS Lite (64-bit)** — no desktop needed.
3. Click the gear icon first: set hostname (e.g. `plantpi`), enable SSH with
   your username/password, and configure Wi-Fi.
4. Write to the microSD card, insert it, and power on.

## 3. Install the software

SSH into the Pi, then:

```bash
git clone https://github.com/walterxiao/plant-monitor.git
cd plant-monitor
./install.sh
```

This installs system packages (ffmpeg, python3-picamera2, …), creates a
Python virtualenv, and installs dependencies.

## 4. Configure

Edit `config.yaml`:

- `plant_name` — your plant's name (shows up in the dashboard/video).
- `location` — set `latitude`/`longitude` for your spot so daylight hours are
  computed correctly, or switch to `mode: indoor` with fixed `start`/`end`
  hours matching your grow light / room lighting.
- `capture.interval_minutes` — 10 is a good default (~150 MB/day of photos).
- `alerts.ntfy_topic` — optional; set a topic name to get phone push alerts
  via [ntfy.sh](https://ntfy.sh) (install the ntfy app on your phone and
  subscribe to the same topic).

Validate the config before going further:

```bash
./venv/bin/python -c "import yaml; print(yaml.safe_load(open('config.yaml'))['plant_name'])"
```

## 5. Test the camera

```bash
./venv/bin/python -c "
from picamera2 import Picamera2
cam = Picamera2()
cam.start()
cam.capture_file('test.jpg')
cam.stop()
print('ok')"
```

Open `test.jpg` (copy it to your computer with `scp`) and check framing.
Adjust the camera until the whole plant is in frame with a little margin.

## 6. Calibrate (important — do this on day 1)

The yellowing alert compares against a baseline of your plant when healthy.
Run the analyzer on today's photos to build it:

```bash
./venv/bin/python analyze.py --calibrate
```

Do this once, on a day the plant looks healthy. If the plant is already
struggling, fix it first, then calibrate — otherwise "sick" becomes normal.

## 7. Enable automatic capture

```bash
sudo cp systemd/plant-capture.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now plant-capture.service
```

The service takes a photo every `interval_minutes` during daylight hours and
skips dark frames. Check it's running:

```bash
sudo systemctl status plant-capture.service
```

## 8. Enable the daily job (metrics, alerts, video, dashboard)

The daily job runs at 22:30: analyzes the day's photos, checks alert rules,
rebuilds the timelapse videos, and regenerates the dashboard.

```bash
sudo cp systemd/plant-daily.service systemd/plant-daily.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now plant-daily.timer
```

You can also run it manually any time:

```bash
./venv/bin/python analyze.py
./venv/bin/python alerts.py
./venv/bin/python timelapse.py
./venv/bin/python dashboard.py
```

## 9. View your dashboard

After the first daily run, open `data/dashboard/index.html` in a browser
(copy it to your computer, or serve it: `python3 -m http.server` in
`data/dashboard/`).

You'll see the latest photo, growth charts, any alerts, and links to the
daily timelapse videos.

## What happens each day

| Time | What |
|------|------|
| Daylight hours | Photo every 10 min → `data/photos/YYYY-MM-DD/` |
| 22:30 | `plant-daily` runs: metrics → `data/metrics.jsonl`, alerts checked (phone push if ntfy set), timelapse rebuilt, dashboard regenerated |

## Interpreting alerts

- **Wilting suspected** — green area AND plant height both dropped vs the
  3-day median. Usually underwatering. Check soil moisture.
- **Yellowing spike** — yellow pixels jumped vs your calibration baseline.
  Often overwatering or nutrient deficiency.
- **Growth stalled** — less than 2% area change in 7 days. Could be normal
  (dormancy) or a light/nutrient issue.
- **No usable frames** — the camera saw only dark frames all day. Check the
  camera didn't get covered or unplugged.

Alerts dedupe: each rule notifies once, then reminds at most every 3 days
while the condition persists.

## Troubleshooting

- **"Camera not detected"** — reseat the ribbon cable (power off first).
  On Pi 5, make sure you used the correct CSI port and latch.
- **Black photos** — the daylight gate may be wrong for your location; check
  `location` in `config.yaml` or switch to `mode: indoor`.
- **Service won't start** — `sudo journalctl -u plant-capture.service -e`
  shows the error log.
- **Dashboard is empty** — the daily job hasn't run yet; run the four
  commands in step 8 manually.
- **Disk filling up** — photos run ~150 MB/day at 10-min intervals. The
  config's `storage.max_days` setting auto-prunes old photos (timelapse
  videos are kept).

## Updating

```bash
cd ~/plant-monitor
git pull
sudo systemctl restart plant-capture.service
```

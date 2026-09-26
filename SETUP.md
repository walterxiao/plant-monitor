# Setup Guide — Plant Monitor on Raspberry Pi

Step-by-step from unboxing to your first timelapse. Assumes Raspberry Pi OS
(Bookworm) 64-bit and a Mac laptop. Total time: about 45 minutes plus one
calibration day.

## 1. Assemble the hardware

1. Seat the camera ribbon cable into the Pi's CSI port. On the Pi 5, pull up
   the connector latch first, slide the cable in with the blue side facing
   the Ethernet port, then push the latch back down. (The Arducam module's
   included 15-to-22-pin cable is the one that fits the Pi 5.)
2. Mount the Pi + camera so the camera faces the plant, ~30–60 cm away, with
   the whole plant in frame. A small tripod or gooseneck mount works well.
3. Insert the flashed microSD card (see step 2), connect power, and boot.

Tip: keep the camera position fixed from now on. The growth metrics measure
pixel changes, so bumping the camera looks like "growth."

## 2. Flash Raspberry Pi OS (on your Mac)

1. Install [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on
   your Mac.
2. Choose **Raspberry Pi OS Lite (64-bit)** — no desktop needed.
3. Click the gear icon *before* writing:
   - Set hostname to `plantpi`
   - Enable SSH, "Use password authentication", and set your username
     (e.g. `pi`) and a password
   - Configure Wi-Fi with your network name and password
   - Set timezone to America/New_York
4. Write to the microSD card, insert it into the Pi, and power on. Give it
   1–2 minutes to boot and join Wi-Fi.

> **Do I need to connect the Pi to a network?** Not strictly — photo
> capture, analysis, timelapse, and the dashboard all work offline. But
> it's strongly recommended, because the Pi has no battery-backed clock:
> without network, its time resets on every reboot (breaking photo
> timestamps, sunrise/sunset math, and alert timing). Wi-Fi also enables
> phone push alerts and viewing the dashboard from your Mac. If you ever
> run it fully offline, add a DS3231 real-time-clock module (~$5) and set
> the time manually.

## 3. Connect to the Pi from your Mac

Everything below happens in **Terminal** on your Mac
(Applications → Utilities → Terminal). You'll do all Pi work through SSH —
no monitor or keyboard needed for the Pi itself.

**Find the Pi on your network.** macOS can usually reach it by name:

```bash
ping -c 2 plantpi.local
```

If you get replies, the name works. If not, find its IP address: open your
router's admin page (often `http://192.168.1.1`) and look for `plantpi` in
the device list, then use that IP instead of `plantpi.local` below.

**SSH in:**

```bash
ssh pi@plantpi.local
```

The first time, you'll see a warning about the host's authenticity — type
`yes`. That's normal; it's SSH introducing itself. Enter the password you
set in the Imager. You're now typing commands *on the Pi* — your prompt
changes to something like `pi@plantpi:~ $`.

**Useful Mac ↔ Pi moves:**

- *Copy a file from the Pi to your Mac* (run this in a Mac Terminal tab,
  not inside SSH):
  ```bash
  scp pi@plantpi.local:~/plant-monitor/test.jpg ~/Desktop/
  ```
- *Copy a whole folder* (e.g. the dashboard):
  ```bash
  scp -r pi@plantpi.local:~/plant-monitor/data/dashboard ~/Desktop/
  ```
- *View the dashboard in your Mac's browser without copying anything* —
  on the Pi, run:
  ```bash
  cd ~/plant-monitor/data/dashboard && python3 -m http.server 8000
  ```
  then open `http://plantpi.local:8000` in Safari/Chrome on your Mac.
  (Press Ctrl+C on the Pi to stop the server when done.)
- *Edit files on the Pi from your Mac:* `nano` works fine over SSH
  (`nano ~/plant-monitor/config.yaml`; Ctrl+O to save, Ctrl+X to exit).
  If you use VS Code, install the "Remote - SSH" extension and connect to
  `pi@plantpi.local` for full GUI editing.

Keep one Terminal tab SSH'd into the Pi for the steps below.

## 4. First-boot Pi setup (on the Pi, over SSH)

```bash
sudo apt update && sudo apt upgrade -y
```

This pulls the latest OS updates — takes a few minutes the first time.

**Verify the camera is detected:**

```bash
rpicam-hello --list-cameras
```

You should see the IMX708 sensor listed. If it says "no cameras found,"
power off the Pi and reseat the ribbon cable (latch up, cable fully in,
latch down).

## 5. Install the plant-monitor software (on the Pi)

```bash
git clone https://github.com/walterxiao/plant-monitor.git
cd plant-monitor
./install.sh
```

This installs system packages (ffmpeg, python3-picamera2, …), creates a
Python virtualenv, and installs dependencies.

## 6. Configure

Edit `config.yaml` (on the Pi: `nano ~/plant-monitor/config.yaml`):

- `plant_name` — your plant's name (shows up in the dashboard/video).
- `lighting` — set `latitude`/`longitude` for your spot so daylight hours
  are computed correctly, or switch to `mode: indoor` with fixed
  `indoor_start`/`indoor_end` hours matching your grow light / room lighting.
- `camera.interval_minutes` — 10 is a good default (~150 MB/day of photos).
- `alerts.ntfy_topic` — optional; set a topic name to get phone push alerts
  via [ntfy.sh](https://ntfy.sh) (install the ntfy app on your phone and
  subscribe to the same topic).

Quick sanity check of the file:

```bash
./venv/bin/python -c "import yaml; print(yaml.safe_load(open('config.yaml'))['plant_name'])"
```

## 7. Test the camera (on the Pi)

```bash
./venv/bin/python -c "
from picamera2 import Picamera2
cam = Picamera2()
cam.start()
cam.capture_file('test.jpg')
cam.stop()
print('ok')"
```

Copy `test.jpg` to your Mac (`scp pi@plantpi.local:~/plant-monitor/test.jpg
~/Desktop/` from a Mac Terminal tab) and check the framing. Adjust the
camera until the whole plant is in frame with a little margin.

## 8. Calibrate (important — do this on day 1)

The yellowing alert compares against a baseline of your plant when healthy.
Take a few photos, then run:

```bash
./venv/bin/python analyze.py
```

Do this once, on a day the plant looks healthy. If the plant is already
struggling, fix it first, then calibrate — otherwise "sick" becomes normal.

## 9. Enable automatic capture (on the Pi)

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

## 10. Enable the daily job (on the Pi)

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

## 11. View your dashboard (on your Mac)

After the first daily run, either:

- **Over the network** (nothing to copy): on the Pi run
  `cd ~/plant-monitor/data/dashboard && python3 -m http.server 8000`,
  then open `http://plantpi.local:8000` in your Mac's browser; or
- **Copy it once**: `scp -r pi@plantpi.local:~/plant-monitor/data/dashboard
  ~/Desktop/` and open `~/Desktop/dashboard/index.html`.

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

- **Can't reach `plantpi.local`** — use the IP from your router's device
  list instead (`ssh pi@192.168.1.XX`). Some routers are slow with `.local`
  names; the IP always works.
- **SSH "connection refused"** — SSH wasn't enabled in the Imager settings.
  Re-flash with SSH enabled (step 2), or plug in a keyboard/monitor once
  and run `sudo systemctl enable --now ssh`.
- **"Camera not detected"** — reseat the ribbon cable (power off first).
  On Pi 5, make sure you used the correct CSI port and latch.
- **Black photos** — the daylight gate may be wrong for your location; check
  `lighting` in `config.yaml` or switch to `mode: indoor`.
- **Service won't start** — `sudo journalctl -u plant-capture.service -e`
  shows the error log.
- **Dashboard is empty** — the daily job hasn't run yet; run the four
  commands in step 10 manually.
- **Disk filling up** — photos run ~150 MB/day at 10-min intervals. The
  config's `storage.max_days` setting auto-prunes old photos (timelapse
  videos are kept).

## Updating

```bash
cd ~/plant-monitor
git pull
sudo systemctl restart plant-capture.service
```

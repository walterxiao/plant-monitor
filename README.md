# 🌱 Plant Monitor

A Raspberry Pi + camera + computer-vision system that watches your plant grow,
measures it every day, alerts you when something looks wrong, and renders it
all into a timelapse video.

```
camera ──▶ capture.py ──▶ photos/YYYY-MM-DD/*.jpg
                              │
                              ▼
                         analyze.py ──▶ metrics.jsonl (green %, height, yellow %)
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
          alerts.py      timelapse.py    dashboard.py
          (wilting,       (daily + full   (charts, latest
           yellowing,     growth videos   photo, alerts)
           stalled)
```

## Hardware

| Part | Notes |
|---|---|
| Raspberry Pi 5 (4GB) | Pi 4 works; Zero 2W works for capture-only |
| Pi Camera Module 3 | 12MP, autofocus — the one to get (~$25) |
| Official Pi 5 power supply | Camera + CV load needs stable 5V/5A |
| 64GB+ microSD | ~150 MB/day at defaults → months of headroom |
| Small tripod / mount | **Do not move it once started** — metrics compare frame-to-frame |
| Consistent light | Grow light on a timer, or a bright window spot |

## Setup

1. Flash Raspberry Pi OS (64-bit) and boot the Pi.
2. Connect the camera ribbon cable, then verify: `rpicam-still -o test.jpg`
3. Copy this project to the Pi (e.g. `~/plant-monitor`), edit `config.yaml`:
   - `plant_name`, your `latitude`/`longitude`
   - `lighting.mode`: `outdoor` (sunrise/sunset capture) or `indoor` (fixed hours)
   - `alerts.ntfy_topic` for phone push alerts (optional, see below)
4. Run `./install.sh`. The capture loop starts immediately; the daily
   pipeline (analyze → alerts → timelapse → dashboard) runs at 22:30.

## How the AI works

No cloud, no API keys — everything runs on the Pi with OpenCV:

- **Green segmentation** (HSV color mask) measures green % of frame and the
  plant's bounding-box height/width each photo. Green area is the growth proxy;
  height tracks vertical growth.
- **Yellow segmentation** is the stress proxy — a jump above your plant's
  3-day calibration baseline suggests nutrient/light issues.
- **Wilting** fires only when green % *and* height both drop vs the 3-day
  median (either alone is usually just lighting noise).
- **Stalled** fires after 7 days with <2% area change.
- **Dark-frame check** catches a failed grow light or covered lens (a dark
  photo in daytime means the *light* failed, not the plant).

The first 3 days are calibration — no growth alerts until there's a baseline.

## Phone alerts (optional, free)

1. Install the ntfy app (iOS/Android) and pick a random topic name.
2. Set `alerts.ntfy_topic` in `config.yaml` to that name.
3. Critical alerts (wilting) and warnings land on your phone.

## Viewing

- **Dashboard**: `python3 serve.py`,
  then open http://localhost:8000/dashboard/
  (serves `data/` so the page's `../videos/` links resolve, and powers
  the dashboard's "Refresh now" button),
  then open `http://<pi-ip>:8000` — latest photo, growth charts, alerts, videos.
- **Videos**: `data/videos/growth-timelapse.mp4` (full run) plus one per day.
  Frames carry the date, day number, live metrics, and a growth sparkline.

## Tuning

- **Thresholds too twitchy?** Raise `wilt_green_drop_pct` / `wilt_height_drop_pct`
  in `config.yaml`.
- **Wrong greens?** If your plant reads low-green, widen `green_hsv_high`
  (e.g. hue up to 90) — check a photo's HSV values first.
- **Disk**: lower `camera.resolution` or raise `interval_minutes`. At 10-min
  intervals the overlay rendering takes ~5 min/day on a Pi 5.

## Upgrade path

The metrics layer (`metrics.jsonl`) is model-agnostic. If you outgrow HSV
segmentation, swap `analyze.py`'s mask for a U-Net leaf-segmentation model —
alerts, timelapse, and dashboard keep working unchanged.

## Files

| File | What it does |
|---|---|
| `capture.py` | daylight-gated capture loop with dark-frame skip |
| `analyze.py` | per-photo CV metrics → `metrics.jsonl` |
| `alerts.py` | rule engine → `alerts.jsonl` + ntfy push |
| `timelapse.py` | PIL overlay frames + ffmpeg daily/full videos |
| `dashboard.py` | static HTML dashboard with growth charts |
| `config.yaml` | all tunables in one place |
| `install.sh` | one-shot Pi setup + systemd registration |

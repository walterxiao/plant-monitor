#!/usr/bin/env python3
"""Plant Monitor — capture loop.

Takes a photo on a fixed interval during the daylight window and skips
frames that are too dark (lights off / night). Runs forever; manage it
with the plant-capture systemd service.
"""
import time
from datetime import date, datetime
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent


def load_config() -> dict:
    with open(ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


def in_daylight(cfg: dict) -> bool:
    now = datetime.now()
    lighting = cfg["lighting"]
    if lighting["mode"] == "indoor":
        start = datetime.strptime(lighting["indoor_start"], "%H:%M").time()
        end = datetime.strptime(lighting["indoor_end"], "%H:%M").time()
        return start <= now.time() <= end
    # outdoor: sunrise/sunset from coordinates
    from astral import LocationInfo
    from astral.sun import sun

    loc = LocationInfo(
        latitude=lighting["latitude"], longitude=lighting["longitude"]
    )
    s = sun(loc.observer, date=date.today())
    sunrise = s["sunrise"].replace(tzinfo=None)
    sunset = s["sunset"].replace(tzinfo=None)
    return sunrise <= now <= sunset


def resolve_data_dir(cfg: dict) -> Path:
    p = Path(cfg["paths"]["data_dir"])
    return p if p.is_absolute() else ROOT / p


def main() -> None:
    cfg = load_config()
    from picamera2 import Picamera2

    picam = Picamera2()
    w, h = cfg["camera"]["resolution"]
    picam.configure(picam.create_still_configuration(main={"size": (w, h)}))
    picam.start()
    time.sleep(2)  # sensor warmup / auto-exposure settle

    data_dir = resolve_data_dir(cfg)
    interval = cfg["camera"]["interval_minutes"] * 60
    min_brightness = cfg["analysis"]["min_brightness"]
    quality = cfg["camera"]["jpeg_quality"]

    print(f"capture loop started, interval={cfg['camera']['interval_minutes']}min",
          flush=True)
    while True:
        try:
            if in_daylight(cfg):
                frame = picam.capture_array()  # RGB numpy array
                brightness = float(np.mean(frame))
                if brightness >= min_brightness:
                    now = datetime.now()
                    day_dir = data_dir / "photos" / now.strftime("%Y-%m-%d")
                    day_dir.mkdir(parents=True, exist_ok=True)
                    path = day_dir / (now.strftime("%H%M%S") + ".jpg")
                    # full-quality still (separate from the preview array)
                    picam.capture_file(str(path), quality=quality)
                    print(f"captured {path} (brightness {brightness:.0f})",
                          flush=True)
                else:
                    print(f"skipped dark frame (brightness {brightness:.0f})",
                          flush=True)
            time.sleep(interval)
        except Exception as e:  # never let the loop die silently
            print(f"capture error: {e}", flush=True)
            time.sleep(60)


if __name__ == "__main__":
    main()

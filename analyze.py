#!/usr/bin/env python3
"""Plant Monitor — per-photo growth metrics.

For every new photo, computes:
  green_ratio   % of frame that is green (growth proxy)
  green_area_px green pixel count
  height_px     height of the largest green blob (plant-height proxy)
  width_px      width of the largest green blob
  yellow_ratio  % of frame that is yellow (stress proxy)
  brightness    mean frame brightness (exposure sanity)

Appends one JSON line per photo to data/metrics.jsonl. Idempotent:
already-processed files are skipped.
"""
import json
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent


def load_config() -> dict:
    with open(ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


def resolve_data_dir(cfg: dict) -> Path:
    p = Path(cfg["paths"]["data_dir"])
    return p if p.is_absolute() else ROOT / p


def photo_timestamp(path: Path) -> str:
    # photos are stored as data/photos/YYYY-MM-DD/HHMMSS.jpg
    ts = datetime.strptime(f"{path.parent.name} {path.stem}", "%Y-%m-%d %H%M%S")
    return ts.isoformat()


def analyze_image(path: Path, cfg: dict) -> dict | None:
    img = cv2.imread(str(path))
    if img is None:
        return None
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    a = cfg["analysis"]

    green = cv2.inRange(hsv, np.array(a["green_hsv_low"]),
                        np.array(a["green_hsv_high"]))
    yellow = cv2.inRange(hsv, np.array(a["yellow_hsv_low"]),
                         np.array(a["yellow_hsv_high"]))

    total = img.shape[0] * img.shape[1]
    green_area = int(cv2.countNonZero(green))

    # largest green blob -> plant bounding box (tolerates the pot shifting
    # a little within the frame; fails only if the plant leaves the view)
    height_px = width_px = 0
    contours, _ = cv2.findContours(green, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        c = max(contours, key=cv2.contourArea)
        _x, _y, w, h = cv2.boundingRect(c)
        width_px, height_px = int(w), int(h)

    return {
        "file": str(path.relative_to(resolve_data_dir(cfg))),
        "timestamp": photo_timestamp(path),
        "green_ratio": round(green_area / total, 5),
        "green_area_px": green_area,
        "height_px": height_px,
        "width_px": width_px,
        "yellow_ratio": round(int(cv2.countNonZero(yellow)) / total, 5),
        "brightness": round(float(np.mean(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))), 1),
    }


def main() -> None:
    cfg = load_config()
    data_dir = resolve_data_dir(cfg)
    metrics_path = data_dir / "metrics.jsonl"

    processed: set[str] = set()
    if metrics_path.exists():
        with open(metrics_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    processed.add(json.loads(line)["file"])

    photos = sorted((data_dir / "photos").rglob("*.jpg"))
    new = [p for p in photos
           if str(p.relative_to(data_dir)) not in processed]
    if not new:
        print("analyze: nothing new", flush=True)
        return

    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(metrics_path, "a") as out:
        for photo in new:
            m = analyze_image(photo, cfg)
            if m is None:
                print(f"analyze: unreadable {photo}", flush=True)
                continue
            out.write(json.dumps(m) + "\n")
            n += 1
    print(f"analyze: {n} new photos -> {metrics_path}", flush=True)


if __name__ == "__main__":
    main()

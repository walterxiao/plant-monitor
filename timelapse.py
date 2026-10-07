#!/usr/bin/env python3
"""Plant Monitor — timelapse video builder.

Renders overlay frames with PIL (date, day number, live growth metrics,
and a mini growth-curve sparkline drawn from the metrics history) for
every photo, then encodes a single end-to-end growth-timelapse.mp4
with ffmpeg.

Idempotent: skipped unless the photo count changed since the last build.
"""
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent


def load_config() -> dict:
    with open(ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


def resolve_data_dir(cfg: dict) -> Path:
    p = Path(cfg["paths"]["data_dir"])
    return p if p.is_absolute() else ROOT / p


def median(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n else 0.0


def load_metrics_by_file(data_dir: Path) -> dict[str, dict]:
    path = data_dir / "metrics.jsonl"
    out: dict[str, dict] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                out[r["file"]] = r
    return out


def daily_green_history(data_dir: Path) -> list[tuple[str, float]]:
    """[(day, median green_ratio)] for the sparkline, oldest -> newest."""
    by_day: dict[str, list[float]] = {}
    path = data_dir / "metrics.jsonl"
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                by_day.setdefault(r["timestamp"][:10], []).append(r["green_ratio"])
    return [(d, median(v)) for d, v in sorted(by_day.items())]


def cover_resize(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    tw, th = size
    scale = max(tw / img.width, th / img.height)
    img = img.resize((int(img.width * scale), int(img.height * scale)))
    x = (img.width - tw) // 2
    y = (img.height - th) // 2
    return img.crop((x, y, x + tw, y + th))


def draw_sparkline(draw: ImageDraw.ImageDraw, history: list[tuple[str, float]],
                   box: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle(box, fill=(0, 0, 0, 140))
    if len(history) < 2:
        return
    vals = [v for _, v in history]
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1e-9
    n = len(history)
    pts = [(x0 + 8 + i * (x1 - x0 - 16) / (n - 1),
            y1 - 8 - (v - lo) / span * (y1 - y0 - 16)) for i, (_, v) in enumerate(history)]
    draw.line(pts, fill=(120, 255, 120), width=3)
    draw.ellipse([pts[-1][0] - 5, pts[-1][1] - 5, pts[-1][0] + 5, pts[-1][1] + 5],
                 fill=(120, 255, 120))


def render_all(all_photos: list[tuple[str, Path]], first_day: str, cfg: dict,
               data_dir: Path, metrics: dict[str, dict],
               history: list[tuple[str, float]], frames_dir: Path) -> Path:
    """Render overlay frames for every photo (all days), sequentially numbered."""
    tw, th = cfg["timelapse"]["overlay_size"]
    font_big = ImageFont.load_default(size=44)
    font_sm = ImageFont.load_default(size=28)
    first_dt = datetime.strptime(first_day, "%Y-%m-%d")

    for i, (day, photo) in enumerate(all_photos):
        img = cover_resize(Image.open(photo).convert("RGB"), (tw, th)).convert("RGBA")
        overlay = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        day_num = (datetime.strptime(day, "%Y-%m-%d") - first_dt).days + 1
        # top bar
        d.rectangle([0, 0, tw, 110], fill=(0, 0, 0, 130))
        d.text((24, 14), f"{cfg['plant_name']} - day {day_num} - {day}",
               font=font_big, fill=(255, 255, 255))
        m = metrics.get(str(photo.relative_to(data_dir)))
        if m:
            d.text((24, 62),
                   f"green {m['green_ratio']:.1%}   "
                   f"height {m['height_px']}px   {photo.stem[:2]}:{photo.stem[2:4]}",
                   font=font_sm, fill=(200, 255, 200))
        # growth sparkline, bottom-right
        draw_sparkline(d, [h for h in history if h[0] <= day],
                       (tw - 340, th - 150, tw - 24, th - 24))
        d.text((tw - 340, th - 178), "growth", font=font_sm, fill=(255, 255, 255))
        img = Image.alpha_composite(img, overlay).convert("RGB")
        img.save(frames_dir / f"{i:06d}.jpg", quality=88)
    return frames_dir


def encode(frames_dir: Path, out_path: Path, fps: int) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-framerate", str(fps),
         "-i", str(frames_dir / "%06d.jpg"),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
         str(out_path)],
        check=True, capture_output=True,
    )


def main() -> None:
    cfg = load_config()
    data_dir = resolve_data_dir(cfg)
    photos_root = data_dir / "photos"
    videos_dir = data_dir / "videos"
    if not photos_root.exists():
        print("timelapse: no photos yet", flush=True)
        return

    metrics = load_metrics_by_file(data_dir)
    history = daily_green_history(data_dir)
    fps = cfg["timelapse"]["fps"]
    manifest = data_dir / "videos_manifest.json"
    done: dict = json.loads(manifest.read_text()) if manifest.exists() else {}

    # every photo across all days, oldest -> newest
    all_photos: list[tuple[str, Path]] = []
    for day_dir in sorted(p for p in photos_root.iterdir() if p.is_dir()):
        for photo in sorted(day_dir.glob("*.jpg")):
            all_photos.append((day_dir.name, photo))
    if not all_photos:
        print("timelapse: no photos yet", flush=True)
        return

    full = videos_dir / "growth-timelapse.mp4"
    if done.get("full") == len(all_photos) and full.exists():
        print(f"timelapse: full video up to date ({len(all_photos)} frames)",
              flush=True)
        return

    first_day = min(day for day, _ in all_photos)
    frames_dir = data_dir / "frames" / "full"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for f in frames_dir.glob("*.jpg"):  # clear stale frames from shorter runs
        f.unlink()
    render_all(all_photos, first_day, cfg, data_dir, metrics, history, frames_dir)
    encode(frames_dir, full, fps)
    if not cfg["timelapse"]["keep_overlay_frames"]:
        shutil.rmtree(frames_dir, ignore_errors=True)
    manifest.write_text(json.dumps({"full": len(all_photos)}, indent=2))
    print(f"timelapse: full video -> {full} ({len(all_photos)} frames)", flush=True)


if __name__ == "__main__":
    main()

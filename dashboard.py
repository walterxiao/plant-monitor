#!/usr/bin/env python3
"""Plant Monitor — dashboard generator.

Renders data/dashboard/index.html with:
  - latest photo
  - growth charts (green % and plant height over time)
  - current stats (days tracked, growth since day 1)
  - recent alerts
  - links to daily + full timelapse videos
Regenerate after analyze/alerts/timelapse run.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

import matplotlib
import yaml

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent


def load_config() -> dict:
    with open(ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


def resolve_data_dir(cfg: dict) -> Path:
    p = Path(cfg["paths"]["data_dir"])
    return p if p.is_absolute() else ROOT / p


def load_rows(data_dir: Path) -> list[dict]:
    path = data_dir / "metrics.jsonl"
    if not path.exists():
        return []
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    for r in rows:
        r["_dt"] = datetime.fromisoformat(r["timestamp"])
    return sorted(rows, key=lambda r: r["_dt"])


def main() -> None:
    cfg = load_config()
    data_dir = resolve_data_dir(cfg)
    dash = data_dir / "dashboard"
    dash.mkdir(parents=True, exist_ok=True)
    rows = load_rows(data_dir)

    latest_img = ""
    stats_html = "<p>No photos yet — the capture loop hasn't run.</p>"
    chart_html = ""
    if rows:
        # latest photo
        latest = max((data_dir / "photos").rglob("*.jpg"),
                     key=lambda p: p.stat().st_mtime)
        shutil.copy(latest, dash / "latest.jpg")
        latest_img = '<img src="latest.jpg" style="max-width:100%">'

        # charts
        times = [r["_dt"] for r in rows]
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
        ax1.plot(times, [r["green_ratio"] * 100 for r in rows], color="green")
        ax1.set_ylabel("green % of frame")
        ax1.set_title(f"{cfg['plant_name']} — growth")
        ax1.grid(alpha=0.3)
        ax2.plot(times, [r["height_px"] for r in rows], color="darkgreen")
        ax2.set_ylabel("height (px)")
        ax2.set_xlabel("time")
        ax2.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(dash / "growth.png", dpi=90)
        plt.close(fig)
        chart_html = '<img src="growth.png" style="max-width:100%">'

        first = rows[0]["green_ratio"] or 1e-9
        growth = (rows[-1]["green_ratio"] - rows[0]["green_ratio"]) / first * 100
        days = (rows[-1]["_dt"] - rows[0]["_dt"]).days + 1
        stats_html = (
            f"<ul><li>Tracking for <b>{days}</b> days "
            f"({len(rows)} photos)</li>"
            f"<li>Green area change since day 1: <b>{growth:+.1f}%</b></li>"
            f"<li>Current height: <b>{rows[-1]['height_px']}px</b>, "
            f"yellow: <b>{rows[-1]['yellow_ratio']:.1%}</b></li></ul>"
        )

    # alerts
    alerts_path = data_dir / "alerts.jsonl"
    alerts_html = "<p>No alerts.</p>"
    if alerts_path.exists():
        items = [json.loads(l) for l in alerts_path.read_text().splitlines()
                 if l.strip()]
        if items:
            lis = "".join(
                f"<li><b>[{a['severity']}]</b> {a['timestamp'][:16]} — "
                f"{a['message']}</li>" for a in reversed(items[-20:])
            )
            alerts_html = f"<ul>{lis}</ul>"

    # videos
    videos_dir = data_dir / "videos"
    vids_html = "<p>No videos yet.</p>"
    if videos_dir.exists():
        links = "".join(
            f'<li><a href="../videos/{p.name}">{p.name}</a></li>'
            for p in sorted(videos_dir.glob("*.mp4"))
        )
        if links:
            vids_html = f"<ul>{links}</ul>"

    (dash / "index.html").write_text(f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{cfg['plant_name']} — Plant Monitor</title></head>
<body style="font-family:sans-serif;max-width:900px;margin:auto;padding:16px">
<h1>🌱 {cfg['plant_name']}</h1>
<h2>Latest</h2>{latest_img}
<h2>Stats</h2>{stats_html}
<h2>Growth</h2>{chart_html}
<h2>Alerts</h2>{alerts_html}
<h2>Timelapses</h2>{vids_html}
<p style="color:#888">Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
</body></html>""")
    print(f"dashboard: {dash / 'index.html'}", flush=True)


if __name__ == "__main__":
    main()

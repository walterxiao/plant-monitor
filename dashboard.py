#!/usr/bin/env python3
"""Plant Monitor — dashboard generator.

Renders data/dashboard/index.html with:
  - latest photo
  - growth charts (green % and plant height over time)
  - current stats (days tracked, growth since day 1)
  - recent alerts
  - links to daily + full timelapse videos
  - last/next refresh timestamps + a manual "Refresh now" button
    (the button needs serve.py — plain http.server can't run refreshes)
Regenerate after analyze/alerts/timelapse run.
"""
import json
import shutil
import subprocess
from datetime import datetime, timedelta
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


def hourly_timer_active() -> bool:
    """True if the hourly refresh timer is running on this machine."""
    try:
        r = subprocess.run(["systemctl", "is-active", "plant-hourly.timer"],
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() == "active"
    except Exception:
        return False


def write_status(data_dir: Path, **updates) -> dict:
    """Read-modify-write data/refresh_status.json.

    Never clobbers keys managed by serve.py (e.g. refresh_in_progress).
    """
    path = data_dir / "refresh_status.json"
    status: dict = {}
    if path.exists():
        try:
            status = json.loads(path.read_text())
        except Exception:
            status = {}
    status.setdefault("refresh_in_progress", False)
    status.update(updates)
    path.write_text(json.dumps(status))
    return status


def fmt_time(dt: datetime) -> str:
    return dt.strftime("%b %-d, %Y %-I:%M %p")


def refresh_section(now: datetime) -> str:
    """HTML block: last/next refresh timestamps + manual refresh button."""
    if hourly_timer_active():
        next_run = (now.replace(minute=0, second=0, microsecond=0)
                    + timedelta(hours=1))
        next_html = f"Next refresh: <b>{fmt_time(next_run)}</b> (hourly)"
    else:
        next_html = ("Next refresh: <b>not scheduled</b> — install the hourly "
                     "timer or use the Refresh button below")
    return f"""
<h2>Refresh</h2>
<p>Last refresh: <b>{fmt_time(now)}</b><br>{next_html}</p>
<p><button id="refreshBtn" onclick="manualRefresh()"
style="font-size:16px;padding:8px 16px;cursor:pointer">↻ Refresh now</button>
<span id="refreshMsg" style="margin-left:8px;color:#555"></span></p>
<script>
const pageRefresh = "{now.isoformat(timespec='seconds')}";
async function manualRefresh() {{
  const btn = document.getElementById('refreshBtn');
  const msg = document.getElementById('refreshMsg');
  btn.disabled = true;
  msg.textContent = 'Starting refresh…';
  const t0 = Date.now();
  try {{
    const r = await fetch('/api/refresh', {{method: 'POST'}});
    if (r.status === 409) {{
      msg.textContent = 'A refresh is already running — waiting for it to finish…';
    }}
  }} catch (e) {{
    msg.textContent = 'Could not reach the refresh server.';
    btn.disabled = false;
    return;
  }}
  const poll = setInterval(async () => {{
    try {{
      const s = await (await fetch('/refresh_status.json', {{cache: 'no-store'}})).json();
      if (!s.refresh_in_progress && s.last_refresh && s.last_refresh !== pageRefresh) {{
        clearInterval(poll);
        msg.textContent = 'Done — reloading…';
        location.reload();
      }} else if (!s.refresh_in_progress && s.last_error) {{
        clearInterval(poll);
        msg.textContent = 'Refresh failed — check the Pi and try again.';
        btn.disabled = false;
      }} else {{
        msg.textContent = 'Refreshing… ' + Math.round((Date.now() - t0) / 1000) + 's';
      }}
    }} catch (e) {{ /* status file not written yet — keep waiting */ }}
  }}, 5000);
}}
</script>"""


def main() -> None:
    cfg = load_config()
    data_dir = resolve_data_dir(cfg)
    dash = data_dir / "dashboard"
    dash.mkdir(parents=True, exist_ok=True)
    rows = load_rows(data_dir)
    now = datetime.now()
    write_status(data_dir, last_refresh=now.isoformat(timespec="seconds"))

    latest_img = ""
    stats_html = "<p>No photos yet — the capture loop hasn't run.</p>"
    chart_html = ""
    if rows:
        # latest photo
        latest = max((data_dir / "photos").rglob("*.jpg"),
                     key=lambda p: p.stat().st_mtime)
        shutil.copy(latest, dash / "latest.jpg")
        v = int(now.timestamp())
        latest_img = f'<img src="latest.jpg?v={v}" style="max-width:100%">'

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
        chart_html = f'<img src="growth.png?v={v}" style="max-width:100%">'

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
{refresh_section(now)}
<h2>Latest</h2>{latest_img}
<h2>Stats</h2>{stats_html}
<h2>Growth</h2>{chart_html}
<h2>Alerts</h2>{alerts_html}
<h2>Timelapses</h2>{vids_html}
</body></html>""")
    print(f"dashboard: {dash / 'index.html'}", flush=True)


if __name__ == "__main__":
    main()

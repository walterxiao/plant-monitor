#!/usr/bin/env python3
"""Plant Monitor — health alerts.

Reads data/metrics.jsonl, aggregates daily medians, and evaluates rules:

  wilting   green_ratio AND height both drop vs the 3-day median
            (a green dip alone can just be lighting; both together = droop)
  yellowing yellow_ratio jumps above its calibration baseline
  stalled   green_area changes <2% over stall_days (no measurable growth)
  dark      many skipped/dark frames during daylight -> light may have failed

Alerts are appended to data/alerts.jsonl and, if alerts.ntfy_topic is set,
pushed to your phone via ntfy.sh. Each rule alerts once, then reminds only
after alerts.remind_after_days. No growth alerts fire during the
calibration window (first calibration_days of data).
"""
import json
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

import yaml

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
    if n == 0:
        return 0.0
    mid = n // 2
    return (s[mid] + s[~mid]) / 2 if n % 2 == 0 else s[mid]


def load_metrics(data_dir: Path) -> list[dict]:
    path = data_dir / "metrics.jsonl"
    if not path.exists():
        return []
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                r = json.loads(line)
                r["_dt"] = datetime.fromisoformat(r["timestamp"])
                rows.append(r)
    return sorted(rows, key=lambda r: r["_dt"])


def daily_medians(rows: list[dict]) -> dict[str, dict]:
    by_day: dict[str, list[dict]] = {}
    for r in rows:
        by_day.setdefault(r["_dt"].date().isoformat(), []).append(r)
    out = {}
    for day, rs in sorted(by_day.items()):
        out[day] = {
            "green_ratio": median([r["green_ratio"] for r in rs]),
            "green_area_px": median([r["green_area_px"] for r in rs]),
            "height_px": median([r["height_px"] for r in rs]),
            "yellow_ratio": median([r["yellow_ratio"] for r in rs]),
            "n": len(rs),
        }
    return out


def send_ntfy(topic: str, message: str) -> None:
    req = urllib.request.Request(
        f"https://ntfy.sh/{topic}",
        data=message.encode(),
        headers={"Title": "Plant Monitor"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=10)


def main() -> None:
    cfg = load_config()
    acfg = cfg["alerts"]
    data_dir = resolve_data_dir(cfg)
    rows = load_metrics(data_dir)
    if not rows:
        print("alerts: no metrics yet", flush=True)
        return

    daily = daily_medians(rows)
    days = sorted(daily)
    today = days[-1]
    now = datetime.now()

    state_path = data_dir / "state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    last_alert: dict[str, str] = state.get("last_alert", {})

    def due(rule: str) -> bool:
        prev = last_alert.get(rule)
        if not prev:
            return True
        return (now - datetime.fromisoformat(prev)).days >= acfg["remind_after_days"]

    alerts_path = data_dir / "alerts.jsonl"
    fired: list[dict] = []

    def fire(rule: str, severity: str, message: str) -> None:
        if not due(rule):
            return
        alert = {"timestamp": now.isoformat(), "rule": rule,
                 "severity": severity, "message": message}
        with open(alerts_path, "a") as f:
            f.write(json.dumps(alert) + "\n")
        last_alert[rule] = now.isoformat()
        fired.append(alert)
        print(f"ALERT [{severity}] {rule}: {message}", flush=True)
        if acfg["ntfy_topic"]:
            try:
                send_ntfy(acfg["ntfy_topic"], f"[{severity}] {message}")
            except Exception as e:
                print(f"ntfy failed: {e}", flush=True)

    # --- dark-frame / light-failure check ---------------------------------
    # capture.py only logs skips; here we infer gaps: expected ~1 photo per
    # interval during daylight. A day with <25% of the expected frames while
    # the Pi was up suggests the light failed or the lens is covered.
    expected_per_day = int(14 * 60 / cfg["camera"]["interval_minutes"])
    if daily[today]["n"] < 0.25 * expected_per_day and len(days) >= 2:
        fire("dark", "warning",
             f"only {daily[today]['n']} photos today "
             f"(expected ~{expected_per_day}) — check the grow light / lens")

    # --- growth rules need a calibration baseline --------------------------
    if len(days) >= acfg["calibration_days"]:
        baseline_days = days[:acfg["calibration_days"]]
        base_yellow = median([daily[d]["yellow_ratio"] for d in baseline_days])

        recent = days[-3:-1] if len(days) > 3 else days[:-1]
        ref_green = median([daily[d]["green_ratio"] for d in recent])
        ref_height = median([daily[d]["height_px"] for d in recent])
        cur = daily[today]

        # wilting: green AND height both down (either alone is noise)
        if ref_green > 0 and ref_height > 0:
            green_drop = (ref_green - cur["green_ratio"]) / ref_green * 100
            height_drop = (ref_height - cur["height_px"]) / ref_height * 100
            if (green_drop >= acfg["wilt_green_drop_pct"]
                    and height_drop >= acfg["wilt_height_drop_pct"]):
                fire("wilting", "critical",
                     f"possible wilting: green -{green_drop:.0f}%, "
                     f"height -{height_drop:.0f}% vs 3-day median — check water")

        # yellowing: stress proxy above baseline
        if cur["yellow_ratio"] - base_yellow >= acfg["yellow_spike_ratio"]:
            fire("yellowing", "warning",
                 f"yellowing up: {cur['yellow_ratio']:.1%} of frame vs "
                 f"{base_yellow:.1%} baseline — check nutrients/light")

        # stalled growth
        window = days[-acfg["stall_days"]:]
        if len(window) >= acfg["stall_days"]:
            areas = [daily[d]["green_area_px"] for d in window]
            if max(areas) > 0 and (max(areas) - min(areas)) / max(areas) < 0.02:
                fire("stalled", "info",
                     f"no measurable growth for {acfg['stall_days']} days — "
                     f"plant may need more light or feeding")

    state["last_alert"] = last_alert
    state_path.write_text(json.dumps(state, indent=2))
    print(f"alerts: {len(fired)} fired, {len(days)} days of data", flush=True)


if __name__ == "__main__":
    main()

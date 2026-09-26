# How the Plant Monitor Works 🌱

*A line-by-line tour of the code, written for a curious 10-year-old.
No programming experience needed — just bring your questions.*

## The big idea

Imagine you hire a tiny robot to babysit your plant. The robot has five jobs,
and each job is one Python file (a Python file is just a recipe the computer
follows):

| File | Job | Nickname |
|------|-----|----------|
| `capture.py` | Takes photos all day | 📷 The Photographer |
| `analyze.py` | Measures how green and tall the plant is in each photo | 🔍 The Detective |
| `alerts.py` | Notices when the plant looks sick and tells you | 🩺 The Doctor |
| `timelapse.py` | Turns the photos into a fast-forward movie | 🎬 The Movie Maker |
| `dashboard.py` | Builds a web page showing everything | 🖼️ The Poster Maker |
| `config.yaml` | The settings list — the robot's instruction card | 📋 The Recipe Card |

Let's walk through each one, top to bottom, the way the computer reads it.

---

## 📋 The Recipe Card (`config.yaml`)

This isn't really code — it's a list of settings, like the settings screen in
a video game. The other files keep peeking at this card to know what to do.

- `plant_name: "Basil"` — your plant's name. It shows up on the videos and
  the web page. Change it to your plant's real name!
- `camera: resolution` — how detailed each photo is (2592 × 1944 dots).
  Bigger = prettier but hungrier for disk space.
- `camera: interval_minutes: 10` — take a photo every 10 minutes.
- `lighting: mode` — `"outdoor"` means "use real sunrise and sunset";
  `"indoor"` means "use the fixed hours below" (for a grow light).
- `lighting: latitude/longitude` — your spot on Earth, so the robot can look
  up when the sun rises and sets. (Right now it says Vienna, Virginia!)
- `analysis: min_brightness: 40` — if a photo is darker than this, throw it
  away (someone turned the lights off).
- The `green_hsv_low/high` and `yellow_hsv_low/high` numbers — the exact
  shades of green and yellow the Detective should look for. More on HSV
  (a way of describing colors) in the Detective section!
- `alerts:` — the Doctor's rules: how much drooping counts as "wilting"
  (15% less green + 10% shorter), how much yellow is a "spike", and so on.
- `timelapse: fps: 30` — the movie plays 30 photos per second.

**In one sentence:** this card holds every number the robot needs, so you
can tweak behavior without touching any code.

---

## 📷 The Photographer (`capture.py`)

This program runs *forever* — it wakes up every 10 minutes, takes a photo,
and goes back to sleep. Here's what each part does:

```python
import time
from datetime import date, datetime
from pathlib import Path
import numpy as np
import yaml
```

**Translation:** "Hey computer, I need your clock (`datetime`), your
stopwatch (`time`), your filing cabinet (`Path`), your math brain (`numpy`),
and your recipe-card reader (`yaml`)." `import` just means "go get me
that tool."

```python
ROOT = Path(__file__).resolve().parent
```

**Translation:** "Figure out which folder this file lives in, and remember
it." Every other file starts the same way — it's how they find the recipe
card and where to save photos.

```python
def load_config() -> dict:
    with open(ROOT / "config.yaml") as f:
        return yaml.safe_load(f)
```

**Translation:** "Open the recipe card and read it into a dictionary"
(a dictionary is like a labeled toy box: you ask for `"camera"` and get
the camera settings). Every file has this same little helper.

```python
def in_daylight(cfg: dict) -> bool:
```

**Translation:** "Here's a yes/no question I can ask: *is it daytime right
now?*" (`-> bool` means the answer is always True or False.)

Inside, there are two cases:

- **Indoor mode:** it reads `indoor_start` ("07:00") and `indoor_end`
  ("21:00") from the recipe card and checks whether the current time is
  between them. Like checking "is it between breakfast and bedtime?"
- **Outdoor mode:** it uses the `astral` library — a tiny astronomy
  calculator — with your latitude/longitude to compute today's actual
  sunrise and sunset. Then: is right now between them?

```python
def main() -> None:
    cfg = load_config()
    from picamera2 import Picamera2
    picam = Picamera2()
```

**Translation:** `main` is where the real action starts. It reads the recipe
card, then wakes up the camera (`Picamera2` is the tool that talks to the
physical camera board).

```python
    picam.configure(picam.create_still_configuration(main={"size": (w, h)}))
    picam.start()
    time.sleep(2)  # sensor warmup / auto-exposure settle
```

**Translation:** "Camera, please take photos at this size." Then it starts
the camera and waits 2 seconds — like letting your eyes adjust when you walk
into a bright room. (The `#` part is a *comment* — a note for humans that
the computer ignores.)

```python
    while True:
```

**Translation:** "Do the following steps forever." This is called a loop,
and it's the heartbeat of the Photographer.

```python
        if in_daylight(cfg):
            frame = picam.capture_array()
            brightness = float(np.mean(frame))
```

**Translation:** "If it's daytime, snap a quick preview photo and measure
its average brightness." `np.mean` = the average of all the dots' brightness.

```python
            if brightness >= min_brightness:
                day_dir = data_dir / "photos" / now.strftime("%Y-%m-%d")
                day_dir.mkdir(parents=True, exist_ok=True)
                path = day_dir / (now.strftime("%H%M%S") + ".jpg")
                picam.capture_file(str(path), quality=quality)
```

**Translation:** "If the photo isn't too dark, file it away." It creates a
folder named like `photos/2026-09-26` (the `mkdir` line means "make the
folder if it isn't there"), and saves the photo as something like
`143022.jpg` (that's 2:30:22 PM — hours, minutes, seconds squished together).
So every photo's *name* is the exact time it was taken. Clever, right?

```python
            else:
                print(f"skipped dark frame ...")
        time.sleep(interval)
```

**Translation:** "If it was too dark, skip it and say so. Then nap for 10
minutes." `print` writes a message to the log so humans can see what happened.

```python
        except Exception as e:
            print(f"capture error: {e}", flush=True)
            time.sleep(60)
```

**Translation:** "If *anything* goes wrong — camera hiccup, full disk,
whatever — don't crash. Write down the error, wait a minute, and try again."
This is the Photographer's superpower: it never gives up.

```python
if __name__ == "__main__":
    main()
```

**Translation:** "When someone runs this file directly, start at `main`."
(Every file ends with this. It's Python's way of saying "action!")

**In one sentence:** the Photographer naps, wakes up every 10 minutes during
daytime, takes a photo named by the time it was taken, and never quits.

---

## 🔍 The Detective (`analyze.py`)

The Photographer collects photos. The Detective examines each one and writes
down measurements — like a scientist filling in a lab notebook. It runs once
a day.

```python
def photo_timestamp(path: Path) -> str:
    ts = datetime.strptime(f"{path.parent.name} {path.stem}", "%Y-%m-%d %H%M%S")
    return ts.isoformat()
```

**Translation:** Remember how each photo is filed as
`photos/2026-09-26/143022.jpg`? This function reads the folder name (the
date) and the file name (the time) and glues them into one proper timestamp:
`2026-09-26T14:30:22`. The Detective reconstructs *when* each photo was
taken purely from where it was filed. No extra notes needed!

```python
def analyze_image(path: Path, cfg: dict) -> dict | None:
    img = cv2.imread(str(path))
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
```

**Translation:** "Open the photo." Then convert it from RGB (red-green-blue,
how screens think about color) to **HSV** (hue-saturation-value — how
*humans* think about color: *what* color is it, how *vivid*, how *bright*).
HSV makes it much easier to say "find me all the green dots," because all
greens live in one neighborhood of hue, whether they're in sunshine or shade.

```python
    green = cv2.inRange(hsv, np.array(a["green_hsv_low"]),
                        np.array(a["green_hsv_high"]))
    yellow = cv2.inRange(hsv, np.array(a["yellow_hsv_low"]),
                         np.array(a["yellow_hsv_high"]))
```

**Translation:** "Make two stencils: one with holes everywhere the photo is
green, one with holes everywhere it's yellow." `inRange` keeps only the dots
whose color falls between the recipe card's low/high numbers. The result is a
black-and-white image: white dots = "green here!", black = "not green."

```python
    total = img.shape[0] * img.shape[1]
    green_area = int(cv2.countNonZero(green))
```

**Translation:** "Count all the dots in the photo (`total`), then count the
white dots on the green stencil (`green_area`)." If the plant grows, the
green count goes up. That's the whole growth measurement — beautifully simple.

```python
    contours, _ = cv2.findContours(green, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        c = max(contours, key=cv2.contourArea)
        _x, _y, w, h = cv2.boundingRect(c)
        width_px, height_px = int(w), int(h)
```

**Translation:** "Now find the blobs." `findContours` traces the outlines of
all the white regions on the green stencil — each leaf cluster becomes a
blob. Then: pick the *biggest* blob (that's probably the plant, not a tiny
green speck), and draw the smallest box around it. The box's width and height
(in dots, a.k.a. pixels) are the plant's width and height. If the plant grows
taller, the box gets taller!

```python
    return {
        "file": ...,
        "timestamp": photo_timestamp(path),
        "green_ratio": round(green_area / total, 5),
        ...
    }
```

**Translation:** "Write all the measurements on one lab-notebook line":
which file, when, what fraction of the photo is green (`green_ratio`),
how many green dots, how tall/wide the biggest green blob is, the yellow
fraction, and brightness.

```python
def main() -> None:
    ...
    processed: set[str] = set()
    if metrics_path.exists():
        for line in f:
            processed.add(json.loads(line)["file"])
    new = [p for p in photos if str(p.relative_to(data_dir)) not in processed]
```

**Translation:** "Open the lab notebook (`metrics.jsonl` — one JSON
measurement per line) and memorize which photos I've already measured.
Then find only the *new* photos." This makes the Detective **idempotent**
(a fancy word meaning "running it twice does the same as running it once")
— it never measures the same photo twice, even if you run it ten times.

**In one sentence:** the Detective turns each photo into numbers — how much
green, how tall, how yellow — and appends them to a growing lab notebook,
never repeating itself.

---

## 🩺 The Doctor (`alerts.py`)

Numbers are nice, but someone has to *worry* about them. The Doctor reads the
Detective's notebook once a day and checks four rules. Think of it as a plant
pediatrician doing a daily checkup.

```python
def median(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    ...
```

**Translation:** "Find the middle value of a list." Why the middle and not
the average? Imagine 9 photos where the plant looks normal, and 1 photo where
a shadow fell across it. The *average* would be dragged down by that one weird
photo; the *median* (the middle one when lined up) ignores it. The Doctor
uses medians everywhere so one odd photo can't cause a false alarm. Smart!

```python
def daily_medians(rows: list[dict]) -> dict[str, dict]:
```

**Translation:** "Squash each day's ~84 measurements into one typical set of
numbers per day." One photo can be fluky; a whole day's median is trustworthy.

```python
def send_ntfy(topic: str, message: str) -> None:
```

**Translation:** "Send a text message to a phone." It posts the alert to
ntfy.sh — a free service — and if you've installed the ntfy app and
subscribed to your secret topic name, your phone buzzes. (If no topic is set
on the recipe card, alerts just get written to a file.)

```python
    def due(rule: str) -> bool:
        prev = last_alert.get(rule)
        if not prev:
            return True
        return (now - datetime.fromisoformat(prev)).days >= acfg["remind_after_days"]
```

**Translation:** "Should I bug the human about this rule *again*?" Each rule
gets to alert once, then must wait 3 days (`remind_after_days`) before
reminding. Nobody likes a robot that cries wolf every 10 minutes. The last
alert times are remembered in `state.json`, so the Doctor has a memory even
between runs.

Now the four checkups:

**1. The dark check** 🔦
```python
    expected_per_day = int(14 * 60 / cfg["camera"]["interval_minutes"])
    if daily[today]["n"] < 0.25 * expected_per_day and len(days) >= 2:
```
**Translation:** "We expect ~84 photos on a 14-hour day. If today has fewer
than a quarter of that, something's wrong — maybe the grow light died or
something is covering the lens." Note it needs at least 2 days of history
first, so day 1 (a partial day) can't trigger it.

**2. The wilting check** 🥀
```python
        if (green_drop >= acfg["wilt_green_drop_pct"]
                and height_drop >= acfg["wilt_height_drop_pct"]):
```
**Translation:** "Compare today against the median of the last 3 days. If
the plant is BOTH 15% less green AND 10% shorter — alert!" Why both? A cloudy
day alone can make green dip (lighting, not the plant). But green *plus*
shorter together means the leaves are actually drooping. Two clues beat one —
that's real detective thinking.

**3. The yellowing check** 💛
```python
        if cur["yellow_ratio"] - base_yellow >= acfg["yellow_spike_ratio"]:
```
**Translation:** "Is there much more yellow today than during the first 3
calibration days (when the plant was healthy)?" Yellow leaves often mean
overwatering or hungry-for-nutrients. The first 3 days are the "what does
healthy look like?" baseline — that's why the setup guide says to calibrate
on a good day!

**4. The stalled-growth check** 🐌
```python
        if max(areas) > 0 and (max(areas) - min(areas)) / max(areas) < 0.02:
```
**Translation:** "Look at the last 7 days of green area. If the biggest and
smallest days differ by less than 2%, the plant hasn't measurably grown all
week." (It might just be resting — plants do that — so this one is gentle
`info` level, not an emergency.)

**In one sentence:** the Doctor compares each day's typical numbers against
recent history and a healthy baseline, and only bothers you when two clues
agree or something is clearly off — then politely waits 3 days before
reminding you again.

---

## 🎬 The Movie Maker (`timelapse.py`)

This is the fun one: it turns hundreds of still photos into a fast-forward
movie of your plant growing, with cool overlays.

```python
def cover_resize(img, size):
    ...
    scale = max(tw / img.width, th / img.height)
```

**Translation:** "Resize each photo to fill a 1280×720 movie frame, cropping
the edges if needed" — exactly like a phone wallpaper set to "fill screen."

```python
def draw_sparkline(draw, history, box):
```

**Translation:** "Draw the tiny growth chart in the corner." It takes the
history of daily green measurements, squishes them into a little box, and
draws a green line going up (hopefully!) with a dot on the latest day. A
*sparkline* is just a word for a tiny chart with no axes — like the little
graphs on a stock app.

```python
def render_day(day, photos, cfg, data_dir, metrics, history):
    ...
        d.rectangle([0, 0, tw, 110], fill=(0, 0, 0, 130))
        d.text((24, 14), f"{cfg['plant_name']} - day {day_num} - {day}", ...)
```

**Translation:** "For each photo, paint a see-through black bar across the
top and write 'Basil - day 5 - 2026-09-26' on it, plus the live measurements
('green 23.4%  height 512px  14:30') and the sparkline in the corner." `PIL`
(Pillow) is the drawing toolkit — the Movie Maker is literally finger-painting
text onto every frame, one by one.

```python
def encode(frames_dir, out_path, fps):
    subprocess.run(["ffmpeg", "-y", "-framerate", str(fps), "-i", ...,
                    "-c:v", "libx264", ...])
```

**Translation:** "Now hand the stack of painted frames to `ffmpeg`" — a
famous free video-building program — "and say: stitch these into a movie at
30 frames per second, using the H.264 format (the same format YouTube uses)."
`subprocess.run` just means "run another program and wait for it to finish."

```python
    done: dict[str, int] = json.loads(manifest.read_text()) if manifest.exists() else {}
    ...
        if done.get(day) == len(photos) and out.exists():
            continue
```

**Translation:** "Don't re-render movies I've already made!" A manifest file
remembers which days are done and how many photos each had. If a day already
has a video and no new photos arrived, skip it. (Idempotent again — the whole
project loves that word.)

```python
        concat_list.write_text("".join(f"file '{p.name}'\n" for p in built))
        subprocess.run(["ffmpeg", "-y", "-f", "concat", ...])
```

**Translation:** "Finally, glue all the daily movies into one big
`growth-timelapse.mp4`." It writes a little playlist file (`concat.txt`
listing each day's video) and asks ffmpeg to join them end to end — no
re-encoding, so it's fast.

**In one sentence:** the Movie Maker paints the date, measurements, and a
tiny growth chart onto every photo, stitches each day into a mini-movie, then
glues the days into one full growing-up film.

---

## 🖼️ The Poster Maker (`dashboard.py`)

The grand finale: one web page (`index.html`) that shows everything — the
latest photo, the stats, the charts, the alerts, and links to the movies.

```python
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
```

**Translation:** `matplotlib` is Python's chart-drawing toolkit. The
`"Agg"` line means "draw charts silently, without trying to open a window"
(there's no screen on the Pi — it's headless!).

```python
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
        ax1.plot(times, [r["green_ratio"] * 100 for r in rows], color="green")
        ax2.plot(times, [r["height_px"] for r in rows], color="darkgreen")
```

**Translation:** "Draw two stacked charts sharing one timeline: green % on
top, plant height below." Each dot is one photo's measurement. Watching the
lines climb over days is the whole payoff!

```python
        first = rows[0]["green_ratio"] or 1e-9
        growth = (rows[-1]["green_ratio"] - rows[0]["green_ratio"]) / first * 100
```

**Translation:** "How much has the green area changed since the very first
photo, as a percent?" (The `or 1e-9` is a tiny guard: never divide by zero,
even if the first photo had no green at all. `1e-9` is a teeny-tiny number.)

```python
    (dash / "index.html").write_text(f"""<!doctype html>
    ...
    <h1>🌱 {cfg['plant_name']}</h1>
    ...""")
```

**Translation:** "Write out the whole web page as one long piece of text,
with the fresh numbers and chart images plugged in." The `f"""..."""` is a
*template* — the parts in `{curly braces}` get filled in with real values,
like Mad Libs. Then you just open `index.html` in any browser. No internet
needed.

**In one sentence:** the Poster Maker draws the growth charts, computes the
"how much bigger since day 1" stats, and assembles a simple web page tying
the latest photo, charts, alerts, and movies together.

---

## 🔁 How they all fit together (a day in the life)

```
 6:00 AM ── sunrise ─────────────────────────────────────────────
                │
   📷 capture.py    photo every 10 min → data/photos/2026-09-26/*.jpg
                │    (runs all day, forever)
                │
10:30 PM ───────────────────────────────────────────────────────
                │
   🔍 analyze.py    measures every new photo → data/metrics.jsonl
                │
   🩺 alerts.py     checks the 4 rules → data/alerts.jsonl (+ phone buzz)
                │
   🎬 timelapse.py  paints overlays, builds data/videos/2026-09-26.mp4,
                │    updates growth-timelapse.mp4
                │
   🖼️ dashboard.py  rebuilds data/dashboard/index.html
                │
   😊 you           open the dashboard, watch your plant grow!
```

The Photographer works the day shift. At 10:30 PM the night crew
(Detective → Doctor → Movie Maker → Poster Maker) runs in order, each one
reading what the previous one wrote. Everything talks through simple files
in the `data/` folder — photos, a measurements notebook, an alerts notebook —
so each program is small, independent, and replaceable. That's called a
**pipeline**, and it's how a lot of real-world software is built.

---

## 🧪 Try it yourself!

You don't need the Raspberry Pi to explore. On any computer with Python:

1. Put a few plant photos in `data/photos/2026-09-26/` (phone photos work —
   name them like `093000.jpg` for 9:30 AM).
2. Run `python analyze.py` — watch the Detective measure them.
3. Run `python dashboard.py` — open `data/dashboard/index.html` and see
   your charts!

*Questions to think about: what would happen if you moved the camera halfway
through the week? (Hint: ask the Detective what it measures!) What new rule
would you teach the Doctor — maybe "alert me when a flower blooms"?*

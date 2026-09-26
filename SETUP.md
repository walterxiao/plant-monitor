# Setup Guide — Plant Monitor on Raspberry Pi

**Never touched a Raspberry Pi before? Perfect — this guide assumes zero
experience.** Follow it top to bottom and you'll go from sealed boxes to a
plant that texts you when it's thirsty. About 45 minutes of hands-on time,
plus one day of the plant just growing.

## 0. What all these parts are

You've ordered (or are about to order) a few things from the shopping list.
Here's what each one actually *is*, in plain English:

- **Raspberry Pi 5** — a complete computer the size of a credit card. It has
  a processor, memory, and ports, just like your Mac — just much smaller,
  much cheaper, and with no screen or keyboard of its own. It'll sit next
  to your plant 24/7 taking photos.
- **Camera Module** — a tiny camera that plugs directly into the Pi with a
  flat ribbon cable. Think of it as the Pi's eyes.
- **microSD card** — this is the Pi's "hard drive." Everything — the
  operating system, our programs, all the photos — lives on this little
  card. The kit's card comes with the operating system already on it.
- **Power supply** — the Pi's charger. Phones and Pis are picky: use the
  one from the kit, not a random phone charger, or the Pi may act flaky.
- **Case + fan** — a little plastic shell so the bare circuit board isn't
  sitting exposed on your shelf, plus a fan because the Pi 5 runs warm.

And two concepts you'll meet below:

- **Terminal** — the black window on your Mac (Applications → Utilities →
  Terminal) where you type text commands instead of clicking. Every step
  below gives you the exact text to type.
- **SSH** — a way to remote-control the Pi from your Mac. You'll type
  commands on your Mac, but they'll *run on the Pi*. The Pi itself never
  needs a screen or keyboard.

## 1. Assemble the hardware

1. **Connect the camera to the Pi.** On the Pi board, find the port labeled
   `CAMERA` (it's the small slot between the HDMI ports and the audio
   jack). Gently pull up the black latch on the port — it slides up about
   2mm. Slide the camera's ribbon cable straight in with the **blue side
   facing the Ethernet port** (the big network jack). Push the latch back
   down to lock it. The cable should feel snug, not loose.
2. **Put the Pi in its case** per the kit's little instruction sheet, and
   plug in the fan if it isn't pre-installed.
3. **Position it** so the camera faces the plant, about 30–60 cm (1–2 feet)
   away, with the whole plant in the frame. A small tripod or gooseneck
   mount helps aim it.
4. **Insert the microSD card** into the slot on the underside of the Pi,
   then **connect power**. A red light should come on, then a green light
   will flicker — that's it booting up.

> Tip: from now on, try not to bump the camera. Our software measures
> growth by counting green pixels, so moving the camera looks like the
> plant suddenly grew!

## 2. Put the operating system on the card (on your Mac)

Wait — didn't the kit card come with the OS preloaded? Yes, but we're
going to redo it once, properly, because this sets up Wi-Fi, your login,
and the Pi's name in one shot. (An "operating system" is the base software
every computer needs — like macOS on your Mac. "Flashing" just means
copying it onto the card.)

1. Install [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on
   your Mac — it's the official free tool for this.
2. Put the microSD card into your Mac (you may need the little SD adapter
   that came with the kit).
3. In the Imager: **Choose Device** → Raspberry Pi 5; **Choose OS** →
   Raspberry Pi OS Lite (64-bit) ("Lite" means no desktop — we don't need
   one since we'll control it remotely); **Choose Storage** → your SD card.
4. Click the **gear icon** ⚙️ *before* hitting Write, and fill in:
   - **Hostname:** `plantpi` (the Pi's name on your network)
   - **Enable SSH**, "Use password authentication"
   - **Username:** `pi` (or your name), plus a **password** you'll remember
   - **Configure wireless LAN:** your Wi-Fi name and password
   - **Timezone:** America/New_York
5. Hit **Write**, wait for it to finish, put the card back in the Pi, and
   power it on. Give it 1–2 minutes to boot and join your Wi-Fi.

> **Do I need to connect the Pi to a network?** Not strictly — photos,
> analysis, videos, and the dashboard all work offline. But it's strongly
> recommended: the Pi has no clock battery, so without network its time
> resets on every reboot (breaking photo timestamps, sunrise/sunset math,
> and alert timing). Wi-Fi also enables phone alerts and viewing the
> dashboard from your Mac.

## 3. Connect to the Pi from your Mac

From here on, everything happens in **Terminal** on your Mac
(Applications → Utilities → Terminal). You'll SSH into the Pi — type on
your Mac, run on the Pi.

**Step 1 — check the Pi is reachable.** Type this and press Enter:

```bash
ping -c 2 plantpi.local
```

If you see replies, great — your Mac found the Pi by name. If it says
"cannot resolve," find the Pi's IP address in your router's admin page
(usually `http://192.168.1.1` in a browser, look for `plantpi` in the
device list) and use that IP instead of `plantpi.local` below.

**Step 2 — log in:**

```bash
ssh pi@plantpi.local
```

The first time, SSH asks "are you sure you want to continue?" — type `yes`.
This is just the two computers introducing themselves. Then type the
password you set in the Imager. **Nothing appears as you type the
password** — that's normal, it's hiding it. Press Enter.

Your prompt changes to something like `pi@plantpi:~ $`. Congratulations —
you're now "inside" the Pi. Everything you type runs on the little
computer by your plant.

**Handy Mac ↔ Pi moves** (run these in a *Mac* Terminal tab, not inside SSH):

| What | Command |
|------|---------|
| Copy a file Pi → Mac | `scp pi@plantpi.local:~/plant-monitor/test.jpg ~/Desktop/` |
| Copy a folder Pi → Mac | `scp -r pi@plantpi.local:~/plant-monitor/data/dashboard ~/Desktop/` |

**Editing files on the Pi:** `nano` is a simple text editor that works over
SSH. Example: `nano ~/plant-monitor/config.yaml`. Type your changes,
press **Ctrl+O** then Enter to save, **Ctrl+X** to exit. (If you use VS
Code on your Mac, its "Remote - SSH" extension lets you edit Pi files in
the full editor — connect to `pi@plantpi.local`.)

## 4. First-boot setup (on the Pi, over SSH)

You're SSH'd in (prompt says `pi@plantpi`). Two things:

**Update the system.** This downloads the latest fixes — takes a few
minutes the first time:

```bash
sudo apt update && sudo apt upgrade -y
```

(`sudo` means "do this as the administrator" — the Pi asks for extra
permission before system-level changes, like macOS asking for your
password.)

**Check the camera is detected:**

```bash
rpicam-hello --list-cameras
```

You should see the IMX708 sensor listed. Success looks like a line
mentioning `imx708`. If it says no cameras were found, the ribbon cable
isn't seated right: shut the Pi down (`sudo shutdown now`), unplug power,
and redo step 1's cable seating.

## 5. Install the plant-monitor software (on the Pi)

```bash
git clone https://github.com/walterxiao/plant-monitor.git
cd plant-monitor
./install.sh
```

What this does: `git clone` downloads our project from GitHub;
`install.sh` then installs the helper programs it needs (like `ffmpeg`
for video) and sets up an isolated Python environment. Takes a few
minutes. When it finishes without red error text, you're good.

## 6. Configure (on the Pi)

Open the settings file:

```bash
nano ~/plant-monitor/config.yaml
```

The settings you care about:

- `plant_name` — your plant's name (shows up on videos and the web page).
- `lighting` — your `latitude`/`longitude` so daytime is computed from
  real sunrise/sunset (or switch `mode` to `indoor` with fixed hours if
  you use a grow light).
- `camera.interval_minutes` — how often a photo is taken. The default is
  `10` (every 10 minutes), which gives a smooth timelapse and a detailed
  growth curve. **If you'd rather it wakes up less often — say every 6
  hours — set this to `360`.** Fewer photos = less storage and a
  lazier timelapse, but it's still plenty for tracking growth and health.
  (With `lighting: outdoor`, only daylight hours count, so every 6 hours
  is roughly 2 photos a day.)
- `alerts.ntfy_topic` — optional. Set a random topic name (e.g.
  `my-plant-xyz123`), install the free **ntfy** app on your phone,
  subscribe to that topic, and the Pi will text you when something's
  wrong. Leave it empty (`""`) to just log alerts.

Save (Ctrl+O, Enter) and exit (Ctrl+X).

## 7. Test the camera (on the Pi)

```bash
cd ~/plant-monitor
./venv/bin/python -c "
from picamera2 import Picamera2
cam = Picamera2()
cam.start()
cam.capture_file('test.jpg')
cam.stop()
print('ok')"
```

If it prints `ok`, the camera works. Now look at the photo: from a **Mac**
Terminal tab (not inside SSH), run

```bash
scp pi@plantpi.local:~/plant-monitor/test.jpg ~/Desktop/
```

and open it. Is the whole plant in frame with a little margin? If not,
adjust the camera and re-run the test. This framing is what every future
photo will look like, so get it right now.

## 8. Calibrate — do this on day 1 (on the Pi)

The "yellowing" alert needs to know what *your healthy plant* looks like,
so it has something to compare against. Take a few test photos first (or
wait a day), then:

```bash
cd ~/plant-monitor && ./venv/bin/python analyze.py
```

Do this while the plant looks healthy. If it's already struggling, help it
recover first — otherwise the software learns "sick" as normal.

## 9. Turn on automatic photo capture (on the Pi)

We want the photo-taking to run by itself forever, even after reboots.
Linux does this with a **service** — think of it as an alarm clock that
makes sure our program is always running:

```bash
sudo cp systemd/plant-capture.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now plant-capture.service
```

In plain English: "install the alarm clock, wake it up, and start it now."
Check it's alive:

```bash
sudo systemctl status plant-capture.service
```

Green `active (running)` = the Photographer is on duty. (Press `q` to exit
that view.)

## 10. Turn on the nightly job (on the Pi)

Every night at 22:30, a second alarm clock (a **timer**) runs the rest of
the pipeline: measure the day's photos, check for problems, build the
timelapse video, and rebuild the web page:

```bash
sudo cp systemd/plant-daily.service systemd/plant-daily.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now plant-daily.timer
```

Impatient? Run the night crew manually right now:

```bash
cd ~/plant-monitor
./venv/bin/python analyze.py
./venv/bin/python alerts.py
./venv/bin/python timelapse.py
./venv/bin/python dashboard.py
```

## 11. See your dashboard (on your Mac)

Pick whichever is easier:

- **Over the network** (nothing to copy): on the Pi, run
  ```bash
  cd ~/plant-monitor/data/dashboard && python3 -m http.server 8000
  ```
  then open **`http://plantpi.local:8000`** in Safari or Chrome on your
  Mac. (Back on the Pi, press Ctrl+C to stop the little web server.)
- **Copy it to your Mac**: in a Mac Terminal tab,
  ```bash
  scp -r pi@plantpi.local:~/plant-monitor/data/dashboard ~/Desktop/
  ```
  then double-click `~/Desktop/dashboard/index.html`.

You'll see the latest photo, growth charts, any alerts, and links to the
timelapse videos. 🌱

## What happens each day (once set up, you do nothing)

| Time | What |
|------|------|
| Daylight hours | Photo every 10 min → `data/photos/YYYY-MM-DD/` |
| 22:30 | Night crew runs: measurements → `data/metrics.jsonl`, health check (phone buzz if ntfy set), timelapse rebuilt, web page rebuilt |

## What the alerts mean

- **Wilting suspected** 🥀 — the plant got less green AND shorter vs the
  last 3 days. Usually thirsty. Check the soil.
- **Yellowing spike** 💛 — more yellow than your healthy baseline. Often
  too much water or needs nutrients.
- **Growth stalled** 🐌 — barely changed in 7 days. Might just be resting
  (plants do that!) or might want more light.
- **No usable frames** 🔦 — all of today's photos were dark. Is something
  covering the lens? Did the grow light die?

Each alert fires once, then waits 3 days before reminding you again.

## Troubleshooting (when something looks wrong)

- **Can't reach `plantpi.local`** — use the IP address from your router's
  device list instead: `ssh pi@192.168.1.XX`. The IP always works even
  when the name doesn't.
- **SSH says "connection refused"** — SSH wasn't enabled when flashing.
  Redo step 2 with SSH enabled.
- **Camera not listed in step 4** — cable isn't seated. Power off
  (`sudo shutdown now`), unplug, and redo the ribbon cable in step 1.
- **Photos are black** — the Pi thinks it's night. Check the
  `lighting` section of `config.yaml` (wrong coordinates?), or switch to
  `mode: indoor`.
- **A service won't start** — read its diary:
  `sudo journalctl -u plant-capture.service -e` (use `-u plant-daily`
  for the night crew). The last lines usually say exactly what's wrong.
- **Dashboard is empty** — the night crew hasn't run yet. Run the four
  commands in step 10 manually.
- **Running out of space** — photos use ~150 MB/day at 10-minute
  intervals. The `storage.max_days` setting auto-deletes old photos
  (videos are kept).

## Keeping it updated

Every so often, SSH in and run:

```bash
cd ~/plant-monitor
git pull
sudo systemctl restart plant-capture.service
```

This downloads the latest version of our code and restarts the
Photographer with it. That's it — your plant robot is a low-maintenance
pet. 🌿

## Changing settings later (e.g. photo frequency)

Nothing here is permanent — change any setting anytime:

1. SSH into the Pi, then open the settings:
   ```bash
   nano ~/plant-monitor/config.yaml
   ```
2. Change what you want. For example, to take a photo every 6 hours
   instead of every 10 minutes, change
   `interval_minutes: 10` → `interval_minutes: 360`.
3. Save (Ctrl+O, Enter) and exit (Ctrl+X).
4. Restart the Photographer so it picks up the change:
   ```bash
   sudo systemctl restart plant-capture.service
   ```

   That's it — the new rhythm starts immediately. (Settings read only by
   the night crew, like `alerts`, take effect at the next 22:30 run with
   no restart needed.)

Common intervals: `10` = every 10 min (default), `60` = hourly,
`360` = every 6 hours, `1440` = once a day.

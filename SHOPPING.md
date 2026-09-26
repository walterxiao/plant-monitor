# Shopping List

Everything needed to run the plant monitor, all from Amazon. Prices checked
Sep 26, 2026 — they move around, so confirm at checkout.

## Required

| # | Item | Why | Price |
|---|------|-----|-------|
| 1 | | Pi 5 8GB board, 128GB microSD (OS preloaded), case + fan, and 45W USB-C power supply — one box covers the whole computer side | $259.99 |
| 2 | | The camera. Standard lens (75° field of view) is fine for one plant | $34.50 |
| 3 | Raspberry Pi 5 camera cable (15-pin to 22-pin) | **Don't skip this.** The cable in the Camera Module 3 box fits older Pis; the Pi 5 needs the smaller 22-pin cable. Search Amazon for "Raspberry Pi 5 camera cable" — a few dollars | ~$8 |

## Nice to have

| # | Item | Why | Price |
|---|------|-----|-------|
| 4 | | Bendable legs wrap around a shelf or pot edge to aim the camera at the plant (currently on a Prime deal) | $12.22 |

**Total: roughly $315** for the full setup.

## Notes

- The CanaKit kit's 128GB card comes preloaded with Raspberry Pi OS, so you
can skip the flashing step in SETUP.md if you like (still worth setting
hostname/SSH/Wi-Fi via Raspberry Pi Imager for a headless setup).
- 8GB RAM is overkill for this project — it just happens to be the common
kit configuration. A 4GB Pi 5 would do the same job if you find one
cheaper.
- If the plant will live somewhere dim, add an LED grow light on a timer and
set `mode: indoor` with matching hours in `config.yaml`.

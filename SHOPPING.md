# Shopping List

Everything needed to run the plant monitor, all from Amazon. Prices checked
Sep 26, 2026 — they move around, so confirm at checkout.

## Required

| # | Item | Why | Price |
|---|------|-----|-------|
| 1 | [CanaKit Raspberry Pi 5 Starter Kit PRO (8GB RAM, 128GB Edition)](https://www.amazon.com/dp/B0CRSNCJ6Y) | Pi 5 8GB board, 128GB microSD (OS preloaded), case + fan, and 45W USB-C power supply — one box covers the whole computer side | $259.99 |
| 2 | [Arducam Camera Module 3, 12MP IMX708 autofocus](https://www.amazon.com/dp/B0C9PYCV9S) | Same sensor and autofocus as the official module, works with the project's camera code — and the Pi 5 ribbon cable is in the box, so no separate cable needed | $36.00 |

## Nice to have

| # | Item | Why | Price |
|---|------|-----|-------|
| 3 | [Amazon Basics 10-inch flexible tripod](https://www.amazon.com/dp/B0CQP77YP4) | Bendable legs wrap around a shelf or pot edge to aim the camera at the plant (currently on a Prime deal) | $12.22 |

**Total: roughly $308** for the full setup.

## Notes

- The CanaKit kit's 128GB card comes preloaded with Raspberry Pi OS, so you
  can skip the flashing step in SETUP.md if you like (still worth setting
  hostname/SSH/Wi-Fi via Raspberry Pi Imager for a headless setup).
- 8GB RAM is overkill for this project — it just happens to be the common
  kit configuration. A 4GB Pi 5 would do the same job if you find one
  cheaper.
- If the plant will live somewhere dim, add an LED grow light on a timer and
  set `mode: indoor` with matching hours in `config.yaml`.

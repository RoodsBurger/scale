# scale

A digital scale built around an HX711 load-cell amplifier and a Raspberry Pi Zero. The challenge was that the Pi Zero's scheduler isn't tight enough for the off-the-shelf `hx711py` library — reads come back corrupted because the clock pulses get stretched. Half the files here are me figuring that out; the one that actually works is `scale.py`, which talks to the HX711 with raw `GPIO.output()` calls and no `sleep()` between edges.

## Wiring

| HX711 pin | Pi GPIO |
|---|---|
| VCC  | 3.3 V (5 V also works) |
| GND  | GND |
| DOUT | GPIO 5 |
| SCK  | GPIO 6 |

## Files

- `scale.py` — the working one. Raw GPIO, no library dependency. Tare + calibrate prompts on startup, then a continuous read loop.
- `diagnose_hx711.py` — run this first on a new build. Checks DOUT idles high, that clock pulses get acknowledged, and which channel/gain the chip is configured for.
- `debug_continuous.py` — bare-bones read loop. Useful when chasing noise or drift.
- `test_pigpio.py` — same idea as `scale.py` but using the `pigpio` daemon for edge timing. Works on a Pi 3/4 but offered no improvement on the Pi Zero.
- `test_raw_gpio.py` — earlier prototype, kept for reference.
- `test_scale.py`, `test_scale_v01.py` — wrappers around the upstream `hx711py` library (current and pinned-to-v0.1). Both are flaky on the Zero.
- `hx711py/` — vendored copy of the upstream library so the test scripts work without a pip install.

## Usage

```bash
python3 scale.py
```

Tare, drop a known weight on, type the weight, and it'll save the calibration factor. After that it just streams grams.

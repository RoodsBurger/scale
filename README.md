# scale

HX711 + load-cell digital scale running on a Raspberry Pi (tested on Pi Zero). Several implementations were tried because the off-the-shelf `hx711py` library has timing issues on low-power Pis; the one that actually works (`scale.py`) talks to the HX711 via raw GPIO bit-banging — no library dependency.

## Hardware

| HX711 pin | Pi GPIO |
|---|---|
| VCC  | 3.3 V (or 5 V) |
| GND  | GND |
| DOUT | GPIO 5 |
| SCK  | GPIO 6 |

## Files

| File | Purpose |
|---|---|
| `scale.py` | **Use this.** Raw GPIO implementation — reliable on Pi Zero. Handles calibration, tare, and continuous weight reads. |
| `diagnose_hx711.py` | Diagnostic — checks wiring, DOUT pulse train, channel/gain bits. Run first if a new build isn't reading correctly. |
| `debug_continuous.py` | Stripped-down continuous-read loop for troubleshooting drift / noise. |
| `test_pigpio.py` | Attempt using `pigpio` for better edge timing — kept for reference. |
| `test_raw_gpio.py` | Earlier raw-GPIO prototype that informed `scale.py`. |
| `test_scale.py` | Wrapper around the `hx711py` library — flaky on Pi Zero, kept for comparison. |
| `test_scale_v01.py` | Same but pinned to `hx711py` v0.1 for slightly different timing tolerance. |
| `hx711py/` | Vendored copy of the upstream `hx711py` library (used only by the test scripts). |

## Usage

```bash
python3 scale.py
```

Follow the prompts to tare and calibrate with a known weight. The reported `SCALE` factor is reproducible across runs — set it as the default in the source once you have it.

## Why so many scripts

The HX711 protocol is timing-sensitive: clock pulses must be 0.2–50 µs wide. Linux schedulers on the Pi Zero produce jitter large enough to corrupt reads when using high-level libraries that use `sleep()`. Raw `GPIO.output()` calls without sleeps are tight enough to work consistently — that's what `scale.py` does.

#!/usr/bin/env python3
"""
HX711 Scale Test - Using v0.1 Library (slower but more reliable)
----------------------------------------------------------------
The v0.1 library runs at ~1 reading/second but is more tolerant
of Raspberry Pi timing issues.
"""

import sys
import time
import os

# Add hx711py to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, 'hx711py'))

try:
    import RPi.GPIO as GPIO
    from hx711 import HX711  # v0.1 library
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

# GPIO pins
DOUT_PIN = 5
SCK_PIN = 6


def main():
    print("="*50)
    print("HX711 Test using v0.1 Library (slower, more stable)")
    print("="*50)
    print(f"DOUT: GPIO {DOUT_PIN}")
    print(f"SCK:  GPIO {SCK_PIN}")
    print()

    hx = HX711(DOUT_PIN, SCK_PIN)

    # Try different reading formats
    formats = [
        ("MSB", "MSB"),
        ("MSB", "LSB"),
        ("LSB", "MSB"),
        ("LSB", "LSB"),
    ]

    print("Testing reading formats (5 samples each, ~1/sec)...")
    print("This will take about 20 seconds.\n")

    best_format = None
    best_std = float('inf')

    for byte_fmt, bit_fmt in formats:
        hx.set_reading_format(byte_fmt, bit_fmt)
        hx.reset()
        time.sleep(0.5)

        readings = []
        for i in range(5):
            val = hx.get_weight(times=1)
            readings.append(val)
            print(f"  {byte_fmt}/{bit_fmt} #{i+1}: {val}")

        avg = sum(readings) / len(readings)
        std = (sum((x - avg) ** 2 for x in readings) / len(readings)) ** 0.5
        variance = max(readings) - min(readings)

        print(f"  -> avg={avg:.0f}, std={std:.0f}, var={variance}\n")

        if std < best_std and variance < 100000:
            best_std = std
            best_format = (byte_fmt, bit_fmt)

    if best_format:
        print(f"Best format: {best_format[0]}/{best_format[1]}")
        hx.set_reading_format(best_format[0], best_format[1])
    else:
        print("No stable format found - using MSB/MSB")
        hx.set_reading_format("MSB", "MSB")

    # Tare
    print("\n" + "="*50)
    print("TARE: Remove all weight from the scale")
    input("Press Enter when ready...")

    print("Taring (averaging multiple readings)...")
    hx.reset()
    hx.tare(times=15)
    print(f"Tare complete. Offset: {hx.OFFSET}")

    # Continuous reading
    print("\n" + "="*50)
    print("CONTINUOUS READING (Ctrl+C to stop)")
    print("="*50)
    print("Note: v0.1 library is slow (~1 reading/second)\n")

    try:
        while True:
            # Average 5 readings for stability
            val = hx.get_weight(times=5)
            print(f"Raw value: {val:>12.0f}")
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    main()

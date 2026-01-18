#!/usr/bin/env python3
"""
HX711 Scale - Raw GPIO Implementation
-------------------------------------
Working scale using direct GPIO control (no library dependencies).

Wiring:
    HX711 DOUT  -> GPIO 5
    HX711 SCK   -> GPIO 6
    HX711 VCC   -> 3.3V
    HX711 GND   -> GND
"""

import time
import sys

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("Must run on Raspberry Pi")
    sys.exit(1)

# Pin configuration (DOUT=5, SCK=6 confirmed working)
DOUT_PIN = 5
SCK_PIN = 6

# Calibration values (will be set during calibration)
OFFSET = 0
SCALE = 1


def setup():
    """Initialize GPIO pins."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(DOUT_PIN, GPIO.IN)
    GPIO.setup(SCK_PIN, GPIO.OUT)
    GPIO.output(SCK_PIN, 0)


def is_ready():
    """Check if HX711 is ready (DOUT low)."""
    return GPIO.input(DOUT_PIN) == 0


def wait_ready(timeout=2.0):
    """Wait for HX711 to be ready."""
    start = time.time()
    while not is_ready():
        if time.time() - start > timeout:
            return False
        time.sleep(0.001)
    return True


def read_raw():
    """Read raw 24-bit value from HX711."""
    if not wait_ready():
        return None

    # Read 24 bits
    raw_value = 0
    for _ in range(24):
        GPIO.output(SCK_PIN, 1)
        GPIO.output(SCK_PIN, 0)
        raw_value = (raw_value << 1) | GPIO.input(DOUT_PIN)

    # 25th pulse for gain = 128 (channel A)
    GPIO.output(SCK_PIN, 1)
    GPIO.output(SCK_PIN, 0)

    # Convert from 24-bit two's complement
    if raw_value & 0x800000:
        raw_value -= 0x1000000

    return raw_value


def read_average(times=10):
    """Read multiple values and return the average."""
    values = []
    for _ in range(times):
        val = read_raw()
        if val is not None:
            values.append(val)
        time.sleep(0.01)

    if values:
        return sum(values) / len(values)
    return None


def tare(times=20):
    """Set the zero offset (tare)."""
    global OFFSET
    print("Taring... keep scale empty")
    avg = read_average(times)
    if avg is not None:
        OFFSET = avg
        print(f"Offset set to: {OFFSET:.0f}")
        return True
    print("Tare failed!")
    return False


def calibrate(known_weight_grams, times=20):
    """Calibrate with a known weight."""
    global SCALE
    print(f"Place {known_weight_grams}g on the scale...")
    input("Press Enter when ready...")

    avg = read_average(times)
    if avg is not None:
        SCALE = (avg - OFFSET) / known_weight_grams
        print(f"Scale factor set to: {SCALE:.2f}")
        return True
    print("Calibration failed!")
    return False


def get_weight():
    """Get weight in grams."""
    raw = read_raw()
    if raw is not None:
        return (raw - OFFSET) / SCALE
    return None


def get_weight_average(times=5):
    """Get averaged weight in grams."""
    avg = read_average(times)
    if avg is not None:
        return (avg - OFFSET) / SCALE
    return None


def main():
    print("="*50)
    print("HX711 SCALE (Raw GPIO)")
    print("="*50)
    print(f"DOUT: GPIO {DOUT_PIN}")
    print(f"SCK:  GPIO {SCK_PIN}")
    print()

    setup()

    # Test reading
    print("Testing communication...")
    val = read_raw()
    if val is None:
        print("ERROR: Could not read from HX711")
        GPIO.cleanup()
        return

    print(f"Raw reading: {val} ✓")

    # Tare
    print("\n" + "-"*50)
    input("Remove all weight from scale, press Enter to tare...")
    tare()

    # Calibration
    print("\n" + "-"*50)
    response = input("Calibrate with known weight? (y/n): ")
    if response.lower() == 'y':
        weight = input("Enter calibration weight in grams: ")
        try:
            calibrate(float(weight))
        except ValueError:
            print("Invalid weight, using default scale factor")

    # Continuous reading
    print("\n" + "="*50)
    print("CONTINUOUS WEIGHT READING")
    print("Press Ctrl+C to stop")
    print("="*50 + "\n")

    try:
        while True:
            weight = get_weight_average(3)
            if weight is not None:
                if abs(weight) >= 1000:
                    print(f"\rWeight: {weight/1000:8.3f} kg  ", end="", flush=True)
                else:
                    print(f"\rWeight: {weight:8.1f} g   ", end="", flush=True)
            else:
                print("\rWeight: ERROR      ", end="", flush=True)
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\nStopped.")
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    main()

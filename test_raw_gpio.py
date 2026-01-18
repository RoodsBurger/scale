#!/usr/bin/env python3
"""
Raw GPIO test for HX711 - No libraries, just direct GPIO manipulation
----------------------------------------------------------------------
This script tests the absolute basics to diagnose HX711 issues.
"""

import sys
import time

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("Must run on Raspberry Pi")
    sys.exit(1)

def test_pins(dout_pin, sck_pin):
    """Test a specific pin configuration."""
    print(f"\n{'='*50}")
    print(f"Testing: DOUT=GPIO{dout_pin}, SCK=GPIO{sck_pin}")
    print('='*50)

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    GPIO.setup(dout_pin, GPIO.IN)
    GPIO.setup(sck_pin, GPIO.OUT)
    GPIO.output(sck_pin, 0)

    time.sleep(0.1)

    # Step 1: Check DOUT state with SCK low
    print("\n[Step 1] Initial state (SCK=LOW)")
    dout_state = GPIO.input(dout_pin)
    print(f"  DOUT = {dout_state} ({'HIGH - not ready' if dout_state else 'LOW - ready!'})")

    if dout_state == 1:
        print("\n  Waiting up to 2 seconds for DOUT to go LOW...")
        start = time.time()
        while GPIO.input(dout_pin) == 1 and (time.time() - start) < 2:
            time.sleep(0.01)

        dout_state = GPIO.input(dout_pin)
        if dout_state == 1:
            print(f"  TIMEOUT: DOUT stayed HIGH for 2 seconds")
            print("  → HX711 is not responding (check power & wiring)")
        else:
            print(f"  DOUT went LOW after {time.time()-start:.2f}s - HX711 ready!")

    # Step 2: Toggle SCK and watch DOUT
    if GPIO.input(dout_pin) == 0:
        print("\n[Step 2] Reading 24 bits by toggling SCK")
        print("  Bit | SCK↑ | DOUT | Running Value")
        print("  ----+------+------+--------------")

        raw_value = 0
        bits = []

        for i in range(24):
            # SCK HIGH
            GPIO.output(sck_pin, 1)
            time.sleep(0.000001)  # 1 microsecond

            # SCK LOW and read DOUT
            GPIO.output(sck_pin, 0)
            bit = GPIO.input(dout_pin)
            bits.append(bit)

            raw_value = (raw_value << 1) | bit

            if i < 8 or i >= 16:  # Show first and last 8 bits
                print(f"  {i+1:3} |  ↑↓  |  {bit}   | 0x{raw_value:06X}")
            elif i == 8:
                print("  ... |  ... | ...  | ...")

            time.sleep(0.000001)

        # 25th pulse for gain = 128
        GPIO.output(sck_pin, 1)
        time.sleep(0.000001)
        GPIO.output(sck_pin, 0)

        # Convert to signed
        if raw_value & 0x800000:
            signed_value = raw_value - 0x1000000
        else:
            signed_value = raw_value

        print(f"\n  Raw bits: {''.join(map(str, bits))}")
        print(f"  Hex: 0x{raw_value:06X}")
        print(f"  Decimal: {signed_value}")

        # Analyze the bits
        byte1 = (raw_value >> 16) & 0xFF
        byte2 = (raw_value >> 8) & 0xFF
        byte3 = raw_value & 0xFF

        print(f"\n  Byte analysis:")
        print(f"    Byte 1 (MSB): 0x{byte1:02X} = {byte1:08b}")
        print(f"    Byte 2:       0x{byte2:02X} = {byte2:08b}")
        print(f"    Byte 3 (LSB): 0x{byte3:02X} = {byte3:08b}")

        if raw_value == 0xFFFFFF:
            print("\n  ⚠ All bits are 1 - DOUT appears stuck HIGH during read")
        elif raw_value == 0x000000:
            print("\n  ⚠ All bits are 0 - DOUT appears stuck LOW during read")
        elif byte2 == 0xFF:
            print("\n  ⚠ Middle byte is 0xFF - possible timing issue")
        else:
            print("\n  ✓ Got varied bits - HX711 is communicating!")

        return raw_value

    return None


def main():
    print("#"*50)
    print("# RAW GPIO TEST FOR HX711")
    print("#"*50)
    print("\nThis test directly manipulates GPIO without any library.")
    print("It will help identify exactly where communication fails.")

    # Test configurations to try
    configs = [
        (5, 6, "Default"),
        (6, 5, "Swapped"),
        (17, 27, "Alt pins"),
        (27, 17, "Alt swapped"),
    ]

    results = []

    try:
        for dout, sck, name in configs:
            GPIO.cleanup()
            result = test_pins(dout, sck)
            results.append((name, dout, sck, result))
            time.sleep(0.5)

        # Summary
        print("\n" + "#"*50)
        print("# SUMMARY")
        print("#"*50)

        for name, dout, sck, result in results:
            if result is None:
                status = "TIMEOUT (no response)"
            elif result == 0xFFFFFF:
                status = "ALL 1s (stuck HIGH)"
            elif result == 0x000000:
                status = "ALL 0s (stuck LOW)"
            else:
                status = f"0x{result:06X} ✓"

            print(f"  {name:12} (DOUT={dout}, SCK={sck}): {status}")

        print("\n" + "="*50)
        print("INTERPRETATION:")
        print("="*50)
        print("""
  ALL TIMEOUT:
    → HX711 not powered, or DOUT not connected

  ALL 1s (0xFFFFFF):
    → SCK not reaching HX711, or pins swapped

  ALL 0s (0x000000):
    → DOUT shorted to ground

  One config works:
    → Use that pin configuration!

  Varied readings on one config:
    → That's the working setup, may need stabilization
""")

    except KeyboardInterrupt:
        print("\nInterrupted")
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    main()

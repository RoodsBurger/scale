#!/usr/bin/env python3
"""
HX711 Diagnostic Script
-----------------------
Diagnoses common issues with HX711 wiring and communication.
"""

import sys
import time

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("ERROR: This script must run on a Raspberry Pi with RPi.GPIO installed")
    sys.exit(1)

# Default pins (BCM numbering)
DOUT_PIN = 5
SCK_PIN = 6

def setup_gpio():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(DOUT_PIN, GPIO.IN)
    GPIO.setup(SCK_PIN, GPIO.OUT)

def check_dout_state():
    """Check initial DOUT state."""
    print("\n" + "="*50)
    print("CHECK 1: DOUT Pin State")
    print("="*50)

    # Make sure SCK is LOW
    GPIO.output(SCK_PIN, False)
    time.sleep(0.1)

    dout_state = GPIO.input(DOUT_PIN)
    print(f"DOUT (GPIO {DOUT_PIN}) state: {'HIGH' if dout_state else 'LOW'}")

    if dout_state == GPIO.LOW:
        print("✓ HX711 is signaling READY (DOUT is LOW)")
        return True
    else:
        print("⚠ HX711 is signaling NOT READY (DOUT is HIGH)")
        print("  This could mean:")
        print("  - HX711 is still powering up (wait a moment)")
        print("  - DOUT pin is not connected")
        print("  - Wrong GPIO pin configured")
        return False

def check_sck_toggle():
    """Check if toggling SCK affects DOUT."""
    print("\n" + "="*50)
    print("CHECK 2: SCK Toggle Test")
    print("="*50)

    # Read initial DOUT
    initial_dout = GPIO.input(DOUT_PIN)
    print(f"Initial DOUT state: {'HIGH' if initial_dout else 'LOW'}")

    # Toggle SCK and observe DOUT
    dout_states = []
    for i in range(25):  # 24 data bits + 1 gain pulse
        GPIO.output(SCK_PIN, True)
        time.sleep(0.000001)  # 1 microsecond
        GPIO.output(SCK_PIN, False)
        time.sleep(0.000001)
        dout_states.append(GPIO.input(DOUT_PIN))

    # Check if we got any LOW states (0s)
    highs = sum(dout_states)
    lows = len(dout_states) - highs

    print(f"After 25 clock pulses:")
    print(f"  HIGH readings: {highs}")
    print(f"  LOW readings:  {lows}")
    print(f"  Bit pattern: {''.join(['1' if s else '0' for s in dout_states[:24]])}")

    if highs == 25:
        print("\n✗ All bits are HIGH - this indicates:")
        print("  1. DOUT and SCK pins might be SWAPPED")
        print("  2. DOUT is not connected properly")
        print("  3. HX711 is not powered")
        return False
    elif lows == 25:
        print("\n✗ All bits are LOW - this indicates:")
        print("  1. DOUT might be shorted to ground")
        print("  2. Load cell connection issue")
        return False
    else:
        print("\n✓ Mixed bit pattern detected - communication working!")
        return True

def check_ready_signal():
    """Wait for HX711 to become ready and measure timing."""
    print("\n" + "="*50)
    print("CHECK 3: Ready Signal Test")
    print("="*50)

    GPIO.output(SCK_PIN, False)

    print("Waiting for HX711 to signal ready (DOUT goes LOW)...")

    start_time = time.time()
    timeout = 2.0  # 2 second timeout

    while GPIO.input(DOUT_PIN) == GPIO.HIGH:
        if time.time() - start_time > timeout:
            print(f"✗ Timeout after {timeout}s - HX711 never signaled ready")
            print("  Check power connections (VCC and GND)")
            return False
        time.sleep(0.001)

    elapsed = (time.time() - start_time) * 1000
    print(f"✓ HX711 ready signal received in {elapsed:.1f}ms")
    return True

def read_raw_value():
    """Try to read a raw 24-bit value."""
    print("\n" + "="*50)
    print("CHECK 4: Raw Value Read")
    print("="*50)

    # Wait for ready
    GPIO.output(SCK_PIN, False)
    timeout = time.time() + 1.0
    while GPIO.input(DOUT_PIN) == GPIO.HIGH:
        if time.time() > timeout:
            print("✗ Timeout waiting for ready signal")
            return None

    # Read 24 bits
    raw_value = 0
    for i in range(24):
        GPIO.output(SCK_PIN, True)
        GPIO.output(SCK_PIN, False)
        bit = GPIO.input(DOUT_PIN)
        raw_value = (raw_value << 1) | bit

    # Send one more pulse for gain=128 (channel A)
    GPIO.output(SCK_PIN, True)
    GPIO.output(SCK_PIN, False)

    # Convert from 24-bit two's complement
    if raw_value & 0x800000:
        signed_value = raw_value - 0x1000000
    else:
        signed_value = raw_value

    print(f"Raw 24-bit value: 0x{raw_value:06X}")
    print(f"Binary: {raw_value:024b}")
    print(f"Signed decimal: {signed_value}")

    if raw_value == 0xFFFFFF:
        print("\n✗ All bits are 1 (0xFFFFFF = -1)")
        print("  LIKELY CAUSE: DOUT and SCK pins are SWAPPED!")
        print(f"  Try swapping: DOUT->GPIO{SCK_PIN}, SCK->GPIO{DOUT_PIN}")
        return None
    elif raw_value == 0x000000:
        print("\n✗ All bits are 0")
        print("  Check load cell wiring to HX711")
        return None
    else:
        print("\n✓ Valid reading obtained!")
        return signed_value

def try_swapped_pins():
    """Try reading with swapped pins."""
    global DOUT_PIN, SCK_PIN

    print("\n" + "="*50)
    print("CHECK 5: Testing Swapped Pins")
    print("="*50)

    # Swap pins
    DOUT_PIN, SCK_PIN = SCK_PIN, DOUT_PIN
    print(f"Trying with DOUT=GPIO{DOUT_PIN}, SCK=GPIO{SCK_PIN}")

    # Re-setup
    GPIO.setup(DOUT_PIN, GPIO.IN)
    GPIO.setup(SCK_PIN, GPIO.OUT)
    GPIO.output(SCK_PIN, False)

    time.sleep(0.1)

    # Wait for ready
    timeout = time.time() + 1.0
    while GPIO.input(DOUT_PIN) == GPIO.HIGH:
        if time.time() > timeout:
            print("✗ Still timing out with swapped pins")
            return None

    # Read value
    raw_value = 0
    for i in range(24):
        GPIO.output(SCK_PIN, True)
        GPIO.output(SCK_PIN, False)
        bit = GPIO.input(DOUT_PIN)
        raw_value = (raw_value << 1) | bit

    GPIO.output(SCK_PIN, True)
    GPIO.output(SCK_PIN, False)

    if raw_value & 0x800000:
        signed_value = raw_value - 0x1000000
    else:
        signed_value = raw_value

    print(f"Raw value with swapped pins: 0x{raw_value:06X} ({signed_value})")

    if raw_value != 0xFFFFFF and raw_value != 0x000000:
        print("\n✓ SWAPPED PINS WORK!")
        print(f"  Use: --dout {DOUT_PIN} --sck {SCK_PIN}")
        return signed_value

    return None

def main():
    print("#" * 50)
    print("# HX711 DIAGNOSTIC TOOL")
    print("#" * 50)
    print(f"\nUsing BCM GPIO numbering")
    print(f"DOUT pin: GPIO {DOUT_PIN}")
    print(f"SCK pin:  GPIO {SCK_PIN}")

    try:
        setup_gpio()

        check_dout_state()
        check_ready_signal()
        comm_ok = check_sck_toggle()
        value = read_raw_value()

        if value is None and not comm_ok:
            try_swapped_pins()

        print("\n" + "="*50)
        print("DIAGNOSIS COMPLETE")
        print("="*50)

        if value is not None and value != -1:
            print("\n✓ HX711 appears to be working!")
            print("  You can proceed with calibration.")
        else:
            print("\nTroubleshooting steps:")
            print("1. Check power: VCC->5V, GND->GND")
            print("2. Try swapping DOUT and SCK wires")
            print("3. Verify GPIO pin numbers (BCM, not physical)")
            print("4. Check load cell connections to HX711:")
            print("   - Red   -> E+")
            print("   - Black -> E-")
            print("   - White -> A-")
            print("   - Green -> A+")

    except KeyboardInterrupt:
        print("\nInterrupted")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()

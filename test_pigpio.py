#!/usr/bin/env python3
"""
HX711 Test using pigpio (DMA-based GPIO for better timing)
----------------------------------------------------------
pigpio provides more precise GPIO timing than RPi.GPIO,
which can help with timing-sensitive protocols like HX711.

Install: sudo apt install pigpio python3-pigpio
Run daemon first: sudo pigpiod
"""

import sys
import time

try:
    import pigpio
except ImportError:
    print("pigpio not installed. Run:")
    print("  sudo apt install pigpio python3-pigpio")
    sys.exit(1)

# GPIO pins (BCM numbering)
DOUT_PIN = 5
SCK_PIN = 6

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dout', type=int, default=5)
    parser.add_argument('--sck', type=int, default=6)
    args = parser.parse_args()

    global DOUT_PIN, SCK_PIN
    DOUT_PIN = args.dout
    SCK_PIN = args.sck

    print("="*50)
    print("HX711 Test using pigpio (DMA-based timing)")
    print("="*50)
    print(f"DOUT: GPIO {DOUT_PIN}")
    print(f"SCK:  GPIO {SCK_PIN}")
    print()

    # Connect to pigpio daemon
    pi = pigpio.pi()
    if not pi.connected:
        print("ERROR: Could not connect to pigpio daemon")
        print("Run: sudo pigpiod")
        sys.exit(1)

    # Setup pins
    pi.set_mode(DOUT_PIN, pigpio.INPUT)
    pi.set_mode(SCK_PIN, pigpio.OUTPUT)
    pi.write(SCK_PIN, 0)

    print("Taking 10 readings...\n")

    for i in range(10):
        # Wait for DOUT to go LOW (ready)
        timeout = time.time() + 2
        while pi.read(DOUT_PIN) == 1:
            if time.time() > timeout:
                print(f"Reading {i+1}: TIMEOUT (DOUT stuck HIGH)")
                break
        else:
            # Read 24 bits
            raw_value = 0
            for bit in range(24):
                pi.write(SCK_PIN, 1)
                pi.write(SCK_PIN, 0)
                raw_value = (raw_value << 1) | pi.read(DOUT_PIN)

            # One more pulse for gain=128
            pi.write(SCK_PIN, 1)
            pi.write(SCK_PIN, 0)

            # Convert from 24-bit two's complement
            if raw_value & 0x800000:
                signed_value = raw_value - 0x1000000
            else:
                signed_value = raw_value

            binary = f"{raw_value:024b}"
            print(f"Reading {i+1}: {signed_value:>10}  (0x{raw_value:06X} = {binary})")

        time.sleep(0.1)

    pi.write(SCK_PIN, 0)
    pi.stop()
    print("\nDone.")


if __name__ == "__main__":
    main()

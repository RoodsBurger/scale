#!/usr/bin/env python3
"""
Continuous raw reading - shows exactly what's coming from HX711
"""

import time
import sys
import RPi.GPIO as GPIO

DOUT = 5
SCK = 6

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(DOUT, GPIO.IN)
GPIO.setup(SCK, GPIO.OUT)
GPIO.output(SCK, 0)

print("Continuous HX711 Debug (DOUT=5, SCK=6)")
print("Press Ctrl+C to stop")
print("-" * 60)
print(f"{'#':>3} | {'Raw':>12} | {'Hex':>10} | {'Binary':<24} | Status")
print("-" * 60)

count = 0
try:
    while True:
        # Wait for ready (DOUT LOW)
        timeout = time.time() + 1
        while GPIO.input(DOUT) == 1:
            if time.time() > timeout:
                print(f"{count:3} | {'TIMEOUT':>12} | {'--':>10} | {'DOUT stuck HIGH':<24} | ❌")
                count += 1
                time.sleep(0.5)
                continue

        # Read 24 bits
        raw = 0
        for _ in range(24):
            GPIO.output(SCK, 1)
            GPIO.output(SCK, 0)
            raw = (raw << 1) | GPIO.input(DOUT)

        # 25th pulse
        GPIO.output(SCK, 1)
        GPIO.output(SCK, 0)

        # Convert
        if raw & 0x800000:
            signed = raw - 0x1000000
        else:
            signed = raw

        # Status
        if raw == 0xFFFFFF:
            status = "❌ ALL 1s"
        elif raw == 0x000000:
            status = "❌ ALL 0s"
        else:
            status = "✓"

        binary = f"{raw:024b}"
        print(f"{count:3} | {signed:>12} | 0x{raw:06X} | {binary[:8]} {binary[8:16]} {binary[16:]} | {status}")

        count += 1
        time.sleep(0.2)

except KeyboardInterrupt:
    print("\nStopped")
finally:
    GPIO.cleanup()

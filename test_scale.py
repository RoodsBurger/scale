#!/usr/bin/env python3
"""
HX711 Scale Test Script
-----------------------
Test script for a Raspberry Pi scale using HX711 load cell amplifier.

Wiring (default):
    HX711 DOUT  -> GPIO 5
    HX711 PD_SCK -> GPIO 6
    HX711 VCC   -> 5V
    HX711 GND   -> GND

Usage:
    python3 test_scale.py [--dout PIN] [--sck PIN]
"""

import sys
import time
import argparse
import os

# Add hx711py to path (relative to this script's location)
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, 'hx711py'))

try:
    import RPi.GPIO as GPIO
    from hx711v0_5_1 import HX711
    EMULATOR_MODE = False
except ImportError:
    print("RPi.GPIO not found - running in emulator mode")
    from hx711_emulator import HX711
    EMULATOR_MODE = True


class ScaleTest:
    def __init__(self, dout_pin=5, sck_pin=6, gain=128):
        self.dout_pin = dout_pin
        self.sck_pin = sck_pin
        self.gain = gain
        self.hx = None
        self.reference_unit = 1

    def initialize(self):
        """Initialize the HX711 sensor."""
        print(f"Initializing HX711...")
        print(f"  DOUT pin: GPIO {self.dout_pin}")
        print(f"  SCK pin:  GPIO {self.sck_pin}")
        print(f"  Gain:     {self.gain}")
        print()

        if EMULATOR_MODE:
            self.hx = HX711(self.dout_pin, self.sck_pin)
            self.hx.set_reference_unit(1)
        else:
            self.hx = HX711(dout=self.dout_pin, pd_sck=self.sck_pin, gain=self.gain)
            self.hx.setReadingFormat("MSB", "MSB")

        print("HX711 initialized successfully!")
        return True

    def test_connection(self):
        """Test basic communication with the HX711."""
        print("\n" + "="*50)
        print("TEST 1: Connection Test")
        print("="*50)

        try:
            if EMULATOR_MODE:
                raw_value = self.hx.get_weight(1)
            else:
                raw_value = self.hx.getLong()

            print(f"Raw reading: {raw_value}")

            if raw_value is not None:
                print("✓ Connection successful!")
                return True
            else:
                print("✗ No data received from HX711")
                return False
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False

    def test_reading_formats(self):
        """Test different byte/bit format combinations."""
        if EMULATOR_MODE:
            print("Skipping format test in emulator mode")
            return

        print("\n" + "="*50)
        print("TEST: Reading Format Detection")
        print("="*50)
        print("Testing all byte/bit format combinations...")
        print()

        formats = [
            ("MSB", "MSB"),
            ("MSB", "LSB"),
            ("LSB", "MSB"),
            ("LSB", "LSB"),
        ]

        best_format = None
        best_variance = float('inf')
        best_readings = []

        for byte_fmt, bit_fmt in formats:
            self.hx.setReadingFormat(byte_fmt, bit_fmt)
            time.sleep(0.2)

            readings = []
            for _ in range(5):
                val = self.hx.getLong()
                readings.append(val)
                time.sleep(0.05)

            avg = sum(readings) / len(readings)
            variance = max(readings) - min(readings)

            # Check for suspicious power-of-2 patterns
            suspicious = all(
                (r & (r + 1)) == 0 or r == 0  # Check if r is 2^n - 1
                for r in readings if r > 0
            )

            status = "⚠ SUSPICIOUS" if suspicious else ""
            print(f"  {byte_fmt}/{bit_fmt}: avg={avg:>10.0f}  var={variance:>8}  {status}")
            print(f"           readings: {readings}")

            if not suspicious and variance < best_variance:
                best_variance = variance
                best_format = (byte_fmt, bit_fmt)
                best_readings = readings

        if best_format:
            print(f"\n✓ Best format: {best_format[0]}/{best_format[1]}")
            self.hx.setReadingFormat(best_format[0], best_format[1])
        else:
            print("\n⚠ All formats show suspicious patterns - check wiring")
            self.hx.setReadingFormat("MSB", "MSB")

    def test_stability(self, num_readings=10):
        """Test reading stability by taking multiple samples."""
        print("\n" + "="*50)
        print("TEST 2: Stability Test")
        print("="*50)
        print(f"Taking {num_readings} readings...")
        print("(Keep the scale empty and still)")
        print()

        time.sleep(1)
        readings = []

        for i in range(num_readings):
            if EMULATOR_MODE:
                value = self.hx.get_weight(1)
            else:
                # Get raw bytes and show binary for debugging
                raw_bytes = self.hx.getRawBytes()
                value = self.hx.rawBytesToLong(raw_bytes)
                if raw_bytes:
                    binary = ''.join(f'{b:08b}' for b in raw_bytes)
                    print(f"  Reading {i+1}: {value:>10}  (0x{raw_bytes[0]:02X}{raw_bytes[1]:02X}{raw_bytes[2]:02X} = {binary})")
                else:
                    print(f"  Reading {i+1}: {value}")
            readings.append(value if value else 0)
            time.sleep(0.1)

        if readings:
            avg = sum(readings) / len(readings)
            min_val = min(readings)
            max_val = max(readings)
            variance = max_val - min_val

            print()
            print(f"Average:  {avg:.2f}")
            print(f"Min:      {min_val}")
            print(f"Max:      {max_val}")
            print(f"Variance: {variance}")

            # Check for power-of-2-minus-1 pattern (indicates bit issues)
            suspicious_count = sum(1 for r in readings if r > 0 and (r & (r + 1)) == 0)
            if suspicious_count > len(readings) // 2:
                print("\n⚠ WARNING: Values are mostly 2^n-1 patterns (511, 1023, 2047...)")
                print("  This suggests timing/wiring issues, not normal noise.")
                print("  Try: check connections, use shorter wires, or try the v0.1 library")

            # Check if variance is reasonable (less than 5% of average)
            elif avg != 0 and abs(variance / avg) < 0.05:
                print("✓ Readings are stable!")
            else:
                print("⚠ Readings show some variance (this may be normal)")

            return avg
        return None

    def calibrate_zero(self):
        """Calibrate the zero point (tare)."""
        print("\n" + "="*50)
        print("CALIBRATION: Zero Point (Tare)")
        print("="*50)
        print("Remove all weight from the scale...")
        input("Press Enter when ready...")

        print("Calibrating zero point...")

        if EMULATOR_MODE:
            self.hx.tare()
            offset = 0
        else:
            self.hx.autosetOffset()
            offset = self.hx.getOffset()

        print(f"✓ Zero offset set to: {offset}")
        return offset

    def calibrate_reference(self, known_weight_grams):
        """Calibrate with a known weight to set the reference unit."""
        print("\n" + "="*50)
        print("CALIBRATION: Reference Weight")
        print("="*50)
        print(f"Place a {known_weight_grams}g weight on the scale...")
        input("Press Enter when ready...")

        print("Reading value with known weight...")
        time.sleep(1)

        readings = []
        for _ in range(10):
            if EMULATOR_MODE:
                value = self.hx.get_weight(1)
            else:
                value = self.hx.getLongWithOffset()
            readings.append(value)
            time.sleep(0.1)

        avg_value = sum(readings) / len(readings)

        if avg_value != 0:
            self.reference_unit = avg_value / known_weight_grams

            if EMULATOR_MODE:
                self.hx.set_reference_unit(self.reference_unit)
            else:
                self.hx.setReferenceUnit(self.reference_unit)

            print(f"Average raw value: {avg_value:.2f}")
            print(f"✓ Reference unit set to: {self.reference_unit:.4f}")
            return self.reference_unit
        else:
            print("✗ Could not calibrate - no change detected")
            return None

    def continuous_reading(self):
        """Continuously read and display weight."""
        print("\n" + "="*50)
        print("CONTINUOUS WEIGHT READING")
        print("="*50)
        print("Press Ctrl+C to stop")
        print()

        try:
            while True:
                if EMULATOR_MODE:
                    weight = self.hx.get_weight(5)
                else:
                    weight = self.hx.getWeight()

                # Display with units
                if abs(weight) >= 1000:
                    print(f"\rWeight: {weight/1000:.3f} kg    ", end="", flush=True)
                else:
                    print(f"\rWeight: {weight:.1f} g      ", end="", flush=True)

                time.sleep(0.1)

        except KeyboardInterrupt:
            print("\n\nStopped.")

    def run_full_test(self):
        """Run all tests in sequence."""
        print("\n" + "#"*50)
        print("# HX711 SCALE TEST SUITE")
        print("#"*50)

        if EMULATOR_MODE:
            print("\n⚠ Running in EMULATOR MODE (no real hardware)")

        # Initialize
        if not self.initialize():
            return False

        # Test connection
        if not self.test_connection():
            return False

        # Test reading formats
        self.test_reading_formats()

        # Test stability
        self.test_stability()

        # Ask about calibration
        print("\n" + "="*50)
        response = input("Would you like to calibrate the scale? (y/n): ")

        if response.lower() == 'y':
            self.calibrate_zero()

            weight = input("Enter the weight of your calibration object in grams (or skip): ")
            if weight.strip() and weight.strip().lower() != 'skip':
                try:
                    self.calibrate_reference(float(weight))
                except ValueError:
                    print("Invalid weight entered, skipping reference calibration")

        # Continuous reading
        print("\n" + "="*50)
        response = input("Start continuous weight reading? (y/n): ")

        if response.lower() == 'y':
            self.continuous_reading()

        return True

    def cleanup(self):
        """Clean up GPIO resources."""
        if not EMULATOR_MODE:
            try:
                GPIO.cleanup()
                print("GPIO cleaned up.")
            except:
                pass


def main():
    parser = argparse.ArgumentParser(description='HX711 Scale Test Script')
    parser.add_argument('--dout', type=int, default=5, help='GPIO pin for DOUT (default: 5)')
    parser.add_argument('--sck', type=int, default=6, help='GPIO pin for PD_SCK (default: 6)')
    parser.add_argument('--gain', type=int, default=128, choices=[32, 64, 128],
                        help='Gain setting (default: 128)')
    parser.add_argument('--quick', action='store_true', help='Quick test without calibration')

    args = parser.parse_args()

    scale = ScaleTest(dout_pin=args.dout, sck_pin=args.sck, gain=args.gain)

    try:
        if args.quick:
            scale.initialize()
            scale.test_connection()
            scale.test_stability()
        else:
            scale.run_full_test()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    except Exception as e:
        print(f"\nError: {e}")
        raise
    finally:
        scale.cleanup()


if __name__ == "__main__":
    main()

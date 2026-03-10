#!/usr/bin/env python3
"""
AURA EEG Stream Test Script
Verifies the AURA LSL stream format: channels, sample rate (~250 Hz), and data structure.
Saves a short sample to aura_test_output.csv for manual inspection.
"""
import csv
import sys
import time

try:
    from pylsl import StreamInlet, resolve_byprop
except ImportError:
    print("Error: pylsl not installed. Run: pip install pylsl")
    sys.exit(1)


def main():
    print("Looking for AURA EEG stream...")
    try:
        streams = resolve_byprop('name', 'AURA')
    except Exception as e:
        print(f"Error resolving stream: {e}")
        sys.exit(1)

    if not streams:
        print("No AURA stream found. Make sure AURA is running and broadcasting via LSL.")
        sys.exit(1)

    print(f"Found stream: {streams[0].name()}", flush=True)
    print("Connecting to stream (may take a few seconds)...", flush=True)
    inlet = StreamInlet(streams[0])
    print("Connected.", flush=True)

    # Get stream info (avoid XML channel parsing - AURA can hang there)
    print("Getting stream info...", flush=True)
    info = inlet.info()
    channel_count = info.channel_count()
    nominal_sr = info.nominal_srate()
    channel_names = [f"ch{i+1}" for i in range(channel_count)]

    print(f"\n--- Stream Info ---")
    print(f"Channels: {channel_count}")
    print(f"Nominal sample rate: {nominal_sr} Hz")
    print(f"Channel names: {channel_names[:8]}{'...' if len(channel_names) > 8 else ''}")

    # Collect samples for ~5 seconds
    duration_sec = 5
    samples = []
    start = time.time()
    last_print = start
    print(f"\nCollecting samples for {duration_sec} seconds...", flush=True)

    while time.time() - start < duration_sec:
        sample, timestamp = inlet.pull_sample(timeout=1.0)
        if sample is not None:
            samples.append((timestamp, sample))
        if time.time() - last_print >= 1.0:
            elapsed_loop = time.time() - start
            print(f"  ... {elapsed_loop:.1f}s elapsed, {len(samples)} samples so far", flush=True)
            last_print = time.time()

    elapsed = time.time() - start
    actual_rate = len(samples) / elapsed if elapsed > 0 else 0
    print(f"Collected {len(samples)} samples in {elapsed:.2f}s (~{actual_rate:.1f} Hz)")

    if not samples:
        print("No samples received. Check AURA connection.")
        sys.exit(1)

    # Print first few samples
    print(f"\n--- First 3 samples ---")
    for i, (ts, samp) in enumerate(samples[:3]):
        print(f"  Sample {i+1}: timestamp={ts:.4f}, values={samp[:5]}{'...' if len(samp) > 5 else ''}")

    # Save to CSV
    output_path = "aura_test_output.csv"
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        header = ["timestamp"] + channel_names
        writer.writerow(header)
        for ts, samp in samples[:500]:  # Limit to 500 rows for test
            writer.writerow([ts] + list(samp))

    print(f"\nSaved {min(len(samples), 500)} rows to {output_path}")
    print("Test complete.")


if __name__ == "__main__":
    main()

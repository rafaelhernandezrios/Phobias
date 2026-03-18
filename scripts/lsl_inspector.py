#!/usr/bin/env python3
"""
LSL Inspector — list active LSL streams and optionally preview samples.

Examples:
  python scripts/lsl_inspector.py
  python scripts/lsl_inspector.py --name AURA
  python scripts/lsl_inspector.py --watch 1.0
  python scripts/lsl_inspector.py --name AURA --sample --pick 0
  python scripts/lsl_inspector.py --uid <uid> --sample
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Optional

try:
    from pylsl import StreamInlet, resolve_streams  # type: ignore
except Exception:
    print("Error: pylsl not installed. Run: pip install pylsl")
    raise SystemExit(1)


def _safe(call, default="—"):
    try:
        return call()
    except Exception:
        return default


def list_streams(name: Optional[str], stype: Optional[str]) -> list:
    streams = resolve_streams()
    if name:
        streams = [s for s in streams if _safe(s.name, "") == name]
    if stype:
        streams = [s for s in streams if _safe(s.type, "") == stype]
    return streams


def print_streams(streams: list) -> None:
    if not streams:
        print("No LSL streams found.")
        return

    print(f"Found {len(streams)} stream(s):\n")
    for i, s in enumerate(streams):
        print(f"[{i}] name={_safe(s.name)!r} type={_safe(s.type)!r}")
        print(f"    source_id={_safe(s.source_id)!r}")
        print(f"    uid={_safe(s.uid)!r}")
        print(f"    hostname={_safe(s.hostname)!r}")
        print(f"    channels={_safe(s.channel_count)!r} srate={_safe(s.nominal_srate)!r} fmt={_safe(s.channel_format)!r}")
        print(f"    created_at={_safe(s.created_at)!r}")
        print()


def preview_samples(streams: list, pick: Optional[int], uid: Optional[str], seconds: float) -> int:
    chosen = None
    if uid:
        for s in streams:
            if _safe(s.uid, None) == uid:
                chosen = s
                break
        if chosen is None:
            print(f"Error: no stream with uid={uid!r} in current selection.")
            return 2
    else:
        if pick is None:
            pick = 0
        if pick < 0 or pick >= len(streams):
            print(f"Error: --pick must be between 0 and {max(0, len(streams)-1)}")
            return 2
        chosen = streams[pick]

    print("Previewing samples from:")
    print(f"  name={_safe(chosen.name)!r} type={_safe(chosen.type)!r} source_id={_safe(chosen.source_id)!r} uid={_safe(chosen.uid)!r}")
    print("  (Ctrl+C to stop)\n")

    inlet = StreamInlet(chosen, max_buflen=10)
    t0 = time.time()
    n = 0
    try:
        while time.time() - t0 < seconds:
            sample, ts = inlet.pull_sample(timeout=0.5)
            if sample is None:
                continue
            n += 1
            print(f"{n:06d}  ts={ts:.6f}  sample={sample}")
        return 0
    except KeyboardInterrupt:
        return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="List active LSL streams and optionally preview samples.")
    ap.add_argument("--name", default=None, help="Filter by stream name (exact match), e.g. AURA")
    ap.add_argument("--type", default=None, help="Filter by stream type (exact match), e.g. EEG")
    ap.add_argument("--watch", type=float, default=0.0, help="Refresh listing every N seconds (0 = once)")
    ap.add_argument("--sample", action="store_true", help="Preview samples from a selected stream")
    ap.add_argument("--pick", type=int, default=None, help="Index from the printed list to sample (default: 0)")
    ap.add_argument("--uid", default=None, help="UID of stream to sample (overrides --pick)")
    ap.add_argument("--seconds", type=float, default=10.0, help="How long to sample for (default: 10s)")
    args = ap.parse_args()

    def run_once() -> int:
        streams = list_streams(args.name, args.type)
        print_streams(streams)
        if args.sample:
            if not streams:
                return 2
            return preview_samples(streams, args.pick, args.uid, args.seconds)
        return 0

    if args.watch and args.watch > 0 and not args.sample:
        try:
            while True:
                print("\n" + "=" * 72 + "\n")
                run_once()
                time.sleep(args.watch)
        except KeyboardInterrupt:
            return 0

    return run_once()


if __name__ == "__main__":
    raise SystemExit(main())


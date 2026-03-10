#!/usr/bin/env python3
"""
AURA EEG Recorder — LSL + WebSocket bridge
Reads AURA EEG stream, receives experiment events from browser via WebSocket,
and saves CSV with timestamp, channel values, and label (phobia_level).
"""
import asyncio
import csv
import json
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

try:
    from pylsl import StreamInlet, resolve_stream
except ImportError:
    print("Error: pylsl not installed. Run: pip install pylsl")
    sys.exit(1)

try:
    import websockets
except ImportError:
    print("Error: websockets not installed. Run: pip install websockets")
    sys.exit(1)


# --- Configuration ---
WS_PORT = 8765
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
STREAM_NAME = "AURA"


class EEGRecorder:
    def __init__(self):
        self.inlet = None
        self.channel_names = []
        self.samples_buffer = []
        self.current_label = None
        self.current_phobia_id = None
        self.recording = False
        self.lock = threading.Lock()
        self.thread = None

    def _resolve_stream(self):
        print(f"Looking for stream '{STREAM_NAME}'...")
        streams = resolve_stream('name', STREAM_NAME)
        if not streams:
            raise RuntimeError(f"No stream named '{STREAM_NAME}' found. Is AURA running?")
        return streams[0]

    def _init_channel_names(self):
        info = self.inlet.info()
        channel_count = info.channel_count()
        self.channel_names = [f"ch{i+1}" for i in range(channel_count)]

    def _reader_thread(self):
        while self.recording and self.inlet:
            try:
                sample, timestamp = self.inlet.pull_sample(timeout=0.1)
                if sample is not None and self.current_label:
                    with self.lock:
                        self.samples_buffer.append((timestamp, list(sample), self.current_label))
            except Exception as e:
                if self.recording:
                    print(f"[EEG] Read error: {e}")
                break

    def start_lsl(self):
        stream_info = self._resolve_stream()
        self.inlet = StreamInlet(stream_info)
        self._init_channel_names()
        print(f"Connected to AURA. Channels: {len(self.channel_names)}")

    def start_recording(self, phobia_id):
        with self.lock:
            self.current_phobia_id = phobia_id
            self.current_label = f"{phobia_id}_level2"  # Start at level 2
            self.recording = True
            self.samples_buffer = []
        self.thread = threading.Thread(target=self._reader_thread, daemon=True)
        self.thread.start()
        print(f"[EEG] Recording started. Label: {self.current_label}")

    def set_level(self, level):
        if self.current_phobia_id:
            new_label = f"{self.current_phobia_id}_level{level}"
            with self.lock:
                self.current_label = new_label
            print(f"[EEG] Level changed to {level}. Label: {new_label}")

    def stop_recording(self):
        self.recording = False
        if self.thread:
            self.thread.join(timeout=2.0)
        with self.lock:
            self.current_label = None
            self.current_phobia_id = None
        print("[EEG] Recording stopped.")

    def save_csv(self, filepath=None):
        with self.lock:
            samples = list(self.samples_buffer)

        if not samples:
            print("[EEG] No samples to save.")
            return None

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        if filepath is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = OUTPUT_DIR / f"eeg_{self.current_phobia_id or 'session'}_{ts}.csv"

        header = ["timestamp"] + self.channel_names + ["label"]
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for ts, vals, label in samples:
                writer.writerow([ts] + vals + [label])

        print(f"[EEG] Saved {len(samples)} rows to {filepath}")
        return str(filepath)


recorder = EEGRecorder()


async def handle_websocket(websocket, path="/"):
    print(f"Browser connected: {websocket.remote_address}")
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get("type")
                if msg_type == "start":
                    phobia_id = data.get("phobia_id", "unknown")
                    if recorder.recording:
                        recorder.save_csv()
                        recorder.stop_recording()
                    recorder.start_recording(phobia_id)
                    await websocket.send(json.dumps({"status": "started", "phobia_id": phobia_id}))
                elif msg_type == "level_change":
                    level = data.get("level", 2)
                    recorder.set_level(level)
                    await websocket.send(json.dumps({"status": "level_changed", "level": level}))
                elif msg_type == "stop":
                    path = recorder.save_csv()
                    recorder.stop_recording()
                    await websocket.send(json.dumps({"status": "stopped", "file": path}))
                else:
                    await websocket.send(json.dumps({"error": f"Unknown type: {msg_type}"}))
            except json.JSONDecodeError as e:
                await websocket.send(json.dumps({"error": f"Invalid JSON: {e}"}))
            except Exception as e:
                await websocket.send(json.dumps({"error": str(e)}))
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        if recorder.recording:
            recorder.save_csv()
            recorder.stop_recording()
        print("Browser disconnected.")


def run_websocket_server(use_wss=False):
    ssl_ctx = None
    if use_wss:
        import ssl
        cert = PROJECT_ROOT / "cert.pem"
        key = PROJECT_ROOT / "key.pem"
        if cert.exists() and key.exists():
            ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_ctx.load_cert_chain(str(cert), str(key))
            print("Using WSS (HTTPS) with cert.pem/key.pem")
        else:
            print("Warning: --wss requested but cert.pem/key.pem not found. Run: npm run cert")
            use_wss = False

    host = "0.0.0.0"  # accept connections from VR headset and other devices
    scheme = "wss" if use_wss else "ws"

    async def run_ws():
        async with websockets.serve(
            handle_websocket, host, WS_PORT, ssl=ssl_ctx,
            ping_interval=20, ping_timeout=20,
        ):
            print(f"WebSocket server listening on {scheme}://{host}:{WS_PORT}")
            if use_wss:
                print("  (HTTPS page must use wss:// - this server supports it)")
            else:
                print("  (If page is HTTPS, run with: python aura_recorder.py --wss)")
            await asyncio.Future()  # run forever

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def quiet_handshake_error(loop, context):
        exc = context.get("exception")
        msg = context.get("message", "")
        if exc and ("InvalidMessage" in type(exc).__name__ or "EOFError" in str(exc) or "handshake" in msg.lower()):
            print(f"[WS] Connection rejected - protocol mismatch? (HTTPS page needs --wss)")
            return
        asyncio.default_exception_handler(loop, context)

    loop.set_exception_handler(quiet_handshake_error)
    loop.run_until_complete(run_ws())


def main(use_wss=False):
    print("=== AURA EEG Recorder ===")
    print("Make sure AURA is running and streaming via LSL.")
    print()

    try:
        recorder.start_lsl()
    except Exception as e:
        print(f"Failed to connect to AURA: {e}")
        sys.exit(1)

    ws_thread = threading.Thread(target=lambda: run_websocket_server(use_wss), daemon=True)
    ws_thread.start()

    print("\nReady. Open experiment.html in browser and start an experiment.")
    print("Press Ctrl+C to exit.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        if recorder.recording:
            recorder.save_csv()
            recorder.stop_recording()
        print("\nExiting.")


if __name__ == "__main__":
    use_wss = "--wss" in sys.argv
    main(use_wss=use_wss)

#!/usr/bin/env python3
"""
AURA EEG Recorder — LSL + WebSocket bridge
Reads AURA EEG stream, receives experiment events from browser via WebSocket,
saves CSV, and sends adaptive Fear/Engagement index for level control.
"""
import asyncio
import csv
import json
import queue
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from pylsl import StreamInlet, StreamOutlet, StreamInfo, resolve_stream
except ImportError:
    StreamOutlet = StreamInfo = None
    from pylsl import StreamInlet, resolve_stream

try:
    import websockets
except ImportError:
    print("Error: websockets not installed. Run: pip install websockets")
    sys.exit(1)

try:
    import numpy as np
except ImportError:
    print("Error: numpy not installed. Run: pip install numpy")
    sys.exit(1)

# Adaptive EEG (same package when run from scripts/)
try:
    from config_eeg import WINDOW_SAMPLES, ADAPTIVE_UPDATE_INTERVAL_S
    from eeg_adaptive import (
        BaselineStats,
        compute_fear_engagement_index,
        suggest_level,
    )
except ImportError:
    WINDOW_SAMPLES = 1000
    ADAPTIVE_UPDATE_INTERVAL_S = 2.0
    BaselineStats = None
    compute_fear_engagement_index = None
    suggest_level = None

# --- Configuration ---
WS_PORT = 8765
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
STREAM_NAME = "AURA"
LSL_STATE_STREAM_NAME = "VRPhobia_State"
LSL_MANUAL_LEVEL_STREAM_NAME = "VRPhobia_ManualLevel"

# Optional LSL: publish state and listen for manual level (--lsl)
USE_LSL_EXTRA = False
manual_level_lsl_queue = None
lsl_state_outlet_ref = []


class EEGRecorder:
    def __init__(self):
        self.inlet = None
        self.channel_names = []
        self.samples_buffer = []
        self.current_label = None
        self.current_phobia_id = None
        self.current_level = 2
        self.recording = False
        self.lock = threading.Lock()
        self.thread = None
        self.baseline = BaselineStats() if BaselineStats else None

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
            self.current_label = f"{phobia_id}_level2"
            self.current_level = 2
            self.recording = True
            self.samples_buffer = []
            if self.baseline:
                self.baseline = BaselineStats()
        self.thread = threading.Thread(target=self._reader_thread, daemon=True)
        self.thread.start()
        print(f"[EEG] Recording started. Label: {self.current_label}")

    def set_level(self, level):
        if self.current_phobia_id:
            self.current_level = int(level)
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

    def get_recent_window(self):
        """Return last WINDOW_SAMPLES as (n, 8) float array, or None if not enough data."""
        with self.lock:
            buf = list(self.samples_buffer)
        if len(buf) < WINDOW_SAMPLES or not buf:
            return None
        recent = buf[-WINDOW_SAMPLES:]
        arr = np.array([v for _, v, _ in recent], dtype=np.float64)
        if arr.shape[1] != 8:
            return None
        return arr


recorder = EEGRecorder()
connected_clients = set()


async def handle_websocket(websocket, path="/"):
    connected_clients.add(websocket)
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
                elif msg_type == "manual_level":
                    level = max(1, min(3, int(data.get("level", 2))))
                    recorder.set_level(level)
                    payload = json.dumps({"type": "force_level", "level": level})
                    for client in list(connected_clients):
                        try:
                            await client.send(payload)
                        except Exception:
                            connected_clients.discard(client)
                    await websocket.send(json.dumps({"status": "manual_level_sent", "level": level}))
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
        connected_clients.discard(websocket)
        # Only stop recording when no clients remain (e.g. browser closed). Do not stop when
        # the GUI closes its short-lived connection after sending manual_level.
        if recorder.recording and len(connected_clients) == 0:
            recorder.save_csv()
            recorder.stop_recording()
        print(f"Client disconnected ({len(connected_clients)} remaining).")


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

    async def adaptive_broadcast_loop():
        """Every ADAPTIVE_UPDATE_INTERVAL_S, compute Fear/Engagement index and broadcast to clients."""
        if not compute_fear_engagement_index or not recorder.baseline:
            return
        while True:
            await asyncio.sleep(ADAPTIVE_UPDATE_INTERVAL_S)
            if not recorder.recording or not connected_clients:
                continue
            data = recorder.get_recent_window()
            if data is None:
                continue
            try:
                fear_index, metrics = compute_fear_engagement_index(data, recorder.baseline)
                def _v(k):
                    v = metrics.get(k)
                    return v if v is not None else np.nan
                recorder.baseline.update(
                    _v("theta_fz"), _v("beta_alpha_fz_cz"), _v("alpha_posterior"), _v("faa"),
                )
                level_suggestion = suggest_level(fear_index, recorder.current_level)
                fear_display = max(-3.0, min(3.0, fear_index))
                payload = json.dumps({
                    "type": "adaptive_state",
                    "fear_index": round(fear_display, 4),
                    "level_suggestion": level_suggestion,
                    "current_level": recorder.current_level,
                    "metrics": {k: (round(v, 6) if isinstance(v, (int, float)) else v) for k, v in metrics.items()},
                })
                for ws in list(connected_clients):
                    try:
                        await ws.send(payload)
                    except Exception:
                        connected_clients.discard(ws)
                if USE_LSL_EXTRA and StreamOutlet and StreamInfo:
                    try:
                        if not lsl_state_outlet_ref:
                            info = StreamInfo(LSL_STATE_STREAM_NAME, "VRPhobia", 2, 0.5, "float32", "adaptive_state")
                            info.desc().append_child_value("channels", "fear_index,current_level")
                            lsl_state_outlet_ref.append(StreamOutlet(info))
                        lsl_state_outlet_ref[0].push_sample([float(fear_display), float(recorder.current_level)])
                    except Exception as e:
                        print(f"[LSL state] {e}")
            except Exception as e:
                print(f"[Adaptive] Error: {e}")

    async def check_manual_level_lsl_queue():
        """If --lsl, broadcast force_level when LSL manual stream sends a level."""
        if not USE_LSL_EXTRA or not manual_level_lsl_queue:
            return
        while True:
            await asyncio.sleep(0.4)
            try:
                level = manual_level_lsl_queue.get_nowait()
            except queue.Empty:
                continue
            level = max(1, min(3, int(level)))
            recorder.set_level(level)
            payload = json.dumps({"type": "force_level", "level": level})
            for ws in list(connected_clients):
                try:
                    await ws.send(payload)
                except Exception:
                    connected_clients.discard(ws)

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
            if compute_fear_engagement_index:
                asyncio.create_task(adaptive_broadcast_loop())
            if USE_LSL_EXTRA and manual_level_lsl_queue is not None:
                asyncio.create_task(check_manual_level_lsl_queue())
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


def _lsl_manual_level_thread():
    """Resolve VRPhobia_ManualLevel and push received levels to manual_level_lsl_queue."""
    global manual_level_lsl_queue
    try:
        from pylsl import resolve_stream
        streams = resolve_stream("name", LSL_MANUAL_LEVEL_STREAM_NAME)
        if not streams:
            print("[LSL] No stream 'VRPhobia_ManualLevel' found. Start a sender to control level via LSL.")
            return
        inlet = StreamInlet(streams[0])
        while True:
            sample, _ = inlet.pull_sample(timeout=0.5)
            if sample and len(sample) and 1 <= sample[0] <= 3:
                try:
                    manual_level_lsl_queue.put(int(sample[0]))
                except Exception:
                    pass
    except Exception as e:
        print(f"[LSL manual level] {e}")


def main(use_wss=False, use_lsl=False):
    global USE_LSL_EXTRA, manual_level_lsl_queue
    print("=== AURA EEG Recorder ===")
    print("Make sure AURA is running and streaming via LSL.")
    print()

    try:
        recorder.start_lsl()
    except Exception as e:
        print(f"Failed to connect to AURA: {e}")
        sys.exit(1)

    if use_lsl:
        USE_LSL_EXTRA = True
        manual_level_lsl_queue = queue.Queue()
        threading.Thread(target=_lsl_manual_level_thread, daemon=True).start()
        print("LSL: state outlet 'VRPhobia_State' + listening for 'VRPhobia_ManualLevel'")

    ws_thread = threading.Thread(target=lambda: run_websocket_server(use_wss), daemon=True)
    ws_thread.start()

    print("\nReady. Open experiment.html in browser and start an experiment.")
    if use_lsl:
        print("  Optional: run adaptive_monitor_gui.py to see state on PC; or send level 1/2/3 via LSL stream 'VRPhobia_ManualLevel'.")
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
    use_lsl = "--lsl" in sys.argv
    main(use_wss=use_wss, use_lsl=use_lsl)

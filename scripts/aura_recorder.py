#!/usr/bin/env python3
"""
AURA EEG Recorder — LSL + WebSocket bridge
Reads AURA EEG stream, receives experiment events from browser via WebSocket,
saves CSV, and sends adaptive Fear/Engagement index for level control.
"""
import asyncio
import csv
import json
import math
import queue
import sys
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from pylsl import StreamInlet, StreamOutlet, StreamInfo, resolve_byprop     
except ImportError:
    StreamOutlet = StreamInfo = None
    from pylsl import StreamInlet, resolve_byprop

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
    from config_eeg import (
        ADAPTIVE_UPDATE_INTERVAL_S,
        FEAR_ADAPT_AGGREGATE_MIN_TICKS,
        FEAR_ADAPT_AGGREGATE_S,
        FEAR_ADAPT_BASELINE_SAMPLES,
        FEAR_ADAPT_DWELL_S,
        WINDOW_SAMPLES,
    )
    from eeg_adaptive import (
        BaselineStats,
        compute_fear_engagement_index,
        fear_stress_threshold,
        tick_dwell_and_suggest,
    )
except ImportError:
    WINDOW_SAMPLES = 1000
    ADAPTIVE_UPDATE_INTERVAL_S = 2.0
    FEAR_ADAPT_AGGREGATE_S = 30.0
    FEAR_ADAPT_AGGREGATE_MIN_TICKS = 10
    FEAR_ADAPT_BASELINE_SAMPLES = 8
    FEAR_ADAPT_DWELL_S = 30.0
    BaselineStats = None
    compute_fear_engagement_index = None
    fear_stress_threshold = None
    tick_dwell_and_suggest = None

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
        self.current_experiment_id = None
        self.current_level = 2
        self.recording = False
        self.lock = threading.Lock()
        self.thread = None
        self.baseline = BaselineStats() if BaselineStats else None
        self.lsl_source_id = None
        # Fear-index calibration + rolling aggregate (~FEAR_ADAPT_AGGREGATE_S) for level suggestion
        self._fear_baseline_values: list[float] = []
        self.fear_ref_mean: float | None = None
        self.fear_ref_std: float | None = None
        self.fear_ref_ready = False
        self._fear_index_ring: deque[float] = deque(
            maxlen=max(2, int(math.ceil(FEAR_ADAPT_AGGREGATE_S / ADAPTIVE_UPDATE_INTERVAL_S)))
        )
        self._fear_dwell_above_s = 0.0
        self._fear_dwell_below_s = 0.0
        self._baseline_calibration_s = 0.0
        self._recording_t0_monotonic: float | None = None

    def _resolve_byprop(self):
        print(f"Looking for stream '{STREAM_NAME}'...")
        streams = resolve_byprop("name", STREAM_NAME)
        if not streams:
            raise RuntimeError(f"No stream named '{STREAM_NAME}' found. Is AURA running?")

        # If multiple streams share the same name (e.g., stale/zombie simulator instances),
        # prefer the most recently created stream, or a specific source_id if provided.
        chosen = None
        if self.lsl_source_id:
            for s in streams:
                try:
                    if s.source_id() == self.lsl_source_id:
                        chosen = s
                        break
                except Exception:
                    continue

        if chosen is None:
            def _created_at(si):
                try:
                    return float(si.created_at())
                except Exception:
                    return -1.0
            streams = sorted(streams, key=_created_at, reverse=True)
            chosen = streams[0]

        try:
            print(f"Found {len(streams)} stream(s). Using source_id={chosen.source_id()!r}, uid={chosen.uid()!r}")
        except Exception:
            print(f"Found {len(streams)} stream(s). Using first match.")
        return chosen

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
        stream_info = self._resolve_byprop()
        self.inlet = StreamInlet(stream_info)
        self._init_channel_names()
        print(f"Connected to AURA. Channels: {len(self.channel_names)}")

    def start_recording(self, phobia_id, initial_level=2, experiment_id=None, baseline_calibration_seconds=None):
        initial_level = int(initial_level)
        # Levels:
        # - 0 = baseline (relaxation/calibration for the selected phobia)
        # - 1..5 = exposure intensity
        initial_level = max(0, min(5, initial_level))
        try:
            bcal = float(baseline_calibration_seconds)
        except (TypeError, ValueError):
            bcal = 0.0
        bcal = max(0.0, bcal)
        with self.lock:
            self.current_phobia_id = phobia_id
            self.current_experiment_id = experiment_id or "session"
            self.current_label = f"{phobia_id}_level{initial_level}"
            self.current_level = initial_level
            self.recording = True
            self.samples_buffer = []
            if self.baseline:
                self.baseline = BaselineStats()
            self._fear_baseline_values = []
            self.fear_ref_mean = None
            self.fear_ref_std = None
            self.fear_ref_ready = False
            self._fear_index_ring.clear()
            self._fear_dwell_above_s = 0.0
            self._fear_dwell_below_s = 0.0
            self._baseline_calibration_s = bcal
        self._recording_t0_monotonic = time.monotonic()
        self.thread = threading.Thread(target=self._reader_thread, daemon=True)
        self.thread.start()
        print(
            f"[EEG] Recording started. Label: {self.current_label} (experiment_id={self.current_experiment_id!r}, "
            f"baseline_calibration_s={bcal})"
        )

    def set_level(self, level):
        if self.current_phobia_id:
            level = int(level)
            level = max(0, min(5, level))
            self.current_level = level
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
            self.current_experiment_id = None
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
            exp_id = self.current_experiment_id or "session"
            filepath = OUTPUT_DIR / f"eeg_{self.current_phobia_id or 'session'}_{exp_id}_{ts}.csv"

        header = ["timestamp"] + self.channel_names + ["label"]
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for ts, vals, label in samples:
                writer.writerow([ts] + vals + [label])

        print(f"[EEG] Saved {len(samples)} rows to {filepath}")
        return str(filepath)

    def get_recent_window(self):
        """Return last WINDOW_SAMPLES as (n, 8) float array.

        If the incoming LSL stream provides fewer channels (e.g. front-only device with 5),
        we pad the missing channels with NaN so adaptive EEG metrics can still be computed.
        """
        with self.lock:
            buf = list(self.samples_buffer)
        if len(buf) < WINDOW_SAMPLES or not buf:
            return None
        recent = buf[-WINDOW_SAMPLES:]
        arr = np.array([v for _, v, _ in recent], dtype=np.float64)
        # Expected by eeg_adaptive.py: 8-channel array (F1/Fp1/Fz/Fp2/F2 + posterior channels).
        if arr.shape[1] == 8:
            return arr

        # Front-only devices may stream only 5 electrodes.
        if arr.shape[1] == 5:
            padded = np.full((arr.shape[0], 8), np.nan, dtype=np.float64)
            padded[:, :5] = arr
            return padded

        return None


recorder = EEGRecorder()
connected_clients = set()
auto_adaptation_enabled = True


async def handle_websocket(websocket, path="/"):
    connected_clients.add(websocket)
    print(f"Browser connected: {websocket.remote_address}")
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get("type")
                if msg_type in ("start", "controller_start"):
                    phobia_id = data.get("phobia_id", "unknown")
                    initial_level = data.get("level", data.get("initial_level", 2))
                    experiment_id = data.get("experiment_id", data.get("experimentId", "session"))
                    duration_seconds = data.get("duration_seconds", data.get("durationSeconds", None))
                    session_type = data.get("session_type", data.get("sessionType", "hybrid"))
                    try:
                        initial_level = int(initial_level)
                    except Exception:
                        initial_level = 2
                    try:
                        if duration_seconds is not None:
                            duration_seconds = float(duration_seconds)
                    except Exception:
                        duration_seconds = None
                    if recorder.recording:
                        recorder.save_csv()
                        recorder.stop_recording()
                    bcal = data.get("baseline_calibration_seconds")
                    try:
                        bcal_f = float(bcal) if bcal is not None else 0.0
                    except (TypeError, ValueError):
                        bcal_f = 0.0
                    recorder.start_recording(
                        phobia_id,
                        initial_level=initial_level,
                        experiment_id=experiment_id,
                        baseline_calibration_seconds=bcal_f,
                    )
                    # If start came from a controller GUI, broadcast to all clients so the
                    # experiment page can auto-select the phobia without sending "start" again.
                    if msg_type == "controller_start":
                        payload = json.dumps({
                            "type": "start_experiment",
                            "phobia_id": phobia_id,
                            "phobia_name": data.get("phobia_name"),
                            "level": initial_level,
                            "experiment_id": experiment_id,
                            "duration_seconds": duration_seconds,
                            "session_type": session_type,
                            "baseline_calibration_seconds": bcal_f,
                        })
                        for client in list(connected_clients):
                            try:
                                await client.send(payload)
                            except Exception:
                                connected_clients.discard(client)
                    await websocket.send(json.dumps({
                        "status": "started",
                        "phobia_id": phobia_id,
                        "level": recorder.current_level,
                        "experiment_id": recorder.current_experiment_id
                    }))
                elif msg_type == "level_change":
                    level = data.get("level", 2)
                    level = max(0, min(5, int(level)))
                    recorder.set_level(level)
                    await websocket.send(json.dumps({"status": "level_changed", "level": level}))
                elif msg_type == "manual_level":
                    level = max(0, min(5, int(data.get("level", 2))))
                    recorder.set_level(level)
                    payload = json.dumps({"type": "force_level", "level": level})
                    for client in list(connected_clients):
                        try:
                            await client.send(payload)
                        except Exception:
                            connected_clients.discard(client)
                    await websocket.send(json.dumps({"status": "manual_level_sent", "level": level}))
                elif msg_type == "set_auto_adaptation":
                    enabled = bool(data.get("enabled", True))
                    global auto_adaptation_enabled
                    auto_adaptation_enabled = enabled
                    payload = json.dumps({"type": "auto_adaptation_toggle", "enabled": enabled})
                    for client in list(connected_clients):
                        try:
                            await client.send(payload)
                        except Exception:
                            connected_clients.discard(client)
                    await websocket.send(json.dumps({"status": "auto_adaptation_updated", "enabled": enabled}))
                elif msg_type == "stop_video":
                    payload = json.dumps({"type": "stop_video"})
                    for client in list(connected_clients):
                        try:
                            await client.send(payload)
                        except Exception:
                            connected_clients.discard(client)
                    await websocket.send(json.dumps({"status": "stop_video_sent"}))
                elif msg_type == "stop":
                    path = recorder.save_csv()
                    recorder.stop_recording()
                    payload = json.dumps({"type": "stop_video"})
                    for client in list(connected_clients):
                        try:
                            await client.send(payload)
                        except Exception:
                            connected_clients.discard(client)
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
        if not compute_fear_engagement_index or not recorder.baseline or not tick_dwell_and_suggest or not fear_stress_threshold:
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

                def _finalize_fear_ref_buffer() -> None:
                    vals = recorder._fear_baseline_values
                    if not vals:
                        recorder.fear_ref_mean = 0.0
                        recorder.fear_ref_std = 0.1
                    else:
                        arr = np.asarray(vals, dtype=np.float64)
                        recorder.fear_ref_mean = float(np.mean(arr))
                        recorder.fear_ref_std = float(max(np.std(arr), 1e-10, 0.05))
                    recorder.fear_ref_ready = True

                bcal = float(recorder._baseline_calibration_s or 0.0)
                t0 = recorder._recording_t0_monotonic
                elapsed = (time.monotonic() - t0) if t0 is not None else 0.0
                use_timed_baseline = bcal > 0.0

                stress_thr = None
                agg = None
                level_suggestion = "hold"
                adaptive_phase = "adaptation"
                baseline_remaining_s = None

                if use_timed_baseline:
                    if elapsed < bcal:
                        adaptive_phase = "calibration"
                        baseline_remaining_s = max(0.0, bcal - elapsed)
                        recorder._fear_baseline_values.append(float(fear_index))
                    else:
                        if not recorder.fear_ref_ready:
                            _finalize_fear_ref_buffer()
                            recorder._fear_index_ring.clear()
                            recorder._fear_dwell_above_s = 0.0
                            recorder._fear_dwell_below_s = 0.0
                            if recorder.current_level == 0:
                                recorder.set_level(1)
                                fl = json.dumps({"type": "force_level", "level": 1})
                                for ws in list(connected_clients):
                                    try:
                                        await ws.send(fl)
                                    except Exception:
                                        connected_clients.discard(ws)
                                print("[Adaptive] Timed baseline done → level 1, adaptation armed.")
                        if recorder.fear_ref_ready:
                            recorder._fear_index_ring.append(float(fear_index))
                            if len(recorder._fear_index_ring) >= FEAR_ADAPT_AGGREGATE_MIN_TICKS:
                                agg = float(np.mean(np.asarray(recorder._fear_index_ring, dtype=np.float64)))
                            if (
                                recorder.fear_ref_mean is not None
                                and recorder.fear_ref_std is not None
                                and agg is not None
                            ):
                                stress_thr = fear_stress_threshold(
                                    recorder.fear_ref_mean, recorder.fear_ref_std,
                                )
                                level_suggestion, recorder._fear_dwell_above_s, recorder._fear_dwell_below_s = (
                                    tick_dwell_and_suggest(
                                        agg,
                                        recorder.current_level,
                                        stress_thr,
                                        recorder._fear_dwell_above_s,
                                        recorder._fear_dwell_below_s,
                                        ADAPTIVE_UPDATE_INTERVAL_S,
                                        FEAR_ADAPT_DWELL_S,
                                    )
                                )
                else:
                    if not recorder.fear_ref_ready:
                        recorder._fear_baseline_values.append(float(fear_index))
                        if len(recorder._fear_baseline_values) >= FEAR_ADAPT_BASELINE_SAMPLES:
                            _finalize_fear_ref_buffer()
                    recorder._fear_index_ring.append(float(fear_index))
                    if len(recorder._fear_index_ring) >= FEAR_ADAPT_AGGREGATE_MIN_TICKS:
                        agg = float(np.mean(np.asarray(recorder._fear_index_ring, dtype=np.float64)))
                    if (
                        recorder.fear_ref_ready
                        and recorder.fear_ref_mean is not None
                        and recorder.fear_ref_std is not None
                        and agg is not None
                    ):
                        stress_thr = fear_stress_threshold(recorder.fear_ref_mean, recorder.fear_ref_std)
                        level_suggestion, recorder._fear_dwell_above_s, recorder._fear_dwell_below_s = (
                            tick_dwell_and_suggest(
                                agg,
                                recorder.current_level,
                                stress_thr,
                                recorder._fear_dwell_above_s,
                                recorder._fear_dwell_below_s,
                                ADAPTIVE_UPDATE_INTERVAL_S,
                                FEAR_ADAPT_DWELL_S,
                            )
                        )

                fear_display = max(-3.0, min(3.0, fear_index))
                payload = json.dumps({
                    "type": "adaptive_state",
                    "fear_index": round(fear_display, 4),
                    "fear_index_aggregate": None if agg is None else round(agg, 4),
                    "fear_ref_mean": None if recorder.fear_ref_mean is None else round(recorder.fear_ref_mean, 4),
                    "fear_ref_std": None if recorder.fear_ref_std is None else round(recorder.fear_ref_std, 4),
                    "fear_stress_threshold": None if stress_thr is None else round(stress_thr, 4),
                    "dwell_above_s": round(recorder._fear_dwell_above_s, 2),
                    "dwell_below_s": round(recorder._fear_dwell_below_s, 2),
                    "adaptive_phase": adaptive_phase,
                    "baseline_remaining_s": None if baseline_remaining_s is None else round(baseline_remaining_s, 1),
                    "baseline_calibration_total_s": bcal if use_timed_baseline else None,
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
            level = max(0, min(5, int(level)))
            recorder.set_level(level)
            payload = json.dumps({"type": "force_level", "level": level})
            for ws in list(connected_clients):
                try:
                    await ws.send(payload)
                except Exception:
                    connected_clients.discard(ws)

    async def run_ws():
        try:
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
        except OSError as e:
            if getattr(e, "errno", None) == 48:
                print(f"[WS] Port {WS_PORT} already in use. Stop the other process or run with: --ws-port 8766")
                return
            raise

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
        from pylsl import resolve_byprop
        streams = resolve_byprop("name", LSL_MANUAL_LEVEL_STREAM_NAME)
        if not streams:
            print("[LSL] No stream 'VRPhobia_ManualLevel' found. Start a sender to control level via LSL.")
            return
        inlet = StreamInlet(streams[0])
        while True:
            sample, _ = inlet.pull_sample(timeout=0.5)
            if sample and len(sample) and 0 <= sample[0] <= 5:
                try:
                    manual_level_lsl_queue.put(int(sample[0]))
                except Exception:
                    pass
    except Exception as e:
        print(f"[LSL manual level] {e}")


def main(use_wss=False, use_lsl=False):
    global USE_LSL_EXTRA, manual_level_lsl_queue, WS_PORT
    print("=== AURA EEG Recorder ===")
    print("Make sure AURA is running and streaming via LSL.")
    print()

    # Optional WebSocket port override when 8765 is already used.
    if "--ws-port" in sys.argv:
        try:
            idx = sys.argv.index("--ws-port")
            WS_PORT = int(sys.argv[idx + 1])
        except Exception:
            print("Error: --ws-port requires an integer value")
            sys.exit(2)

    # Optional selection of a specific LSL source_id when multiple "AURA" streams exist.
    # Usage: python aura_recorder.py --lsl-source-id AURA_SIMULATOR_xxx
    if "--lsl-source-id" in sys.argv:
        try:
            idx = sys.argv.index("--lsl-source-id")
            recorder.lsl_source_id = sys.argv[idx + 1]
        except Exception:
            print("Error: --lsl-source-id requires a value")
            sys.exit(2)

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

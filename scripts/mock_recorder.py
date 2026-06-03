#!/usr/bin/env python3
"""
Mock recorder — replaces aura_recorder.py for running without EEG hardware.

Same WebSocket protocol on port 8765, synthetic adaptive_state broadcasts.
Only dependency: websockets (no pylsl, numpy, scipy).
"""

import asyncio
import json
import math
import os
import random
import ssl
import sys
import time
from pathlib import Path

try:
    import websockets
except ImportError:
    print("Error: websockets not installed. Run: pip install websockets")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WS_PORT = 8765

connected_clients: set = set()
recording = False
current_level = 2
current_phobia_id = "unknown"
current_experiment_id = "session"
auto_adaptation_enabled = True
recording_t0: float | None = None
baseline_calibration_s = 0.0


def _synthetic_fear_index(t: float) -> float:
    """Slow sine wave + noise to simulate a plausible fear index."""
    base = 0.3 * math.sin(2 * math.pi * t / 30.0)
    noise = random.gauss(0.0, 0.15)
    return round(max(-3.0, min(3.0, base + noise)), 4)


async def adaptive_broadcast_loop():
    global current_level
    while True:
        await asyncio.sleep(2.0)
        if not recording or not connected_clients:
            continue

        t = time.monotonic() - (recording_t0 or time.monotonic())
        fi = _synthetic_fear_index(t)

        in_calibration = baseline_calibration_s > 0 and t < baseline_calibration_s
        phase = "calibration" if in_calibration else "adaptation"
        remaining = round(max(0.0, baseline_calibration_s - t), 1) if in_calibration else None

        suggestion = "hold"
        if not in_calibration:
            r = random.random()
            if r < 0.05 and current_level < 5:
                suggestion = "up"
            elif r > 0.95 and current_level > 1:
                suggestion = "down"

        payload = json.dumps({
            "type": "adaptive_state",
            "fear_index": fi,
            "fear_index_aggregate": fi,
            "fear_ref_mean": 0.0,
            "fear_ref_std": 0.3,
            "fear_stress_threshold": 0.45,
            "dwell_above_s": 0.0,
            "dwell_below_s": 0.0,
            "adaptive_phase": phase,
            "baseline_remaining_s": remaining,
            "baseline_calibration_total_s": baseline_calibration_s if baseline_calibration_s > 0 else None,
            "level_suggestion": suggestion,
            "current_level": current_level,
            "metrics": {
                "theta_fz": round(random.uniform(5, 15), 4),
                "beta_alpha_fz_cz": round(random.uniform(0.8, 2.5), 4),
                "alpha_posterior": round(random.uniform(8, 20), 4),
                "faa": round(random.gauss(0, 0.3), 4),
            },
        })
        for ws in list(connected_clients):
            try:
                await ws.send(payload)
            except Exception:
                connected_clients.discard(ws)


async def handle_websocket(websocket):
    global recording, current_level, current_phobia_id, current_experiment_id
    global auto_adaptation_enabled, recording_t0, baseline_calibration_s

    connected_clients.add(websocket)
    addr = getattr(websocket, 'remote_address', None)
    print(f"[mock] Client connected: {addr} ({len(connected_clients)} total)")
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get("type")
                print(f"[mock] ← {msg_type} from {addr}")

                if msg_type in ("start", "controller_start"):
                    current_phobia_id = data.get("phobia_id", "unknown")
                    current_level = int(data.get("level", data.get("initial_level", 2)))
                    current_level = max(0, min(5, current_level))
                    current_experiment_id = data.get("experiment_id", data.get("experimentId", "session"))
                    duration = data.get("duration_seconds", data.get("durationSeconds"))
                    session_type = data.get("session_type", data.get("sessionType", "hybrid"))
                    try:
                        bcal = float(data.get("baseline_calibration_seconds") or 0)
                    except (TypeError, ValueError):
                        bcal = 0.0
                    baseline_calibration_s = max(0.0, bcal)
                    recording = True
                    recording_t0 = time.monotonic()
                    print(f"[mock] Recording started: {current_phobia_id} level={current_level} id={current_experiment_id}")

                    payload = json.dumps({
                        "type": "start_experiment",
                        "phobia_id": current_phobia_id,
                        "phobia_name": data.get("phobia_name"),
                        "level": current_level,
                        "experiment_id": current_experiment_id,
                        "duration_seconds": duration,
                        "session_type": session_type,
                        "baseline_calibration_seconds": baseline_calibration_s,
                    })
                    print(f"[mock] → Broadcasting start_experiment to {len(connected_clients)} client(s)")
                    for client in list(connected_clients):
                        try:
                            await client.send(payload)
                        except Exception:
                            connected_clients.discard(client)

                    await websocket.send(json.dumps({
                        "status": "started",
                        "phobia_id": current_phobia_id,
                        "level": current_level,
                        "experiment_id": current_experiment_id,
                    }))

                elif msg_type == "level_change":
                    current_level = max(0, min(5, int(data.get("level", 2))))
                    await websocket.send(json.dumps({"status": "level_changed", "level": current_level}))

                elif msg_type == "manual_level":
                    current_level = max(0, min(5, int(data.get("level", 2))))
                    payload = json.dumps({"type": "force_level", "level": current_level})
                    for client in list(connected_clients):
                        try:
                            await client.send(payload)
                        except Exception:
                            connected_clients.discard(client)
                    await websocket.send(json.dumps({"status": "manual_level_sent", "level": current_level}))

                elif msg_type == "set_auto_adaptation":
                    auto_adaptation_enabled = bool(data.get("enabled", True))
                    payload = json.dumps({"type": "auto_adaptation_toggle", "enabled": auto_adaptation_enabled})
                    for client in list(connected_clients):
                        try:
                            await client.send(payload)
                        except Exception:
                            connected_clients.discard(client)
                    await websocket.send(json.dumps({"status": "auto_adaptation_updated", "enabled": auto_adaptation_enabled}))

                elif msg_type == "stop_video":
                    payload = json.dumps({"type": "stop_video"})
                    for client in list(connected_clients):
                        try:
                            await client.send(payload)
                        except Exception:
                            connected_clients.discard(client)
                    await websocket.send(json.dumps({"status": "stop_video_sent"}))

                elif msg_type == "stop":
                    recording = False
                    print(f"[mock] Recording stopped (no CSV in mock mode)")
                    payload = json.dumps({"type": "stop_video"})
                    for client in list(connected_clients):
                        try:
                            await client.send(payload)
                        except Exception:
                            connected_clients.discard(client)
                    await websocket.send(json.dumps({"status": "stopped", "file": "(mock — no file)"}))

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
        if recording and len(connected_clients) == 0:
            recording = False
            print("[mock] All clients disconnected — stopped.")
        print(f"[mock] Client disconnected ({len(connected_clients)} remaining)")


def main():
    global WS_PORT
    use_wss = "--wss" in sys.argv

    if "--ws-port" in sys.argv:
        try:
            idx = sys.argv.index("--ws-port")
            WS_PORT = int(sys.argv[idx + 1])
        except Exception:
            print("Error: --ws-port requires an integer")
            sys.exit(2)

    ssl_ctx = None
    if use_wss:
        cert = PROJECT_ROOT / "cert.pem"
        key = PROJECT_ROOT / "key.pem"
        if cert.exists() and key.exists():
            ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_ctx.load_cert_chain(str(cert), str(key))
        else:
            print("Warning: --wss but cert.pem/key.pem not found. Run: npm run cert")
            use_wss = False

    scheme = "wss" if use_wss else "ws"

    print("=== Mock Recorder (no EEG) ===")
    print(f"WebSocket on {scheme}://0.0.0.0:{WS_PORT}")
    print("Synthetic fear index will be broadcast every 2 s while recording.")
    print()

    async def serve():
        async with websockets.serve(
            handle_websocket, "0.0.0.0", WS_PORT, ssl=ssl_ctx,
            ping_interval=20, ping_timeout=20,
        ):
            print(f"[mock] Listening on {scheme}://0.0.0.0:{WS_PORT}")
            asyncio.create_task(adaptive_broadcast_loop())
            await asyncio.Future()

    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        print("\n[mock] Stopped.")


if __name__ == "__main__":
    main()

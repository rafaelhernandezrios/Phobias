#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor de estado adaptativo EEG — Interfaz gráfica en PC.
Muestra en tiempo real: fear_index, level_suggestion, current_level y métricas.
Permite cambiar nivel manualmente (Level 1/2/3) por WebSocket.
Conecta al mismo WebSocket que el experimento (aura_recorder).
"""
from __future__ import annotations

import json
import queue
import socket
import sys
import threading
from pathlib import Path
from typing import List, Tuple

try:
    import tkinter as tk
    from tkinter import ttk, font as tkfont
except ImportError:
    print("Error: tkinter not available (install python3-tk or use a GUI-capable Python)")
    sys.exit(1)

try:
    import asyncio
    import websockets
    HAS_WEBSOCKETS = True
except Exception:
    HAS_WEBSOCKETS = False

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WS_HOST = "127.0.0.1"
WS_PORT = 8765
WS_USE_SSL = False  # Set True if recorder runs with --wss (use wss:// for HTTPS)
CONTENT_JSON = PROJECT_ROOT / "app" / "data" / "content.json"


def get_ws_url():
    scheme = "wss" if WS_USE_SSL else "ws"
    return f"{scheme}://{WS_HOST}:{WS_PORT}"


def _ssl_for_wss():
    if not WS_USE_SSL:
        return None
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


async def _ws_receive_loop(url: str, msg_queue: queue.Queue, stop_event: threading.Event):
    ssl_ctx = _ssl_for_wss()
    while not stop_event.is_set():
        try:
            async with websockets.connect(url, open_timeout=5, close_timeout=2, ssl=ssl_ctx) as ws:
                while not stop_event.is_set():
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        try:
                            msg_queue.put(("message", json.loads(msg)))
                        except json.JSONDecodeError:
                            msg_queue.put(("raw", msg))
                    except asyncio.TimeoutError:
                        continue
                    except asyncio.CancelledError:
                        break
        except Exception as e:
            msg_queue.put(("error", str(e)))
        if not stop_event.is_set():
            msg_queue.put(("closed", None))
        break


def connect_ws_thread(url: str, msg_queue: queue.Queue, stop_event: threading.Event):
    """Run in thread: asyncio + websockets async client."""
    asyncio.run(_ws_receive_loop(url, msg_queue, stop_event))


class AdaptiveMonitorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("VR Phobia — Adaptive State Monitor")
        self.root.minsize(320, 380)
        self.root.geometry("380x520")
        self._msg_queue = queue.Queue()
        self._ws_thread = None
        self._stop_event = threading.Event()
        self._ws_conn = None
        self._level_buttons = []

        self._phobias: List[Tuple[str, str]] = self._load_phobias()
        self._phobia_var = tk.StringVar(value=(self._phobias[0][0] if self._phobias else "arachnophobia"))

        # State
        self.fear_index = tk.StringVar(value="—")
        self.level_suggestion = tk.StringVar(value="—")
        self.current_level = tk.StringVar(value="—")
        self.theta_fz = tk.StringVar(value="—")
        self.beta_alpha = tk.StringVar(value="—")
        self.alpha_post = tk.StringVar(value="—")
        self.faa = tk.StringVar(value="—")
        self.connection_status = tk.StringVar(value="Disconnected")

        self._build_ui()
        self._start_connection()
        self._poll_queue()

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        title_font = tkfont.Font(size=11, weight="bold")
        ttk.Label(main, text="Adaptive state (EEG)", font=title_font).pack(anchor=tk.W)

        status = ttk.Label(main, textvariable=self.connection_status, foreground="gray")
        status.pack(anchor=tk.W)

        sep = ttk.Separator(main, orient=tk.HORIZONTAL)
        sep.pack(fill=tk.X, pady=(8, 8))

        def row(label: str, var: tk.StringVar):
            f = ttk.Frame(main)
            f.pack(fill=tk.X, pady=2)
            ttk.Label(f, text=label, width=18, anchor=tk.W).pack(side=tk.LEFT)
            ttk.Label(f, textvariable=var, anchor=tk.E).pack(side=tk.RIGHT)

        row("Fear/Engagement index:", self.fear_index)
        row("Level suggestion:", self.level_suggestion)
        row("Current level:", self.current_level)
        row("θ Fz:", self.theta_fz)
        row("β/α Fz,Cz:", self.beta_alpha)
        row("α posterior:", self.alpha_post)
        row("FAA (F3–F4):", self.faa)

        sep_sel = ttk.Separator(main, orient=tk.HORIZONTAL)
        sep_sel.pack(fill=tk.X, pady=(12, 8))
        ttk.Label(main, text="Controller (start/stop)", font=title_font).pack(anchor=tk.W)

        sel_frame = ttk.Frame(main)
        sel_frame.pack(fill=tk.X, pady=(6, 6))
        ttk.Label(sel_frame, text="Phobia:", width=10).pack(side=tk.LEFT)
        phobia_values = [f"{pid} — {pname}" for pid, pname in self._phobias] if self._phobias else ["arachnophobia — Arachnophobia"]
        self._phobia_combo = ttk.Combobox(sel_frame, state="readonly", values=phobia_values, width=28)
        # Map display -> id via index
        if phobia_values:
            self._phobia_combo.current(0)
        self._phobia_combo.pack(side=tk.LEFT, padx=6)

        btns = ttk.Frame(main)
        btns.pack(fill=tk.X, pady=(0, 6))
        tk.Button(
            btns,
            text="Start selected",
            command=self._send_start_selected,
            bg="#1f6f4a",
            fg="white",
            activebackground="#2f855a",
            relief=tk.FLAT,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=4)
        tk.Button(
            btns,
            text="Stop video",
            command=self._send_stop_video,
            bg="#7b2c2c",
            fg="white",
            activebackground="#9b2c2c",
            relief=tk.FLAT,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=4)

        sep2 = ttk.Separator(main, orient=tk.HORIZONTAL)
        sep2.pack(fill=tk.X, pady=(12, 8))
        ttk.Label(main, text="Manual level (send to VR)", font=title_font).pack(anchor=tk.W)

        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=6)
        for level in (1, 2, 3):
            btn = tk.Button(
                btn_frame,
                text=f"Level {level}",
                width=8,
                command=lambda l=level: self._send_manual_level(l),
                bg="#2d3748",
                fg="white",
                activebackground="#4a5568",
                activeforeground="white",
                relief=tk.FLAT,
                cursor="hand2",
            )
            btn.pack(side=tk.LEFT, padx=4)
            self._level_buttons.append(btn)

        ttk.Label(main, text="(Changes scene in browser/VR)", foreground="gray", font=("", 8)).pack(anchor=tk.W, pady=(2, 0))

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _start_connection(self):
        if not HAS_WEBSOCKETS:
            self.connection_status.set("Error: install websockets")
            return
        url = get_ws_url()
        self.connection_status.set("Connecting…")
        self._stop_event.clear()
        self._ws_thread = threading.Thread(
            target=connect_ws_thread,
            args=(url, self._msg_queue, self._stop_event),
            daemon=True,
        )
        self._ws_thread.start()

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self._msg_queue.get_nowait()
                if kind == "message":
                    self._on_ws_message(payload)
                elif kind == "error":
                    self.connection_status.set(f"Error: {payload}")
                elif kind == "closed":
                    self.connection_status.set("Disconnected")
        except queue.Empty:
            pass
        self.root.after(200, self._poll_queue)

    def _on_ws_message(self, data: dict):
        if data.get("type") == "adaptive_state":
            self.connection_status.set("Connected (receiving state)")
            if data.get("fear_index") is not None:
                self.fear_index.set(f"{float(data['fear_index']):.2f}")
            self.level_suggestion.set(str(data.get("level_suggestion", "—")))
            self.current_level.set(str(data.get("current_level", "—")))
            m = data.get("metrics") or {}
            self.theta_fz.set(_fmt(m.get("theta_fz")))
            self.beta_alpha.set(_fmt(m.get("beta_alpha_fz_cz")))
            self.alpha_post.set(_fmt(m.get("alpha_posterior")))
            self.faa.set(_fmt(m.get("faa")))
        elif data.get("type") == "force_level":
            self.current_level.set(str(data.get("level", "—")))

    def _send_manual_level(self, level: int):
        if not HAS_WEBSOCKETS:
            return
        url = get_ws_url()
        try:
            ssl_ctx = _ssl_for_wss()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            async def send():
                async with websockets.connect(url, open_timeout=3, close_timeout=1, ssl=ssl_ctx) as ws:
                    await ws.send(json.dumps({"type": "manual_level", "level": level}))
            loop.run_until_complete(send())
            loop.close()
            self.current_level.set(str(level))
        except Exception as e:
            self.connection_status.set(f"Send failed: {e}")

    def _selected_phobia_id(self) -> str:
        try:
            idx = int(self._phobia_combo.current())
        except Exception:
            idx = 0
        if self._phobias and 0 <= idx < len(self._phobias):
            return self._phobias[idx][0]
        return "arachnophobia"

    def _send_start_selected(self):
        phobia_id = self._selected_phobia_id()
        self._send_control({"type": "controller_start", "phobia_id": phobia_id})

    def _send_stop_video(self):
        self._send_control({"type": "stop_video"})

    def _send_control(self, payload: dict):
        if not HAS_WEBSOCKETS:
            self.connection_status.set("Error: install websockets")
            return
        url = get_ws_url()
        try:
            ssl_ctx = _ssl_for_wss()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            async def send():
                async with websockets.connect(url, open_timeout=3, close_timeout=1, ssl=ssl_ctx) as ws:
                    await ws.send(json.dumps(payload))
            loop.run_until_complete(send())
            loop.close()
        except Exception as e:
            self.connection_status.set(f"Send failed: {e}")

    def _load_phobias(self) -> List[Tuple[str, str]]:
        try:
            data = json.loads(CONTENT_JSON.read_text(encoding="utf-8"))
            phs = data.get("phobias") or []
            out = []
            for p in phs:
                pid = p.get("id")
                pname = p.get("name") or pid
                if pid:
                    out.append((pid, pname))
            return out
        except Exception:
            return []

    def _on_close(self):
        self._stop_event.set()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def _fmt(v):
    if v is None:
        return "—"
    try:
        return f"{float(v):.4g}"
    except (TypeError, ValueError):
        return str(v)


def main():
    global WS_HOST, WS_PORT, WS_USE_SSL
    import argparse
    parser = argparse.ArgumentParser(description="VR Phobia adaptive state monitor (GUI)")
    parser.add_argument("--host", default=WS_HOST, help="WebSocket host")
    parser.add_argument("--port", type=int, default=WS_PORT, help="WebSocket port")
    parser.add_argument("--wss", action="store_true", help="Use WSS (if recorder uses --wss)")
    args = parser.parse_args()
    WS_HOST = args.host
    WS_PORT = args.port
    WS_USE_SSL = args.wss

    app = AdaptiveMonitorApp()
    app.run()


if __name__ == "__main__":
    main()

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
import time
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

PHOBIA_JP_NAMES = {
    "arachnophobia": "アラクノフォビア",
    "claustrophobia": "クラクストフォビア",
    "acrophobia": "アクロフォビア",
    "ophidiophobia": "オフィディオフォビア",
    "entomophobia": "エントモフォビア",
}


def get_ws_url():
    scheme = "wss" if WS_USE_SSL else "ws"
    return f"{scheme}://{WS_HOST}:{WS_PORT}"


def _ssl_for_wss():
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


async def _ws_receive_loop(url: str, msg_queue: queue.Queue, stop_event: threading.Event):
    ssl_ctx = _ssl_for_wss() if url.startswith("wss://") else None
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


def _get_candidate_ws_urls() -> List[str]:
    host_port = f"{WS_HOST}:{WS_PORT}"
    if WS_USE_SSL:
        return [f"wss://{host_port}", f"ws://{host_port}"]
    return [f"ws://{host_port}", f"wss://{host_port}"]


async def _ws_receive_loop_fallback(urls: List[str], msg_queue: queue.Queue, stop_event: threading.Event):
    # Try both schemes; on failure, keep retrying until stop.
    while not stop_event.is_set():
        for url in urls:
            if stop_event.is_set():
                break
            await _ws_receive_loop(url, msg_queue, stop_event)
        if not stop_event.is_set():
            await asyncio.sleep(2.0)


def connect_ws_thread(urls: List[str], msg_queue: queue.Queue, stop_event: threading.Event):
    """Run in thread: asyncio + websockets async client."""
    asyncio.run(_ws_receive_loop_fallback(urls, msg_queue, stop_event))


class AdaptiveMonitorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("VR Phobia — Adaptive State Monitor / VR恐怖症—EEG適応状態モニター")
        self.root.minsize(320, 380)
        self.root.geometry("420x780")
        self._msg_queue = queue.Queue()
        self._ws_thread = None
        self._stop_event = threading.Event()
        self._ws_conn = None
        self._level_buttons = []
        self._logo_atr = None
        self._logo_mirai = None

        # Experiments: baseline + the five phobias
        self._experiments: List[Tuple[str, str]] = self._load_experiments()
        self._experiment_var = tk.StringVar(value=(self._experiments[0][0] if self._experiments else "baseline"))

        self._load_logos()

        # Controller config
        self._start_level_var = tk.StringVar(value="0")
        self._experiment_id_var = tk.StringVar(value=f"exp_{int(time.time())}")
        self._duration_seconds_var = tk.StringVar(value="120")
        self._auto_adaptation_enabled = True

        # State
        self.fear_index = tk.StringVar(value="—")
        self.level_suggestion = tk.StringVar(value="—")
        self.current_level = tk.StringVar(value="—")
        self.theta_fz = tk.StringVar(value="—")
        self.beta_alpha = tk.StringVar(value="—")
        self.alpha_post = tk.StringVar(value="—")
        self.faa = tk.StringVar(value="—")
        self.connection_status = tk.StringVar(value="Disconnected / 未接続")
        self._mood_var = tk.StringVar(value="—")

        self._build_ui()
        self._start_connection()
        self._poll_queue()

    def _load_logos(self) -> None:
        """Load header logos for Tkinter."""
        try:
            atr_path = PROJECT_ROOT / "app" / "assets" / "thumbnails" / "atr_logo.png"
            mirai_path = PROJECT_ROOT / "app" / "assets" / "thumbnails" / "mirai_logo.png"

            def _scale_photo(photo: tk.PhotoImage, target_height: int) -> tk.PhotoImage:
                try:
                    h = int(photo.height())
                    if h <= 0:
                        return photo
                    factor = max(1, int(round(h / float(target_height))))
                    if factor <= 1:
                        return photo
                    # tk.PhotoImage.subsample keeps aspect ratio.
                    return photo.subsample(factor, factor)
                except Exception:
                    return photo

            target_height = 52
            if atr_path.exists():
                raw_atr = tk.PhotoImage(file=str(atr_path))
                self._logo_atr = _scale_photo(raw_atr, target_height)
            if mirai_path.exists():
                raw_mirai = tk.PhotoImage(file=str(mirai_path))
                self._logo_mirai = _scale_photo(raw_mirai, target_height)
        except Exception:
            # If logos fail to load, we just skip them.
            self._logo_atr = None
            self._logo_mirai = None

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        title_font = tkfont.Font(size=11, weight="bold")
        logo_row = ttk.Frame(main)
        logo_row.pack(fill=tk.X, pady=(0, 3))
        if self._logo_atr:
            ttk.Label(logo_row, image=self._logo_atr).pack(side=tk.LEFT)
        if self._logo_mirai:
            ttk.Label(logo_row, image=self._logo_mirai).pack(side=tk.RIGHT)

        ttk.Label(main, text="Adaptive state (EEG) / EEG適応状態（EEG）", font=title_font).pack(anchor=tk.W)

        status = ttk.Label(main, textvariable=self.connection_status, foreground="gray")
        status.pack(anchor=tk.W)

        sep = ttk.Separator(main, orient=tk.HORIZONTAL)
        sep.pack(fill=tk.X, pady=(8, 8))

        def row(label: str, var: tk.StringVar):
            f = ttk.Frame(main)
            f.pack(fill=tk.X, pady=2)
            ttk.Label(f, text=label, width=26, anchor=tk.W).pack(side=tk.LEFT)
            ttk.Label(f, textvariable=var, anchor=tk.E).pack(side=tk.RIGHT)

        row("Fear/Engagement index / 恐怖・関与指数:", self.fear_index)
        row("Level suggestion / レベル提案:", self.level_suggestion)
        row("Current level / 現在のレベル:", self.current_level)
        row("θ Fz / θFz:", self.theta_fz)
        row("β/α Fz,Cz / β/α（Fz,Cz）:", self.beta_alpha)
        row("α posterior / α後部:", self.alpha_post)
        row("FAA (F3–F4) / FAA（F3–F4）:", self.faa)

        sep_sel = ttk.Separator(main, orient=tk.HORIZONTAL)
        sep_sel.pack(fill=tk.X, pady=(12, 8))
        ttk.Label(main, text="Controller (start/stop) / コントローラ（開始/停止）", font=title_font).pack(anchor=tk.W)

        sel_frame = ttk.Frame(main)
        sel_frame.pack(fill=tk.X, pady=(6, 6))
        ttk.Label(sel_frame, text="Experiment / 実験:", width=16).pack(side=tk.LEFT)
        exp_values = []
        for eid, ename in self._experiments:
            jp = PHOBIA_JP_NAMES.get(eid, eid)
            exp_values.append(f"{eid} — {ename} / {jp}")
        self._experiment_combo = ttk.Combobox(sel_frame, state="readonly", values=exp_values, width=28)
        if exp_values:
            self._experiment_combo.current(0)
        self._experiment_combo.pack(side=tk.LEFT, padx=6)

        lvl_frame = ttk.Frame(main)
        lvl_frame.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(lvl_frame, text="Start level / 開始レベル:", width=18).pack(side=tk.LEFT)
        self._start_level_combo = ttk.Combobox(
            lvl_frame,
            state="readonly",
            values=[str(i) for i in range(0, 6)],
            width=6,
            textvariable=self._start_level_var,
        )
        self._start_level_combo.current(0)  # default 0 (baseline)
        self._start_level_combo.pack(side=tk.LEFT, padx=6)

        id_frame = ttk.Frame(main)
        id_frame.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(id_frame, text="Experiment ID / 実験ID:", width=18).pack(side=tk.LEFT)
        ttk.Entry(id_frame, textvariable=self._experiment_id_var, width=28).pack(side=tk.LEFT, padx=6)

        dur_frame = ttk.Frame(main)
        dur_frame.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(dur_frame, text="Duration (sec) / 総時間（秒）:", width=18).pack(side=tk.LEFT)
        ttk.Entry(dur_frame, textvariable=self._duration_seconds_var, width=28).pack(side=tk.LEFT, padx=6)

        btns = ttk.Frame(main)
        btns.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(
            btns,
            text="Start experiment / 実験開始",
            command=self._send_start_selected,
        ).pack(side=tk.LEFT, padx=4)
        ttk.Button(
            btns,
            text="Stop experiment / 実験停止",
            command=self._send_stop_experiment,
        ).pack(side=tk.LEFT, padx=4)

        self._auto_adaptation_button = ttk.Button(
            btns,
            text="Adaptive mood: ON / 適応モード：ON",
            command=self._toggle_auto_adaptation,
        )
        self._auto_adaptation_button.pack(side=tk.LEFT, padx=4)

        ttk.Label(main, text="Mood (from EEG): / EEGストレス状態：", foreground="gray", font=("", 9)).pack(anchor=tk.W)
        ttk.Label(main, textvariable=self._mood_var, font=title_font).pack(anchor=tk.W)

        sep2 = ttk.Separator(main, orient=tk.HORIZONTAL)
        sep2.pack(fill=tk.X, pady=(12, 8))
        ttk.Label(main, text="Manual level (send to VR) / 手動レベル（VRへ送信）", font=title_font).pack(anchor=tk.W)

        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.BOTH, pady=6, expand=False)
        levels = (0, 1, 2, 3, 4, 5)
        columns = 3
        for c in range(columns):
            btn_frame.grid_columnconfigure(c, weight=1)

        for idx, level in enumerate(levels):
            row = idx // columns
            col = idx % columns
            btn = ttk.Button(
                btn_frame,
                text=("Baseline / ベースライン" if level == 0 else f"Level {level} / レベル{level}"),
                width=12,
                command=lambda l=level: self._send_manual_level(l),
            )
            btn.grid(row=row, column=col, padx=6, pady=6, sticky="ew")
            self._level_buttons.append(btn)

        ttk.Label(main, text="(Changes scene in browser/VR) / ブラウザ/VRのシーンが変わります", foreground="gray", font=("", 8)).pack(anchor=tk.W, pady=(2, 0))

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _start_connection(self):
        if not HAS_WEBSOCKETS:
            self.connection_status.set("Error: install websockets / websocketsをインストールしてください")
            return
        urls = _get_candidate_ws_urls()
        self.connection_status.set("Connecting… / 接続中…")
        self._stop_event.clear()
        self._ws_thread = threading.Thread(
            target=connect_ws_thread,
            args=(urls, self._msg_queue, self._stop_event),
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
                    self.connection_status.set(f"Error: {payload} / エラー：{payload}")
                elif kind == "closed":
                    self.connection_status.set("Disconnected / 未接続")
        except queue.Empty:
            pass
        self.root.after(200, self._poll_queue)

    def _on_ws_message(self, data: dict):
        if data.get("type") == "adaptive_state":
            self.connection_status.set("Connected (receiving state) / 状態受信中（EEG）")
            if data.get("fear_index") is not None:
                self.fear_index.set(f"{float(data['fear_index']):.2f}")
                self._update_mood_from_fear(data.get("fear_index"))
            self.level_suggestion.set(str(data.get("level_suggestion", "—")))
            self.current_level.set(str(data.get("current_level", "—")))
            m = data.get("metrics") or {}
            self.theta_fz.set(_fmt(m.get("theta_fz")))
            self.beta_alpha.set(_fmt(m.get("beta_alpha_fz_cz")))
            self.alpha_post.set(_fmt(m.get("alpha_posterior")))
            self.faa.set(_fmt(m.get("faa")))
        elif data.get("type") == "force_level":
            self.current_level.set(str(data.get("level", "—")))
        elif data.get("type") == "stop_video":
            self.connection_status.set("Stopped / 停止")

        elif data.get("type") == "auto_adaptation_toggle":
            enabled = bool(data.get("enabled", True))
            self._auto_adaptation_enabled = enabled
            self._set_auto_adaptation_button_text(enabled)

    def _send_manual_level(self, level: int):
        if not HAS_WEBSOCKETS:
            return
        urls = _get_candidate_ws_urls()
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            async def send():
                last_exc = None
                for url in urls:
                    try:
                        ssl_ctx = _ssl_for_wss() if url.startswith("wss://") else None
                        async with websockets.connect(url, open_timeout=3, close_timeout=1, ssl=ssl_ctx) as ws:
                            await ws.send(json.dumps({"type": "manual_level", "level": level}))
                        return
                    except Exception as e:
                        last_exc = e
                raise last_exc or RuntimeError("No WS endpoint reachable")
            loop.run_until_complete(send())
            loop.close()
            self.current_level.set(str(level))
        except Exception as e:
            self.connection_status.set(f"Send failed: {e} / 送信失敗：{e}")

    def _toggle_auto_adaptation(self):
        self._auto_adaptation_enabled = not self._auto_adaptation_enabled
        # Best-effort: inform recorder so the waiting page can ignore adaptive_state when disabled.
        self._send_control({
            "type": "set_auto_adaptation",
            "enabled": self._auto_adaptation_enabled,
        })
        self._set_auto_adaptation_button_text(self._auto_adaptation_enabled)

    def _set_auto_adaptation_button_text(self, enabled: bool):
        if hasattr(self, "_auto_adaptation_button") and self._auto_adaptation_button:
            self._auto_adaptation_button.configure(text=f"Adaptive mood: {'ON' if enabled else 'OFF'} / 適応モード：{'ON' if enabled else 'OFF'}")

    def _update_mood_from_fear(self, fear_index_val):
        try:
            fi = float(fear_index_val)
        except Exception:
            self._mood_var.set("—")
            return
        threshold_low = -0.3
        threshold_high = 0.8
        if fi <= threshold_low:
            self._mood_var.set("CALM / 落ち着き")
        elif fi >= threshold_high:
            self._mood_var.set("STRESSED / ストレス高")
        else:
            self._mood_var.set("MEDIUM / 中間")

    def _selected_experiment(self) -> Tuple[str, str]:
        try:
            idx = int(self._experiment_combo.current())
        except Exception:
            idx = 0
        if self._experiments and 0 <= idx < len(self._experiments):
            return self._experiments[idx]
        return "arachnophobia", "Arachnophobia"

    def _send_start_selected(self):
        eid, ename = self._selected_experiment()
        try:
            start_level = int(self._start_level_combo.get())
        except Exception:
            start_level = 2
        try:
            duration_seconds = float(self._duration_seconds_var.get())
        except Exception:
            duration_seconds = 0
        experiment_id = self._experiment_id_var.get().strip() or f"exp_{int(time.time())}"

        self._send_control({
            "type": "controller_start",
            "phobia_id": eid,
            "phobia_name": ename,
            "level": start_level,
            "experiment_id": experiment_id,
            "duration_seconds": duration_seconds,
        })

    def _send_stop_experiment(self):
        self._send_control({"type": "stop"})

    def _send_control(self, payload: dict):
        if not HAS_WEBSOCKETS:
            self.connection_status.set("Error: install websockets / websocketsをインストールしてください")
            return
        urls = _get_candidate_ws_urls()
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            async def send():
                last_exc = None
                for url in urls:
                    try:
                        ssl_ctx = _ssl_for_wss() if url.startswith("wss://") else None
                        async with websockets.connect(url, open_timeout=3, close_timeout=1, ssl=ssl_ctx) as ws:
                            await ws.send(json.dumps(payload))
                        return
                    except Exception as e:
                        last_exc = e
                raise last_exc or RuntimeError("No WS endpoint reachable")
            loop.run_until_complete(send())
            loop.close()
        except Exception as e:
            self.connection_status.set(f"Send failed: {e} / 送信失敗：{e}")

    def _load_experiments(self) -> List[Tuple[str, str]]:
        try:
            data = json.loads(CONTENT_JSON.read_text(encoding="utf-8"))
            out: List[Tuple[str, str]] = []
            phs = data.get("phobias") or []
            for p in phs:
                pid = p.get("id")
                pname = p.get("name") or pid
                if pid:
                    out.append((pid, pname))

            return out
        except Exception:
            return [("arachnophobia", "Arachnophobia")]

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

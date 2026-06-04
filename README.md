# WebVR Phobia Exposure + EEG Adaptive Levels

Web VR platform for gradual exposure to 5 phobias, with 3 levels per phobia, event logging, and EEG-based adaptation via LSL/WebSocket.

---

## For research centers — start here

1. **[Mac + Windows quick start](docs/RUN_MAC_AND_WINDOWS.md)** — After `git pull`, how to run on each OS.  
   **Delivery:** [DELIVERY.md](DELIVERY.md) · **Windows:** [DELIVERY_WINDOWS.md](DELIVERY_WINDOWS.md)
2. **[Getting started](docs/GETTING_STARTED.md)** — What the repo is, prerequisites, and **step-by-step instructions** to run:
   - **Demo (no EEG):** try the app in the browser (e.g. classic menu flow).
   - **Full EEG experiment:** AURA + recorder + HTTPS; participant accepts disclosure and waits; **researcher** drives start/stop and parameters from the **PC monitor GUI**.
   - **With PC monitor:** adaptive metrics, session control (ID, phobia, levels 0–5, duration), and manual overrides.
3. **[Platform overview](docs/PLATFORM_VR_PHOBIAS.md)** — What the platform does, full flow, integrations, safety, data outputs.  
   **日本語：** [プラットフォーム概要（研究機関向け）](docs/PLATFORM_VR_PHOBIAS_JA.md)

Quick try (no EEG): `npm install` → `npm run preflight` → `npm run experiment:mock` → open `https://127.0.0.1:8443`.

**Verify before delivery:** `npm run preflight`

**Executable without Node/Python on lab PC:** [STANDALONE_EXECUTABLE.md](docs/STANDALONE_EXECUTABLE.md) — `npm run package:standalone:win` or `:mac`

---

## Purpose

- Web VR experience (research-controlled EEG session **or** classic self-guided flow): 360° exposure with logging.
- Synchronized logs: `session_id`, `phobia_id`, `level`, `video_id`, `timestamp_start/end`, `user_actions`.
- Safety: disclosure on landing, **EMERGENCY EXIT** button always visible.

### Default EEG experiment flow (roles) / Flujo por defecto (roles)

**English.** The default entry (`index.html` → `disclaimer-v2.html`) is optimized for **lab sessions**:

1. **Participant** — Reads the disclosure and taps **Accept / 同意**. They do **not** choose phobia or level in the browser for this protocol; the app opens **Waiting for configuration** (`experiment-wait-config.html`) and stays there until the researcher starts the run.
2. **Researcher** — On the PC, runs the stack (e.g. `npm run experiment`) and uses the **Adaptive State Monitor** (Electron app in [`monitor-electron/`](monitor-electron/)): pick **Experiment** (phobia from `content.json`), **Start level** (0 = baseline through 5), **Experiment ID**, **Duration (seconds)**, then **Start experiment**. Optional: **Stop experiment**, toggle **Adaptive mood** (ON/OFF), or **Manual level** buttons to push levels to VR in real time. Legacy Tk UI: `npm run monitor:tk` or `python3 scripts/adaptive_monitor_gui.py --wss`.

**Español.** La entrada por defecto está pensada para **sesión en laboratorio**: el **participante** solo **acepta el disclosure**; no configura fobia ni nivel en la web. Pasa a la pantalla **esperando configuración** y permanece ahí. El **investigador** configura e **inicia el experimento** desde el **monitor en PC** (Electron en `monitor-electron/`, o la GUI Tk heredada con `npm run monitor:tk`): fobia, nivel inicial 0–5, ID de sesión, duración, inicio/parada, modo adaptativo y niveles manuales vía WebSocket.

## Project Structure

```
VR-ATR Phobias/
├── app/                      # Web app (served as root by server)
│   ├── index.html            # Redirects to disclaimer-v2 (default entry)
│   ├── disclaimer-v2.html    # Disclosure + VR; Accept → wait for researcher config (EEG path)
│   ├── experiment-wait-config.html  # Participant wait screen; receives start/stop from recorder/GUI
│   ├── index-classic.html    # Classic consent → optional EEG / menu links
│   ├── menu.html             # VR menu: 5 phobias (self-guided test)
│   ├── level-select.html     # Level 1–3 per phobia
│   ├── player.html           # 360° player + HUD
│   ├── experiment.html       # Legacy/alternate EEG experiment UI (phobia pick in page)
│   ├── css/
│   │   └── shared.css
│   ├── js/
│   │   ├── app-base.js
│   │   ├── logger.js
│   │   └── vr-ui.js
│   ├── data/
│   │   └── content.json      # Phobias, levels, video URLs
│   └── assets/
│       ├── thumbnails/
│       └── videos/
├── monitor-electron/          # Electron adaptive monitor (researcher UI)
├── scripts/
│   ├── aura_test.py
│   ├── aura_recorder.py
│   ├── adaptive_monitor_gui.py   # Legacy Tk monitor (optional)
│   ├── config_eeg.py
│   └── eeg_adaptive.py
├── docs/
│   ├── GETTING_STARTED.md       ← Start here (how to run)
│   ├── PLATFORM_VR_PHOBIAS.md   ← Platform overview (EN)
│   ├── PLATFORM_VR_PHOBIAS_JA.md   ← プラットフォーム概要（日本語）
│   ├── EEG_EXPERIMENT_SETUP.md
│   └── EEG_ADAPTIVE_LEVELS.md
├── output/                   # EEG CSVs (generated)
├── server-https.js           # Serves app/ over HTTPS
├── generate-cert.js
├── package.json
├── requirements.txt
└── README.md
```

## Quick Test

1. **Local server** (recommended to load `data/content.json` and avoid CORS):
   ```bash
   npx serve app
   # or: npx serve ./app
   ```
2. Open in browser: **http://localhost:3000** (or the port shown by `serve`).
3. **Default site:** Accept disclosure → **waiting for configuration** (EEG lab flow) or use **index-classic.html** / **menu.html** for self-guided: menu → level → 360° player.

The HTTPS server (`npm run serve:https`) serves the `app/` folder as the site root.

## Content (360° Videos)

- The 5 phobias and 3 levels are defined in `app/data/content.json`. URLs point to `assets/videos/<phobia>_level<n>.mp4` (relative to the app).
- If those files are missing, the player falls back to a default 360° test video (A-Frame).
- For production: replace with your own equirectangular videos or licensed URLs.

## Included Phobias

| # | Phobia          | Type                |
|---|-----------------|---------------------|
| 1 | Arachnophobia   | Spiders             |
| 2 | Claustrophobia  | Enclosed spaces     |
| 3 | Acrophobia      | Heights             |
| 4 | Ophidiophobia   | Snakes              |
| 5 | Entomophobia    | Insects             |

## Logs

- Every action (consent, phobia chosen, level, video start/end, pause, restart, exit, emergency exit) is logged with `VRPhobiaLogger`.
- Logs are printed to the console and can be exported with `VRPhobiaLogger.exportJSON()` or `VRPhobiaLogger.downloadLogs()` (e.g. from the browser console).

## EEG Experiment (AURA)

Experiment mode records EEG while the user watches videos with adaptive or timed level changes.

**Requirements:** AURA streaming LSL; Python 3.8+ with `pylsl`, `websockets`, `numpy`, `scipy` (see `requirements.txt`).

**Full guide:** [docs/EEG_EXPERIMENT_SETUP.md](docs/EEG_EXPERIMENT_SETUP.md)

**Quick start (HTTPS + VR):**

```bash
# First time: certificates
npm run cert

# Option A: single command (server + recorder + PC monitor GUI)
npm run experiment
# or double-click: run-experiment.bat (Windows) / run-experiment.sh (Mac/Linux)

# Option B: two terminals (no GUI)
# Terminal 1: python scripts/aura_recorder.py --wss
# Terminal 2: npm run serve:https
```

Open `https://127.0.0.1:8443` (or your PC's IP for VR). **Participant:** accept disclosure → stay on **Waiting for configuration**. **Researcher:** use the **Electron monitor** (opens with `npm run experiment`): set experiment ID, phobia, start level (0–5), duration → **Start experiment**. The monitor shows Fear/Engagement metrics, adaptive suggestion, **Adaptive mood** toggle, and **manual level** 0–5. CSVs are saved in `output/`. Tk fallback: `npm run monitor:tk`. Details: [monitor-electron/README.md](monitor-electron/README.md).

## EEG Adaptive Levels

- **10–20 montage:** 8 electrodes F3, F4, Fz, Cz, Pz, P3, P4, Oz (mapping in `scripts/config_eeg.py`).
- **Fear/Engagement index:** combination of theta Fz, beta/alpha Fz–Cz, posterior alpha suppression (Pz, P3, P4, Oz), and frontal alpha asymmetry (F3–F4). Computed in `scripts/eeg_adaptive.py`.
- The recorder sends `adaptive_state` (fear_index, level_suggestion) via WebSocket every 2 s; the experiment applies level up/hold/down with hysteresis and cooldown. **High distress** button lowers the level immediately.
- **PC monitor / controller:** `python scripts/adaptive_monitor_gui.py` shows adaptive state in real time, **starts/stops** the run (`controller_start` / `stop`) with phobia, level **0–5**, session ID and duration, toggles **auto adaptation**, and sends **manual levels** 0–5 to VR. With HTTPS: `--wss`.
- **LSL:** with `--lsl` the recorder publishes state to **VRPhobia_State** and listens to **VRPhobia_ManualLevel** to change the scene from other apps.
- Documentation: [docs/EEG_ADAPTIVE_LEVELS.md](docs/EEG_ADAPTIVE_LEVELS.md).

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) | **Run the project:** demo, EEG experiment, PC monitor; prerequisites; troubleshooting. |
| [docs/PLATFORM_VR_PHOBIAS.md](docs/PLATFORM_VR_PHOBIAS.md) | Platform description and flow for research centers. |
| [docs/EEG_EXPERIMENT_SETUP.md](docs/EEG_EXPERIMENT_SETUP.md) | EEG setup (HTTPS, WebSocket, certificates). |
| [docs/EEG_ADAPTIVE_LEVELS.md](docs/EEG_ADAPTIVE_LEVELS.md) | Adaptive index, montage, LSL, monitor. |
| [docs/PLATFORM_VR_PHOBIAS_JA.md](docs/PLATFORM_VR_PHOBIAS_JA.md) | プラットフォーム概要（日本語）。 |

## Stack

- **Core:** A-Frame (CDN), static HTML/CSS/JS.
- Optional: minimal server (Node or Python) to serve files and, for the experiment, WebSocket.

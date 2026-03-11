# WebVR Phobia Exposure + EEG Adaptive Levels

Web VR platform for gradual exposure to 5 phobias, with 3 levels per phobia, event logging, and EEG-based adaptation via LSL/WebSocket.

---

## For research centers — start here

1. **[Getting started](docs/GETTING_STARTED.md)** — What the repo is, prerequisites, and **step-by-step instructions** to run:
   - **Demo (no EEG):** try the app in the browser.
   - **Full EEG experiment:** AURA + recorder + HTTPS server; where data is saved.
   - **With PC monitor:** view adaptive state and change level manually.
2. **[Platform overview](docs/PLATFORM_VR_PHOBIAS.md)** — What the platform does, full flow, integrations, safety, data outputs.  
   **日本語：** [プラットフォーム概要（研究機関向け）](docs/PLATFORM_VR_PHOBIAS_JA.md)

Quick try (no EEG): `npm install` → `npx serve app` → open `http://localhost:3000`.

---

## Purpose

- Web VR experience: menu → choose phobia → choose level (1–3) → play 360° video.
- Synchronized logs: `session_id`, `phobia_id`, `level`, `video_id`, `timestamp_start/end`, `user_actions`.
- Safety: disclaimer on landing, **EMERGENCY EXIT** button always visible.

## Project Structure

```
VR-ATR Phobias/
├── app/                      # Web app (served as root by server)
│   ├── index.html            # Landing / Consent
│   ├── menu.html             # VR menu: 5 phobias
│   ├── level-select.html     # Level 1–3 per phobia
│   ├── player.html           # 360° player + HUD
│   ├── experiment.html       # EEG experiment (adaptive levels)
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
├── scripts/
│   ├── aura_test.py
│   ├── aura_recorder.py
│   ├── adaptive_monitor_gui.py
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
3. Flow: Accept consent → Menu (choose phobia) → Choose level → 360° player.

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

Open `https://127.0.0.1:8443` (or your PC's IP for VR) → "Start EEG experiment" → choose phobia. The **monitor window** (Fear/Engagement index + Level 1/2/3 buttons) opens automatically with `npm run experiment`. CSVs are saved in `output/`.

## EEG Adaptive Levels

- **10–20 montage:** 8 electrodes F3, F4, Fz, Cz, Pz, P3, P4, Oz (mapping in `scripts/config_eeg.py`).
- **Fear/Engagement index:** combination of theta Fz, beta/alpha Fz–Cz, posterior alpha suppression (Pz, P3, P4, Oz), and frontal alpha asymmetry (F3–F4). Computed in `scripts/eeg_adaptive.py`.
- The recorder sends `adaptive_state` (fear_index, level_suggestion) via WebSocket every 2 s; the experiment applies level up/hold/down with hysteresis and cooldown. **High distress** button lowers the level immediately.
- **PC monitor:** `python scripts/adaptive_monitor_gui.py` shows adaptive state in real time and allows manual level change (Level 1/2/3). With HTTPS: `--wss`.
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

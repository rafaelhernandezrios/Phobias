# WebVR Phobia Exposure + EEG Adaptive Levels

Web VR platform for gradual exposure to 5 phobias, with 3 levels per phobia, event logging, and EEG-based adaptation via LSL/WebSocket.

**Quick try (no EEG):** `npm install` → `npx serve .` → open `http://localhost:3000`.

**For research centers:** platform description, full flow, and integrations in [docs/PLATFORM_VR_PHOBIAS.md](docs/PLATFORM_VR_PHOBIAS.md).

## Purpose

- Web VR experience: menu → choose phobia → choose level (1–3) → play 360° video.
- Synchronized logs: `session_id`, `phobia_id`, `level`, `video_id`, `timestamp_start/end`, `user_actions`.
- Safety: disclaimer on landing, **EMERGENCY EXIT** button always visible.

## Project Structure

```
VR-ATR Phobias/
├── index.html          # Landing / Consent (disclaimer + accept)
├── menu.html           # VR menu: 5 cards (phobias)
├── level-select.html   # Level selection 1–3 per phobia
├── player.html         # 360° player + HUD
├── experiment.html     # EEG experiment (adaptive or timed levels)
├── data/
│   └── content.json    # Phobias, levels, 360 video URLs
├── js/
│   └── logger.js       # Event logging
├── scripts/
│   ├── aura_test.py    # AURA stream test
│   ├── aura_recorder.py # LSL + WebSocket → CSV
│   └── adaptive_monitor_gui.py # PC monitor (state + manual level)
├── output/             # EEG CSVs (generated)
├── docs/
│   ├── PLATFORM_VR_PHOBIAS.md
│   ├── EEG_EXPERIMENT_SETUP.md
│   └── EEG_ADAPTIVE_LEVELS.md
├── assets/
│   ├── thumbnails/
│   └── videos/
└── README.md
```

## Quick Test

1. **Local server** (recommended to load `data/content.json` and avoid CORS):
   ```bash
   npx serve .
   # or: python -m http.server 8080
   ```
2. Open in browser: `http://localhost:3000` (or the port used by `serve`).
3. Flow: Accept consent → Menu (choose phobia) → Choose level → 360° player.

Without a server, opening `index.html` directly may fail to load `content.json` due to browser policies.

## Content (360° Videos)

- The 5 phobias and 3 levels are defined in `data/content.json`. URLs point to `assets/videos/<phobia>_level<n>.mp4`.
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

# Option A: two terminals
# Terminal 1: python scripts/aura_recorder.py --wss
# Terminal 2: npm run serve:https

# Option B: single terminal
npm run experiment

# Option C: double-click (Windows)
run-experiment.bat
```

Open `https://127.0.0.1:8443` (or your PC's IP for VR) → "Start EEG experiment" → choose phobia. CSVs are saved in `output/`.

## EEG Adaptive Levels

- **10–20 montage:** 8 electrodes F3, F4, Fz, Cz, Pz, P3, P4, Oz (mapping in `scripts/config_eeg.py`).
- **Fear/Engagement index:** combination of theta Fz, beta/alpha Fz–Cz, posterior alpha suppression (Pz, P3, P4, Oz), and frontal alpha asymmetry (F3–F4). Computed in `scripts/eeg_adaptive.py`.
- The recorder sends `adaptive_state` (fear_index, level_suggestion) via WebSocket every 2 s; the experiment applies level up/hold/down with hysteresis and cooldown. **High distress** button lowers the level immediately.
- **PC monitor:** `python scripts/adaptive_monitor_gui.py` shows adaptive state in real time and allows manual level change (Level 1/2/3). With HTTPS: `--wss`.
- **LSL:** with `--lsl` the recorder publishes state to **VRPhobia_State** and listens to **VRPhobia_ManualLevel** to change the scene from other apps.
- Documentation: [docs/EEG_ADAPTIVE_LEVELS.md](docs/EEG_ADAPTIVE_LEVELS.md).

## Stack

- **Core:** A-Frame (CDN), static HTML/CSS/JS.
- Optional: minimal server (Node or Python) to serve files and, for the experiment, WebSocket.

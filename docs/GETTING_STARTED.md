# Getting Started — VR-ATR Phobias

This guide is for research centers that receive the repository. It explains **what the project does**, **what you need**, and **exactly how to run it** in each scenario.

---

## 1. What This Repository Is

- **Web app:** VR phobia exposure platform. Users accept consent → choose a phobia → choose or get an exposure level (1–3) → watch 360° videos. Works in browser and in VR headsets (WebXR).
- **EEG experiment mode:** Records EEG (via LSL) while the user watches videos. Optionally **adapts the level in real time** from an EEG-derived index (Fear/Engagement). Saves CSV per session and can show state on a PC monitor.
- **Integrations:** AURA (or other LSL EEG), WebSocket (browser ↔ recorder), optional LSL streams for external tools (e.g. LabRecorder).

Full description and flow: [PLATFORM_VR_PHOBIAS.md](PLATFORM_VR_PHOBIAS.md).

---

## 2. Prerequisites

| What | Required for |
|------|------------------|
| **Node.js** (e.g. LTS) | Serving the app, HTTPS, certificates |
| **Python 3.8+** | EEG recorder, adaptive index, PC monitor |
| **AURA** (or LSL EEG) | Only for EEG experiment; must be running and streaming LSL `AURA` |
| **Browser** (Chrome recommended) | Running the app; for VR, use HTTPS |

**Python dependencies** (for recorder and adaptive levels):

```bash
pip install -r requirements.txt
```

(`requirements.txt`: pylsl, websockets, numpy, scipy)

**Node dependencies** (for serving and experiment script):

```bash
npm install
```

---

## 3. How to Run — Three Options

### Option A: Demo (no EEG)

To only try the VR exposure app (no recording, no adaptive levels):

1. Install Node deps and start the server:
   ```bash
   npm install
   npx serve .
   ```
2. Open in browser: **http://localhost:3000** (or the port shown by `serve`, often 3000).
3. Accept consent → choose a phobia → choose level 1, 2, or 3 → watch the 360° video.

No Python or AURA needed.

---

### Option B: Full EEG Experiment (with adaptive levels)

Use this when you have **AURA (or compatible LSL EEG)** and want to record EEG and use adaptive levels.

**One-time setup**

```bash
npm install
pip install -r requirements.txt
npm run cert
```

(`cert` creates `cert.pem` and `key.pem` for HTTPS.)

**Every time you run the experiment**

1. **Start AURA** (or your LSL EEG device) and make sure it is streaming the stream named `AURA`.

2. **Start the recorder and the web server.**  
   Either use **one terminal**:
   ```bash
   npm run experiment
   ```
   Or **two terminals**:
   - Terminal 1: `python scripts/aura_recorder.py --wss`
   - Terminal 2: `npm run serve:https`

3. **Open the app:**  
   - On the same PC: **https://127.0.0.1:8443**  
   - From VR headset or another device: **https://&lt;YOUR_PC_IP&gt;:8443** (e.g. https://192.168.1.100:8443)  
   Accept the browser warning about the self-signed certificate if prompted.

4. In the app: click **"Start EEG experiment"** → check that the WebSocket status is **green (Connected)** → choose a **phobia**. The video starts (e.g. at level 2) and the level can change automatically from the EEG or stay fixed depending on configuration.

5. When finished: click **"End Experiment"** or **EMERGENCY EXIT**. The EEG CSV is saved under **`output/eeg_<phobia>_<timestamp>.csv`**.

**Optional: LSL state + manual level by LSL**

If you want the recorder to publish state to LSL and listen for manual level commands:

```bash
python scripts/aura_recorder.py --wss --lsl
```

See [EEG_ADAPTIVE_LEVELS.md](EEG_ADAPTIVE_LEVELS.md) for LSL stream names and usage.

---

### Option C: EEG Experiment + PC Monitor

Same as Option B, but you also run the **PC monitor** so the researcher can see the adaptive state and change the level manually (Level 1 / 2 / 3).

1. Do **Option B** (recorder + server running, app open in browser/VR).

2. On the same machine (or another on the network), open a **second terminal** and run:
   ```bash
   python scripts/adaptive_monitor_gui.py --wss
   ```
   (Use `--wss` if the app is served over HTTPS; use the same `--host` / `--port` if the recorder is on another PC.)

3. The monitor window shows the Fear/Engagement index, level suggestion, current level, and metrics. Use the **Level 1**, **Level 2**, **Level 3** buttons to change the exposure level in the participant’s scene immediately.

---

## 4. Where Data and Logs Go

| Output | Location | When |
|--------|----------|------|
| **EEG CSV** | `output/eeg_<phobia>_<timestamp>.csv` | After each experiment session (when you stop or exit) |
| **Session logs** (events in the app) | Browser only; export via console: `VRPhobiaLogger.exportJSON()` or `VRPhobiaLogger.downloadLogs()` | When you need them |

CSV columns: LSL `timestamp`, `ch1`–`ch8` (raw EEG), `label` (e.g. `arachnophobia_level2`).

---

## 5. What Each Main Part Does

| Component | Role |
|-----------|------|
| **index.html** | Landing: consent / disclaimer; must accept to continue. |
| **menu.html** | Menu of phobias; links to level selection or to experiment. |
| **level-select.html** | Choose level 1–3 for a phobia (standard mode). |
| **player.html** | 360° video player with HUD (pause, exit, etc.). |
| **experiment.html** | EEG experiment: one phobia, level can be adaptive or fixed; WebSocket to recorder; EMERGENCY EXIT and High distress. |
| **scripts/aura_recorder.py** | Connects to LSL (AURA), saves EEG to CSV, computes Fear/Engagement index, sends adaptive_state to browser, accepts manual_level from monitor. |
| **scripts/adaptive_monitor_gui.py** | PC GUI: shows state from recorder, sends Level 1/2/3 to recorder (which updates the participant’s scene). |
| **data/content.json** | Defines phobias, levels, and video URLs; edit to change content or paths. |

---

## 6. Documentation Index

| Document | Use it for |
|----------|------------|
| [README.md](../README.md) | Project overview and quick commands. |
| **[GETTING_STARTED.md](GETTING_STARTED.md)** (this file) | How to run: demo, full experiment, monitor. |
| [PLATFORM_VR_PHOBIAS.md](PLATFORM_VR_PHOBIAS.md) | What the platform is, full flow, integrations, safety, for research centers. |
| [EEG_EXPERIMENT_SETUP.md](EEG_EXPERIMENT_SETUP.md) | Detailed EEG setup: HTTPS, WebSocket, certificates, troubleshooting. |
| [EEG_ADAPTIVE_LEVELS.md](EEG_ADAPTIVE_LEVELS.md) | Fear/Engagement index, 10–20 montage, adaptation rules, LSL, monitor. |

---

## 7. Troubleshooting (Short)

| Issue | What to do |
|-------|------------|
| WebSocket shows "Disconnected" | Start the recorder: `python scripts/aura_recorder.py --wss` (with `--wss` if the page is HTTPS). |
| "Connection rejected" / WebSocket fails | Use `--wss` when the app is served over HTTPS. |
| No AURA stream | Ensure AURA is running and streaming LSL with name `AURA`. Test with `python scripts/aura_test.py`. |
| App not loading / CORS | Serve the app (e.g. `npx serve .` or `npm run serve:https`); do not open `index.html` as a file. |
| VR headset cannot open the app | Use HTTPS and the PC’s IP (e.g. https://192.168.1.100:8443). Accept the certificate warning in the browser. |
| Certificate warning in browser | Expected for self-signed cert; accept (or add exception) to continue. |

More detail: [EEG_EXPERIMENT_SETUP.md](EEG_EXPERIMENT_SETUP.md#troubleshooting).

---

If something is unclear or you need to adapt the setup (e.g. different EEG device or LSL stream name), check the docs above or the code comments in `scripts/` and `data/content.json`.

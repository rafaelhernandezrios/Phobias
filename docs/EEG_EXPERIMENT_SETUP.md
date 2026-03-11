# EEG Experiment Setup — VR Phobia + AURA

Guide for running the exposure experiment with EEG recording (AURA) using HTTPS (required for VR/WebXR).

---

## Flow Diagram

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  AURA (EEG)     │────▶│  aura_recorder.py     │◀────│  experiment.html │
│  LSL Stream     │     │  LSL + WebSocket WSS  │     │  (browser/VR)    │
└─────────────────┘     └──────────────────────┘     └─────────────────┘
         │                        │                            │
         │ 250 Hz                 │ ws://localhost:8765        │ https://
         │ 8 channels             │ or wss://...:8765           │ 192.168.x.x:8443
         └────────────────────────┴────────────────────────────┘
                                    │
                                    ▼
                          ┌─────────────────────┐
                          │  output/*.csv       │
                          │  timestamp,ch1..8,  │
                          │  label              │
                          └─────────────────────┘
```

---

## Prerequisites

| Component | Requirement |
|-----------|-------------|
| **AURA** | Running and streaming LSL stream `AURA` |
| **Python** | 3.8+ with `pylsl`, `websockets`, `numpy`, `scipy` (for adaptive levels) |
| **Node.js** | To serve the app and generate certificates |

---

## Installation

```bash
# 1. Node dependencies (already in project)
npm install

# 2. Python dependencies
pip install -r requirements.txt
```

---

## Quick Launcher (double-click)

**Windows:** Double-click `run-experiment.bat`

**Mac/Linux:**
```bash
chmod +x run-experiment.sh
./run-experiment.sh
```

The script generates certificates if missing and starts server + recorder. Requires AURA to be running and `npm install` + `pip install -r requirements.txt` to have been run at least once.

---

## Step-by-Step Execution

### Terminal 1: Certificates (first time only)

```bash
npm run cert
```

Generates `cert.pem` and `key.pem` in the project root.

---

### Terminal 2: EEG Recorder (Python)

```bash
# With HTTPS (required if the app uses HTTPS)
python scripts/aura_recorder.py --wss
```

If the app uses HTTP (port 8080):

```bash
python scripts/aura_recorder.py
```

You should see something like:

```
=== AURA EEG Recorder ===
Connected to AURA. Channels: 8
WebSocket server listening on wss://0.0.0.0:8765
  (HTTPS page must use wss:// - this server supports it)
Ready. Open experiment.html in browser and start an experiment.
```

---

### Terminal 3: HTTPS Web Server

```bash
npm run serve:https
```

Or:

```bash
npx http-server -p 8443 -S -c-1
```

**Alternative: everything in one terminal**

```bash
npm run experiment
```

Runs HTTPS server + recorder in parallel (requires `concurrently` and AURA to be running).

---

The app will be available at:

- **Same PC:** `https://127.0.0.1:8443`
- **VR / other device:** `https://192.168.x.x:8443` (use your PC's IP on the network)

---

## Experiment Flow

1. Open the app in the browser (or VR): `https://...:8443`
2. Click **"Start EEG experiment"**
3. Check that the WebSocket status is **green** (Connected)
4. Choose a phobia (e.g. Acrophobia)
5. Video starts at **level 2**; level can change adaptively (or on a timer) between 1, 2 and 3
6. When finished: **"End Experiment"** or **EMERGENCY EXIT**
7. CSV is saved to `output/eeg_<phobia>_<timestamp>.csv`

---

## HTTPS + WebSocket Compatibility

| App (server) | WebSocket (recorder) | Recorder command |
|--------------|----------------------|------------------|
| HTTP (8080)  | ws://                | `python scripts/aura_recorder.py` |
| HTTPS (8443) | wss://                | `python scripts/aura_recorder.py --wss` |

The page automatically uses `ws://` or `wss://` based on the URL protocol.

---

## Quick Test (no experiment)

```bash
# Verify that AURA is sending data
python scripts/aura_test.py
```

Generates `aura_test_output.csv` with ~500 samples.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| WebSocket: Disconnected | Run `aura_recorder.py` (with `--wss` if using HTTPS) |
| "Connection rejected" | Use `--wss` when the app is on HTTPS |
| No AURA stream | Check that AURA is running and streaming LSL |
| Not visible in VR | Use HTTPS and your PC's IP (e.g. `https://192.168.10.114:8443`) |
| Invalid certificate | In the browser, accept the self-signed certificate warning |

---

## Output CSV Structure

```csv
timestamp,ch1,ch2,ch3,ch4,ch5,ch6,ch7,ch8,label
352727.9048,-89908.86,-173967.2,...,acrophobia_level2
352727.9088,-89860.09,-173963.5,...,acrophobia_level2
...
352728.5,-90123.4,...,acrophobia_level1
```

- **timestamp:** LSL time
- **ch1–ch8:** EEG channels (raw)
- **label:** `{phobia}_level{N}` (e.g. `acrophobia_level2`)

---

## EEG Adaptive Levels

The experiment can adapt the level (1–3) in real time based on a Fear/Engagement index computed from the EEG. This requires the 8-electrode 10–20 montage (F3, F4, Fz, Cz, Pz, P3, P4, Oz) and the Python dependencies `numpy` and `scipy`.

**Documentation:** [EEG_ADAPTIVE_LEVELS.md](EEG_ADAPTIVE_LEVELS.md) — montage, index formula, and level up/hold/down rules.

---

## Recorder as .exe (Optional)

To distribute the recorder without Python installed:

```bash
pip install pyinstaller
pyinstaller --onefile --name aura-recorder scripts/aura_recorder.py
```

The `.exe` will be in `dist/aura-recorder.exe`. Run with `--wss` for HTTPS:

```bash
dist/aura-recorder.exe --wss
```

**Note:** AURA and LSL must be installed on the system; the .exe only bundles the Python script. Run the .exe from the project folder (where `cert.pem` and `key.pem` are located for `--wss`).

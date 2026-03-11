# VR-ATR Phobias Platform — Overview for Research Centers

Presentation document: what the platform is, what it is for, how it works, and what integrations it offers. Aimed at research teams evaluating or adopting the tool.

---

## 1. Summary

**VR-ATR Phobias** is a web platform for **gradual exposure to phobias in virtual reality (VR)** with optional **electroencephalography (EEG) recording** and **exposure levels that adapt to brain signals**. It is designed for:

- **Virtual Reality Exposure Therapy (VRET):** the user selects a phobia and an intensity level (1–3) and watches immersive 360° videos.
- **Research:** experiment mode with continuous EEG recording and, optionally, automatic level adaptation based on an EEG-derived index (vigilance, arousal, engagement).
- **Safety:** informed consent on entry, an always-visible emergency exit button, and manual level control by the researcher or the user (high distress).

The platform runs in a browser (including in VR headsets via WebXR) and integrates with EEG systems that stream via **LSL (Lab Streaming Layer)** and with standard recording tools (e.g. LabRecorder) via optional LSL streams.

---

## 2. What Does the Platform Do?

### 2.1 User (Participant) Experience

1. **Entry:** welcome screen with legal notice and consent; the user must accept to continue.
2. **Menu:** available phobias are shown (e.g. arachnophobia, claustrophobia, acrophobia, ophidiophobia, entomophobia). The user selects one.
3. **Exposure level:** each phobia has 3 levels (mild, medium, high). The user can choose the level manually or enter **experiment mode**, where the level can be adjusted automatically or by the researcher.
4. **VR exposure:** an immersive 360° video is played. The user can pause, restart, or exit at any time. An **EMERGENCY EXIT** button allows leaving the session immediately.
5. **End of session:** the user returns to the menu or closes the application.

### 2.2 Two Modes of Use

| Mode | Description | Exposure level |
|------|-------------|----------------|
| **Standard** | The user chooses phobia and level (1–3) from the menu. 360° playback only. | Fixed (chosen by the user) |
| **EEG Experiment** | For studies with brain recording. The level can be **adaptive** (based on EEG) or manually controlled by the researcher. | Variable: automatic from EEG, manual from PC, or combined |

In experiment mode, session events are logged and, if EEG is configured, brain signals are saved to CSV files with timestamps and level labels.

---

## 3. Full Flow (EEG Experiment Mode)

Below is the typical flow when using the platform with EEG and adaptive levels, so that the research center understands the path of data and control.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  PARTICIPANT (browser or VR headset)                                    │
│  • Accepts consent → Chooses phobia → Enters experiment mode            │
│  • Watches 360° video; level (1–3) may change automatically or by researcher │
│  • Can press "High distress" (lower level) or "EMERGENCY EXIT" (quit)    │
└─────────────────────────────────────────────────────────────────────────┘
                    │                              ▲
                    │ WebSocket (events, level)    │ WebSocket (adaptive_state, force_level)
                    ▼                              │
┌─────────────────────────────────────────────────────────────────────────┐
│  WEB SERVER (HTML/JS + optional Node/Python)                            │
│  • Serves the app (HTTPS for VR/WebXR)                                  │
│  • experiment.html receives adaptive index and applies level rules      │
└─────────────────────────────────────────────────────────────────────────┘
                    │
                    │ WebSocket (same server or same PC)
                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  RECORDER (Python: aura_recorder.py)                                     │
│  • Receives LSL from EEG device (e.g. AURA, 8 channels, ~250 Hz)        │
│  • Saves EEG + labels to CSV (output/)                                   │
│  • Computes Fear/Engagement index every 2 s and sends "adaptive_state"   │
│  • Accepts "manual_level" (e.g. from GUI) and forwards "force_level"    │
│  • Optional --lsl: publishes state to LSL and listens for manual level  │
└─────────────────────────────────────────────────────────────────────────┘
        │                    │
        │ LSL (EEG)          │ LSL (optional): VRPhobia_State, VRPhobia_ManualLevel
        ▼                    ▼
┌──────────────┐    ┌─────────────────────────────────────────────────────┐
│  EEG DEVICE  │    │  PC MONITOR (adaptive_monitor_gui.py)                │
│  (e.g. AURA) │    │  • Shows index and metrics in real time             │
│              │    │  • Level 1 / 2 / 3 buttons to change scene          │
└──────────────┘    └─────────────────────────────────────────────────────┘
```

**Flow summary:**

1. The **participant** opens the app in a browser or VR headset (HTTPS), accepts consent, chooses a phobia, and enters experiment mode.
2. The **recorder** (Python) is connected to the EEG device via LSL and to the browser via WebSocket. It saves the EEG signal to CSV with level labels and, if adaptive mode is on, computes an index from the EEG every 2 seconds and sends a level suggestion (up, hold, down).
3. The **web app** receives that suggestion and, if safety rules (hysteresis, cooldown) are met, changes the video level. The participant can lower the level at any time with "High distress".
4. The **researcher** can view brain state in real time on the **PC monitor interface** and, if desired, change the level manually (Level 1, 2, or 3). That change is applied immediately to the scene the participant sees.
5. Optionally, the recorder can publish state (index, current level) to LSL and listen for level commands via LSL, to integrate with other systems (e.g. BCI, LabRecorder).

---

## 4. Content: Phobias and Levels

The platform includes **5 phobias**, each with **3 intensity levels** (different 360° videos). Content is defined in a data file (`app/data/content.json`) that the center can modify (videos, durations, text).

| Phobia | Brief description | Levels (example) |
|--------|-------------------|------------------|
| Arachnophobia | Fear of spiders | 1: mild / 2: medium / 3: strong (close, multiple) |
| Claustrophobia | Fear of enclosed spaces | 1: small room / 2: elevator / 3: tunnel, walls closing in |
| Acrophobia | Fear of heights | 1: low balcony / 2: tall building / 3: edge, bridge |
| Ophidiophobia | Fear of snakes | 1: at distance / 2: moving nearby / 3: approaching |
| Entomophobia | Fear of insects | 1: one small insect / 2: several / 3: swarm, many nearby |

A **baseline** (neutral) scene can also be defined for calibration or EEG baseline. Videos are replaceable; the platform only requires URLs and metadata in `content.json`.

---

## 5. Technical Integrations

### 5.1 Electroencephalography (EEG)

- **Protocol:** LSL (Lab Streaming Layer), standard in real-time signal research.
- **Example device:** AURA (8 channels, ~250 Hz). Other LSL-compatible devices can be used if channel mapping is adjusted.
- **Recommended montage (8 electrodes, 10–20 system):** F3, F4, Fz, Cz, Pz, P3, P4, Oz. Allows computing a composite index (frontal theta, beta/alpha, posterior alpha suppression, frontal asymmetry) to adapt the level.
- **Output:** CSV files in the `output/` folder with timestamp, per-channel values, and label (phobia + level). Same LSL timestamps for synchronization with other tools.

### 5.2 EEG Adaptive Levels

- **Fear/Engagement index:** combination of EEG bands (theta, alpha, beta) and frontal asymmetry, normalized to a baseline estimated at the start of the session.
- **Rules:** the system suggests going up (1→2) when the index is in a moderate range; going down (2/3→1/2) when the index exceeds an activation threshold or the user presses "High distress". Hysteresis and minimum times between changes are applied to avoid oscillation.
- **Technical documentation:** [EEG_ADAPTIVE_LEVELS.md](EEG_ADAPTIVE_LEVELS.md) (formula, montage, thresholds).

### 5.3 PC Monitor (Researcher)

- **Application:** Python script with graphical interface (`scripts/adaptive_monitor_gui.py`).
- **Features:** view Fear/Engagement index, level suggestion, current level, and EEG metrics in real time; change level manually with Level 1, 2, and 3 buttons. The change is sent via WebSocket to the recorder, which forwards it to the browser and updates the VR scene.
- **Usage:** run on the same machine (or on the network) as the recorder; use `--wss` when the experiment is served over HTTPS.

### 5.4 Additional LSL (Optional)

With the recorder's `--lsl` option:

- **VRPhobia_State output stream:** the recorder publishes the current state (fear/engagement index, current level) to LSL. Any LSL-capable application (e.g. LabRecorder) can record this data together with the EEG.
- **VRPhobia_ManualLevel input stream:** the recorder listens to an LSL stream that accepts values 1, 2, or 3. Other applications (scripts, BCI, etc.) can send the desired level via LSL and the platform updates the VR scene the same as with the monitor buttons.

This allows the platform to integrate into research pipelines that already use LSL without relying only on the browser or the included monitor.

### 5.5 Event Logging

- User actions (consent, phobia chosen, level, video start/end, pause, emergency exit, etc.) are logged in the browser with session ID and timestamps. Logs can be exported as JSON from the browser console for later analysis.

---

## 6. Safety and Ethics

- **Consent:** the app displays a notice and requires explicit acceptance before accessing the menu.
- **Emergency exit:** **EMERGENCY EXIT** button is always visible during exposure; it ends the session and redirects to the menu.
- **High distress:** in experiment mode, the participant can lower the level at any time without leaving the session.
- **Researcher control:** the researcher can raise or lower the level from the PC monitor (or via LSL) if needed.

The platform does not replace the ethical design of the study (protocol, participant information, committee approval). Each center should define its own procedures and consent documentation according to its regulations.

---

## 7. Technical Requirements (Summary)

| Component | Requirement |
|-----------|-------------|
| **Browser / VR** | Modern browser with WebXR support (e.g. Chrome). For VR headsets, access via HTTPS (same network as the server). |
| **Server** | Static web server (Node, Python, or similar) to serve the app. For experiment mode with VR, HTTPS is recommended (self-signed or valid certificate). |
| **EEG** | LSL-compatible device (e.g. AURA), running and streaming on the same machine or network as the recorder. |
| **Python (recorder)** | Python 3.8+ with dependencies: `pylsl`, `websockets`, `numpy`, `scipy` (for adaptive levels). |
| **Monitor (optional)** | Python with `websockets` and a GUI-capable environment (tkinter). |

Step-by-step guide for installing and running the EEG experiment: [EEG_EXPERIMENT_SETUP.md](EEG_EXPERIMENT_SETUP.md).

---

## 8. Data Outputs for Research

- **EEG CSV:** one file per session in `output/`, with columns: LSL timestamp, channels (ch1–ch8 or per device), label (e.g. `arachnophobia_level2`). Synchronizable with LSL and other recordings.
- **VRPhobia_State LSL stream (optional):** index and current level at the recorder update rate (~0.5 Hz), for recording in LabRecorder or real-time analysis.
- **Session logs:** app events exportable as JSON (consent, phobia, level, timestamps, actions). Useful for behavior analysis and protocol adherence.

---

## 9. Further Documentation

| Document | Content |
|----------|---------|
| [README.md](../README.md) | Project overview, folder structure, quick commands. |
| [GETTING_STARTED.md](GETTING_STARTED.md) | **How to run:** demo, full EEG experiment, PC monitor; prerequisites; troubleshooting. |
| [EEG_EXPERIMENT_SETUP.md](EEG_EXPERIMENT_SETUP.md) | EEG experiment setup (HTTPS, WebSocket, certificates, detailed steps). |
| [EEG_ADAPTIVE_LEVELS.md](EEG_ADAPTIVE_LEVELS.md) | Fear/Engagement index detail, 10–20 montage, adaptation rules, PC monitor. |
| [PLATFORM_VR_PHOBIAS_JA.md](PLATFORM_VR_PHOBIAS_JA.md) | **Japanese (日本語):** same overview for research centers. |

---

*Document prepared for evaluation by research centers. For further technical or integration information, see the documentation in the `docs/` folder and the repository code.*

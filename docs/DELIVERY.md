# Delivery guide — VR Phobia platform / Guía de entrega

How to hand off this project to a lab or client as a **runnable package**, with or without EEG hardware.

Cómo entregar el proyecto a un laboratorio como **paquete ejecutable**, con o sin hardware EEG.

---

## What you are delivering / Qué se entrega

| Component | Role |
|-----------|------|
| **Web app** (`app/`) | Participant UI in browser / Quest (360° video, disclosure, wait screen) |
| **HTTPS server** (`server-https.js`) | Serves the app on port **8443** + WebSocket proxy `/ws` |
| **Recorder** | `scripts/aura_recorder.py` (real EEG) or `scripts/mock_recorder.py` (demo, no AURA) |
| **Researcher monitor** (`monitor-electron/`) | Electron UI: start/stop, phobia, levels, metrics |
| **Videos** (`app/assets/videos/*.mp4`) | Large files — must be included in the ZIP/USB |

---

## Recommended delivery modes / Modos de entrega

### Mode A — Full project folder (recommended)

**Best for:** Mac lab with Node + Python, updates possible, Quest on same Wi‑Fi.

1. Copy the whole project folder (including `app/assets/videos/`).
2. On the target Mac, once:
   ```bash
   cd /path/to/Phobias
   npm install
   npm run setup:python
   npm run cert
   ```
3. **Demo / mock (no AURA):** double-click **`run-experiment-mock.command`**  
   Or: `./run-experiment.sh --mock`
4. **Real EEG:** double-click **`run-experiment.command`**
5. Participant: `https://<LAN_IP>:8443` on Quest (URL printed in terminal).
6. Researcher: Electron monitor window + **Start experiment**.

**Verify before delivery:**
```bash
npm run preflight
```

---

### Mode B — Researcher monitor as macOS `.app`

**Best for:** Investigators who only need the **control panel** as a familiar Mac app.  
The web server and recorder still start via the `.command` launcher (Mode A).

```bash
cd monitor-electron
npm install
npm run build
npm run package:mac
```

Output: `monitor-electron/release/VR Phobia Monitor.app` (and `.dmg` if configured).

Launch the monitor with the project root set:

```bash
export PHOBIAS_ROOT="/path/to/Phobias"
open "monitor-electron/release/VR Phobia Monitor.app" --args --wss
```

The `.app` alone does **not** start HTTPS or the recorder — use **`run-experiment-mock.command`** for the full stack.

---

### Mode C — What not to expect (without extra work)

| Approach | Limitation |
|----------|------------|
| Only the Electron `.app` | No VR page, no videos, no WebSocket bridge |
| Only `index.html` opened as file | WebXR / HTTPS / WebSocket will not work |
| PyInstaller on Python only | Still need Node for HTTPS; videos path must stay relative to `app/` |

A **single double-click with zero installs** on a clean Mac requires bundling Node + Python + ~2GB of videos (e.g. custom Electron launcher or installer). Mode A is the supported path today.

---

## Files to include in the ZIP / Archivos del paquete

**Include:**
- `app/` (with `assets/videos/*.mp4`)
- `monitor-electron/` (source; `node_modules` optional — recipient runs `npm install`)
- `scripts/`, `docs/`, `package.json`, `server-https.js`, `generate-cert.js`, `requirements.txt`
- `run-experiment.command`, `run-experiment-mock.command`, `run-experiment.sh`, `run-experiment.bat`, `run-experiment-mock.bat`
- `scripts/preflight.cjs`, `scripts/ensure-python-venv.cjs`, `scripts/run-python.cjs` (cross-platform)

**Exclude (regenerate on site):**
- `node_modules/` (large; run `npm install`)
- `.venv/` (run `npm run setup:python`)
- `cert.pem`, `key.pem` (run `npm run cert` on target machine so LAN IP is in the certificate)
- `output/` (EEG CSVs from test runs)
- `.git/`

---

## Target machine requirements / Requisitos

| Software | Version |
|----------|---------|
| **macOS** | 12+ (tested with `.command` launchers) |
| **Node.js** | 18 LTS or 20 LTS |
| **Python** | 3.8+ (mock: only `websockets`; full EEG: `requirements.txt`) |
| **Network** | Mac and Quest on the **same Wi‑Fi** |
| **Browser (Quest)** | Meta Browser; accept self-signed cert once |

**Windows:** see **[DELIVERY_WINDOWS.md](DELIVERY_WINDOWS.md)** — double-click `run-experiment-mock.bat` or `run-experiment.bat`.

---

## Quick checklist before handoff / Checklist

- [ ] `npm run preflight` passes
- [ ] `npm run experiment:mock` — browser shows **WebSocket: Connected**
- [ ] Quick Start or monitor **Start** loads 360° video
- [ ] Quest opens `https://<LAN_IP>:8443` and plays video
- [ ] `npm run lan-urls` shows the correct Wi‑Fi IP
- [ ] README + this file included

---

## Scripts reference

| Command | Purpose |
|---------|---------|
| `npm run preflight` | Check Node, Python, certs, videos |
| `npm run experiment:mock` | Full stack without AURA |
| `npm run experiment` | Full stack with `aura_recorder.py` (needs AURA LSL) |
| `npm run lan-urls` | Print Quest URLs |
| `npm run cert` | Regenerate TLS cert (after IP/network change) |
| `npm run package:monitor` | Build macOS Monitor `.app` |

---

## Support docs

- [GETTING_STARTED.md](GETTING_STARTED.md) — run instructions  
- [LATEST_EXECUTABLE_STACK.md](LATEST_EXECUTABLE_STACK.md) — architecture  
- [EEG_EXPERIMENT_SETUP.md](EEG_EXPERIMENT_SETUP.md) — real EEG setup  

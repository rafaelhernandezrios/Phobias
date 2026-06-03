# Windows delivery — VR Phobia / Entrega en Windows

Step-by-step guide to install, run, and deliver the project on **Windows 10/11**.

Guía para instalar, ejecutar y entregar el proyecto en **Windows 10/11**.

---

## Requirements / Requisitos

| Software | Notes |
|----------|--------|
| **Windows 10/11** | 64-bit |
| **Node.js** | LTS 18 or 20 — [https://nodejs.org](https://nodejs.org) — enable “Add to PATH” |
| **Python 3** | From [python.org](https://www.python.org/downloads/) — check **“Add python.exe to PATH”** |
| **Same Wi‑Fi** | PC and Meta Quest on the same network |

Optional: **Git** (not required for running; npm scripts work without Bash).

---

## First-time setup / Instalación (una vez)

1. Copy the project folder (e.g. `C:\Phobias`) **including** `app\assets\videos\*.mp4`.

2. Open **Command Prompt** or **PowerShell** in that folder:
   ```cmd
   cd C:\Phobias
   npm install
   npm run setup:python
   npm run cert
   npm run preflight
   ```
   All lines should show `[OK]`.

3. If Windows Firewall asks, allow **Node.js** on **private networks**.

---

## Run the experiment / Ejecutar

### Mock (no AURA / no EEG) — recommended for demo

**Double-click:** `run-experiment-mock.bat`

Or in a terminal:
```cmd
run-experiment-mock.bat
```

### Full EEG (AURA + LSL)

**Double-click:** `run-experiment.bat`

---

## URLs for browser and Quest

After start, the window shows LAN URLs. Also:

```cmd
npm run lan-urls
```

| Device | URL |
|--------|-----|
| PC browser | `https://127.0.0.1:8443` |
| Meta Quest | `https://<YOUR_PC_IP>:8443` (e.g. `https://192.168.1.50:8443`) |

On Quest: open **Meta Browser**, type the **LAN** URL, accept the certificate warning once.

Participant flow: disclosure → **Waiting for configuration** → researcher **Start** (monitor) or **Quick Start** in browser.

---

## What each `.bat` file does

| File | Purpose |
|------|---------|
| `run-experiment-mock.bat` | HTTPS + mock recorder + Electron monitor (no EEG) |
| `run-experiment.bat` | HTTPS + aura_recorder + monitor (needs AURA) |

---

## Package for delivery / Entregar a otro PC

**Include in ZIP/USB:**
- Full project folder with `app\assets\videos\`
- `run-experiment.bat`, `run-experiment-mock.bat`
- `scripts\`, `docs\`, `package.json`, `server-https.js`, `requirements.txt`

**Do not include** (recipient creates locally):
- `node_modules\`
- `.venv\`
- `cert.pem`, `key.pem` (run `npm run cert` on target PC)

**On target PC:** repeat [First-time setup](#first-time-setup--instalación-una-vez), then double-click `run-experiment-mock.bat`.

---

## Standalone `.exe` (no Node / Python on target PC) / Ejecutable todo-en-uno

**Recommended for delivery without installing Node or Python.**

On your **build machine** (Node only needed once to compile):

```cmd
npm install
npm run package:standalone:win
```

Output: `monitor-electron\release\VR-Phobia-Lab-1.0.0-portable.exe`

Double-click → HTTPS server + mock EEG + monitor start together.  
See **[STANDALONE_EXECUTABLE.md](STANDALONE_EXECUTABLE.md)**.

---

## Optional: Monitor-only `.exe` (needs Node/Python stack separately)

```cmd
npm run package:monitor:win
```

Does **not** start HTTPS or videos alone — use standalone portable above instead.

---

## Troubleshooting / Problemas

| Problem | Solution |
|---------|----------|
| `'node' is not recognized` | Reinstall Node.js, restart terminal, check PATH |
| `'py' is not recognized` | Install Python; or use `python -m venv .venv` then `npm run setup:python` |
| WebSocket disconnected | Use mock `.bat`; check firewall for Node on port **8443** |
| Quest cannot open page | Same Wi‑Fi; use PC IP not `127.0.0.1`; run `npm run cert` after IP change |
| Certificate error | `npm run cert` then restart stack |
| Videos do not play | `npm run preflight` — need `.mp4` in `app\assets\videos\` |

---

## Commands reference

```cmd
npm run preflight          REM check environment
npm run experiment:mock    REM full mock stack
npm run lan-urls           REM print Quest URLs
npm run cert               REM regenerate TLS cert
```

See also: [DELIVERY.md](DELIVERY.md) (general), [GETTING_STARTED.md](GETTING_STARTED.md).

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

| Role | URL |
|------|-----|
| **VR / Quest (participant)** | `https://<YOUR_PC_IP>:8443/` |
| **Researcher (PC browser)** | `https://<YOUR_PC_IP>:8443/researcher.html` |
| Local only | `https://127.0.0.1:8443/` and `.../researcher.html` |

On Quest: open **Meta Browser**, type the **LAN** participant URL, accept the certificate once.

On the lab PC: open **researcher.html** in Chrome/Edge — **Start experiment**, manual levels, metrics (same WebSocket as Electron had).

Participant flow: disclosure → **Waiting for configuration** → researcher **Start** on the panel (or Quick Start on the wait page).

---

## What each `.bat` file does

| File | Purpose |
|------|---------|
| `run-experiment-mock.bat` | One Node process: HTTPS + mock EEG (no AURA, no Electron) |
| `run-experiment.bat` | HTTPS + Python `aura_recorder` (needs AURA); researcher panel in browser |

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

## Error: "Error during start dev server" / "electron uninstall"

This happens when **Electron cannot start** (often in Cursor/VS Code because `ELECTRON_RUN_AS_NODE` is set).

**Fix (recommended):**

1. Close Cursor/VS Code terminal, open **cmd.exe** in the project folder.
2. Run:
   ```cmd
   scripts\fix-electron-windows.cmd
   ```
3. Then double-click **`run-experiment-mock.bat`** (uses production build, not dev server).

**Manual fix** (error: `Electron failed to install correctly`):

```cmd
cd C:\Users\atr-rp4\Desktop\Phobias
scripts\fix-electron-windows.cmd
```

Or step by step:

```cmd
set ELECTRON_RUN_AS_NODE=
rmdir /s /q monitor-electron\node_modules\electron
cd monitor-electron
npm install electron@33.4.11 --save-dev
node node_modules\electron\install.js
cd ..
node scripts\ensure-electron-install.cjs
npm run build --prefix monitor-electron
run-experiment-mock.bat
```

If download fails (firewall/antivirus), try:

```cmd
npm config set electron_mirror https://npmmirror.com/mirrors/electron/
```

Then run `scripts\fix-electron-windows.cmd` again.

The project now starts the monitor with `npm run start:wss` (build + run) instead of `electron-vite dev`, which is more stable on Windows.

---

## Troubleshooting / Problemas

| Problem | Solution |
|---------|----------|
| **electron uninstall / dev server** | Run `scripts\fix-electron-windows.cmd`; clear `ELECTRON_RUN_AS_NODE`; use `run-experiment-mock.bat` |
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

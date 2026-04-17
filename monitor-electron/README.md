# Adaptive monitor (Electron)

Desktop UI for researchers: connects to `aura_recorder.py` over WebSocket (`ws`/`wss` on port **8765**), same protocol as the legacy Tk monitor (`scripts/adaptive_monitor_gui.py`).

## Run (from repository root)

```bash
npm install          # also installs this package via postinstall
npm run monitor      # electron-vite dev + pass --wss to Electron
```

Or from this folder:

```bash
npm install
npm run dev -- --wss
```

## Production build

```bash
npm run build
npm start
```

(`package.json` `main` is `bootstrap.cjs`, which loads `out/main/index.js`.)

## Environment

- **`PHOBIAS_ROOT`**: optional absolute path to the repo root if `app/data/content.json` cannot be found by walking up from the compiled main file.
- **`ELECTRON_RUN_AS_NODE`**: must **not** be set to `1` when launching Electron, or `require('electron')` breaks. The `npm run dev` script uses `cross-env` to clear it; if you start Electron manually, run `unset ELECTRON_RUN_AS_NODE` first (Unix) or `set ELECTRON_RUN_AS_NODE=` (Windows cmd).

## Fallback (Tkinter)

```bash
# from repo root
npm run monitor:tk
# or: python3 scripts/adaptive_monitor_gui.py --wss
```

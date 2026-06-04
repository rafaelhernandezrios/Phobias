# Run on Mac and Windows / Mac と Windows での起動

Quick reference after `git pull`. Keep this file in the repo.

`git pull` 後のクイックリファレンス。

---

## macOS

### First time (once)

```bash
cd /path/to/Phobias
npm install
npm run setup:python
npm run cert
npm run preflight
```

Copy 360° videos to `app/assets/videos/` (not in GitHub).

### Run experiment

| Mode | How |
|------|-----|
| **Mock (no AURA)** | Double-click `run-experiment-mock.command` or `./run-experiment.sh --mock` |
| **Real EEG** | Double-click `run-experiment.command` or `./run-experiment.sh` |

### URLs

- PC: `https://127.0.0.1:8443`
- Quest: `https://<LAN_IP>:8443` → `npm run lan-urls`

### Optional: standalone `.app` (no Node/Python on target Mac)

Build on a Mac with Node:

```bash
npm run package:standalone:mac
```

→ `monitor-electron/release/VR Phobia Lab.app` (do not commit `release/` to git)

### Electron error in Cursor terminal

```bash
unset ELECTRON_RUN_AS_NODE
./run-experiment.sh --mock
```

---

## Windows

### First time (once)

Open **cmd.exe** (not Cursor terminal):

```cmd
cd C:\path\to\Phobias
npm install
npm run setup:python
npm run cert
npm run preflight
```

Copy videos to `app\assets\videos\`.

### Run experiment

| Mode | How |
|------|-----|
| **Mock (no AURA)** | Double-click `run-experiment-mock.bat` |
| **Real EEG** | Double-click `run-experiment.bat` |

### Fix "electron uninstall" / dev server error

```cmd
scripts\fix-electron-windows.cmd
run-experiment-mock.bat
```

Use **cmd outside Cursor**; clears `ELECTRON_RUN_AS_NODE`.

### URLs

- PC: `https://127.0.0.1:8443`
- Quest: `https://<LAN_IP>:8443` → `npm run lan-urls`

### Optional: portable `.exe` (no Node/Python on lab PC)

Build on a PC with Node:

```cmd
npm run package:standalone:win
```

→ `monitor-electron\release\VR-Phobia-Lab-1.0.0-portable.exe`

---

## After git pull on Windows (checklist)

```cmd
git pull
npm install
npm run setup:python
npm run cert
scripts\fix-electron-windows.cmd
run-experiment-mock.bat
```

---

## After git pull on Mac (checklist)

```bash
git pull
npm install
npm run setup:python
npm run cert
./run-experiment.sh --mock
```

---

## What is NOT in GitHub

- `app/assets/videos/*.mp4` — copy manually
- `node_modules/`, `.venv/` — run `npm install` + `npm run setup:python`
- `cert.pem`, `key.pem` — run `npm run cert` on each machine
- `monitor-electron/release/` — local build output only

---

## More docs

- [DELIVERY_WINDOWS.md](DELIVERY_WINDOWS.md)
- [DELIVERY.md](DELIVERY.md)
- [STANDALONE_EXECUTABLE.md](STANDALONE_EXECUTABLE.md)

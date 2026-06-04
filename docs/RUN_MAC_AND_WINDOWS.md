# Run on Mac and Windows / Mac と Windows での起動

Quick reference after `git pull`. Keep this file in the repo.

`git pull` 後のクイックリファレンス。

---

## macOS

### First time (once)

```bash
cd /path/to/Phobias
npm install
npm run cert
npm run preflight:mock   # mock; for real EEG also: npm run setup:python && npm run preflight
```

Copy 360° videos to `app/assets/videos/` (not in GitHub).

### Run experiment

| Mode | How |
|------|-----|
| **Mock (no AURA)** | Double-click `run-experiment-mock.command` or `./run-experiment.sh --mock` |
| **Real EEG** | Double-click `run-experiment.command` or `./run-experiment.sh` |

### URLs (two browser UIs — no Electron required)

| Role | URL |
|------|-----|
| **VR / participant (Quest)** | `https://<LAN_IP>:8443/` |
| **Researcher (PC browser)** | `https://<LAN_IP>:8443/researcher.html` |

`npm run lan-urls` prints both. Mock mode: one process (`npm run experiment:mock`).

### Optional: standalone `.app` (legacy Electron bundle)

Build on a Mac with Node:

```bash
npm run package:standalone:mac
```

→ `monitor-electron/release/VR Phobia Lab.app` (do not commit `release/` to git)

---

## Windows

### First time (once)

Open **cmd.exe** (not Cursor terminal):

```cmd
cd C:\path\to\Phobias
npm install
npm run cert
npm run preflight:mock
```
For real EEG add: `npm run setup:python` and `npm run preflight`.

Copy videos to `app\assets\videos\`.

### Run experiment

| Mode | How |
|------|-----|
| **Mock (no AURA)** | Double-click `run-experiment-mock.bat` |
| **Real EEG** | Double-click `run-experiment.bat` |

### URLs (no Electron)

| Role | URL |
|------|-----|
| **Quest / participant** | `https://<LAN_IP>:8443/` |
| **Researcher PC** | `https://<LAN_IP>:8443/researcher.html` |

`npm run lan-urls`

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
npm run cert
run-experiment-mock.bat
```

Open **researcher panel** on the PC: `https://127.0.0.1:8443/researcher.html`

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

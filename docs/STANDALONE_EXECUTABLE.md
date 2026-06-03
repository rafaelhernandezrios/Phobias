# Standalone executable (no Node / Python install) / Ejecutable sin Node ni Python

## Answer / Respuesta corta

**Sí**, pero no existe una sola librería mágica para “web + Python + vídeos”. La opción recomendada en este proyecto es:

| Librería | Qué hace |
|----------|----------|
| **[Electron](https://www.electronjs.org/)** | App de escritorio con **Node embebido** (Chromium + Node en un solo `.exe` / `.app`) |
| **[electron-builder](https://www.electron.build/)** | Empaqueta todo en instalador o `.exe` portable |

El modo **`standalone`** integra dentro del Electron:

- Servidor HTTPS + app web (`app/`)
- Mock WebSocket (sustituye Python `mock_recorder.py`)
- Monitor del investigador (la misma UI)

El usuario final **no instala Node ni Python**.

---

## Build the executable / Crear el ejecutable

**Requisito en tu PC de desarrollo:** Node.js (solo para compilar, no en el PC destino).

### Windows (`.exe` portable)

```cmd
cd C:\ruta\a\Phobias
npm install
npm run package:standalone:win
```

Salida típica:

`monitor-electron\release\VR-Phobia-Lab-1.0.0-portable.exe`

Doble clic → arranca servidor + monitor. Consola muestra URLs para Quest.

### macOS (`.app` + `.dmg`)

```bash
npm run package:standalone:mac
```

Salida: `monitor-electron/release/VR Phobia Lab.app`

---

## What gets bundled / Qué incluye

- Electron runtime (~150–200 MB)
- Carpeta `app/` (HTML, JS, **`assets/videos/`** → el instalador pesa **varios GB** si incluyes todos los MP4)
- Certificado TLS: se **genera en la primera ejecución** en la carpeta de datos del usuario (incluye IPs LAN actuales)

---

## Other libraries (not used here) / Otras opciones

| Herramienta | Sirve para | No cubre en este proyecto |
|-------------|------------|---------------------------|
| **pkg** / **nexe** | Un solo `.exe` con un script Node | Solo el servidor; no el monitor ni Python |
| **PyInstaller** | `.exe` del recorder Python | Sigue faltando HTTPS + monitor |
| **Tauri** | App ligera (Rust + WebView) | Habría que reescribir el backend |
| **ZIP portable** con `node.exe` + `python.exe` embebidos | Sin instalar en el sistema | No es un solo archivo; ~500 MB+ |

Por eso **Electron standalone** es la vía más práctica con el código actual.

---

## Run in dev (without packaging) / Probar sin empaquetar

```bash
npm run build --prefix monitor-electron
cd monitor-electron
npx electron . --standalone --wss
```

---

## Delivery checklist / Entrega

1. Build en tu máquina: `npm run package:standalone:win` (o `:mac`)
2. Copia el `.exe` o `.dmg` + README con URL Quest
3. En el laboratorio: doble clic, aceptar firewall, abrir `https://IP:8443` en Quest
4. Monitor → **Start experiment** (o Quick Start en el navegador)

**EEG real (AURA):** el ejecutable standalone es solo **mock**. Para AURA sigue haciendo falta Python + `aura_recorder.py` (modo `run-experiment.bat` con Node/Python instalados).

---

## Size note / Tamaño

Si los vídeos 360° no deben ir dentro del `.exe`, se puede entregar:

- `VR-Phobia-Lab-portable.exe` + carpeta `app/assets/videos/` al lado (requiere ajuste de rutas; el build actual **incluye** `app/` en resources).

Para entrega típica con vídeos: espera **2–4 GB** en el instalador/portable.

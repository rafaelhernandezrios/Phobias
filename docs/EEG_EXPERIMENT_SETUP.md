# EEG Experiment Setup — VR Phobia + AURA

Guía para ejecutar el experimento de exposición con registro EEG (AURA) usando HTTPS (necesario para VR/WebXR).

---

## Diagrama de flujo

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  AURA (EEG)     │────▶│  aura_recorder.py     │◀────│  experiment.html │
│  Stream LSL     │     │  LSL + WebSocket WSS  │     │  (navegador/VR)  │
└─────────────────┘     └──────────────────────┘     └─────────────────┘
         │                        │                            │
         │ 250 Hz                 │ ws://localhost:8765        │ https://
         │ 8 canales              │ o wss://...:8765           │ 192.168.x.x:8443
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

## Requisitos previos

| Componente | Requisito |
|-----------|-----------|
| **AURA** | Ejecutándose y emitiendo stream LSL `AURA` |
| **Python** | 3.8+ con `pylsl`, `websockets`, `numpy`, `scipy` (para niveles adaptativos) |
| **Node.js** | Para servir la app y generar certificados |

---

## Instalación

```bash
# 1. Dependencias Node (ya en el proyecto)
npm install

# 2. Dependencias Python
pip install -r requirements.txt
```

---

## Lanzador rápido (ejecutable / doble clic)

**Windows:** Doble clic en `run-experiment.bat`

**Mac/Linux:**
```bash
chmod +x run-experiment.sh
./run-experiment.sh
```

El script genera certificados si faltan y arranca servidor + recorder. Requiere tener AURA activo y haber ejecutado `npm install` + `pip install -r requirements.txt` al menos una vez.

---

## Ejecución paso a paso

### Terminal 1: Certificados (solo la primera vez)

```bash
npm run cert
```

Genera `cert.pem` y `key.pem` en la raíz del proyecto.

---

### Terminal 2: Recorder EEG (Python)

```bash
# Con HTTPS (obligatorio si la app usa HTTPS)
python scripts/aura_recorder.py --wss
```

Si la app usa HTTP (puerto 8080):

```bash
python scripts/aura_recorder.py
```

Debes ver algo como:

```
=== AURA EEG Recorder ===
Connected to AURA. Channels: 8
WebSocket server listening on wss://0.0.0.0:8765
  (HTTPS page must use wss:// - this server supports it)
Ready. Open experiment.html in browser and start an experiment.
```

---

### Terminal 3: Servidor web HTTPS

```bash
npm run serve:https
```

O:

```bash
npx http-server -p 8443 -S -c-1
```

**Alternativa: todo en una sola terminal**

```bash
npm run experiment
```

Ejecuta servidor HTTPS + recorder en paralelo (requiere `concurrently` y AURA activo).

---

La app estará en:

- **Mismo PC:** `https://127.0.0.1:8443`
- **VR / otro dispositivo:** `https://192.168.x.x:8443` (usa la IP de tu PC en la red)

---

## Flujo del experimento

1. Abrir la app en el navegador (o VR): `https://...:8443`
2. Clic en **"Start EEG experiment"**
3. Comprobar que el estado WebSocket sea **verde** (Connected)
4. Elegir una fobia (ej. Acrophobia)
5. El video empieza en **level 2** y cambia cada **8 segundos** entre 1, 2 y 3
6. Al terminar: **"End Experiment"** o **EMERGENCY EXIT**
7. El CSV se guarda en `output/eeg_<phobia>_<timestamp>.csv`

---

## Compatibilidad HTTPS + WebSocket

| App (servidor) | WebSocket (recorder) | Comando recorder |
|----------------|----------------------|------------------|
| HTTP (8080)    | ws://                | `python scripts/aura_recorder.py` |
| HTTPS (8443)   | wss://               | `python scripts/aura_recorder.py --wss` |

La página usa automáticamente `ws://` o `wss://` según el protocolo de la URL.

---

## Test rápido (sin experimento)

```bash
# Verificar que AURA envía datos
python scripts/aura_test.py
```

Genera `aura_test_output.csv` con ~500 muestras.

---

## Solución de problemas

| Problema | Solución |
|---------|----------|
| WebSocket: Disconnected | Ejecutar `aura_recorder.py` (con `--wss` si usas HTTPS) |
| "Connection rejected" | Usar `--wss` cuando la app está en HTTPS |
| No AURA stream | Comprobar que AURA esté activo y emitiendo LSL |
| No se ve en VR | Usar HTTPS y la IP de la PC (ej. `https://192.168.10.114:8443`) |
| Certificado inválido | En el navegador, aceptar el aviso de certificado autofirmado |

---

## Estructura del CSV de salida

```csv
timestamp,ch1,ch2,ch3,ch4,ch5,ch6,ch7,ch8,label
352727.9048,-89908.86,-173967.2,...,acrophobia_level2
352727.9088,-89860.09,-173963.5,...,acrophobia_level2
...
352728.5,-90123.4,...,acrophobia_level1
```

- **timestamp:** tiempo LSL
- **ch1–ch8:** canales EEG (raw)
- **label:** `{phobia}_level{N}` (ej. `acrophobia_level2`)

---

## Niveles adaptativos por EEG

El experimento puede adaptar el nivel (1–3) en tiempo real según un índice Fear/Engagement calculado a partir del EEG. Requiere el montaje de 8 electrodos en posiciones 10–20 (F3, F4, Fz, Cz, Pz, P3, P4, Oz) y las dependencias Python `numpy`, `scipy`.

**Documentación:** [EEG_ADAPTIVE_LEVELS.md](EEG_ADAPTIVE_LEVELS.md) — montaje, fórmula del índice y reglas de subir/mantener/bajar nivel.

---

## Recorder como .exe (opcional)

Si quieres distribuir el recorder sin Python instalado:

```bash
pip install pyinstaller
pyinstaller --onefile --name aura-recorder scripts/aura_recorder.py
```

El `.exe` estará en `dist/aura-recorder.exe`. Ejecutar con `--wss` para HTTPS:

```bash
dist/aura-recorder.exe --wss
```

**Nota:** AURA y LSL deben estar instalados en el sistema; el .exe solo empaqueta el script Python. Ejecutar el .exe desde la carpeta del proyecto (donde están `cert.pem` y `key.pem` para `--wss`).

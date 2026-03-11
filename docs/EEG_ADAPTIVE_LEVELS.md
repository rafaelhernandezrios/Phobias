# EEG Adaptive Levels — Fear/Engagement Index

Sistema de adaptación del nivel de exposición (1–3) según señal EEG en tiempo real.

---

## Montaje 10–20 (8 electrodos)

Configuración recomendada para AURA (ch1–ch8):

| Canal AURA | Posición 10–20 | Uso |
|------------|----------------|-----|
| ch1        | F3             | Frontal alpha asymmetry (FAA) |
| ch2        | F4             | Frontal alpha asymmetry (FAA) |
| ch3        | Fz             | Theta frontal, beta/alpha |
| ch4        | Cz             | Beta/alpha (apoyo) |
| ch5        | Pz             | Alpha posterior / supresión |
| ch6        | P3             | Alpha posterior |
| ch7        | P4             | Alpha posterior |
| ch8        | Oz             | Alpha posterior / atención visual |

**Bloques funcionales:**
- **Frontal (F3, F4, Fz):** regulación emocional, ansiedad, FAA.
- **Línea media (Fz, Cz, Pz):** seguimiento estable del estado.
- **Posterior (Pz, P3, P4, Oz):** atención visual y carga perceptual en VR.

---

## Índice Fear/Engagement

Índice compuesto (z-scores sobre baseline):

```
Fear/Engagement = w1·z(θ_Fz) + w2·z(β/α)_Fz,Cz + w3·z(AlphaSuppression) + w4·z(FAA)
```

- **θ Fz:** potencia theta (4–8 Hz) en Fz → vigilancia, control cognitivo, ansiedad.
- **β/α Fz,Cz:** ratio beta/alpha en Fz y Cz → activación/arousal.
- **Alpha suppression:** potencia alpha (8–13 Hz) en Pz, P3, P4, Oz; menos alpha = más engagement → se usa `-z(alpha_posterior)`.
- **FAA:** frontal alpha asymmetry (F4−F3)/(F4+F3) en alpha → modulador afectivo.

Pesos por defecto: `w1 = w2 = w3 = w4 = 0.25`. El baseline se estima con las primeras ventanas del experimento (ver `scripts/eeg_adaptive.py`).

---

## Reglas de adaptación de nivel

| Transición | Condición |
|------------|-----------|
| **Nivel 1 → 2** | `level_suggestion === "up"`: theta frontal moderada, alpha posterior baja, índice en rango medio. Se aplica tras **histeresis** (2 sugerencias consecutivas) y **cooldown** (45 s desde el último cambio). |
| **Mantener (2)** | Índice en zona media; respuesta fisiológica sin escalada. |
| **Nivel 2 o 3 → bajar** | `level_suggestion === "down"`: theta/beta-alpha altos (índice por encima de umbral). Se aplica tras histeresis (2 sugerencias) y cooldown (20 s). También al pulsar **Malestar alto**. |

Umbrales del servidor (en `eeg_adaptive.suggest_level`):  
- Subir (1→2): `threshold_low < fear_index < threshold_high` (p. ej. −0.3 y 0.8).  
- Bajar: `fear_index >= threshold_high`.

---

## Flujo técnico

1. **aura_recorder.py** lee LSL, mantiene buffer de las últimas 4 s (1000 muestras a 250 Hz).
2. Cada 2 s calcula el índice con `eeg_adaptive` (bandas, baseline, z-scores) y `level_suggestion` ("up" / "hold" / "down").
3. Envía por WebSocket a todos los clientes: `{ type: "adaptive_state", fear_index, level_suggestion, current_level, metrics }`.
4. **experiment.html** recibe el mensaje, actualiza el HUD (índice) y aplica cambio de nivel solo si se cumplen histeresis y cooldown.
5. El botón **Malestar alto** baja un nivel de inmediato y notifica al servidor con `level_change`.

---

## Monitor en PC y control manual

- **Interfaz gráfica (PC):** ejecutar `python scripts/adaptive_monitor_gui.py` para ver en tiempo real el estado adaptativo (fear index, suggestion, métricas) y cambiar nivel manualmente con los botones Level 1/2/3 (envía `manual_level` por WebSocket al recorder, que reenvía `force_level` al navegador).
  - Si el experimento usa HTTPS: `python scripts/adaptive_monitor_gui.py --wss`
  - Opciones: `--host`, `--port`, `--wss`
- **LSL (opcional):** con `python scripts/aura_recorder.py --wss --lsl`:
  - El recorder publica el estado en el stream LSL **VRPhobia_State** (canales: fear_index, current_level) para que otras apps (p. ej. LabRecorder) lo registren.
  - El recorder escucha el stream **VRPhobia_ManualLevel**: si otra app envía muestras con valor 1, 2 o 3, el nivel en VR se actualiza (igual que con los botones de la GUI).

---

## Archivos

| Archivo | Contenido |
|---------|-----------|
| `scripts/config_eeg.py` | Mapeo ch1–ch8 → 10–20, constantes (bandas, ventana, intervalo). |
| `scripts/eeg_adaptive.py` | Filtros, potencias por banda, FAA, baseline, índice compuesto, `suggest_level()`. |
| `scripts/aura_recorder.py` | Buffer, `adaptive_state` por WebSocket; `manual_level` → `force_level`; opcional `--lsl` (outlet VRPhobia_State, inlet VRPhobia_ManualLevel). |
| `scripts/adaptive_monitor_gui.py` | GUI en PC: estado en tiempo real + botones Level 1/2/3 por WebSocket. |
| `experiment.html` | Recepción `adaptive_state` y `force_level`, lógica de nivel, botón Malestar alto. |

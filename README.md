# WebVR Phobia Exposure + EEG Adaptive Levels

Plataforma web VR para exposición gradual a 5 fobias, con 3 niveles por fobia, registro de eventos y preparada para fase 2 (adaptación por EEG vía LSL/WebSocket).

## Objetivo

- Experiencia VR web: menú → elegir fobia → elegir nivel (1–3) → reproducir video 360°.
- Logs sincronizados: `session_id`, `phobia_id`, `level`, `video_id`, `timestamp_start/end`, `user_actions`.
- Seguridad: disclaimer en landing, botón **EMERGENCY EXIT** siempre visible.

## Estructura del proyecto

```
VR-ATR Phobias/
├── index.html          # Landing / Consent (disclaimer + aceptar)
├── menu.html           # Menú VR: 5 tarjetas (fobias)
├── level-select.html   # Selección de nivel 1–3 por fobia
├── player.html         # Reproductor 360° + HUD (play, pause, reiniciar, volver, EMERGENCY EXIT)
├── data/
│   └── content.json    # Fobias, niveles, URLs de videos 360
├── js/
│   └── logger.js       # Registro de eventos (session, phobia, level, timestamps, actions)
├── assets/             # Opcional: thumbnails y videos
│   ├── thumbnails/
│   └── videos/
└── README.md
```

## Cómo probar

1. **Servidor local** (recomendado para cargar `data/content.json` y evitar CORS):
   ```bash
   npx serve .
   # o: python -m http.server 8080
   ```
2. Abre en el navegador: `http://localhost:3000` (o el puerto que use `serve`).
3. Flujo: Aceptar consent → Menú (elegir fobia) → Elegir nivel → Player 360°.

Sin servidor, abrir `index.html` directamente puede fallar al cargar `content.json` por políticas del navegador.

## Contenido (videos 360°)

- En `data/content.json` están definidas las 5 fobias y 3 niveles. Las URLs apuntan a `assets/videos/<fobia>_level<n>.mp4`.
- Si no existen esos archivos, el reproductor usa por defecto un video 360° de prueba (A-Frame).
- Para producción: sustituir por tus propios videos equirectangulares o URLs con licencia.

## Fobias incluidas

| # | Fobia            | Tipo               |
|---|------------------|--------------------|
| 1 | Arachnophobia    | Arañas             |
| 2 | Claustrophobia   | Espacios cerrados  |
| 3 | Acrophobia       | Alturas            |
| 4 | Ophidiophobia    | Serpientes         |
| 5 | Entomophobia     | Insectos           |

## Logs

- Cada acción (consent, fobia elegida, nivel, inicio/fin de video, pausa, reinicio, salida, emergency exit) se registra con `VRPhobiaLogger`.
- Los logs se imprimen en consola y se pueden exportar con `VRPhobiaLogger.exportJSON()` o `VRPhobiaLogger.downloadLogs()` (por ejemplo desde la consola del navegador).

## Fase 2 (EEG adaptativo)

- Bridge LSL → WebSocket (p. ej. Python con `pylsl`) para enviar `stress_score` al navegador.
- En el player, recibir el score y aplicar reglas de adaptación (umbrales, histeresis, cooldown) para subir/bajar nivel automáticamente.
- Sincronizar timestamps de eventos VR con marcadores EEG.

## Stack

- **MVP:** A-Frame (CDN), HTML/CSS/JS estático.
- Opcional: servidor mínimo (Node o Python) para servir archivos y, en Fase 2, WebSocket.

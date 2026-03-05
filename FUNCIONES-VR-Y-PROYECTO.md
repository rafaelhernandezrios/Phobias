# Funciones y tecnologías del proyecto IKAN_VR / GCA Virtual

**Documentación en formato acordeón** — Funciones utilizadas en el proyecto, con énfasis en VR, reproducción de video 360°/VR, frameworks y componentes.

---

## Frameworks y bibliotecas

<details>
<summary><strong>🖼️ A-Frame (aframe.io) — Framework VR Web</strong></summary>

- **Versión:** 1.2.0 (CDN)
- **Uso:** Escenas VR en `aframe-osaka-castle.html`, `aframe-mirai-skybox-fixed.html`
- **Elementos:** `a-scene`, `a-sky`, `a-videosphere`, `a-camera`, `a-cursor`, `a-light`, `a-image`, `a-text`, `a-plane`, `a-assets`
- **Componentes nativos:** `camera`, `look-controls`, `wasd-controls`, `raycaster`, `material`, `geometry`, `animation`
- **URL:** `https://aframe.io/releases/1.2.0/aframe.min.js`
</details>

<details>
<summary><strong>🎮 Three.js — Gráficos 3D y WebXR</strong></summary>

- **Uso:** Escenas VR nativas en `quest3-vr-simple-hands.html`, `quest3-osaka-castle.html`
- **APIs:** `THREE.Scene`, `THREE.PerspectiveCamera`, `THREE.WebGLRenderer`, `THREE.VideoTexture`, `THREE.SphereGeometry`, `THREE.MeshBasicMaterial`, `THREE.Mesh`
- **WebXR:** `renderer.xr`, `navigator.xr`, sesiones `immersive-vr`, controladores, referencias `local-floor`
</details>

<details>
<summary><strong>🌐 WebXR Device API</strong></summary>

- **Uso:** Detección de VR, sesiones inmersivas, controladores (Quest 3, etc.)
- **Funciones:** `navigator.xr.isSessionSupported('immersive-vr')`, `navigator.xr.requestSession()`, `renderer.xr.setSession()`, `setReferenceSpaceType('local')`
- **Eventos:** `sessionstart`, `sessionend`, `selectstart`, `selectend`
</details>

<details>
<summary><strong>🔧 Otras dependencias del proyecto</strong></summary>

- **serve / live-server:** Servidor local (package.json)
- **Font Awesome:** Iconos en `vr-experience-selector.html` (CDN 6.0.0)
- **Sin build:** Proyecto estático HTML/CSS/JS
</details>

---

## Reproducción de video VR / 360°

<details>
<summary><strong>📹 A-Frame: videosphere y transición (aframe-osaka-castle.html)</strong></summary>

| Función | Descripción |
|--------|-------------|
| `initializeTransitionVideo()` | Configura el `<video>` de transición (muted, playsinline), listeners de `loadstart`, `loadedmetadata`, `canplay`, `error`, `stalled` y llama a `load()`. |
| `playTransitionVideo()` | Oculta skybox estático, muestra `a-videosphere` con el video, configura muted/playsinline, `currentTime = 0`, llama a `transitionVideo.play()` y maneja autoplay bloqueado (click/touchend para reanudar). |
| `handleVideoEnd()` | Al terminar el video: oculta videosphere, cambia `a-sky` a segunda imagen (`#castleImage2`), actualiza rotación y continúa con el siguiente diálogo. |
</details>

<details>
<summary><strong>📹 A-Frame: video 360° en Laboratorio Mirai (aframe-mirai-skybox-fixed.html)</strong></summary>

| Función | Descripción |
|--------|-------------|
| `initializeVideo()` | Inicializa el elemento de video 360°, atributos muted/playsinline y listeners (loadstart, loadedmetadata, canplay, error, stalled). |
| `playVideo360()` | Oculta skybox del lab, muestra esfera de video (`videoSphere`), guarda rotación de cámara y aplica `180 + cameraRotation.y` al videosphere; configura y ejecuta `videoEl.play()` con manejo de autoplay (click/touchend). |
| `backToLab()` | Pausa video, `currentTime = 0`, oculta esfera de video, muestra skybox del lab y botón “volver”. |
| `closeVideo()` | Cierra overlay 2D del video robot: pause, currentTime = 0, oculta `videoOverlay`. |
</details>

<details>
<summary><strong>📹 Three.js: video 360° en Quest (quest3-vr-simple-hands.html)</strong></summary>

| Función | Descripción |
|--------|-------------|
| `playVideo360()` | Crea escena de video, `THREE.VideoTexture` con elemento `<video>`, `THREE.SphereGeometry` + `MeshBasicMaterial` (BackSide), cambia `scene`/`camera` a la escena de video, `video.play()` con fallbacks; usa `setAnimationLoop(renderVideo)` en XR o `requestAnimationFrame` en 2D; timeout de seguridad con fallback a imagen estática; auto-stop a los 20 s. |
| `stopVideo360()` | Restaura escena/cámara original, pausa y limpia el video (pause, currentTime, src, load), restaura el loop de animación principal. |
| `renderVideo()` (interna) | Actualiza `videoTexture.needsUpdate` cuando el video tiene datos y hace `renderer.render(scene, camera)`. |
</details>

<details>
<summary><strong>📹 Three.js: video de transición Osaka (quest3-osaka-castle.html)</strong></summary>

| Función | Descripción |
|--------|-------------|
| `playTransitionVideo()` | Reproduce el video de transición en la escena Three.js (videosphere o textura equivalente), con listeners `ended` y `playing`. |
| `handleVideoEnd(fromFallback)` | Al terminar (o fallback): oculta videosphere, cambia skybox/textura a segunda vista del castillo y avanza el flujo de la historia. |
</details>

---

## Funciones VR: escena y controles

<details>
<summary><strong>🎯 aframe-osaka-castle.html — Escena y cámara</strong></summary>

| Función | Descripción |
|--------|-------------|
| `checkSkyboxStatus()` / `checkSkyboxImage()` | Comprueba si el skybox tiene textura cargada (`getObject3D('mesh').material.map.image`) y actualiza el indicador en pantalla. |
| `showObjectInfo(element)` | Muestra panel 3D de información (`infoPanel`, `infoTitle`, `infoText`) con `data-name` y `data-info` del elemento; no muestra panel para el avatar guía. |
| `startAvatarAnimation()` | Animación de rebote suave del avatar con `setInterval`, actualizando `position.y` con `Math.sin(bounceTime) * 0.15`. |
| `toggleOrientationLogging()` | Activa/desactiva el panel de orientación y el logging (start/stop `orientationInterval`). |
| `startOrientationLogging()` / `stopOrientationLogging()` | Inician/detienen el intervalo que llama a `updateOrientationDisplay()` cada 100 ms. |
| `updateOrientationDisplay()` | Lee rotación de la cámara y actualiza los spans `rotationX`, `rotationY`, `rotationZ`. |
| `logCurrentOrientation()` | Imprime en consola posición y rotación de la cámara y opcionalmente copia al portapapeles. |
| `resetCameraOrientation()` | Establece rotación de la cámara a `0 0 0`. |
</details>

<details>
<summary><strong>📖 aframe-osaka-castle.html — Historia y diálogos 3D</strong></summary>

| Función | Descripción |
|--------|-------------|
| `showStoryIntro()` | Muestra el modal de introducción de la historia (clase `show`). |
| `startStory()` | Oculta intro, marca `isStoryActive`, reinicia `currentDialogueIndex`, muestra progreso y controles de audio, llama a `showDialogue3D()`. |
| `showDialogue3D()` | Muestra el bloque de diálogo 3D actual, actualiza paso, muestra/oculta “Look at Castle”, ejecuta `animateAvatarGesture()`, `speakText()` y `typeText3D()`; en índice 1 muestra botón “Advance”. |
| `typeText3D(element, text, callback)` | Efecto de escritura en `a-text` con `setInterval` y `formatTextFor3D()` (líneas de ~22 caracteres). |
| `formatTextFor3D(text)` | Divide el texto en líneas por `maxCharsPerLine` para mejor lectura en 3D. |
| `animateAvatarGesture()` | Animación de “hablando” del avatar (salto y escala con `Math.sin`) durante ~5 s y luego resetea posición/escala. |
| `showAdvanceButton()` / `hideAdvanceButton()` | Muestran/ocultan el botón “Advance” y el texto “Continue” en el diálogo 3D. |
| `advanceToNextScene()` | Detiene voz y animación del avatar, oculta diálogo y botón Advance, llama a `playTransitionVideo()`. |
| `nextDialogue3D()` | Detiene voz y animación del avatar, limpia typing, oculta diálogo, incrementa índice y llama a `showDialogue3D()` tras 500 ms. |
| `endStory()` | Marca fin de historia, detiene voz, oculta diálogo, look prompt, progreso y controles de audio; muestra botón del quiz. |
</details>

<details>
<summary><strong>🔊 aframe-osaka-castle.html — Text-to-Speech y audio</strong></summary>

| Función | Descripción |
|--------|-------------|
| `speakText(text)` | Usa `SpeechSynthesisUtterance` y `speechSynthesis.speak()`; prioriza voces Neural/Natural, luego Zira/Mark/Samantha/Alex/Google/Microsoft, luego cualquier voz en-US/en-GB; ajusta rate, pitch y volume. |
| `stopSpeech()` | `speechSynthesis.cancel()` y limpia `currentSpeech`. |
| `toggleMute()` | Alterna `isMuted` y actualiza texto del botón Silenciar/Activar; llama a `stopSpeech()` si se silencia. |
| `toggleVoice()` | Alterna `isVoiceEnabled` y actualiza botón Voz/Sin Voz; detiene voz si se desactiva. |
| `changeSpeed(value)` | Actualiza `speechRate` y el indicador de velocidad en la UI. |
</details>

<details>
<summary><strong>🧭 aframe-osaka-castle.html — Navegación y teclado</strong></summary>

| Función | Descripción |
|--------|-------------|
| `goBack()` | Detiene animación del avatar y voz, muestra “Loading…”, redirige a `../dashboard.html`. |
| `goToQuiz()` | Redirige a `../quiz.html`. |
| Atajos teclado | `Escape` → `goBack()`; `O` → `toggleOrientationLogging()`; `L` → `logCurrentOrientation()`. |
</details>

<details>
<summary><strong>🥽 quest3-vr-simple-hands / quest3-osaka-castle — WebXR y controles</strong></summary>

| Función | Descripción |
|--------|-------------|
| `checkWebXR()` | Comprueba `navigator.xr` y `isSessionSupported('immersive-vr')`, muestra mensaje o inicia escena. |
| `enterVR()` | Solicita sesión WebXR con opciones (local-floor, etc.), configura renderer.xr y referencia. |
| `initScene()` | Crea escena Three.js, cámara, renderer, iluminación, controladores XR (`XRControllerModelFactory`), grips y cursores; configura `setAnimationLoop(animate)`. |
| `createControllerGrip(controller)` | Añade modelo 3D del controlador a la escena. |
| `createControllerCursor(controller)` | Crea indicador visual del rayo del controlador. |
| `onSelectStart` / `onSelectEnd` | Gestionan pulsación de gatillo para interacción (info, video, etc.). |
| `updateControllerIndicators()` | Actualiza estado visual de los controladores. |
| `showObjectInfo(object)` | Muestra panel de información 3D (o 2D) según el objeto seleccionado. |
| `showObjectCoordinates()` / `updateCoordinates()` | Muestran/actualizan coordenadas del objeto o cámara en la UI. |
</details>

---

## Componentes A-Frame personalizados (vr-components.js)

<details>
<summary><strong>🎮 vr-fallback-controls</strong></summary>

- **Schema:** `movementSpeed`, `rotationSpeed`, `enableKeyboard`, `enableMouse`
- **init:** `checkVRSupport()`, `setupEventListeners()`, `setupFallbackControls()`
- **checkVRSupport:** `navigator.xr.isSessionSupported('immersive-vr')` → muestra botón “ENTRAR VR” o activa fallback (teclado + pointer lock).
- **enterVR:** `navigator.xr.requestSession('immersive-vr')`, `renderer.xr.setSession()`, `setReferenceSpaceType('local')`
- **setupFallbackControls:** Loop ~60 fps con WASD y rotación con ratón (pointer lock).
- **remove:** Limpia interval y elimina botón e instrucciones.
</details>

<details>
<summary><strong>🖱️ vr-interaction</strong></summary>

- **Schema:** `type`, `action`
- **Eventos:** click → emite `vr-action` con la acción; mouseenter/mouseleave → escala 1.1 / 1.
</details>

<details>
<summary><strong>📊 progress-tracker, floating-text, holographic</strong></summary>

- **progress-tracker:** Escucha `vr-action` y aumenta `value`, emite `progress-update`.
- **floating-text:** Crea `a-text` con valor, color y tamaño.
- **holographic:** Material flat transparente con animación de opacidad pulsante.
</details>

<details>
<summary><strong>🖼️ vr-ui, teleport, quiz-element</strong></summary>

- **vr-ui:** Crea panel (a-plane + a-text) tipo “VR Interface”.
- **teleport:** Al hacer click, mueve `#camera` a `target` (vec3).
- **quiz-element:** Al hacer click crea UI de quiz en 3D (pregunta + opciones como cajas); `selectAnswer` muestra feedback y emite `quiz-answered`.
</details>

<details>
<summary><strong>🌍 environment, vr-audio, hand-tracking, performance-optimizer</strong></summary>

- **environment:** Crea entornos según tipo (office, classroom, laboratory).
- **vr-audio:** Aplica componente `sound` de A-Frame con src, autoplay, loop.
- **hand-tracking:** Comprueba soporte XR y prepara hand tracking (Quest).
- **performance-optimizer:** Ajusta renderer (antialias, colorManagement, physicallyCorrectLights) según nivel low/medium/high.
</details>

---

## Selector de experiencia y dashboard

<details>
<summary><strong>📱 vr-experience-selector.html</strong></summary>

| Función | Descripción |
|--------|-------------|
| `detectDevice()` | Detecta si es móvil, tablet o desktop para ofrecer la experiencia adecuada. |
| `selectExperience(experienceType)` | Redirige según elección: 'vr' → Quest/Osaka, 'browser' → A-Frame (Laboratorio/Osaka). |
| `showDeviceInfo()` | Muestra información del dispositivo detectado. |
| `autoDetectVR()` | Intenta detectar si hay visor VR conectado. |
| `showSelectedCityInfo()` | Muestra la ciudad seleccionada antes de elegir tipo de dispositivo. |
</details>

<details>
<summary><strong>📊 dashboard.js (relación con VR)</strong></summary>

| Función | Descripción |
|--------|-------------|
| `openVRToursModal()` | Abre el modal de tours VR con países/ciudades. |
| `startVRSession(locationId, cityName, locationName)` | Inicia la sesión VR según ubicación (redirige a la página VR correspondiente). |
| `getCityMapData()`, `loadCityMap()` | Carga datos del mapa de la ciudad y colocación de botones VR. |
| `addVRButtonsToMap()`, `setupVRButtonListeners()` | Añaden botones VR al mapa y sus listeners. |
| `getCityDisplayName()`, `getLocationDisplayName()` | Nombres mostrados para ciudad y ubicación. |
</details>

---

## Resumen rápido por archivo

| Archivo | Tipo | Funciones VR / video principales |
|--------|------|-----------------------------------|
| `aframe-osaka-castle.html` | A-Frame | Skybox, videosphere transición, diálogos 3D, TTS, orientación cámara, quiz |
| `aframe-mirai-skybox-fixed.html` | A-Frame | Skybox lab, playVideo360, backToLab, closeVideo (overlay 2D) |
| `quest3-vr-simple-hands.html` | Three.js + WebXR | playVideo360, stopVideo360, controladores, enterVR, showObjectInfo |
| `quest3-osaka-castle.html` | Three.js + WebXR | Historia, playTransitionVideo, handleVideoEnd, controladores, story/dialogue |
| `vr-components.js` | A-Frame components | vr-fallback-controls, vr-interaction, teleport, quiz-element, vr-audio, etc. |
| `vr-experience-selector.html` | HTML/JS | selectExperience, detectDevice, autoDetectVR |
| `dashboard.js` | JS | openVRToursModal, startVRSession, mapas y botones VR |

---

*Documento generado a partir del análisis del proyecto IKAN_VR / GCA Virtual. Última revisión: marzo 2025.*

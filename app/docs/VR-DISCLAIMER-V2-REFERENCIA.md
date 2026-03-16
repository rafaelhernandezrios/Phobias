# Referencia técnica: Disclaimer VR v2

Documento de referencia con las funciones importantes, cómo se implementaron los botones, manos, selección, altura y qué herramientas/librerías se usan.

---

## 1. Herramientas y librerías

| Recurso | Versión / Origen | Uso |
|--------|-------------------|-----|
| **A-Frame** | `https://aframe.io/releases/1.7.0/aframe.min.js` | Motor WebXR/3D, escena, cámara, raycaster, cursor, entidades. |
| **WebXR Hand Tracking** | Incluido en A-Frame 1.7 (API del navegador/headset) | `hand-tracking-controls` para manos en VR. |
| **CSS / shared.css** | Proyecto (`css/shared.css`) | Variables (colores, radios) y estilos 2D. |
| **Logger** | `js/logger.js` | Registro de sesión y consentimiento (opcional). |

No se usan librerías extra (ni aframe-extras ni three.js directo). Todo se hace con A-Frame 1.7 y componentes registrados a mano en la misma página.

---

## 2. Altura del contenido en VR

### Problema
En muchos headsets (p. ej. Quest) la **altura de la cámara** la fija el dispositivo (referencia “local floor”) y no se puede subir más allá de un tope.

### Solución
- **No forzar la cámara** más de lo razonable: se usa `vr-camera-height="height: 2.0"` en el camera-rig.
- **Subir solo el panel en la escena**: el panel del disclaimer es una entidad en el mundo con `position="0 3.5 -2"` (valor final usado: Y = 3.5). Así el contenido queda “arriba” sin depender del tope del headset.

### Componente: `vr-camera-height`

```javascript
AFRAME.registerComponent('vr-camera-height', {
  schema: { height: { type: 'number', default: 2.0 } },
  tick: function () {
    if (this.el.sceneEl.is && this.el.sceneEl.is('vr-mode'))
      this.el.object3D.position.y = this.data.height;
  }
});
```

- **Dónde:** En el `<a-entity id="cam-rig">` que contiene la cámara.
- **Qué hace:** En cada frame, si la escena está en modo VR, pone la posición Y del rig a `height` (p. ej. 2.0). En dispositivos que ignoran esto, el contenido igual se ve bien si subes el **panel** (posición Y del panel, no de la cámara).

---

## 3. Botones 3D (estructura y selección)

### Estructura de un botón

Cada botón es un `<a-entity>` con `data-action` (accept / eeg / decline). Dentro:

1. **Plano de “borde”** (opcional): `<a-plane>` detrás, un poco más grande y más oscuro, `position="0 0 -0.008"` para dar profundidad. Sin `class="clickable"`.
2. **Plano clickable**: `<a-plane>` con `class="clickable"` y `material="side: double"` para que el rayo lo detecte desde ambos lados.
3. **Texto**: `<a-text>` delante (`position="0 0 0.02"`), `font-size="0.11"` o mayor para legibilidad en VR.

Ejemplo (Accept):

```html
<a-entity id="btn-accept-vr" position="-0.72 -0.42 0" data-action="accept">
  <a-plane width="0.72" height="0.22" color="#2d4a6e" position="0 0 -0.008" material="side: double"></a-plane>
  <a-plane width="0.68" height="0.2" color="#5b9cf5" position="0 0 0" material="side: double" class="clickable"></a-plane>
  <a-text value="Accept / 同意" anchor="center" align="center" position="0 0 0.02" width="0.65" color="#ffffff" font-size="0.115"></a-text>
</a-entity>
```

### Cómo se seleccionan (click)

- **Desde la mirada:** La cámara lleva `cursor` y `raycaster`. El `cursor` de A-Frame dispara el evento `click` cuando el rayo intersecta un objeto con la clase que tenga `raycaster` (aquí `objects: .clickable`) durante el tiempo de “fuse” (p. ej. 2 s).
- **Desde las manos:** Cada mano tiene `raycaster` y el componente `hand-pinch-cursor`, que en el evento `pinchended` mira la primera intersección del raycaster, sube al padre con `data-action` y hace `target.emit('click')`.

En ambos casos el **listener** en JS busca el entity con `data-action` y ejecuta la acción:

```javascript
function onVrButtonClick(evt) {
  var el = evt.target;
  while (el && el.getAttribute && !el.getAttribute('data-action')) el = el.parentEl;
  if (!el || !el.getAttribute('data-action')) return;
  var action = el.getAttribute('data-action');
  if (action === 'accept') goMenu();
  else if (action === 'eeg') goExperiment();
  else if (action === 'decline') decline();
}
document.getElementById('btn-accept-vr').addEventListener('click', onVrButtonClick);
// ... y lo mismo para los a-plane hijos con el mismo listener
```

Puntos clave:
- El elemento que debe recibir el “click” lógico es el que tiene `data-action`; el evento puede venir del `a-plane` hijo, por eso se sube con `parentEl` hasta encontrar `data-action`.
- Todos los planos clickables llevan `class="clickable"` para que el `raycaster` los incluya (`raycaster="objects: .clickable; far: 10"` en cámara, `far: 8` en manos).

---

## 4. Manos en VR

### Entidades

Dos entidades hijas del mismo camera-rig que la cámara:

```html
<a-entity hand-tracking-controls="hand: left; modelStyle: mesh"  raycaster="objects: .clickable; far: 8" hand-pose-sync hand-pinch-cursor hand-laser-visual position="0 0 0"></a-entity>
<a-entity hand-tracking-controls="hand: right; modelStyle: mesh" raycaster="objects: .clickable; far: 8" hand-pose-sync hand-pinch-cursor hand-laser-visual position="0 0 0"></a-entity>
```

- **hand-tracking-controls:** Componente de A-Frame que usa la API de hand tracking del headset (WebXR). `modelStyle: mesh` muestra la malla de la mano.
- **raycaster:** Mismo selector `objects: .clickable` que la cámara para que las manos puedan “tocar” los botones.
- **hand-pose-sync**, **hand-pinch-cursor**, **hand-laser-visual:** Componentes **custom** registrados en la misma página (ver abajo).

### Componente: `hand-pose-sync`

Sincroniza la posición y rotación de la entidad con la muñeca del modelo de mano que crea `hand-tracking-controls`, para que el rayo y el láser salgan de la mano.

- Usa `this.el.components['hand-tracking-controls'].wristObject3D`.
- Cada frame: `getWorldPosition` / `getWorldQuaternion` de la muñeca, pasa a espacio local del padre, y asigna a `this.el.object3D.position` y `quaternion`.

### Componente: `hand-pinch-cursor`

Cuando el usuario hace “pinch” (juntar índice y pulgar), dispara un click en el elemento bajo el rayo:

- Escucha el evento `pinchended` de la entidad (lo emite A-Frame al soltar el pinch).
- Lee `raycaster.intersectedEls` o `raycaster.intersections[0].object.el`.
- Sube por `parentEl` hasta encontrar un elemento con `class="clickable"` (o el que tenga `data-action` si lo usas).
- Hace `target.emit('click')` para que el mismo listener de los botones procese la acción.

### Componente: `hand-laser-visual`

Dibuja un “láser” desde la mano hasta el punto de intersección (o hasta una distancia máxima):

- **init:** Crea dos hijos: un cilindro (línea) y un anillo (cursor al final), con `rotation="90 0 0"` para que apunten hacia delante, y los añade a la entidad.
- **tick:** Lee la distancia del raycaster (`intersections[0].distance`); si hay intersección acorta el cilindro y mueve el anillo a esa distancia; si no, usa la longitud máxima (p. ej. 8).

Así el usuario ve desde cada mano un rayo y un punto que llega hasta el botón.

---

## 5. Selección por mirada (gaze) y retículo

### Cámara

```html
<a-entity id="cam" camera look-controls
  cursor="rayOrigin: mouse; fuse: true; fuseTimeout: 2000; fuseLength: 0.5"
  raycaster="objects: .clickable; far: 10; showLine: true; lineColor: #00d4ff; lineOpacity: 0.8">
  <a-entity id="reticle" position="0 0 -0.8">
    <a-ring radius-inner="0.012" radius-outer="0.03" color="#00d4ff" material="side: double; transparent: true; opacity: 0.95; depthTest: false; depthWrite: false"></a-ring>
    <a-circle radius="0.006" color="#fff" position="0 0 0.001" material="side: double; depthTest: false; depthWrite: false"></a-circle>
  </a-entity>
</a-entity>
```

- **cursor:** Componente de A-Frame. `rayOrigin: mouse` en VR suele ser la dirección de la mirada. `fuse: true` + `fuseTimeout: 2000` = mantener la mirada 2 s sobre un elemento para disparar `click`. El primer hijo de la entidad con `cursor` se usa como visual del cursor y se mueve al punto de intersección.
- **raycaster:** `objects: .clickable; far: 10` para que solo los elementos con clase `clickable` sean considerados.
- **reticle:** Anillo + círculo delante de la cámara; al haber intersección, el cursor de A-Frame los mueve al punto de impacto para feedback visual.

---

## 6. Refresco del raycaster al entrar en VR

Al entrar en VR, a veces los objetos aún no están en la lista del raycaster. Se fuerza un refresh en la cámara y en cada mano:

```javascript
scene.addEventListener('enter-vr', function () {
  var cam = document.getElementById('cam');
  if (cam && cam.components.raycaster && cam.components.raycaster.refreshObjects) {
    cam.components.raycaster.refreshObjects();
  }
  document.querySelectorAll('[hand-tracking-controls]').forEach(function (hand) {
    if (hand.components.raycaster && hand.components.raycaster.refreshObjects)
      hand.components.raycaster.refreshObjects();
  });
});
```

---

## 7. Resumen de componentes custom (registrados en la página)

| Componente | Dónde se usa | Función |
|------------|----------------|--------|
| `vr-camera-height` | `cam-rig` | Ajusta la Y del rig en VR (puede ser ignorado por el headset). |
| `hand-pose-sync` | Entidades con `hand-tracking-controls` | Sincroniza posición/rotación con la muñeca. |
| `hand-pinch-cursor` | Mismas entidades | En `pinchended`, emite `click` en el elemento intersectado. |
| `hand-laser-visual` | Mismas entidades | Dibuja el láser (cilindro + anillo) hasta la intersección. |

---

## 8. Flujo 2D vs VR

- **2D:** Overlay HTML con botones normales; botón “View in VR” oculta el overlay y llama `scene.enterVR()`.
- **VR:** Se ve solo la escena A-Frame (panel + botones 3D). Interacción por mirada (fuse 2 s) o pinch de mano. Al salir de VR (`exit-vr`) se vuelve a mostrar el overlay 2D.

---

## 9. Archivo de referencia

Implementación completa de estos conceptos: **`disclaimer-v2.html`** en la raíz de `app/`.

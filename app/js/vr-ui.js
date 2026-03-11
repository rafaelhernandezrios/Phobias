/**
 * VR-ATR Phobias — VR UI/UX components
 * Hover feedback, fuse cursor, and shared VR styling
 */
(function () {
  // Hover scale: scales up the card under any raycaster (camera or hand) for clear feedback
  AFRAME.registerComponent('vr-hover-scale', {
    schema: {
      camera: { type: 'selector', default: '[camera]' },
      scale: { type: 'number', default: 1.06 }
    },
    init: function () {
      this.lastHovered = null;
    },
    getHoveredCard: function (intersectedEls) {
      if (!intersectedEls || !intersectedEls.length) return null;
      for (var i = 0; i < intersectedEls.length; i++) {
        var el = intersectedEls[i];
        while (el) {
          if (el.classList && (el.classList.contains('phobia-card') || el.classList.contains('level-card') || el.classList.contains('vr-back-btn'))) {
            return el;
          }
          el = el.parentEl;
        }
      }
      return null;
    },
    tick: function () {
      var scene = this.el;
      var camera = this.data.camera;
      var hovered = null;
      if (camera && camera.components && camera.components.raycaster) {
        hovered = this.getHoveredCard(camera.components.raycaster.intersectedEls);
      }
      if (!hovered) {
        var rig = scene.querySelector('#camera-rig');
        if (rig) {
          var rays = rig.querySelectorAll('[raycaster]');
          for (var r = 0; r < rays.length; r++) {
            if (rays[r].components && rays[r].components.raycaster) {
              hovered = this.getHoveredCard(rays[r].components.raycaster.intersectedEls);
              if (hovered) break;
            }
          }
        }
      }
      if (hovered !== this.lastHovered) {
        if (this.lastHovered) this.lastHovered.setAttribute('scale', '1 1 1');
        if (hovered) hovered.setAttribute('scale', this.data.scale + ' ' + this.data.scale + ' ' + this.data.scale);
        this.lastHovered = hovered;
      }
    }
  });

})();

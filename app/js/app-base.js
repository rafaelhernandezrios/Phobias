/**
 * Base URL para cargar recursos (imágenes, data, vídeos) igual en local y en otros dispositivos (ej. Quest).
 * Resuelve la ruta base del proyecto desde la URL actual.
 */
(function () {
  var p = window.location.pathname;
  var base = (!p || p === '/') ? '/' : (p.endsWith('/') ? p : p.substring(0, p.lastIndexOf('/') + 1));
  window.APP_BASE_URL = window.location.origin + base;
  /**
   * Convierte una ruta relativa (ej. "assets/thumbnails/x.jpg") a URL absoluta.
   * Si ya es absoluta (http/https), la devuelve tal cual.
   */
  window.assetUrl = function (path) {
    if (!path) return path;
    if (path.indexOf('http:') === 0 || path.indexOf('https:') === 0) return path;
    var baseUrl = window.APP_BASE_URL || '';
    if (path.indexOf('/') === 0) return window.location.origin + path;
    return baseUrl + (baseUrl.endsWith('/') ? path.replace(/^\//, '') : path);
  };
})();

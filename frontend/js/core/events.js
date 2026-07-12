/* CollabForge AI — tiny pub/sub event bus. */
(function (root) {
  const listeners = {};
  function on(type, fn) {
    (listeners[type] = listeners[type] || []).push(fn);
    return () => off(type, fn);
  }
  function off(type, fn) {
    if (!listeners[type]) return;
    listeners[type] = listeners[type].filter((f) => f !== fn);
  }
  function emit(type, detail) {
    (listeners[type] || []).forEach((fn) => { try { fn(detail); } catch (e) { console.error(e); } });
  }
  root.CF = root.CF || {};
  root.CF.events = { on, off, emit };
})(window);

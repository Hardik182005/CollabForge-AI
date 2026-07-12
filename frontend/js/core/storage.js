/* CollabForge AI — namespaced localStorage wrapper (safe, JSON, quota-tolerant). */
(function (root) {
  const NS = "cf:";
  function get(key, fallback) {
    try {
      const raw = root.localStorage.getItem(NS + key);
      return raw === null ? fallback : JSON.parse(raw);
    } catch (_) { return fallback; }
  }
  function set(key, value) {
    try { root.localStorage.setItem(NS + key, JSON.stringify(value)); return true; }
    catch (_) { return false; }
  }
  function remove(key) { try { root.localStorage.removeItem(NS + key); } catch (_) {} }
  root.CF = root.CF || {};
  root.CF.storage = { get, set, remove };
})(window);

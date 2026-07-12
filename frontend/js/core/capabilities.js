/* CollabForge AI — capability gating (spec §10).
   Feature availability is DERIVED FROM THE BACKEND, never a frontend flag. */
(function (root) {
  const CF = root.CF = root.CF || {};
  let cache = null;

  async function load(force) {
    if (cache && !force) return cache;
    const res = await CF.api.get("/api/v1/system/capabilities");
    cache = (res && res.success && res.data) ? res.data : null;
    if (CF.state) CF.state.set("capabilities", cache || {});
    return cache;
  }

  function get() { return cache; }

  // Path helpers, all null-safe.
  function anakin() { return (cache && cache.anakin) || {}; }
  function wireLive() { return !!(anakin().wire && anakin().wire.available); }
  function scraperLive() { return !!(anakin().scraper && anakin().scraper.available); }
  function searchLive() { return !!(anakin().search && anakin().search.available); }
  function anakinAvailable() { return !!anakin().available; }
  function provider(name) { return (cache && cache[name]) || { available: false }; }
  function feature(name) { return (cache && cache.features && cache.features[name]) || { enabled: false }; }
  function source(name) { return (cache && cache.sources && cache.sources[name]) || { enabled: false }; }

  CF.caps = {
    load, get, anakin, wireLive, scraperLive, searchLive,
    anakinAvailable, provider, feature, source,
  };
})(window);

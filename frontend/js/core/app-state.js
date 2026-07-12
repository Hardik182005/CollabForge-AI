/* CollabForge AI — single application state (spec §13).
   One creator state, one campaign state, one trend context. Persists the
   durable parts to localStorage so context survives view switches & reloads. */
(function (root) {
  const CF = root.CF = root.CF || {};
  const storage = CF.storage;
  const events = CF.events;

  const DEFAULT = {
    workspace: "brand",
    activeView: "discover",
    capabilities: {},
    business: null,
    campaignId: null,
    campaign: null,
    selectedTrend: null,
    selectedScript: null,
    selectedCreator: null,
    shortlistedCreators: [],
    creatorDossiers: {},
    comparison: null,
    roiScenario: null,
    outreachDrafts: null,
    campaignBrief: null,
    contractDraft: null,
    voiceAsset: null,
    reelAsset: null,
    autopilotRun: null,
  };

  // Which keys persist across reloads (capabilities re-fetched live; heavy
  // volatile assets like voice/reel base64 are not persisted).
  const PERSIST_KEYS = [
    "workspace", "business", "campaignId", "campaign", "selectedTrend",
    "selectedScript", "selectedCreator", "shortlistedCreators",
    "creatorDossiers", "comparison", "roiScenario", "outreachDrafts",
    "campaignBrief", "contractDraft",
  ];

  const saved = storage.get("app-state", {});
  const state = Object.assign({}, DEFAULT, saved || {});
  state.capabilities = {}; // always start empty, fetched live

  // One-time cleanup: older formatters persisted the literal "Unavailable" into
  // some fields; strip that junk so it never prefills an input.
  (function scrubJunk() {
    if (!CF.fmt) return;
    const clean = (o, keys) => { if (o && typeof o === "object") keys.forEach((k) => { if (o[k] && CF.fmt.inputValue(o[k]) === "") o[k] = ""; }); };
    clean(state.business, ["name", "website", "product", "industry"]);
    clean(state.selectedCreator, ["name", "handle"]);
  })();

  function persist() {
    const slim = {};
    PERSIST_KEYS.forEach((k) => { slim[k] = state[k]; });
    storage.set("app-state", slim);
  }

  function get(key) { return key ? state[key] : state; }

  function set(key, value) {
    if (typeof key === "object") {
      Object.assign(state, key);
      Object.keys(key).forEach((k) => events.emit("state:" + k, state[k]));
    } else {
      state[key] = value;
      events.emit("state:" + key, value);
    }
    events.emit("state:change", state);
    persist();
  }

  function selectCreator(creator) {
    set("selectedCreator", creator);
    if (creator && creator.dossier && creator.id) {
      state.creatorDossiers[creator.id] = creator.dossier;
      persist();
    }
  }

  function shortlist(creator) {
    if (!creator) return;
    const key = creator.id || creator.name;
    const exists = state.shortlistedCreators.some((c) => (c.id || c.name) === key);
    if (!exists) { state.shortlistedCreators.push(creator); set("shortlistedCreators", state.shortlistedCreators); }
  }

  function unshortlist(idOrName) {
    state.shortlistedCreators = state.shortlistedCreators.filter((c) => (c.id || c.name) !== idOrName);
    set("shortlistedCreators", state.shortlistedCreators);
  }

  function reset() {
    Object.assign(state, DEFAULT);
    state.capabilities = {};
    persist();
    events.emit("state:change", state);
  }

  CF.state = { get, set, selectCreator, shortlist, unshortlist, reset, DEFAULT };
})(window);

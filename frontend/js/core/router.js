/* CollabForge AI — hash/query router for the single app.html shell.
   Reads ?workspace=&view= (and #view) and drives view rendering. Views
   register a render(container, params) function keyed by "workspace:view". */
(function (root) {
  const CF = root.CF = root.CF || {};
  const views = {};
  let container = null;
  let current = null;

  function register(workspace, view, renderer) {
    views[workspace + ":" + view] = renderer;
  }

  function parse() {
    const qs = new URLSearchParams(root.location.search);
    let workspace = qs.get("workspace") || CF.state.get("workspace") || "brand";
    let view = qs.get("view");
    // allow #view override for in-app nav without full reload
    const hash = root.location.hash.replace(/^#/, "");
    if (hash) view = hash;
    if (!view) view = workspace === "creator" ? "trends" : "discover";
    return { workspace, view };
  }

  function key(workspace, view) { return workspace + ":" + view; }

  async function navigate(workspace, view, params, opts) {
    opts = opts || {};
    const k = key(workspace, view);
    const renderer = views[k] || views[key(workspace, workspace === "creator" ? "trends" : "discover")];
    CF.state.set({ workspace, activeView: view });
    if (!opts.silent) {
      const url = "app.html?workspace=" + workspace + "&view=" + view;
      root.history.pushState({ workspace, view }, "", url);
    }
    current = k;
    CF.events.emit("route:change", { workspace, view });
    if (renderer && container) {
      container.scrollTop = 0;
      try { await renderer(container, params || {}); }
      catch (e) {
        console.error("view render error", k, e);
        if (CF.ui) CF.ui.error(container, "This view failed to load.", e.message);
      }
    }
  }

  function start(mountEl) {
    container = mountEl;
    const { workspace, view } = parse();
    navigate(workspace, view, {}, { silent: true });
    root.addEventListener("popstate", () => {
      const p = parse();
      navigate(p.workspace, p.view, {}, { silent: true });
    });
  }

  CF.router = { register, navigate, start, parse, get current() { return current; } };
})(window);

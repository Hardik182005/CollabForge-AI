/* CollabForge AI — reusable Anakin pipeline component (spec §19).
   One implementation, two modes: compact (landing) and expanded (autopilot).
   Driven by REAL backend SSE stage events. Wire and Scraper render as
   SEPARATE nodes so a Wire outage is visible and never faked. */
(function (root) {
  const CF = root.CF = root.CF || {};
  const esc = (s) => CF.fmt.escapeHtml(s);

  // Node order + which stages map onto them.
  const NODES = [
    { id: "query",        title: "Your query",        icon: "search",   stages: ["VALIDATING"] },
    { id: "router",       title: "Source router",     icon: "route",    stages: ["ROUTING"] },
    { id: "wire",         title: "Anakin Wire",       icon: "wire",     stages: ["FETCHING_WIRE"], parallel: "sources" },
    { id: "scraper",      title: "Universal Scraper", icon: "scrape",   stages: ["SCRAPING"], parallel: "sources" },
    { id: "evidence",     title: "Evidence layer",    icon: "layers",   stages: ["NORMALIZING"] },
    { id: "intelligence", title: "Intelligence engine", icon: "brain",  stages: ["REASONING"] },
    { id: "campaign",     title: "Your campaign",     icon: "flag",     stages: ["COMPLETE", "PARTIAL"] },
  ];

  const ICONS = {
    search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m21 21-4-4"/></svg>',
    route:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="6" cy="19" r="2"/><circle cx="18" cy="5" r="2"/><path d="M6 17V9a4 4 0 0 1 4-4h6"/></svg>',
    wire:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="6" rx="1"/><rect x="3" y="14" width="18" height="6" rx="1"/><path d="M7 7h.01M7 17h.01"/></svg>',
    scrape: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16v12H4z"/><path d="M4 20h16M9 8l2 2 4-4"/></svg>',
    layers: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 13 9 5 9-5"/></svg>',
    brain:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 3a3 3 0 0 0-3 3 3 3 0 0 0-1 5 3 3 0 0 0 2 5 3 3 0 0 0 5 1V4a3 3 0 0 0-3-1Z"/><path d="M15 3a3 3 0 0 1 3 3 3 3 0 0 1 1 5 3 3 0 0 1-2 5 3 3 0 0 1-5 1"/></svg>',
    flag:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 21V4h13l-2 4 2 4H4"/></svg>',
  };

  function create(container, opts) {
    opts = opts || {};
    const mode = opts.mode || "expanded";
    const state = {}; // id -> {state, sub, chips, stat}
    NODES.forEach((n) => { state[n.id] = { state: "idle", sub: "", chips: [], stat: null }; });
    let metrics = { sourcesRequested: 0, sourcesReturned: 0, evidenceCount: 0, durationMs: 0, provider: "" };
    let result = null;
    let unavailable = null;

    function nodeHtml(n) {
      const s = state[n.id];
      const statusLabel = { idle: "Ready", running: "Running", complete: "Done", partial: "Partial", unavailable: "Standby", failed: "Failed" }[s.state] || "";
      const stat = s.stat ? '<div class="pl-node__stat">' + s.stat + "</div>" : "";
      const chips = (s.chips && s.chips.length) ? '<div class="pl-chips">' + s.chips.map((c) => CF.ui.sourceBadge(c)).join("") + "</div>" : "";
      return '<div class="pl-node" data-node="' + n.id + '" data-state="' + s.state + '">' +
        '<div class="pl-node__icon">' + ICONS[n.icon] + "</div>" +
        '<div class="pl-node__body"><div class="pl-node__title">' + esc(n.title) +
        '<span class="pl-node__status">' + esc(statusLabel) + "</span></div>" +
        '<div class="pl-node__sub">' + esc(s.sub || DEFAULT_SUB[n.id] || "") + "</div>" +
        chips + stat + "</div></div>";
    }

    function connector(active) { return '<div class="pl-connector' + (active ? " is-active" : "") + '"></div>'; }

    function render() {
      if (unavailable) {
        container.innerHTML = '<div class="pl-unavailable"><strong>Connecting to Anakin…</strong><p>' +
          esc(unavailable) + "</p></div>";
        return;
      }
      let html = '<div class="cf-pipeline ' + (mode === "compact" ? "cf-pipeline--compact" : "") + '"><div class="cf-pipeline__flow">';
      html += '<div class="pl-row">' + nodeHtml(NODES[0]) + "</div>";
      html += connector(state.router.state !== "idle");
      html += '<div class="pl-row">' + nodeHtml(NODES[1]) + "</div>";
      const srcActive = state.wire.state !== "idle" || state.scraper.state !== "idle";
      html += connector(srcActive);
      html += '<div class="pl-row pl-parallel">' + nodeHtml(NODES[2]) + nodeHtml(NODES[3]) + "</div>";
      html += connector(state.evidence.state !== "idle");
      html += '<div class="pl-row">' + nodeHtml(NODES[4]) + "</div>";
      html += connector(state.intelligence.state !== "idle");
      html += '<div class="pl-row">' + nodeHtml(NODES[5]) + "</div>";
      html += connector(state.campaign.state !== "idle");
      html += '<div class="pl-row">' + nodeHtml(NODES[6]) + "</div>";
      html += "</div>";

      if (metrics.evidenceCount || metrics.durationMs) {
        html += '<div class="cf-pipeline__meta">' +
          statTile(metrics.sourcesRequested, "Sources requested") +
          statTile(metrics.sourcesReturned, "Sources returned") +
          statTile(metrics.evidenceCount, "Evidence records") +
          '<div class="stat"><div class="stat__value">' + esc(CF.fmt.formatDuration(metrics.durationMs, "—")) + '</div><div class="stat__label">Duration</div></div>' +
          (metrics.provider ? '<div class="stat"><div class="stat__value" style="font-size:var(--text-base)">' + esc(providerLabel(metrics.provider)) + '</div><div class="stat__label">Provider</div></div>' : "") +
          "</div>";
      }
      if (result) html += resultHtml(result);
      html += "</div>";
      container.innerHTML = html;
    }

    function statTile(v, label) {
      return '<div class="stat"><div class="stat__value">' + esc(CF.fmt.formatNumber(v, "0")) +
        '</div><div class="stat__label">' + esc(label) + "</div></div>";
    }

    function resultHtml(r) {
      const conf = CF.ui.confidenceChip(r.confidence);
      const sources = (r.sources || []).slice(0, 6).map((s) =>
        '<div class="evidence"><div class="evidence__title">' +
        (s.url ? '<a href="' + esc(s.url) + '" target="_blank" rel="noopener">' + esc(s.title) + "</a>" : esc(s.title)) +
        "</div>" + (s.snippet ? '<div class="evidence__snippet">' + esc(s.snippet.slice(0, 140)) + "</div>" : "") +
        '<div class="evidence__meta">' + CF.ui.sourceBadge(s.provider, s.confidence) + "</div></div>").join("");
      const cta = r.cta ? '<a class="btn btn--primary" href="' + esc(r.cta.href) + '">' + esc(r.cta.label) + "</a>" : "";
      return '<div class="pl-result"><div class="card__head"><div>' +
        '<span class="eyebrow">' + esc(r.entityType === "creator" ? "Resolved creator" : "Topic evidence") + "</span>" +
        '<div class="pl-result__title">' + esc(r.title) + "</div></div>" + conf + "</div>" +
        "<p>" + esc(r.summary) + "</p>" +
        (sources ? '<div class="pl-result__sources">' + sources + "</div>" : "") +
        '<div style="margin-top:var(--space-4)">' + cta + "</div></div>";
    }

    // Apply one SSE stage event.
    function apply(ev) {
      if (!ev || !ev.stage) return;
      if (ev.stage === "FAILED" && (!ev.result)) {
        // if anakin fully unavailable
        const w = (ev.warnings || [])[0];
        if (w && w.code === "ANAKIN_UNAVAILABLE") { unavailable = w.message; render(); return; }
      }
      // duration / counts (always latest)
      if (typeof ev.durationMs === "number") metrics.durationMs = ev.durationMs;
      if (ev.evidenceCount != null) metrics.evidenceCount = ev.evidenceCount;
      if (ev.sourcesRequested != null && ev.sourcesRequested) metrics.sourcesRequested = ev.sourcesRequested;
      if (ev.sourcesReturned != null && ev.sourcesReturned) metrics.sourcesReturned = ev.sourcesReturned;
      if (ev.provider && ev.status !== "unavailable") metrics.provider = ev.provider;

      const node = NODES.find((n) => n.stages.indexOf(ev.stage) !== -1);
      if (node) {
        // mark all earlier non-parallel nodes complete
        const idx = NODES.indexOf(node);
        NODES.forEach((n, i) => {
          if (i < idx && state[n.id].state === "running") state[n.id].state = "complete";
        });
        const st = state[node.id];
        if (ev.status === "unavailable") { st.state = "unavailable"; }
        else if (ev.status === "failed") { st.state = "failed"; }
        else if (ev.status === "complete") { st.state = "complete"; }
        else if (ev.status === "partial") { st.state = "partial"; }
        else st.state = "running";
        if (ev.label) st.sub = ev.label;
        if (ev.provider) st.chips = [ev.provider];
        if (node.id === "wire" || node.id === "scraper") {
          st.stat = "";
        }
      }
      // Terminal events mark evidence/intelligence/campaign
      if (ev.stage === "COMPLETE" || ev.stage === "PARTIAL") {
        ["query", "router", "wire", "scraper", "evidence", "intelligence"].forEach((id) => {
          if (state[id].state === "running") state[id].state = "complete";
        });
        state.campaign.state = ev.stage === "PARTIAL" ? "partial" : "complete";
        if (ev.result) result = ev.result;
      }
      if (ev.stage === "FAILED") {
        NODES.forEach((n) => { if (state[n.id].state === "running") state[n.id].state = "failed"; });
        if (ev.result) result = ev.result;
      }
      // evidence/intelligence get counts
      state.evidence.stat = metrics.evidenceCount ? "<span>Records <b>" + CF.fmt.formatNumber(metrics.evidenceCount) + "</b></span>" : null;
      render();
    }

    function reset() {
      NODES.forEach((n) => { state[n.id] = { state: "idle", sub: "", chips: [], stat: null }; });
      metrics = { sourcesRequested: 0, sourcesReturned: 0, evidenceCount: 0, durationMs: 0, provider: "" };
      result = null; unavailable = null;
      render();
    }

    // Run via SSE stream (preferred) with JSON fallback.
    async function run(query, endpoint) {
      reset();
      endpoint = endpoint || "/api/v1/pipeline/preview/stream";
      try {
        await CF.api.stream(endpoint, { query }, apply);
      } catch (e) {
        // fallback to non-streaming
        const jsonEndpoint = endpoint.replace("/stream", "");
        const res = await CF.api.post(jsonEndpoint, { query });
        if (res && res.success && res.data) {
          (res.meta && res.meta.stages || []).forEach(apply);
          apply({ stage: "COMPLETE", status: "complete", result: res.data,
                  durationMs: res.meta && res.meta.durationMs,
                  evidenceCount: res.data.evidenceCount,
                  sourcesRequested: res.meta && res.meta.sourcesRequested,
                  sourcesReturned: res.meta && res.meta.sourcesReturned });
        } else {
          apply({ stage: "FAILED", status: "failed",
                  warnings: [(res && res.error) || { code: "FAILED", message: "Pipeline failed." }] });
        }
      }
    }

    reset();
    return { run, reset, apply, get result() { return result; } };
  }

  const DEFAULT_SUB = {
    query: "Creator, business or campaign topic",
    router: "Deterministic: Wire → Scraper → Search",
    wire: "Structured platform actions",
    scraper: "Public pages & business sites",
    evidence: "Normalized, de-duplicated, cited",
    intelligence: "Reasoning over evidence only",
    campaign: "Shortlist, research & outputs",
  };

  function providerLabel(p) {
    return { anakin_wire: "Anakin Wire", anakin_scrape: "Universal Scraper", anakin_search: "Anakin Search" }[p] || p;
  }

  CF.pipeline = { create };
})(window);

/* CollabForge AI — Brand Intelligence views. Discover → Research → Compare → Campaign. */
(function () {
  const CF = window.CF, V = CF.view, fmt = CF.fmt;
  const reg = (view, fn) => CF.router.register("brand", view, fn);

  // ── Discover Creators ──
  reg("discover", async (root) => {
    root.innerHTML = V.viewShell(
      V.sectionHead("Discover", "Discover Creators", "Search a creator by name, or discover candidates for a topic. Live sources only.") +
      '<div class="card card--pad view__section"><div class="search-box"><input class="input" id="d-q" placeholder="Search a creator, channel or handle — try: Technical Guruji">' +
      '<button class="btn btn--primary" id="d-research">Research</button></div>' +
      '<div class="lp-demo-examples" style="margin-top:var(--space-3)"><button class="chip" id="d-tg">Try Technical Guruji</button></div>' +
      '<div class="field-row" style="margin-top:var(--space-4)"><div class="field"><label>Or discover by topic</label>' +
      '<div class="search-box"><input class="input" id="d-topic" placeholder="e.g. hindi tech reviews"><button class="btn btn--ghost" id="d-go">Discover</button></div></div></div></div>' +
      '<div id="d-out"></div>');
    const out = root.querySelector("#d-out");
    CF.ui.empty(out, "Search a creator or a topic", "Technical Guruji is never auto-loaded — click to try it, it still runs live.");
    const goResearch = () => { const q = root.querySelector("#d-q").value.trim(); if (!q) return; CF.state.set("selectedCreator", { name: q }); CF.router.navigate("brand", "research"); };
    root.querySelector("#d-research").addEventListener("click", goResearch);
    root.querySelector("#d-q").addEventListener("keydown", (e) => { if (e.key === "Enter") goResearch(); });
    root.querySelector("#d-tg").addEventListener("click", () => { root.querySelector("#d-q").value = "Technical Guruji"; });
    root.querySelector("#d-go").addEventListener("click", async () => {
      const topic = root.querySelector("#d-topic").value.trim(); if (!topic) return;
      const res = await V.into(out, () => CF.api.post("/api/v1/creators/discover", { topic, limit: 6 }), { loading: "Discovering candidates via Anakin Search…" });
      if (!res) return;
      const list = (res.data && res.data.results) || res.results || [];
      if (!list.length) { CF.ui.empty(out, "No candidates found", "Try another topic."); return; }
      out.innerHTML = '<p class="small muted view__section">' + fmt.escapeHtml((res.data && res.data.note) || res.note || "") + "</p><div class=\"grid grid--auto\">" +
        list.map((e) => '<div class="card card--pad"><div class="card__title">' + fmt.escapeHtml((e.title || "").slice(0, 60)) + "</div>" +
          (e.snippet ? '<p class="small">' + fmt.escapeHtml(String(e.snippet).slice(0, 140)) + "</p>" : "") +
          '<div class="card__meta">' + CF.ui.sourceBadge(e.data_method || "anakin_search") + "</div>" +
          '<div style="margin-top:var(--space-3)"><button class="btn btn--primary btn--sm" data-name="' + fmt.escapeHtml(e.title || "") + '">Research</button></div></div>').join("") + "</div>";
      out.querySelectorAll("[data-name]").forEach((b) => b.addEventListener("click", () => { CF.state.set("selectedCreator", { name: b.getAttribute("data-name") }); CF.router.navigate("brand", "research"); }));
    });
  });

  // ── Creator Research (dossier) ──
  reg("research", async (root) => {
    const sel = CF.state.get("selectedCreator");
    root.innerHTML = V.viewShell(V.sectionHead("Discover", "Creator Research", "Evidence-backed dossier — every signal traces to a source.") +
      '<div class="card card--pad view__section"><div class="search-box"><input class="input" id="r-q" value="' + fmt.escapeHtml(fmt.inputValue(sel && sel.name)) + '" placeholder="Creator name or handle"><button class="btn btn--primary" id="r-go">Research</button></div></div>' +
      '<div id="r-out"></div>');
    const out = root.querySelector("#r-out");
    if (!sel || !sel.name) CF.ui.empty(out, "Enter a creator to research", "Or pick one from Discover Creators.");
    async function research() {
      const q = root.querySelector("#r-q").value.trim(); if (!q) return;
      const res = await V.into(out, () => CF.api.post("/api/v1/creators/research", { creator: q }), { loading: "Resolving creator and gathering live evidence…" });
      if (!res) return;
      const d = res.data || res;
      if (d.status === "not_found") { CF.ui.empty(out, "Creator not found in public sources", d.message); return; }
      renderDossier(out, d);
    }
    root.querySelector("#r-go").addEventListener("click", research);
    if (sel && sel.name) research();
  });

  function renderDossier(out, d) {
    const ov = d.overview || {}; const fit = d.fit_score || {}; const rate = d.rate_estimate || {};
    const eng = d.engagement_signals || {};
    const partial = (d.partial_failures || []).map((p) => ({ code: p.section, message: "Section unavailable: " + p.section }));
    // store dossier for downstream views
    CF.state.selectCreator({ id: (ov.name || d.query), name: ov.name || d.query, handle: ov.handle, subscribers: ov.subscribers, dossier: d });

    const scoreBreak = (fit.components || []).map((c) =>
      '<div class="score-bar' + (c.score == null ? " score-bar__missing" : "") + '"><div><div class="score-bar__label"><span>' + fmt.escapeHtml(c.name) + " · " + fmt.formatPercent(c.weight) +
      '</span><span>' + fmt.safeText(c.score, "n/a") + "</span></div><div class=\"score-bar__track\"><div class=\"score-bar__fill\" style=\"width:" + (typeof c.score === "number" ? c.score : 0) + "%\"></div></div>" +
      (c.note ? '<p class="tiny muted">' + fmt.escapeHtml(c.note) + "</p>" : "") + "</div></div>").join("");

    const recent = (d.recent_content || []).slice(0, 6).map((v) =>
      '<div class="evidence"><div class="evidence__title">' + (v.url ? '<a href="' + fmt.escapeHtml(v.url) + '" target="_blank" rel="noopener">' + fmt.escapeHtml(v.title) + "</a>" : fmt.escapeHtml(v.title)) + "</div>" +
      '<div class="evidence__meta"><span class="muted tiny">' + fmt.formatCompactNumber(v.views, "views n/a") + " views</span>" + (v.published ? '<span class="muted tiny">' + fmt.escapeHtml(v.published) + "</span>" : "") + "</div></div>").join("");

    out.innerHTML =
      '<div class="context-strip">Researching <strong>' + fmt.escapeHtml(ov.name || d.query) + "</strong>" + CF.ui.sourceBadge(d.data_method) +
      '<span class="muted">·</span>' + fmt.formatNumber((d.evidence || []).length) + " evidence records" + CF.ui.confidenceChip(fit.confidence) + "</div>" +
      CF.ui.warnings(partial) +
      '<div class="grid grid--2 view__section">' +
        '<div class="card card--pad"><span class="eyebrow">Overview</span><h3>' + fmt.escapeHtml(ov.name || d.query) + "</h3>" +
          '<div class="stat-row" style="margin-top:var(--space-4)">' +
          '<div class="stat"><div class="stat__value">' + fmt.formatCompactNumber(ov.subscribers, "n/a") + '</div><div class="stat__label">Subscribers</div></div>' +
          '<div class="stat"><div class="stat__value">' + fmt.formatCompactNumber(eng.avg_views, "n/a") + '</div><div class="stat__label">Avg views</div></div>' +
          '<div class="stat"><div class="stat__value">' + fmt.formatNumber((d.recent_content || []).length) + '</div><div class="stat__label">Recent videos</div></div></div>' +
          (ov.niche ? '<p class="small" style="margin-top:var(--space-3)"><strong>Niche:</strong> ' + fmt.escapeHtml(ov.niche) + "</p>" : "") +
          (ov.content_pillars && ov.content_pillars.length ? '<div class="card__meta">' + ov.content_pillars.slice(0, 6).map((p) => '<span class="chip">' + fmt.escapeHtml(p) + "</span>").join("") + "</div>" : "") + "</div>" +
        '<div class="card card--pad"><span class="eyebrow">Brand Fit Score</span>' +
          '<div class="stat" style="margin:var(--space-3) 0"><div class="stat__value">' + fmt.safeText(fit.score, "Insufficient data") + (fit.score != null ? "<span class=\"muted\" style=\"font-size:var(--text-base)\">/100</span>" : "") + '</div><div class="stat__label">Recommendation: ' + fmt.safeText(fit.recommendation, "n/a") + "</div></div>" +
          scoreBreak +
          (fit.missing_data && fit.missing_data.length ? '<p class="tiny muted" style="margin-top:var(--space-3)">Missing: ' + fit.missing_data.map((m) => fmt.escapeHtml(m.component || m.reason)).join(", ") + " — lowers confidence.</p>" : "") + "</div>" +
      "</div>" +
      '<div class="grid grid--2 view__section">' +
        '<div class="card card--pad"><span class="eyebrow">Recent Content</span><div style="margin-top:var(--space-3);display:flex;flex-direction:column;gap:var(--space-2)">' + (recent || '<p class="muted small">No recent content observed.</p>') + "</div></div>" +
        '<div class="card card--pad"><span class="eyebrow">Estimated Collaboration Range</span>' +
          '<div class="stat" style="margin:var(--space-3) 0"><div class="stat__value">' + fmt.formatCurrency(rate.expected, "INR", "On request") + '</div><div class="stat__label">Expected · ' + fmt.formatCurrency(rate.low, "INR", "?") + "–" + fmt.formatCurrency(rate.high, "INR", "?") + "</div></div>" +
          '<p class="tiny muted">' + fmt.escapeHtml(rate.basis || "Estimate from observed reach — negotiate on the creator\'s rate card.") + "</p>" + CF.ui.sourceBadge("heuristic", "estimated") + "</div>" +
      "</div>" +
      '<div class="card card--pad view__section"><span class="eyebrow">Evidence Library</span><div style="margin-top:var(--space-3);display:grid;gap:var(--space-2)">' + V.evidenceList((d.evidence || []).slice(0, 12)) + "</div></div>" +
      '<div style="display:flex;gap:var(--space-2);flex-wrap:wrap"><button class="btn btn--ghost" id="r-shortlist">Add to shortlist</button><button class="btn btn--ghost" id="r-compare">Compare</button><button class="btn btn--primary" id="r-campaign">Use in Campaign</button></div>';

    out.querySelector("#r-shortlist").addEventListener("click", () => { CF.state.shortlist({ id: ov.name || d.query, name: ov.name || d.query, subscribers: ov.subscribers }); CF.ui.toast("Added to shortlist", "success"); });
    out.querySelector("#r-compare").addEventListener("click", () => { CF.state.shortlist({ id: ov.name || d.query, name: ov.name || d.query }); CF.router.navigate("brand", "compare"); });
    out.querySelector("#r-campaign").addEventListener("click", () => CF.router.navigate("brand", "campaign"));
  }

  // ── Compare Creators ──
  reg("compare", async (root) => {
    const shortlist = CF.state.get("shortlistedCreators");
    root.innerHTML = V.viewShell(V.sectionHead("Discover", "Compare Creators", "Side-by-side on fit, reach and safety — from live research.") +
      '<div class="card card--pad view__section"><div class="field"><label>Creators to compare (comma-separated)</label>' +
      '<input class="input" id="c-list" value="' + fmt.escapeHtml(shortlist.map((c) => c.name).join(", ")) + '" placeholder="e.g. Technical Guruji, Trakin Tech"></div>' +
      '<button class="btn btn--primary" id="c-go">Compare</button></div><div id="c-out"></div>');
    const out = root.querySelector("#c-out");
    if (!shortlist.length) CF.ui.empty(out, "Add creators to compare", "Shortlist creators from Research, or type names above.");
    root.querySelector("#c-go").addEventListener("click", async () => {
      const names = root.querySelector("#c-list").value.split(",").map((s) => s.trim()).filter(Boolean);
      if (names.length < 2) { CF.ui.toast("Enter at least two creators", "error"); return; }
      const res = await V.into(out, () => CF.api.post("/api/v1/creators/compare", { creators: names }), { loading: "Researching each creator live…" });
      if (!res) return;
      const d = res.data || res; const rows = d.comparison || d.rows || [];
      if (!rows.length) { CF.ui.empty(out, "Could not compare", "Research failed for the creators provided."); return; }
      out.innerHTML = '<div class="table-wrap"><table class="cf-table"><thead><tr><th>Creator</th><th class="num">Fit</th><th class="num">Reach</th><th class="num">Avg views</th><th class="num">Est. rate</th><th>Confidence</th></tr></thead><tbody>' +
        rows.map((r) => '<tr><td class="row-strong">' + fmt.escapeHtml(r.creator) + "</td><td class=\"num\">" + fmt.safeText(r.fit, "—") + '</td><td class="num">' + fmt.formatCompactNumber(r.reach, "—") + '</td><td class="num">' + fmt.formatCompactNumber(r.avg_views, "—") + '</td><td class="num">' + fmt.formatCurrency(r.rate_expected, "INR", "—") + "</td><td>" + fmt.safeText(r.fit_confidence, "—") + "</td></tr>").join("") + "</tbody></table></div>";
    });
  });

  // ── Campaign Planner (Business DNA + brief) ──
  reg("campaign", async (root) => {
    const biz = CF.state.get("business") || {}; const creator = CF.state.get("selectedCreator");
    root.innerHTML = V.viewShell(V.sectionHead("Campaign", "Campaign Planner", "Analyze the business from its public website, then build the brief.") + V.contextStrip() +
      '<div class="card card--pad view__section"><div class="field-row"><div class="field"><label>Business website</label><input class="input" id="b-url" value="' + fmt.escapeHtml(fmt.inputValue(biz.website)) + '" placeholder="https://…"></div>' +
      '<div class="field"><label>Business name (optional)</label><input class="input" id="b-name" value="' + fmt.escapeHtml(fmt.inputValue(biz.name)) + '"></div></div>' +
      '<div class="field"><label>Extra context (product, goal)</label><input class="input" id="b-ctx" placeholder="New gaming smartphone, launch awareness"></div>' +
      '<button class="btn btn--primary" id="b-go">Analyze Business (Universal Scraper)</button></div><div id="b-out"></div>');
    const out = root.querySelector("#b-out");
    root.querySelector("#b-go").addEventListener("click", async () => {
      const website = root.querySelector("#b-url").value.trim(); if (!website) { CF.ui.toast("Enter a website", "error"); return; }
      const res = await V.into(out, () => CF.api.post("/api/v1/business/analyze", { website, business_name: root.querySelector("#b-name").value.trim(), context: root.querySelector("#b-ctx").value.trim() }), { loading: "Scraping and structuring the business website…" });
      if (!res) return;
      const d = res.data || res;
      if (d.status === "error") { CF.ui.error(out, "Could not analyze the website", (d.error && d.error.message) || ""); return; }
      const dna = d.business_dna || {};
      CF.state.set("business", { name: dna.business_name || root.querySelector("#b-name").value, website, dna });
      const f = (k, v) => v ? '<div class="view__section"><span class="eyebrow">' + k + '</span><p style="color:var(--color-text-primary)">' + fmt.escapeHtml(Array.isArray(v) ? v.join(", ") : v) + "</p></div>" : "";
      out.innerHTML = '<div class="card card--pad"><div class="cf-warnings"><div class="cf-warning"><span class="cf-warning__dot"></span>' + fmt.escapeHtml(d.note || "Extracted from the public website — review before continuing.") + "</div></div>" +
        f("What they sell", dna.what_they_sell) + f("Primary customer", dna.primary_customer) + f("Value proposition", dna.value_proposition) +
        f("Brand tone", dna.brand_tone) + f("Price positioning", dna.price_positioning) + f("Categories", dna.product_categories) + f("Likely objectives", dna.likely_campaign_objectives) +
        '<div style="margin-top:var(--space-4);display:flex;gap:var(--space-2)"><button class="btn btn--primary" id="b-brief">Generate Campaign Brief</button><button class="btn btn--ghost" id="b-outreach">Draft Outreach</button></div>' +
        '<div id="brief-out" style="margin-top:var(--space-5)"></div></div>';
      out.querySelector("#b-outreach").addEventListener("click", () => CF.router.navigate("brand", "outreach"));
      out.querySelector("#b-brief").addEventListener("click", async () => {
        const bo = out.querySelector("#brief-out");
        const r2 = await V.into(bo, () => CF.api.post("/api/v1/campaigns/brief", { business_dna: dna, creator: creator || {}, campaign: { goal: root.querySelector("#b-ctx").value } }), { loading: "Writing brief…" });
        if (!r2) return; const bd = r2.data || r2;
        bo.innerHTML = bd.brief && typeof bd.brief === "object"
          ? V.briefBlock(bd)
          : V.docBlock("brief-md", bd.markdown || bd.brief || fmt.safeText(bd), "Campaign brief");
        V.wireCopy(bo);
      });
    });
  });

  // ── ROI Scenarios ──
  reg("roi", async (root) => {
    root.innerHTML = V.viewShell(V.sectionHead("Campaign", "ROI Scenarios", "Editable assumptions — an estimate, not a guarantee.") +
      '<div class="card card--pad view__section"><div class="field-row">' +
      inp("reach", "Estimated impressions", "500000") + inp("er", "Engagement rate %", "3") + inp("ctr", "Click-through %", "1") +
      inp("cvr", "Conversion %", "2") + inp("aov", "Avg order value", "2000") + inp("cost", "Campaign cost", "150000") +
      "</div><button class=\"btn btn--primary\" id=\"roi-go\">Calculate</button></div><div id=\"roi-out\"></div>");
    const out = root.querySelector("#roi-out");
    root.querySelector("#roi-go").addEventListener("click", async () => {
      const num = (id) => Number(root.querySelector("#roi-" + id).value) || 0;
      const res = await V.into(out, () => CF.api.post("/api/v1/campaigns/roi-scenario", {
        estimated_impressions: num("reach"), engagement_rate_pct: num("er"), click_through_rate_pct: num("ctr"),
        conversion_rate_pct: num("cvr"), average_order_value: num("aov"), campaign_cost: num("cost"), currency: "INR",
      }), { loading: "Modeling…" });
      if (!res) return; const d = res.data || res;
      out.innerHTML = V.roiTable(d);
    });
  });
  function inp(id, label, ph) { return '<div class="field"><label>' + label + '</label><input class="input" id="roi-' + id + '" value="' + ph + '"></div>'; }

  // ── Outreach Studio ──
  reg("outreach", async (root) => {
    const biz = CF.state.get("business") || {}; const creator = CF.state.get("selectedCreator") || {};
    root.innerHTML = V.viewShell(V.sectionHead("Campaign", "Outreach Studio", "Personalized drafts from your business + the creator's real recent content. Never auto-sent.") + V.contextStrip() +
      '<div class="card card--pad view__section"><div class="field"><label>Campaign goal</label><input class="input" id="o-goal" placeholder="Launch awareness and preorders"></div>' +
      '<div class="field"><label>Deliverables</label><input class="input" id="o-deliv" placeholder="1 integrated video + 2 stories"></div>' +
      '<button class="btn btn--primary" id="o-go">Draft Outreach</button></div><div id="o-out"></div>');
    const out = root.querySelector("#o-out");
    if (!creator.name) CF.ui.empty(out, "Select a creator first", "Research a creator, then return here.");
    root.querySelector("#o-go").addEventListener("click", async () => {
      const dossier = creator.dossier || {};
      const res = await V.into(out, () => CF.api.post("/api/v1/campaigns/outreach", {
        business_dna: biz.dna || {}, creator: { name: creator.name }, recent_content: dossier.recent_content || [],
        campaign_goal: root.querySelector("#o-goal").value, deliverables: root.querySelector("#o-deliv").value,
      }), { loading: "Writing drafts…" });
      if (!res) return; const d = res.data || res; const drafts = d.drafts || {};
      out.innerHTML = '<div class="cf-warnings"><div class="cf-warning"><span class="cf-warning__dot"></span>' + fmt.escapeHtml(d.note || "Drafts only — CollabForge never sends messages automatically.") + "</div></div>" +
        Object.entries(drafts).map(([k, v], i) => V.copyBlock("o-" + i, typeof v === "string" ? v : JSON.stringify(v, null, 2)).replace("Editable output", fmt.escapeHtml(k.replace(/_/g, " ")))).join("");
      V.wireCopy(out);
    });
  });

  // ── Contract Builder ──
  reg("contract", async (root) => {
    const biz = CF.state.get("business") || {}; const creator = CF.state.get("selectedCreator") || {};
    root.innerHTML = V.viewShell(V.sectionHead("Campaign", "Contract Builder", "An editable collaboration template. AI-generated for review — not legal advice.") + V.contextStrip() +
      '<div class="card card--pad view__section"><div class="field-row">' +
      '<div class="field"><label>Brand</label><input class="input" id="k-brand" value="' + fmt.escapeHtml(fmt.inputValue(biz.name)) + '"></div>' +
      '<div class="field"><label>Creator</label><input class="input" id="k-creator" value="' + fmt.escapeHtml(fmt.inputValue(creator.name)) + '"></div>' +
      '<div class="field"><label>Compensation</label><input class="input" id="k-comp" placeholder="₹150,000"></div>' +
      '<div class="field"><label>Deliverables</label><input class="input" id="k-deliv" placeholder="1 integrated video"></div></div>' +
      '<button class="btn btn--primary" id="k-go">Generate Contract Template</button></div><div id="k-out"></div>');
    const out = root.querySelector("#k-out");
    root.querySelector("#k-go").addEventListener("click", async () => {
      const fields = { brand: root.querySelector("#k-brand").value, creator: root.querySelector("#k-creator").value, compensation: root.querySelector("#k-comp").value, deliverables: root.querySelector("#k-deliv").value };
      const res = await V.into(out, () => CF.api.post("/api/v1/campaigns/contract", { fields }), { loading: "Drafting contract…" });
      if (!res) return; const d = res.data || res;
      out.innerHTML = '<p class="tiny muted view__section">' + fmt.escapeHtml(d.disclaimer || "AI-generated template for review. This is not legal advice.") + "</p>" +
        V.docBlock("k-md", d.markdown || "Contract generation unavailable.", "Contract template");
      V.wireCopy(out);
    });
  });

  // ── Campaign Room ──
  reg("room", async (root) => {
    root.innerHTML = V.viewShell(V.sectionHead("Workspace", "Campaign Room", "Everything you build is saved here.") + V.contextStrip() +
      '<div style="display:flex;gap:var(--space-2);margin-bottom:var(--space-5)"><button class="btn btn--primary" id="room-save">Save current context</button></div><div id="room-out"></div>');
    const out = root.querySelector("#room-out");
    async function load() {
      const res = await V.into(out, () => CF.api.get("/api/v1/campaigns"), { loading: "Loading campaigns…" });
      if (!res) return; const list = (res.data && res.data.campaigns) || res.campaigns || [];
      if (!list.length) { CF.ui.empty(out, "No campaigns saved yet", "Save the current context to start a Campaign Room."); return; }
      out.innerHTML = '<div class="grid grid--auto">' + list.map((c) => '<div class="card card--pad"><div class="card__title">' + fmt.escapeHtml(c.name || c.id) + "</div>" +
        '<div class="card__meta"><span class="chip">' + fmt.escapeHtml(c.status || "draft") + "</span>" + (c.selected_creator ? '<span class="chip">' + fmt.escapeHtml((c.selected_creator.name) || "creator") + "</span>" : "") + "</div>" +
        '<p class="tiny muted" style="margin-top:var(--space-2)">' + fmt.escapeHtml(fmt.relativeTime(c.updated_at || c.created_at)) + "</p></div>").join("") + "</div>";
    }
    root.querySelector("#room-save").addEventListener("click", async () => {
      const s = CF.state.get(); const creator = s.selectedCreator;
      const name = (s.business && s.business.name ? s.business.name + " × " : "") + (creator ? creator.name : "Campaign") + " " + new Date().toLocaleDateString();
      const res = await CF.api.post("/api/v1/campaigns", {
        name, business_dna: (s.business && s.business.dna) || {}, shortlist: s.shortlistedCreators,
        selected_creator: creator || null, dossier: (creator && creator.dossier) || null, status: "draft",
      });
      if (res && (res.success !== false)) { const rec = (res.data && res.data.campaign) || res.campaign; if (rec && rec.id) CF.state.set("campaignId", rec.id); CF.ui.toast("Saved to Campaign Room", "success"); load(); }
      else CF.ui.toast("Save failed", "error");
    });
    load();
  });
})();

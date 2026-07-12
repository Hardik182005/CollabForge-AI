/* CollabForge AI — Collab Autopilot (inside Brand Intelligence).
   Guided wizard (no giant dark form) → live 10-stage SSE → campaign pack. */
(function () {
  const CF = window.CF, V = CF.view, fmt = CF.fmt;

  const STEPS = ["Business", "Audience", "Goal", "Budget", "Creator strategy", "Review"];
  const STAGE_LABELS = {
    understand_business: ["Understanding business", "Universal Scraper on the public website"],
    build_campaign_dna: ["Building campaign DNA", "Structuring campaign parameters"],
    discover_creators: ["Discovering creators", "Anakin Search / provided candidates"],
    research_candidates: ["Researching candidates", "Live public evidence per creator"],
    score_and_shortlist: ["Scoring & shortlisting", "Explainable fit score"],
    build_roi_scenarios: ["Building ROI scenarios", "Editable assumptions"],
    draft_outreach: ["Drafting outreach", "Personalized, never auto-sent"],
    draft_campaign_brief: ["Drafting campaign brief", "Grounded in evidence"],
    draft_contract: ["Drafting contract", "Editable template — not legal advice"],
    generate_content_concept: ["Generating content concept", "From real recent titles"],
  };
  const STAGE_ORDER = Object.keys(STAGE_LABELS);

  CF.router.register("brand", "autopilot", async (root) => {
    const biz = CF.state.get("business") || {}; const sel = CF.state.get("selectedCreator");
    const data = {
      business_name: biz.name || "", website: biz.website || "", product: "", industry: "",
      goal: "", audience: "", geography: "India", language: "Hindi/English", budget: "",
      strategy: "auto", chips: sel && sel.name ? [sel.name] : [],
    };
    let step = 0;

    root.innerHTML = V.viewShell(
      V.sectionHead("Workspace", "Collab Autopilot", "From a business brief to a shortlist, outreach, brief and contract — one guided run.") +
      '<div class="card card--pad" id="wiz"></div><div id="ap-run"></div>');
    const wiz = root.querySelector("#wiz");
    const runArea = root.querySelector("#ap-run");

    function stepper() {
      return '<div class="segmented" style="margin-bottom:var(--space-6);flex-wrap:wrap">' +
        STEPS.map((s, i) => '<button class="' + (i === step ? "is-active" : "") + '" data-step="' + i + '">' + (i + 1) + ". " + fmt.escapeHtml(s) + "</button>").join("") + "</div>";
    }
    function field(label, key, ph, tag) {
      tag = tag || "input";
      const val = fmt.inputValue(data[key]);
      return '<div class="field"><label>' + label + "</label>" +
        (tag === "textarea" ? '<textarea class="textarea" data-k="' + key + '" placeholder="' + (ph || "") + '">' + fmt.escapeHtml(val) + "</textarea>"
          : '<input class="input" data-k="' + key + '" value="' + fmt.escapeHtml(val) + '" placeholder="' + (ph || "") + '">') + "</div>";
    }

    function body() {
      if (step === 0) return field("Business name", "business_name", "e.g. NovaPlay Electronics") + field("Website (for Universal Scraper)", "website", "https://…") + field("Product / service", "product", "New gaming smartphone");
      if (step === 1) return field("Target audience", "audience", "Hindi/English tech viewers in India") + '<div class="field-row">' + field("Geography", "geography", "India") + field("Language", "language", "Hindi/English") + "</div>" + field("Industry", "industry", "Consumer electronics");
      if (step === 2) return field("Campaign goal", "goal", "Launch awareness and preorders", "textarea");
      if (step === 3) return '<div class="field-row">' + field("Budget (₹)", "budget", "150000") + "</div><p class=\"hint\">Budget is used for ROI and outreach framing — it is an assumption you can edit.</p>";
      if (step === 4) return creatorStrategy();
      return review();
    }

    function creatorStrategy() {
      return '<div class="field"><label>How should Autopilot choose creators?</label>' +
        '<div class="segmented" id="strat" style="flex-wrap:wrap"><button data-s="auto" class="' + (data.strategy === "auto" ? "is-active" : "") + '">Discover automatically</button>' +
        '<button data-s="shortlist" class="' + (data.strategy === "shortlist" ? "is-active" : "") + '">Use shortlist</button>' +
        '<button data-s="manual" class="' + (data.strategy === "manual" ? "is-active" : "") + '">Enter manually</button></div></div>' +
        '<div class="field"><label>Candidate creators (up to 3)</label><div class="card__meta" id="chips"></div>' +
        '<div class="search-box" style="margin-top:var(--space-2)"><input class="input" id="chip-in" placeholder="Add a creator name and press Enter"><button class="btn btn--ghost" id="chip-add">Add</button></div></div>';
    }

    function review() {
      const rows = [["Business", data.business_name], ["Website", data.website || "—"], ["Product", data.product], ["Goal", data.goal], ["Audience", data.audience], ["Budget", data.budget ? fmt.formatCurrency(+data.budget, "INR") : "—"], ["Creators", data.chips.length ? data.chips.join(", ") : "auto-discover"]];
      return '<div class="table-wrap"><table class="cf-table"><tbody>' + rows.map((r) => '<tr><td class="row-strong">' + r[0] + "</td><td>" + fmt.escapeHtml(r[1] || "—") + "</td></tr>").join("") + "</tbody></table></div>";
    }

    function renderChips() {
      const el = wiz.querySelector("#chips"); if (!el) return;
      el.innerHTML = data.chips.map((c, i) => '<span class="chip chip--removable">' + fmt.escapeHtml(c) + ' <button data-rm="' + i + '">×</button></span>').join("") || '<span class="muted tiny">None yet — auto-discovery will be used.</span>';
      el.querySelectorAll("[data-rm]").forEach((b) => b.addEventListener("click", () => { data.chips.splice(+b.getAttribute("data-rm"), 1); renderChips(); }));
    }

    function render() {
      wiz.innerHTML = stepper() + '<div class="view__section">' + body() + "</div>" +
        '<div style="display:flex;justify-content:space-between;gap:var(--space-2)">' +
        '<button class="btn btn--ghost" id="prev"' + (step === 0 ? " disabled" : "") + ">Back</button>" +
        (step < STEPS.length - 1 ? '<button class="btn btn--primary" id="next">Next</button>' : '<button class="btn btn--primary" id="launch">Launch Autopilot</button>') + "</div>";
      // bind inputs
      wiz.querySelectorAll("[data-k]").forEach((el) => el.addEventListener("input", () => { data[el.getAttribute("data-k")] = el.value; }));
      wiz.querySelectorAll("[data-step]").forEach((b) => b.addEventListener("click", () => { save(); step = +b.getAttribute("data-step"); render(); }));
      const strat = wiz.querySelector("#strat");
      if (strat) strat.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => { data.strategy = b.getAttribute("data-s"); if (data.strategy === "shortlist") data.chips = CF.state.get("shortlistedCreators").map((c) => c.name).slice(0, 3); render(); }));
      const add = wiz.querySelector("#chip-add"), inEl = wiz.querySelector("#chip-in");
      if (add) {
        const addChip = () => { const v = inEl.value.trim(); if (v && data.chips.length < 3) { data.chips.push(v); inEl.value = ""; renderChips(); } };
        add.addEventListener("click", addChip);
        inEl.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); addChip(); } });
      }
      renderChips();
      const prev = wiz.querySelector("#prev"); if (prev) prev.addEventListener("click", () => { save(); step--; render(); });
      const next = wiz.querySelector("#next"); if (next) next.addEventListener("click", () => { save(); step++; render(); });
      const launch = wiz.querySelector("#launch"); if (launch) launch.addEventListener("click", run);
    }
    function save() { wiz.querySelectorAll("[data-k]").forEach((el) => { data[el.getAttribute("data-k")] = el.value; }); }

    // ── Run: stream the 10-stage autopilot ──
    async function run() {
      if (!data.business_name || !data.product || !data.goal) { CF.ui.toast("Business, product and goal are required", "error"); step = !data.business_name ? 0 : !data.product ? 0 : 2; render(); return; }
      CF.state.set("business", { name: data.business_name, website: data.website, dna: (biz.dna || {}) });
      const stageState = {}; STAGE_ORDER.forEach((s) => stageState[s] = { state: "idle", sub: STAGE_LABELS[s][1], ev: 0, provider: "" });
      let pack = null;
      renderStages(stageState);
      const payload = {
        business_name: data.business_name, website: data.website, product: data.product,
        industry: data.industry, goal: data.goal, audience: data.audience, geography: data.geography,
        language: data.language, budget: data.budget ? +data.budget : null,
        deliverables: "one integrated video segment",
        candidate_creators: data.strategy === "auto" ? [] : data.chips.slice(0, 3),
      };
      try {
        await CF.api.stream("/api/v1/autopilot/run", payload, (ev) => {
          if (ev.stage === "complete") { pack = ev.data || ev.pack || null; return; }
          const st = stageState[ev.stage]; if (!st) return;
          st.state = ev.status === "done" ? "complete" : ev.status === "partial" ? "partial" : ev.status === "failed" ? "failed" : "running";
          if (ev.message) st.sub = ev.message;
          if (ev.provider) st.provider = ev.provider;
          if (ev.evidence_count) st.ev = ev.evidence_count;
          // mark earlier running stages complete
          const idx = STAGE_ORDER.indexOf(ev.stage);
          STAGE_ORDER.forEach((s, i) => { if (i < idx && stageState[s].state === "running") stageState[s].state = "complete"; });
          renderStages(stageState);
        });
      } catch (e) {
        CF.ui.toast("Autopilot stream failed: " + e.message, "error");
      }
      STAGE_ORDER.forEach((s) => { if (stageState[s].state === "running") stageState[s].state = "complete"; });
      renderStages(stageState, pack);
      if (pack) CF.state.set("autopilotRun", { ranAt: Date.now(), selected: pack.selected });
    }

    function renderStages(stageState, pack) {
      let html = '<div class="cf-pipeline view__section" style="margin-top:var(--space-6)"><div class="cf-pipeline__flow">';
      STAGE_ORDER.forEach((s) => {
        const st = stageState[s]; const lab = STAGE_LABELS[s];
        html += '<div class="pl-node" data-state="' + st.state + '"><div class="pl-node__icon">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg></div>' +
          '<div class="pl-node__body"><div class="pl-node__title">' + fmt.escapeHtml(lab[0]) +
          '<span class="pl-node__status">' + ({ idle: "Ready", running: "Running", complete: "Done", partial: "Partial", failed: "Failed" }[st.state] || "") + "</span></div>" +
          '<div class="pl-node__sub">' + fmt.escapeHtml(st.sub) + "</div>" +
          (st.provider || st.ev ? '<div class="pl-node__stat">' + (st.provider ? "<span>" + CF.ui.sourceBadge(st.provider) + "</span>" : "") + (st.ev ? "<span>Evidence <b>" + fmt.formatNumber(st.ev) + "</b></span>" : "") + "</div>" : "") +
          "</div></div>";
      });
      html += "</div></div>";
      runArea.innerHTML = html + (pack ? packHtml(pack) : "");
      if (pack) V.wireCopy(runArea);
    }

    function packHtml(pack) {
      const sel = pack.selected || {}; const sl = pack.shortlist || [];
      let h = '<div class="pl-result view__section"><span class="eyebrow">Campaign Launch Pack</span>' +
        '<h3>Top pick: ' + fmt.escapeHtml(sel.name || "—") + "</h3>";
      if (sl.length) h += '<div class="table-wrap view__section"><table class="cf-table"><thead><tr><th>Creator</th><th class="num">Fit</th><th>Confidence</th><th class="num">Reach</th></tr></thead><tbody>' +
        sl.map((c) => '<tr><td class="row-strong">' + fmt.escapeHtml(c.name) + '</td><td class="num">' + fmt.safeText(c.fit, "—") + "</td><td>" + fmt.safeText(c.confidence, "—") + '</td><td class="num">' + fmt.formatCompactNumber(c.subscribers, "—") + "</td></tr>").join("") + "</tbody></table></div>";

      // ROI scenarios
      if (pack.roi && pack.roi.scenarios)
        h += '<div class="view__section"><span class="eyebrow">ROI scenarios</span>' + V.roiTable(pack.roi) + "</div>";

      // Outreach — all drafts, each labelled
      const drafts = (pack.outreach && pack.outreach.drafts) || {};
      const draftEntries = Object.entries(drafts).filter(([, v]) => !fmt.isEmpty(v));
      if (draftEntries.length) {
        h += '<div class="view__section"><span class="eyebrow">Outreach drafts</span>' +
          (pack.outreach.note ? '<p class="tiny muted">' + fmt.escapeHtml(pack.outreach.note) + "</p>" : "") +
          draftEntries.map(([k, v], i) => V.copyBlock("ap-o-" + i, typeof v === "string" ? v : JSON.stringify(v, null, 2))
            .replace("Editable output", fmt.escapeHtml(k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())))).join("") + "</div>";
      }

      // Campaign brief
      if (pack.brief) h += '<div class="view__section"><span class="eyebrow">Campaign brief</span>' + V.briefBlock(pack.brief) + "</div>";

      // Content concept
      const cc = pack.content_concept;
      if (cc && (cc.concept_title || cc.hook)) {
        h += '<div class="view__section"><span class="eyebrow">Content concept</span><div class="card card--pad doc-block">';
        if (cc.concept_title) h += "<h4>" + fmt.escapeHtml(cc.concept_title) + "</h4>";
        const cf2 = (label, v) => v ? "<p><strong>" + label + ":</strong> " + fmt.escapeHtml(v) + "</p>" : "";
        h += cf2("Format", cc.format) + cf2("Hook", cc.hook) + cf2("Integration", cc.integration_style) + cf2("CTA", cc.cta) + cf2("Disclosure", cc.disclosure);
        if (Array.isArray(cc.beats) && cc.beats.length) h += "<p><strong>Beats:</strong></p><ul>" + cc.beats.map((b) => "<li>" + fmt.escapeHtml(b) + "</li>").join("") + "</ul>";
        h += "</div></div>";
      }

      // Contract — rendered, not raw markdown
      if (pack.contract && pack.contract.markdown)
        h += '<div class="view__section">' + V.docBlock("ap-contract", pack.contract.markdown, "Contract template") + "</div>";

      if (pack.partial_failures && pack.partial_failures.length) h += CF.ui.warnings(pack.partial_failures.map((p) => ({ message: p })));
      h += '<div style="margin-top:var(--space-4)"><button class="btn btn--primary" id="ap-save">Save to Campaign Room</button></div></div>';
      setTimeout(() => { const b = runArea.querySelector("#ap-save"); if (b) b.addEventListener("click", async () => {
        const res = await CF.api.post("/api/v1/campaigns", { name: (pack.business_dna && pack.business_dna.business_name || data.business_name) + " Autopilot", business_dna: pack.business_dna || {}, shortlist: sl, selected_creator: sel, outreach: pack.outreach, contract: pack.contract, brief: pack.brief, roi: pack.roi, status: "draft" });
        if (res && res.success !== false) CF.ui.toast("Saved to Campaign Room", "success"); else CF.ui.toast("Save failed", "error");
      }); }, 0);
      return h;
    }

    render();
  });
})();

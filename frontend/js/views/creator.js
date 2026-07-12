/* CollabForge AI — Creator Studio views. Trend → Script → Voice → Reel connected. */
(function () {
  const CF = window.CF, V = CF.view, fmt = CF.fmt;
  const reg = (view, fn) => CF.router.register("creator", view, fn);

  // ── Trend Discovery ──
  reg("trends", async (root) => {
    root.innerHTML = V.viewShell(
      V.sectionHead("Intelligence", "Trend Discovery", "Live topics and coverage from Anakin Search — every trend is evidence-backed.") +
      '<div class="card card--pad view__section"><div class="filter-bar">' +
      '<input class="input" id="t-topic" placeholder="Search a topic e.g. AI productivity" style="flex:1;min-width:220px">' +
      '<select class="select" id="t-cat"><option value="all">All categories</option><option>Tech</option><option>AI</option><option>Creator Economy</option><option>Marketing</option><option>Finance</option></select>' +
      '<button class="btn btn--primary" id="t-go">Discover Trends</button></div></div>' +
      '<div id="t-results"></div>');
    const results = root.querySelector("#t-results");
    CF.ui.empty(results, "Search a topic to see live trends", "Nothing is pre-loaded — results come from live sources.");
    async function go() {
      const topic = root.querySelector("#t-topic").value.trim();
      const category = root.querySelector("#t-cat").value;
      const res = await V.into(results, () => CF.api.post("/api/v1/trends/discover", { topic, category, limit: 8 }), { loading: "Querying live sources…" });
      if (!res) return;
      const trends = (res.data && res.data.trends) || res.trends || [];
      if (!trends.length) { CF.ui.empty(results, "No live trends found", res.message || "Try a different topic."); return; }
      results.innerHTML = '<div class="grid grid--auto">' + trends.map((t, i) =>
        '<div class="card card--pad"><div class="card__head"><div class="card__title">' + fmt.escapeHtml(t.title) + "</div></div>" +
        (t.snippet ? '<p class="small">' + fmt.escapeHtml(String(t.snippet).slice(0, 160)) + "</p>" : "") +
        '<div class="card__meta">' + CF.ui.sourceBadge(t.data_method || "anakin_search") +
        (t.published_at ? '<span class="muted tiny">' + fmt.escapeHtml(fmt.relativeTime(t.published_at)) + "</span>" : '<span class="muted tiny">Live coverage</span>') +
        "</div>" +
        '<div style="margin-top:var(--space-4);display:flex;gap:var(--space-2)">' +
        (t.url ? '<a class="btn btn--ghost btn--sm" href="' + fmt.escapeHtml(t.url) + '" target="_blank" rel="noopener">Source</a>' : "") +
        '<button class="btn btn--primary btn--sm" data-use="' + i + '">Use Trend</button></div></div>').join("") + "</div>";
      results.querySelectorAll("[data-use]").forEach((b) => b.addEventListener("click", () => {
        CF.state.set("selectedTrend", trends[+b.getAttribute("data-use")]);
        CF.ui.toast("Trend selected — carried into Script Studio", "success");
        CF.router.navigate("creator", "scripts");
      }));
    }
    root.querySelector("#t-go").addEventListener("click", go);
  });

  reg("selected-trend", async (root) => {
    const t = CF.state.get("selectedTrend");
    if (!t) { root.innerHTML = V.viewShell(V.sectionHead("Intelligence", "Selected Trend", "") + CF.ui.spinner ? "" : ""); root.querySelector(".view").innerHTML += ""; CF.ui.empty(root.querySelector(".view"), "No trend selected", "Pick one in Trend Discovery."); return; }
    root.innerHTML = V.viewShell(V.sectionHead("Intelligence", "Selected Trend", "") + V.contextStrip() +
      '<div class="card card--pad"><h3>' + fmt.escapeHtml(t.title) + "</h3>" +
      (t.snippet ? "<p>" + fmt.escapeHtml(t.snippet) + "</p>" : "") +
      '<div class="card__meta">' + CF.ui.sourceBadge(t.data_method || "anakin_search") +
      (t.url ? '<a class="btn btn--link" href="' + fmt.escapeHtml(t.url) + '" target="_blank" rel="noopener">Open source</a>' : "") + "</div>" +
      '<div style="margin-top:var(--space-5);display:flex;gap:var(--space-2)"><button class="btn btn--primary" id="to-script">Write a script from this trend</button></div></div>');
    root.querySelector("#to-script").addEventListener("click", () => CF.router.navigate("creator", "scripts"));
  });

  // ── Script Studio ──
  reg("scripts", async (root) => {
    const trend = CF.state.get("selectedTrend");
    root.innerHTML = V.viewShell(
      V.sectionHead("Create", "Script Studio", "Hook, story, value and CTA for 15 / 30 / 60-second video.") + V.contextStrip() +
      '<div class="card card--pad view__section"><div class="field"><label>Topic</label>' +
      '<input class="input" id="s-topic" value="' + fmt.escapeHtml(trend ? trend.title : "") + '" placeholder="What is the video about?"></div>' +
      '<div class="field-row"><div class="field"><label>Length</label><select class="select" id="s-dur"><option value="15">15 seconds</option><option value="30" selected>30 seconds</option><option value="60">60 seconds</option></select></div>' +
      '<div class="field"><label>Style</label><select class="select" id="s-style"><option>hooks</option><option>storytelling</option><option>educational</option><option>listicle</option></select></div></div>' +
      '<button class="btn btn--primary" id="s-go">Generate Script</button></div><div id="s-out"></div>');
    const out = root.querySelector("#s-out");
    root.querySelector("#s-go").addEventListener("click", async () => {
      const topic = root.querySelector("#s-topic").value.trim();
      if (!topic) return;
      const res = await V.into(out, () => CF.api.post("/api/v1/content/generate-script", { topic, duration: +root.querySelector("#s-dur").value, style: root.querySelector("#s-style").value }), { loading: "Writing script…" });
      if (!res) return;
      const d = res.data || res;
      CF.state.set("selectedScript", d);
      const part = (label, val) => val ? '<div class="view__section"><span class="eyebrow">' + label + '</span><p style="color:var(--color-text-primary)">' + fmt.escapeHtml(val) + "</p></div>" : "";
      out.innerHTML = '<div class="card card--pad">' + part("Hook", d.hook) + part("Story", d.story) + part("Value", d.insight || d.main_value) + part("CTA", d.cta) +
        (d.virality_tips && d.virality_tips.length ? '<div class="view__section"><span class="eyebrow">Notes</span><ul>' + d.virality_tips.map((x) => "<li>• " + fmt.escapeHtml(x) + "</li>").join("") + "</ul></div>" : "") +
        '<div style="display:flex;gap:var(--space-2)"><button class="btn btn--ghost btn--sm" id="s-voice">Send to Voice Studio</button><button class="btn btn--ghost btn--sm" id="s-reel">Send to Reel Builder</button></div></div>';
      out.querySelector("#s-voice").addEventListener("click", () => CF.router.navigate("creator", "voice"));
      out.querySelector("#s-reel").addEventListener("click", () => CF.router.navigate("creator", "reel"));
    });
  });

  // ── Hook Lab ──
  reg("hooks", async (root) => {
    const trend = CF.state.get("selectedTrend");
    root.innerHTML = V.viewShell(V.sectionHead("Create", "Hook Lab", "Six distinct hooks with the mechanism and why each may work.") +
      '<div class="card card--pad view__section"><div class="filter-bar"><input class="input" id="h-topic" style="flex:1;min-width:220px" value="' + fmt.escapeHtml(trend ? trend.title : "") + '" placeholder="Topic">' +
      '<button class="btn btn--primary" id="h-go">Generate 6 Hooks</button></div></div><div id="h-out"></div>');
    const out = root.querySelector("#h-out");
    root.querySelector("#h-go").addEventListener("click", async () => {
      const topic = root.querySelector("#h-topic").value.trim(); if (!topic) return;
      const res = await V.into(out, () => CF.api.post("/api/v1/content/hooks", { topic }), { loading: "Writing hooks…" });
      if (!res) return;
      const hooks = (res.data && res.data.hooks) || res.hooks || [];
      if (!hooks.length) { CF.ui.empty(out, "No hooks generated", "An LLM provider is required."); return; }
      out.innerHTML = '<div class="grid grid--2">' + hooks.map((hk) =>
        '<div class="card card--pad"><p style="font-weight:600;color:var(--color-text-primary)">' + fmt.escapeHtml(hk.text || hk.hook) + "</p>" +
        '<div class="card__meta"><span class="chip">' + fmt.escapeHtml(hk.mechanism || hk.style || "hook") + "</span></div>" +
        (hk.why_it_works ? '<p class="small muted" style="margin-top:var(--space-2)">' + fmt.escapeHtml(hk.why_it_works) + "</p>" : "") + "</div>").join("") + "</div>";
    });
  });

  // ── Social Content Pack ──
  reg("social", async (root) => {
    const trend = CF.state.get("selectedTrend");
    root.innerHTML = V.viewShell(V.sectionHead("Create", "Social Content Pack", "YouTube, Instagram, LinkedIn, hashtags, thumbnail text and CTA.") +
      '<div class="card card--pad view__section"><div class="filter-bar"><input class="input" id="p-topic" style="flex:1;min-width:220px" value="' + fmt.escapeHtml(trend ? trend.title : "") + '" placeholder="Topic">' +
      '<button class="btn btn--primary" id="p-go">Generate Pack</button></div></div><div id="p-out"></div>');
    const out = root.querySelector("#p-out");
    root.querySelector("#p-go").addEventListener("click", async () => {
      const topic = root.querySelector("#p-topic").value.trim(); if (!topic) return;
      const res = await V.into(out, () => CF.api.post("/api/v1/content/pack", { topic }), { loading: "Building content pack…" });
      if (!res) return;
      const p = (res.data && res.data.pack) || res.pack; if (!p) { CF.ui.empty(out, "Not generated", "An LLM provider is required."); return; }
      const row = (k, v) => v ? '<div class="view__section"><span class="eyebrow">' + k + '</span><p style="color:var(--color-text-primary)">' + fmt.escapeHtml(Array.isArray(v) ? v.join("  ") : v) + "</p></div>" : "";
      out.innerHTML = '<div class="card card--pad">' + row("YouTube title", p.youtube_title) + row("YouTube description", p.youtube_description) +
        row("Instagram caption", p.instagram_caption) + row("LinkedIn post", p.linkedin_post) + row("Hashtags", p.hashtags) +
        row("Thumbnail text", p.thumbnail_text) + row("Pinned comment", p.pinned_comment) + row("CTA", p.cta) + "</div>";
    });
  });

  // ── Voice Studio ──
  reg("voice", async (root) => {
    const script = CF.state.get("selectedScript");
    const defaultText = script ? [script.hook, script.story, script.insight, script.cta].filter(Boolean).join(" ") : "";
    root.innerHTML = V.viewShell(V.sectionHead("Media", "Voice Studio", "ElevenLabs voiceover for your script. No autoplay.") + V.contextStrip() +
      '<div id="v-body"></div>');
    const body = root.querySelector("#v-body");
    CF.ui.loading(body, "Loading voices…");
    const vres = await CF.api.get("/api/v1/media/voices");
    const voices = (vres.data && vres.data.voices) || [];
    if (!voices.length) { body.innerHTML = V.unavailableNotice("ElevenLabs is not configured on the server, so voice generation is disabled."); return; }
    body.innerHTML = '<div class="card card--pad"><div class="field"><label>Script</label><textarea class="textarea" id="v-text" placeholder="Paste or edit narration">' + fmt.escapeHtml(defaultText) + "</textarea></div>" +
      '<div class="field"><label>Voice</label><select class="select" id="v-voice">' + voices.map((vc) => '<option value="' + fmt.escapeHtml(vc.voice_id || vc.id) + '">' + fmt.escapeHtml(vc.name || vc.voice_id) + "</option>").join("") + "</select></div>" +
      '<button class="btn btn--primary" id="v-go">Generate Voiceover</button><div id="v-out" style="margin-top:var(--space-5)"></div></div>';
    root.querySelector("#v-go").addEventListener("click", async () => {
      const text = root.querySelector("#v-text").value.trim(); if (!text) return;
      const out = root.querySelector("#v-out");
      const res = await V.into(out, () => CF.api.post("/api/v1/media/voice", { script_text: text, voice_id: root.querySelector("#v-voice").value }), { loading: "Generating audio…" });
      if (!res) return;
      const b64 = res.data && res.data.audioBase64;
      if (!b64) { CF.ui.error(out, "No audio returned", (res.error && res.error.message) || ""); return; }
      out.innerHTML = '<audio controls src="data:audio/mpeg;base64,' + b64 + '"></audio>' +
        '<a class="btn btn--ghost btn--sm" style="margin-top:var(--space-3)" download="voiceover.mp3" href="data:audio/mpeg;base64,' + b64 + '">Download MP3</a>';
    });
  });

  // ── Reel Builder ──
  reg("reel", async (root) => {
    const script = CF.state.get("selectedScript");
    const basis = script ? [script.hook, script.story, script.insight, script.cta].filter(Boolean).join(" ") : "";
    root.innerHTML = V.viewShell(V.sectionHead("Media", "Reel Builder", "AI-assisted reel composition — storyboard, prompts, narration and captions.") + V.contextStrip() +
      '<div class="card card--pad view__section"><div class="field"><label>Basis (script or topic)</label><textarea class="textarea" id="r-text" placeholder="Script or topic">' + fmt.escapeHtml(basis) + "</textarea></div>" +
      '<button class="btn btn--primary" id="r-go">Build Storyboard</button></div><div id="r-out"></div>');
    const out = root.querySelector("#r-out");
    root.querySelector("#r-go").addEventListener("click", async () => {
      const t = root.querySelector("#r-text").value.trim(); if (!t) return;
      const res = await V.into(out, () => CF.api.post("/api/v1/media/reel", { script_text: t, render_scenes: 3 }), { loading: "Generating reel frames (AI images)… this can take ~30s" });
      if (!res) return;
      const data = res.data || {}; const board = data.storyboard || {}; const scenes = board.scenes || [];
      out.innerHTML = '<div class="card card--pad"><div class="card__head"><span class="eyebrow">AI-assisted reel · ' + fmt.formatNumber(data.framesGenerated, "0") + ' frames generated</span></div>' +
        '<div class="cf-warnings"><div class="cf-warning"><span class="cf-warning__dot"></span>' + fmt.escapeHtml(data.renderNote || "AI-assisted composition.") + "</div></div>" +
        '<div class="grid grid--auto">' + scenes.map((s) => '<div class="card card--pad" style="padding:var(--space-3)">' +
          (s.imageBase64 ? '<img src="data:image/png;base64,' + s.imageBase64 + '" alt="scene ' + fmt.escapeHtml(s.n) + '" style="width:100%;border-radius:var(--radius-sm);aspect-ratio:1;object-fit:cover;margin-bottom:var(--space-2)">'
            : '<div class="cf-state" style="padding:var(--space-5);margin-bottom:var(--space-2)"><span class="muted small">Frame not rendered</span></div>') +
          '<div class="evidence__title">Scene ' + fmt.escapeHtml(s.n) + ' · ' + fmt.escapeHtml(fmt.formatDuration((s.durationSec || 0) * 1000, "")) + "</div>" +
          '<p class="small"><strong>Narration:</strong> ' + fmt.escapeHtml(s.narration) + "</p>" +
          (s.caption ? '<p class="tiny muted">' + fmt.escapeHtml(s.caption) + "</p>" : "") +
          (s.imageBase64 ? '<a class="btn btn--ghost btn--sm" style="margin-top:var(--space-2)" download="scene-' + fmt.escapeHtml(s.n) + '.png" href="data:image/png;base64,' + s.imageBase64 + '">Download frame</a>' : "") +
          "</div>").join("") + "</div></div>";
    });
  });

  // ── Virality Evaluation (clean forecast, no fake view counts) ──
  reg("virality", async (root) => {
    const script = CF.state.get("selectedScript");
    const text = script ? [script.hook, script.story, script.insight, script.cta].filter(Boolean).join(" ") : "";
    root.innerHTML = V.viewShell(V.sectionHead("Analysis", "Virality Evaluation", "A heuristic forecast with stated reasoning — not a measured accuracy claim.") +
      '<div class="card card--pad view__section"><div class="field"><label>Script text</label><textarea class="textarea" id="e-text" placeholder="Paste your script">' + fmt.escapeHtml(text) + "</textarea></div>" +
      '<div class="field"><label>Platform</label><select class="select" id="e-plat"><option>instagram</option><option>youtube</option><option>tiktok</option><option>linkedin</option></select></div>' +
      '<button class="btn btn--primary" id="e-go">Evaluate</button></div><div id="e-out"></div>');
    const out = root.querySelector("#e-out");
    root.querySelector("#e-go").addEventListener("click", async () => {
      const t = root.querySelector("#e-text").value.trim(); if (!t) return;
      const res = await V.into(out, () => CF.api.post("/api/v1/virality/predict", { script_text: t, platform: root.querySelector("#e-plat").value }), { loading: "Assessing…" });
      if (!res) return;
      const d = res.data || res;
      if (d.status === "unavailable") { CF.ui.empty(out, "Not available", d.message); return; }
      const bar = (label, v) => '<div class="score-bar__label"><span>' + label + "</span><span>" + fmt.safeText(v, "—") + "</span></div><div class=\"score-bar__track\"><div class=\"score-bar__fill\" style=\"width:" + (typeof v === "number" ? Math.max(0, Math.min(100, v)) : 0) + "%\"></div></div>";
      out.innerHTML = '<div class="card card--pad"><div class="card__head"><div class="stat"><div class="stat__value">' + fmt.safeText(d.virality_score, "—") + '</div><div class="stat__label">Score · grade ' + fmt.safeText(d.grade, "—") + "</div></div>" + CF.ui.confidenceChip(d.confidence) + "</div>" +
        bar("Hook strength", d.hook_strength) + bar("Novelty", d.content_novelty) + bar("Platform fit", d.platform_fit) +
        (d.explanation ? '<p style="margin-top:var(--space-4)">' + fmt.escapeHtml(d.explanation) + "</p>" : "") +
        '<p class="small muted">' + fmt.escapeHtml(d.label || "Heuristic forecast — not a measured metric.") + "</p></div>";
    });
  });

  // ── Saved Content ──
  reg("saved", async (root) => {
    const s = CF.state.get();
    const items = [];
    if (s.selectedTrend) items.push({ k: "Trend", v: s.selectedTrend.title });
    if (s.selectedScript) items.push({ k: "Script", v: s.selectedScript.hook });
    root.innerHTML = V.viewShell(V.sectionHead("Analysis", "Saved Content", "Context carried in this session.") +
      (items.length ? '<div class="grid grid--auto">' + items.map((i) => '<div class="card card--pad"><span class="eyebrow">' + i.k + '</span><p style="color:var(--color-text-primary)">' + fmt.escapeHtml(String(i.v || "").slice(0, 120)) + "</p></div>").join("") + "</div>"
        : "") );
    if (!items.length) CF.ui.empty(root.querySelector(".view"), "Nothing saved yet", "Select a trend or generate a script.");
  });
})();

/* CollabForge AI — shared view helpers. */
(function (root) {
  const CF = root.CF = root.CF || {};
  const fmt = CF.fmt;

  function h(html) { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstChild; }

  function viewShell(inner) {
    return '<div class="view">' + inner + "</div>";
  }

  function sectionHead(eyebrow, title, sub) {
    return '<div class="section-head"><span class="eyebrow">' + fmt.escapeHtml(eyebrow) + "</span>" +
      "<h2>" + fmt.escapeHtml(title) + "</h2>" + (sub ? '<p class="lead">' + fmt.escapeHtml(sub) + "</p>" : "") + "</div>";
  }

  // Context strip: what's carried across views (creator / campaign / trend).
  function contextStrip() {
    const s = CF.state.get();
    const bits = [];
    if (s.selectedCreator) bits.push("Creator: <strong>" + fmt.escapeHtml(s.selectedCreator.name || s.selectedCreator.title || "selected") + "</strong>");
    if (s.selectedTrend) bits.push("Trend: <strong>" + fmt.escapeHtml((s.selectedTrend.title || "").slice(0, 48)) + "</strong>");
    if (s.business) bits.push("Business: <strong>" + fmt.escapeHtml(s.business.name || "set") + "</strong>");
    if (s.campaignId) bits.push("Campaign: <strong>" + fmt.escapeHtml(s.campaignId) + "</strong>");
    if (!bits.length) return "";
    return '<div class="context-strip">' + bits.join('<span class="muted">·</span>') + "</div>";
  }

  // Run an async backend call into a target element with loading/error handling.
  async function into(el, fn, opts) {
    opts = opts || {};
    CF.ui.loading(el, opts.loading || "Working…");
    try {
      const res = await fn();
      if (res && res.success === false) {
        CF.ui.error(el, (res.error && res.error.message) || "Request failed.", res.error && res.error.code);
        return null;
      }
      return res;
    } catch (e) {
      CF.ui.error(el, "Unexpected error.", e.message);
      return null;
    }
  }

  function evidenceList(list) {
    if (!list || !list.length) return '<p class="muted small">No evidence records available.</p>';
    return list.map((e) =>
      '<div class="evidence"><div class="evidence__title">' +
      (e.url ? '<a href="' + fmt.escapeHtml(e.url) + '" target="_blank" rel="noopener">' + fmt.escapeHtml(e.title) + "</a>" : fmt.escapeHtml(e.title)) +
      "</div>" + (e.snippet ? '<div class="evidence__snippet">' + fmt.escapeHtml(String(e.snippet).slice(0, 180)) + "</div>" : "") +
      '<div class="evidence__meta">' + CF.ui.sourceBadge(e.provider || e.data_method, e.confidence) +
      (e.publishedAt || e.published_at ? '<span class="muted tiny">' + fmt.escapeHtml(fmt.relativeTime(e.publishedAt || e.published_at)) + "</span>" : "") +
      "</div></div>").join("");
  }

  // Missing-data-safe copyable text block (contracts, outreach, briefs).
  function copyBlock(id, text) {
    return '<div class="card card--pad"><div class="card__head"><span class="eyebrow">Editable output</span>' +
      '<button class="btn btn--ghost btn--sm" data-copy="' + id + '">Copy</button></div>' +
      '<textarea class="textarea" id="' + id + '" style="min-height:260px">' + fmt.escapeHtml(text) + "</textarea></div>";
  }

  // Rendered document block: shows formatted markdown (contracts, briefs,
  // concepts) instead of raw ## / ** — with a Copy button that copies the
  // original markdown from a hidden field.
  function docBlock(id, markdown, label) {
    const raw = fmt.isEmpty(markdown) ? "" : (typeof markdown === "string" ? markdown : fmt.safeText(markdown, ""));
    const html = fmt.renderMarkdown(raw);
    return '<div class="card card--pad doc-block"><div class="card__head"><span class="eyebrow">' + fmt.escapeHtml(label || "Document") + "</span>" +
      '<button class="btn btn--ghost btn--sm" data-copyraw="' + id + '">Copy</button></div>' +
      '<div class="doc-block__body">' + (html || '<p class="muted">No content.</p>') + "</div>" +
      '<textarea id="' + id + '-raw" hidden>' + fmt.escapeHtml(raw) + "</textarea></div>";
  }

  // ROI scenario table (worst / base / best). Renders the nested structure
  // the backend returns — never drops the scenarios object.
  function roiTable(roi) {
    if (!roi || !roi.scenarios) return '<p class="muted small">No ROI scenario available.</p>';
    const cur = roi.currency || "INR";
    const s = roi.scenarios;
    const cols = [["worst", "Worst"], ["base", "Base"], ["best", "Best"]].filter((c) => s[c[0]]);
    const metrics = [
      ["impressions", "Impressions", "num"], ["engagements", "Engagements", "num"],
      ["clicks", "Clicks", "num"], ["conversions", "Conversions", "num"],
      ["revenue", "Revenue", "cur"], ["roas", "ROAS", "x"],
    ];
    let h = '<div class="table-wrap"><table class="cf-table"><thead><tr><th>Metric</th>' +
      cols.map((c) => '<th class="num">' + c[1] + "</th>").join("") + "</tr></thead><tbody>";
    metrics.forEach((m) => {
      h += '<tr><td class="row-strong">' + m[1] + "</td>" + cols.map((c) => {
        const v = s[c[0]] ? s[c[0]][m[0]] : null;
        const disp = m[2] === "cur" ? fmt.formatCurrency(v, cur, "—")
          : m[2] === "x" ? (fmt.isEmpty(v) ? "—" : v + "×")
          : fmt.formatNumber(v, "—");
        return '<td class="num">' + disp + "</td>";
      }).join("") + "</tr>";
    });
    h += "</tbody></table></div>";
    h += '<p class="tiny muted" style="margin-top:var(--space-3)">' + fmt.escapeHtml(roi.label || "Scenario simulation with editable assumptions — not guaranteed revenue.") + "</p>";
    if (!fmt.isEmpty(roi.break_even_conversion_rate_pct))
      h += '<p class="tiny muted">Break-even conversion rate: <b>' + fmt.escapeHtml(roi.break_even_conversion_rate_pct) + "%</b></p>";
    return h;
  }

  // Structured campaign brief (object of labelled sections) → readable list.
  function briefBlock(brief) {
    const b = (brief && brief.brief) || brief || {};
    if (!b || typeof b !== "object") return "";
    const rows = Object.entries(b).filter(([, v]) => !fmt.isEmpty(v)).map(([k, v]) => {
      const label = k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
      const val = Array.isArray(v)
        ? "<ul>" + v.map((x) => "<li>" + fmt.escapeHtml(typeof x === "object" ? fmt.safeText(x) : x) + "</li>").join("") + "</ul>"
        : "<p>" + fmt.escapeHtml(v) + "</p>";
      return '<div class="view__section"><span class="eyebrow">' + fmt.escapeHtml(label) + "</span>" + val + "</div>";
    });
    return '<div class="card card--pad doc-block">' + (rows.join("") || '<p class="muted">No brief content.</p>') + "</div>";
  }

  function wireCopy(container) {
    container.querySelectorAll("[data-copy]").forEach((b) => b.addEventListener("click", () => {
      const t = container.querySelector("#" + b.getAttribute("data-copy"));
      if (t) { navigator.clipboard.writeText(t.value).then(() => CF.ui.toast("Copied", "success")); }
    }));
    container.querySelectorAll("[data-copyraw]").forEach((b) => b.addEventListener("click", () => {
      const t = container.querySelector("#" + b.getAttribute("data-copyraw") + "-raw");
      if (t) { navigator.clipboard.writeText(t.value).then(() => CF.ui.toast("Copied", "success")); }
    }));
  }

  // Standard capability-gated notice.
  function unavailableNotice(reason) {
    return '<div class="cf-state"><h4>Needs a provider key</h4><p>' + fmt.escapeHtml(reason || "Add the provider key on the server to enable this.") + "</p></div>";
  }

  CF.view = { h, viewShell, sectionHead, contextStrip, into, evidenceList, copyBlock, docBlock, roiTable, briefBlock, wireCopy, unavailableNotice };
})(window);

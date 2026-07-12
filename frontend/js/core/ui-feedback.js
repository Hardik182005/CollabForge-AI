/* CollabForge AI — shared loading / empty / error / toast primitives (spec §26). */
(function (root) {
  const CF = root.CF = root.CF || {};
  const esc = () => CF.fmt.escapeHtml;

  function spinner(label) {
    return '<div class="cf-loading" role="status" aria-live="polite">' +
      '<span class="cf-spinner" aria-hidden="true"></span>' +
      '<span>' + CF.fmt.escapeHtml(label || "Loading…") + "</span></div>";
  }

  function loading(el, label) { if (el) el.innerHTML = spinner(label); }

  function empty(el, title, sub) {
    if (!el) return;
    el.innerHTML = '<div class="cf-state cf-state--empty"><h4>' + CF.fmt.escapeHtml(title || "Nothing yet") +
      "</h4>" + (sub ? "<p>" + CF.fmt.escapeHtml(sub) + "</p>" : "") + "</div>";
  }

  function error(el, title, detail, onRetry) {
    if (!el) return;
    el.innerHTML = '<div class="cf-state cf-state--error"><h4>' + CF.fmt.escapeHtml(title || "Something went wrong") +
      "</h4>" + (detail ? '<p class="mono small">' + CF.fmt.escapeHtml(detail) + "</p>" : "") +
      (onRetry ? '<button class="btn btn--ghost cf-retry">Try again</button>' : "") + "</div>";
    if (onRetry) { const b = el.querySelector(".cf-retry"); if (b) b.addEventListener("click", onRetry); }
  }

  function warnings(list) {
    if (!list || !list.length) return "";
    return '<div class="cf-warnings">' + list.map((w) =>
      '<div class="cf-warning"><span class="cf-warning__dot"></span>' +
      CF.fmt.escapeHtml(w.message || w.code || "Partial result") + "</div>").join("") + "</div>";
  }

  let toastHost = null;
  function toast(message, kind) {
    if (!toastHost) {
      toastHost = document.createElement("div");
      toastHost.className = "cf-toast-host";
      document.body.appendChild(toastHost);
    }
    const t = document.createElement("div");
    t.className = "cf-toast cf-toast--" + (kind || "info");
    t.textContent = message;
    toastHost.appendChild(t);
    requestAnimationFrame(() => t.classList.add("is-in"));
    setTimeout(() => { t.classList.remove("is-in"); setTimeout(() => t.remove(), 300); }, 3200);
  }

  // Source / provider badge used consistently everywhere (Wire/Scraper/Search).
  function sourceBadge(provider, confidence) {
    const map = {
      anakin_wire: { label: "Anakin Wire", cls: "wire" },
      anakin_scrape: { label: "Universal Scraper", cls: "scrape" },
      anakin_search: { label: "Anakin Search", cls: "search" },
      provider_api: { label: "Official API", cls: "api" },
      heuristic: { label: "Estimated", cls: "est" },
    };
    const m = map[provider] || { label: provider || "Source", cls: "api" };
    const conf = confidence ? '<span class="cf-badge__conf">' + CF.fmt.escapeHtml(confidence) + "</span>" : "";
    return '<span class="cf-badge cf-badge--' + m.cls + '">' + CF.fmt.escapeHtml(m.label) + conf + "</span>";
  }

  function confidenceChip(confidence) {
    const c = CF.fmt.formatConfidence(confidence);
    return '<span class="cf-conf cf-conf--' + c.level + '">' + CF.fmt.escapeHtml(c.label) + "</span>";
  }

  CF.ui = { spinner, loading, empty, error, warnings, toast, sourceBadge, confidenceChip };
})(window);

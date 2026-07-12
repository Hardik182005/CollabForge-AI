/* CollabForge AI — safe formatters (spec §25).
   No rendered page may ever contain undefined / null / NaN / [object Object]. */
(function (root) {
  const UNAVAILABLE = "—";

  function isEmpty(v) {
    return v === undefined || v === null || v === "" ||
      (typeof v === "number" && Number.isNaN(v));
  }

  function safeText(v, fallback) {
    if (isEmpty(v)) return fallback === undefined ? UNAVAILABLE : fallback;
    if (typeof v === "object") {
      try { return JSON.stringify(v); } catch (_) { return fallback || UNAVAILABLE; }
    }
    return String(v);
  }

  // Escape ONLY — empty/null render as empty string, never the "unavailable"
  // fallback. Use safeText()/formatters explicitly when you want a fallback.
  function escapeHtml(v) {
    if (v === undefined || v === null) return "";
    if (typeof v === "object") { try { v = JSON.stringify(v); } catch (_) { return ""; } }
    return String(v).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function formatNumber(v, fallback) {
    const n = typeof v === "string" ? Number(v.replace(/,/g, "")) : v;
    if (isEmpty(n) || typeof n !== "number" || Number.isNaN(n)) return fallback || UNAVAILABLE;
    return n.toLocaleString("en-US");
  }

  function formatCompactNumber(v, fallback) {
    const n = typeof v === "string" ? Number(v.replace(/,/g, "")) : v;
    if (isEmpty(n) || typeof n !== "number" || Number.isNaN(n)) return fallback || UNAVAILABLE;
    const abs = Math.abs(n);
    if (abs >= 1e9) return (n / 1e9).toFixed(abs >= 1e10 ? 0 : 1).replace(/\.0$/, "") + "B";
    if (abs >= 1e6) return (n / 1e6).toFixed(abs >= 1e7 ? 0 : 1).replace(/\.0$/, "") + "M";
    if (abs >= 1e3) return (n / 1e3).toFixed(abs >= 1e4 ? 0 : 1).replace(/\.0$/, "") + "K";
    return String(n);
  }

  function formatPercent(v, fallback) {
    if (isEmpty(v) || typeof v !== "number" || Number.isNaN(v)) return fallback || UNAVAILABLE;
    return (v <= 1 && v > 0 ? v * 100 : v).toFixed(0) + "%";
  }

  function formatCurrency(v, currency, fallback) {
    const n = typeof v === "string" ? Number(v.replace(/[,₹$]/g, "")) : v;
    if (isEmpty(n) || typeof n !== "number" || Number.isNaN(n)) return fallback || UNAVAILABLE;
    try {
      return new Intl.NumberFormat("en-IN", {
        style: "currency", currency: currency || "INR", maximumFractionDigits: 0,
      }).format(n);
    } catch (_) { return (currency === "USD" ? "$" : "₹") + formatNumber(n); }
  }

  function formatDate(v, fallback) {
    if (isEmpty(v)) return fallback || UNAVAILABLE;
    const d = new Date(v);
    if (Number.isNaN(d.getTime())) return safeText(v, fallback);
    return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  }

  function formatDuration(ms, fallback) {
    if (isEmpty(ms) || typeof ms !== "number" || Number.isNaN(ms)) return fallback || UNAVAILABLE;
    if (ms < 1000) return ms + "ms";
    const s = ms / 1000;
    if (s < 60) return s.toFixed(s < 10 ? 1 : 0) + "s";
    return Math.floor(s / 60) + "m " + Math.round(s % 60) + "s";
  }

  function formatMetric(v, opts) {
    opts = opts || {};
    if (isEmpty(v)) return opts.fallback || UNAVAILABLE;
    if (opts.compact) return formatCompactNumber(v, opts.fallback);
    if (opts.percent) return formatPercent(v, opts.fallback);
    if (opts.currency) return formatCurrency(v, opts.currency, opts.fallback);
    return formatNumber(v, opts.fallback);
  }

  function formatConfidence(v) {
    const c = safeText(v, "").toLowerCase();
    if (c === "high") return { label: "High confidence", level: "high" };
    if (c === "medium") return { label: "Medium confidence", level: "medium" };
    if (c === "low") return { label: "Low confidence", level: "low" };
    return { label: "Confidence pending", level: "unknown" };
  }

  // For prefilling <input> values: never surface placeholder junk as a real value.
  const _JUNK = new Set(["unavailable", "—", "null", "undefined", "nan", "[object object]", "on request", "confidence pending"]);
  function inputValue(v) {
    if (isEmpty(v)) return "";
    return _JUNK.has(String(v).trim().toLowerCase()) ? "" : String(v);
  }

  // Inline markdown → HTML on an already-raw string (escapes internally).
  function _inlineMd(raw) {
    let s = escapeHtml(raw);
    return s
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/__([^_]+)__/g, "<strong>$1</strong>")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>")
      .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
        '<a href="$2" target="_blank" rel="noopener">$1</a>');
  }

  // Minimal, injection-safe markdown → HTML (headings, lists, blockquote,
  // hr, bold/italic/code). Used to render contracts, briefs, concepts —
  // never leave raw ## / ** on screen.
  function renderMarkdown(md) {
    if (isEmpty(md)) return "";
    const src = typeof md === "string" ? md : safeText(md, "");
    const lines = src.split(/\r?\n/);
    const out = [];
    let listType = null, para = [];
    const closeList = () => { if (listType) { out.push("</" + listType + ">"); listType = null; } };
    const flushPara = () => { if (para.length) { out.push("<p>" + _inlineMd(para.join(" ")) + "</p>"); para = []; } };
    for (const raw of lines) {
      const line = raw.replace(/\s+$/, "");
      let m;
      if (!line.trim()) { flushPara(); closeList(); continue; }
      if ((m = line.match(/^\s*(#{1,6})\s+(.*)$/))) {
        flushPara(); closeList();
        const lvl = Math.min(m[1].length + 1, 6); // shift: # → h2 (page owns h1)
        out.push("<h" + lvl + ">" + _inlineMd(m[2]) + "</h" + lvl + ">");
      } else if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) {
        flushPara(); closeList(); out.push("<hr>");
      } else if ((m = line.match(/^\s*>\s?(.*)$/))) {
        flushPara(); closeList();
        out.push("<blockquote>" + _inlineMd(m[1]) + "</blockquote>");
      } else if ((m = line.match(/^\s*[-*+]\s+(.*)$/))) {
        flushPara(); if (listType !== "ul") { closeList(); out.push("<ul>"); listType = "ul"; }
        out.push("<li>" + _inlineMd(m[1]) + "</li>");
      } else if ((m = line.match(/^\s*\d+[.)]\s+(.*)$/))) {
        flushPara(); if (listType !== "ol") { closeList(); out.push("<ol>"); listType = "ol"; }
        out.push("<li>" + _inlineMd(m[1]) + "</li>");
      } else {
        closeList(); para.push(line.trim());
      }
    }
    flushPara(); closeList();
    return out.join("");
  }

  function relativeTime(v) {
    if (isEmpty(v)) return UNAVAILABLE;
    const d = new Date(v);
    if (Number.isNaN(d.getTime())) return safeText(v);
    const diff = (Date.now() - d.getTime()) / 1000;
    if (diff < 60) return "just now";
    if (diff < 3600) return Math.floor(diff / 60) + "m ago";
    if (diff < 86400) return Math.floor(diff / 3600) + "h ago";
    if (diff < 2592000) return Math.floor(diff / 86400) + "d ago";
    return formatDate(v);
  }

  root.CF = root.CF || {};
  root.CF.fmt = {
    UNAVAILABLE, isEmpty, safeText, escapeHtml, formatNumber, formatCompactNumber,
    formatPercent, formatCurrency, formatDate, formatDuration, formatMetric,
    formatConfidence, relativeTime, inputValue, renderMarkdown,
  };
})(window);

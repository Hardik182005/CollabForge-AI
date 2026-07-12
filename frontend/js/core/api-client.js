/* CollabForge AI — single API client (spec §26).
   One place that knows the backend URL and the standard response envelope. */
(function (root) {
  const INJECTED = root.COLLABFORGE_BACKEND_URL || "__BACKEND_URL__";

  function detectBase() {
    const h = root.location.hostname;
    if (h === "localhost" || h === "127.0.0.1") return "http://localhost:8001";
    if (INJECTED && !INJECTED.startsWith("__")) return INJECTED.replace(/\/$/, "");
    return root.location.origin; // CloudFront same-origin proxy
  }

  const BASE = detectBase();

  // Normalize any backend shape into { success, data, meta, warnings, error }.
  function normalize(raw, httpOk) {
    if (raw && typeof raw === "object" && "success" in raw) return raw;
    if (raw && typeof raw === "object" && "status" in raw) {
      const ok = raw.status === "success" || raw.status === "ok" || httpOk;
      return { success: ok, data: raw, meta: { status: raw.status || (ok ? "live" : "error") }, warnings: raw.warnings || [] };
    }
    return { success: httpOk, data: raw, meta: {}, warnings: [] };
  }

  async function request(endpoint, method, body, opts) {
    opts = opts || {};
    const init = { method: method || "GET", headers: { "Content-Type": "application/json" } };
    if (body) init.body = JSON.stringify(body);
    if (opts.signal) init.signal = opts.signal;
    try {
      const res = await fetch(BASE + endpoint, init);
      let json = null;
      try { json = await res.json(); } catch (_) { json = null; }
      if (!res.ok) {
        const err = (json && (json.error || json.detail)) || {};
        return {
          success: false,
          error: {
            code: err.code || ("HTTP_" + res.status),
            message: (typeof err === "string" ? err : err.message) || ("Request failed (" + res.status + ")"),
            retryable: res.status >= 500 || res.status === 429,
          },
          data: null, meta: {}, warnings: [],
        };
      }
      return normalize(json, true);
    } catch (e) {
      if (e.name === "AbortError") return { success: false, error: { code: "ABORTED", message: "Cancelled", retryable: false } };
      return {
        success: false,
        error: { code: "NETWORK", message: "Backend unreachable — check your connection.", retryable: true },
        data: null, meta: {}, warnings: [],
      };
    }
  }

  const api = {
    base: BASE,
    get: (e, o) => request(e, "GET", null, o),
    post: (e, b, o) => request(e, "POST", b, o),
    put: (e, b, o) => request(e, "PUT", b, o),
    // SSE via fetch stream — yields parsed JSON events to onEvent.
    stream: async function (endpoint, body, onEvent, opts) {
      opts = opts || {};
      const res = await fetch(BASE + endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "text/event-stream" },
        body: JSON.stringify(body || {}),
        signal: opts.signal,
      });
      if (!res.ok || !res.body) throw new Error("stream_failed_" + res.status);
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop();
        for (const part of parts) {
          const line = part.split("\n").find((l) => l.startsWith("data:"));
          if (!line) continue;
          const payload = line.slice(5).trim();
          if (!payload || payload === "{}") continue;
          try { onEvent(JSON.parse(payload)); } catch (_) {}
        }
      }
    },
  };

  root.CF = root.CF || {};
  root.CF.api = api;
})(window);

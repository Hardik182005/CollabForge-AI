// CollabForge AI — backend URL injection point.
// scripts/deploy_frontend_aws.* replaces __BACKEND_URL__ at deploy time.
// "" means the CloudFront distribution proxies /api/* to the backend (same origin).
window.COLLABFORGE_BACKEND_URL = "__BACKEND_URL__";

// Back-compat shim for any legacy inline caller still using apiCall()/loadCapabilities().
// New code uses window.CF.api (js/core/api-client.js).
window.apiCall = async function (endpoint, method, body) {
  const CF = window.CF;
  if (CF && CF.api) {
    const r = await CF.api[(method || "GET").toLowerCase()](endpoint, body);
    if (r && r.success === false) return { __error: true, status: 0, detail: (r.error && r.error.message) || "error" };
    return r && r.data ? r.data : r;
  }
  return { __error: true, status: 0, detail: "API client not loaded" };
};
window.loadCapabilities = async function () {
  return window.CF && window.CF.caps ? window.CF.caps.load() : null;
};

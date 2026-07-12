// Creatrix AI — API Configuration
// Auto-detects: local dev uses localhost:8080, production uses Cloud Run URL
const CLOUD_RUN_URL = "https://creatrix-ai-backend-PLACEHOLDER.run.app";
const LOCAL_URL = "http://localhost:8080";

function detectApiBase() {
  const hostname = window.location.hostname;
  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return LOCAL_URL;
  }
  // Firebase Hosting rewrites /api → Cloud Run
  return window.location.origin;
}

const API_BASE = detectApiBase();

// API helper with error handling and offline fallback
async function apiCall(endpoint, method = "GET", body = null) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body) opts.body = JSON.stringify(body);
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, opts);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`API call failed for ${endpoint}:`, err.message);
    return null;
  }
}

// Expose globally
window.API_BASE = API_BASE;
window.apiCall = apiCall;

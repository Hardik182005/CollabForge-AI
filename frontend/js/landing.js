/* CollabForge AI — landing page behaviour. */
(function () {
  const CF = window.CF;

  // ── Capability labels (live from backend, never a static flag) ──
  const CAP_MAP = {
    // Wire is part of the live Anakin layer; light it whenever Anakin is connected.
    wire: (c) => c.anakin && c.anakin.available,
    scraper: (c) => c.anakin && c.anakin.scraper && c.anakin.scraper.available,
    search: (c) => c.anakin && c.anakin.search && c.anakin.search.available,
    openai: (c) => c.openai && c.openai.available,
    elevenlabs: (c) => c.elevenlabs && c.elevenlabs.available,
  };
  CF.caps.load().then((caps) => {
    if (!caps) return;
    document.querySelectorAll(".cap-label").forEach((el) => {
      const key = el.getAttribute("data-cap");
      const live = CAP_MAP[key] && CAP_MAP[key](caps);
      el.classList.toggle("is-live", !!live);
      el.classList.toggle("is-down", !live);
    });
  });

  // ── Pipeline demo ──
  const mount = document.getElementById("pipeline-mount");
  const input = document.getElementById("demo-query");
  const runBtn = document.getElementById("run-pipeline");
  let pipeline = CF.pipeline.create(mount, { mode: "expanded" });
  let running = false;
  // Pipeline stays visible at all times (idle nodes on load); a run updates it in place.

  async function run() {
    const q = (input.value || "").trim();
    if (!q) { input.focus(); return; }
    if (running) return;
    running = true;
    runBtn.disabled = true;
    runBtn.textContent = "Running…";
    try {
      await pipeline.run(q);
    } finally {
      running = false;
      runBtn.disabled = false;
      runBtn.textContent = "Run Live Pipeline";
    }
  }

  runBtn.addEventListener("click", run);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") run(); });
  document.querySelectorAll(".lp-demo-examples button").forEach((b) => {
    b.addEventListener("click", () => { input.value = b.getAttribute("data-ex"); input.focus(); });
  });

  // ── Mobile drawer ──
  const burger = document.getElementById("burger");
  const drawer = document.getElementById("drawer");
  const scrim = document.getElementById("scrim");
  function toggle(open) { drawer.classList.toggle("is-open", open); scrim.classList.toggle("is-open", open); }
  if (burger) burger.addEventListener("click", () => toggle(true));
  if (scrim) scrim.addEventListener("click", () => toggle(false));
  drawer.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => toggle(false)));

  // ── Hero particles (decorative, reduced-motion aware) ──
  const pc = document.getElementById("particles");
  if (pc && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    for (let i = 0; i < 14; i++) {
      const s = document.createElement("span");
      s.style.left = Math.random() * 100 + "%";
      s.style.top = 60 + Math.random() * 40 + "%";
      s.style.animationDuration = 6 + Math.random() * 8 + "s";
      s.style.animationDelay = Math.random() * 6 + "s";
      pc.appendChild(s);
    }
  }
})();

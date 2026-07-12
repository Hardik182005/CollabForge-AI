/* CollabForge AI — application shell (spec §12).
   One sidebar, one topbar, workspace switch. Drives the shared router. */
(function () {
  const CF = window.CF;

  const NAV = {
    creator: {
      label: "Creator Studio",
      groups: [
        { title: "Intelligence", items: [
          { view: "trends", label: "Trend Discovery" },
          { view: "selected-trend", label: "Selected Trend" },
        ]},
        { title: "Create", items: [
          { view: "scripts", label: "Script Studio" },
          { view: "hooks", label: "Hook Lab" },
          { view: "social", label: "Social Content Pack" },
        ]},
        { title: "Media", items: [
          { view: "voice", label: "Voice Studio" },
          { view: "reel", label: "Reel Builder" },
        ]},
        { title: "Analysis", items: [
          { view: "virality", label: "Virality Evaluation" },
          { view: "saved", label: "Saved Content" },
        ]},
      ],
    },
    brand: {
      label: "Brand Intelligence",
      groups: [
        { title: "Discover", items: [
          { view: "discover", label: "Discover Creators" },
          { view: "research", label: "Creator Research" },
          { view: "compare", label: "Compare Creators" },
        ]},
        { title: "Campaign", items: [
          { view: "campaign", label: "Campaign Planner" },
          { view: "roi", label: "ROI Scenarios" },
          { view: "outreach", label: "Outreach Studio" },
          { view: "contract", label: "Contract Builder" },
        ]},
        { title: "Workspace", items: [
          { view: "room", label: "Campaign Room" },
          { view: "autopilot", label: "Collab Autopilot" },
        ]},
      ],
    },
  };

  const TITLES = {};
  Object.keys(NAV).forEach((ws) => NAV[ws].groups.forEach((g) => g.items.forEach((it) => { TITLES[ws + ":" + it.view] = it.label; })));

  const navEl = document.getElementById("sidebar-nav");
  const wsSwitch = document.getElementById("ws-switch");
  const titleEl = document.getElementById("view-title");
  const crumbEl = document.getElementById("crumb");
  const sidebar = document.getElementById("sidebar");
  const scrim = document.getElementById("sb-scrim");

  function renderNav(workspace, activeView) {
    const cfg = NAV[workspace];
    navEl.innerHTML = cfg.groups.map((g) =>
      '<div class="nav-group"><div class="nav-group__title">' + CF.fmt.escapeHtml(g.title) + "</div>" +
      g.items.map((it) =>
        '<button class="nav-link' + (it.view === activeView ? " is-active" : "") + '" data-view="' + it.view + '">' +
        '<span>' + CF.fmt.escapeHtml(it.label) + "</span></button>").join("") + "</div>").join("");
    navEl.querySelectorAll(".nav-link").forEach((b) => b.addEventListener("click", () => {
      CF.router.navigate(workspace, b.getAttribute("data-view"));
      closeMobile();
    }));
    wsSwitch.querySelectorAll("button").forEach((b) =>
      b.classList.toggle("is-active", b.getAttribute("data-ws") === workspace));
  }

  wsSwitch.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
    const ws = b.getAttribute("data-ws");
    const first = NAV[ws].groups[0].items[0].view;
    CF.router.navigate(ws, first);
  }));

  CF.events.on("route:change", ({ workspace, view }) => {
    renderNav(workspace, view);
    titleEl.textContent = TITLES[workspace + ":" + view] || view;
    crumbEl.textContent = NAV[workspace].label;
    document.getElementById("topbar-cta").href = "app.html?workspace=brand&view=autopilot";
  });

  // Mobile
  function openMobile() { sidebar.classList.add("is-open"); scrim.classList.add("is-open"); }
  function closeMobile() { sidebar.classList.remove("is-open"); scrim.classList.remove("is-open"); }
  document.getElementById("mobile-menu").addEventListener("click", openMobile);
  scrim.addEventListener("click", closeMobile);

  // Live system status in the sidebar footer (derived from backend).
  CF.caps.load().then((caps) => {
    const el = document.getElementById("sys-status");
    if (!caps) { el.classList.add("is-down"); el.querySelector("span:last-child").textContent = "Backend unreachable"; return; }
    const wire = caps.anakin && caps.anakin.wire && caps.anakin.wire.available;
    const scraper = caps.anakin && caps.anakin.scraper && caps.anakin.scraper.available;
    if (scraper) { el.classList.add("is-live"); el.querySelector("span:last-child").textContent = "Anakin live · evidence flowing"; }
    else { el.classList.add("is-down"); el.querySelector("span:last-child").textContent = "Connecting to Anakin…"; }
  });

  // Boot the router.
  CF.router.start(document.getElementById("view-root"));
})();

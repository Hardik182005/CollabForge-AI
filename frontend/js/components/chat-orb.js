/* CollabForge AI — Forge, the floating AI chat orb (every page).
   OpenAI-backed (via /api/v1/chat/), humorous, knows the whole product.
   Voice: browser STT (SpeechRecognition) in, browser TTS (speechSynthesis) out.
   Self-contained: injects its own DOM + styles; needs only CF.api (config.js + api-client). */
(function () {
  if (window.__forgeOrb) return; window.__forgeOrb = true;

  var STT = window.SpeechRecognition || window.webkitSpeechRecognition;
  var history = [];
  var voiceOn = true;      // speak replies
  var listening = false;
  var recog = null;

  // ── styles ──
  var css = document.createElement("style");
  css.textContent = "\
  .forge-orb{position:fixed;bottom:22px;right:22px;z-index:2000;width:60px;height:60px;border-radius:50%;\
    background:radial-gradient(circle at 38% 32%,#4d82ec,#244fb0 60%,#16306a);box-shadow:0 10px 30px rgba(36,79,176,.5),0 0 0 0 rgba(52,102,214,.5);\
    display:grid;place-items:center;cursor:pointer;transition:transform .2s cubic-bezier(.22,1,.36,1);animation:forge-pulse 3s infinite}\
  .forge-orb:hover{transform:translateY(-3px) scale(1.05)}\
  .forge-orb svg{width:30px;height:30px;color:#dbe7ff}\
  @keyframes forge-pulse{0%,100%{box-shadow:0 10px 30px rgba(36,79,176,.5),0 0 0 0 rgba(52,102,214,.45)}50%{box-shadow:0 10px 30px rgba(36,79,176,.5),0 0 0 12px rgba(52,102,214,0)}}\
  @media (prefers-reduced-motion:reduce){.forge-orb{animation:none}}\
  .forge-panel{position:fixed;bottom:94px;right:22px;z-index:2000;width:min(380px,calc(100vw - 44px));height:min(540px,70vh);\
    background:#0e1a2b;border:1px solid rgba(159,192,255,.18);border-radius:18px;box-shadow:0 30px 80px rgba(0,0,0,.5);\
    display:none;flex-direction:column;overflow:hidden;font-family:'Inter',system-ui,sans-serif}\
  .forge-panel.open{display:flex;animation:forge-in .22s cubic-bezier(.22,1,.36,1)}\
  @keyframes forge-in{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}\
  .forge-head{display:flex;align-items:center;gap:10px;padding:14px 16px;border-bottom:1px solid rgba(159,192,255,.12);color:#eaf1fb}\
  .forge-head b{font-family:'Fraunces',Georgia,serif;font-weight:500;font-size:15px}\
  .forge-head .forge-sub{font-size:11px;color:#9db0c6;font-family:'JetBrains Mono',monospace}\
  .forge-head .forge-x{margin-left:auto;color:#9db0c6;cursor:pointer;font-size:20px;line-height:1;background:none;border:none}\
  .forge-mini{width:26px;height:26px;border-radius:50%;background:radial-gradient(circle at 38% 32%,#4d82ec,#244fb0);flex:none}\
  .forge-body{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px}\
  .forge-msg{max-width:85%;padding:10px 13px;border-radius:14px;font-size:14px;line-height:1.5;white-space:pre-wrap;word-wrap:break-word}\
  .forge-msg.bot{background:rgba(255,255,255,.06);color:#eaf1fb;align-self:flex-start;border-bottom-left-radius:4px}\
  .forge-msg.me{background:#3466d6;color:#fff;align-self:flex-end;border-bottom-right-radius:4px}\
  .forge-typing{align-self:flex-start;color:#9db0c6;font-size:13px;padding:6px 4px}\
  .forge-foot{padding:12px;border-top:1px solid rgba(159,192,255,.12);display:flex;gap:8px;align-items:center}\
  .forge-in{flex:1;background:rgba(255,255,255,.05);border:1px solid rgba(159,192,255,.2);border-radius:12px;color:#eaf1fb;padding:10px 12px;font-size:14px;outline:none;font-family:inherit}\
  .forge-in::placeholder{color:#7d8da3}\
  .forge-btn{width:40px;height:40px;border-radius:11px;border:none;cursor:pointer;display:grid;place-items:center;flex:none;background:rgba(255,255,255,.06);color:#cfe0ff}\
  .forge-btn svg{width:18px;height:18px}\
  .forge-btn.send{background:#3466d6;color:#fff}\
  .forge-btn.mic.on{background:#c33f2c;color:#fff;animation:forge-pulse 1.2s infinite}\
  .forge-btn.voice.off{opacity:.45}\
  .forge-chips{display:flex;flex-wrap:wrap;gap:6px;padding:0 16px 12px}\
  .forge-chip{font-size:12px;color:#cfe0ff;background:rgba(52,102,214,.16);border:1px solid rgba(52,102,214,.35);border-radius:20px;padding:5px 11px;cursor:pointer}\
  ";
  document.head.appendChild(css);

  var esc = function (s) { return (window.CF && CF.fmt) ? CF.fmt.escapeHtml(s) : String(s == null ? "" : s).replace(/[&<>\"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); };

  var ICON_ORB = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3a9 9 0 0 0-9 9 9 9 0 0 0 1.5 5L3 21l4-1.5A9 9 0 1 0 12 3Z"/><circle cx="8.5" cy="12" r="1.1" fill="currentColor"/><circle cx="12" cy="12" r="1.1" fill="currentColor"/><circle cx="15.5" cy="12" r="1.1" fill="currentColor"/></svg>';
  var ICON_SEND = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m5 12 14-7-4 14-3-5-7-2Z"/></svg>';
  var ICON_MIC = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></svg>';
  var ICON_SPK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 9v6h4l5 4V5L8 9H4Z"/><path d="M16 9a3 3 0 0 1 0 6"/></svg>';

  // ── DOM ──
  var orb = document.createElement("button");
  orb.className = "forge-orb"; orb.setAttribute("aria-label", "Chat with Forge"); orb.innerHTML = ICON_ORB;
  var panel = document.createElement("div");
  panel.className = "forge-panel";
  panel.innerHTML =
    '<div class="forge-head"><span class="forge-mini"></span><div><b>Forge</b><div class="forge-sub">your CollabForge sidekick</div></div>' +
    '<button class="forge-btn voice" title="Toggle voice" aria-label="Toggle voice replies">' + ICON_SPK + '</button>' +
    '<button class="forge-x" aria-label="Close">×</button></div>' +
    '<div class="forge-body"></div>' +
    '<div class="forge-chips">' +
      '<span class="forge-chip">What is CollabForge?</span>' +
      '<span class="forge-chip">How do I research a creator?</span>' +
      '<span class="forge-chip">What does Autopilot do?</span>' +
    '</div>' +
    '<div class="forge-foot">' +
      '<button class="forge-btn mic" title="Speak" aria-label="Speak to Forge">' + ICON_MIC + '</button>' +
      '<input class="forge-in" placeholder="Ask Forge anything…" aria-label="Ask Forge anything" />' +
      '<button class="forge-btn send" title="Send" aria-label="Send message">' + ICON_SEND + '</button>' +
    '</div>';
  document.body.appendChild(orb); document.body.appendChild(panel);

  var body = panel.querySelector(".forge-body");
  var input = panel.querySelector(".forge-in");
  var micBtn = panel.querySelector(".forge-btn.mic");
  var voiceBtn = panel.querySelector(".forge-btn.voice");
  if (!STT) micBtn.style.display = "none";

  function scroll() { body.scrollTop = body.scrollHeight; }
  function add(text, who) { var d = document.createElement("div"); d.className = "forge-msg " + who; d.innerHTML = esc(text); body.appendChild(d); scroll(); return d; }

  function speak(text) {
    if (!voiceOn || !window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      var u = new SpeechSynthesisUtterance(text.slice(0, 600));
      u.rate = 1.04; u.pitch = 1.05;
      var vs = window.speechSynthesis.getVoices();
      var pick = vs.find(function (v) { return /female|zira|samantha|google uk english female|natural/i.test(v.name); });
      if (pick) u.voice = pick;
      window.speechSynthesis.speak(u);
    } catch (e) {}
  }

  var greeted = false;
  function open() {
    panel.classList.add("open");
    if (!greeted) { greeted = true; var g = "Hey, I'm Forge — your CollabForge co-pilot. Ask me anything about researching creators, running Autopilot, or where that button went. I promise only mild jokes."; add(g, "bot"); }
    setTimeout(function () { input.focus(); }, 100);
  }
  function close() { panel.classList.remove("open"); if (window.speechSynthesis) window.speechSynthesis.cancel(); }

  orb.addEventListener("click", function () { panel.classList.contains("open") ? close() : open(); });
  panel.querySelector(".forge-x").addEventListener("click", close);
  voiceBtn.addEventListener("click", function () { voiceOn = !voiceOn; voiceBtn.classList.toggle("off", !voiceOn); if (!voiceOn && window.speechSynthesis) window.speechSynthesis.cancel(); });

  async function send(text) {
    text = (text || input.value || "").trim();
    if (!text) return;
    input.value = "";
    add(text, "me");
    history.push({ role: "user", content: text });
    var typing = document.createElement("div"); typing.className = "forge-typing"; typing.textContent = "Forge is thinking…"; body.appendChild(typing); scroll();

    var reply = "Hmm, my wires got crossed. Try again?";
    try {
      var res = await CF.api.post("/api/v1/chat/", { message: text, history: history.slice(-8), page: document.title });
      reply = (res && (res.data && res.data.reply || res.reply)) || reply;
    } catch (e) {}
    typing.remove();
    add(reply, "bot");
    history.push({ role: "assistant", content: reply });
    speak(reply);
  }

  panel.querySelector(".forge-btn.send").addEventListener("click", function () { send(); });
  input.addEventListener("keydown", function (e) { if (e.key === "Enter") send(); });
  panel.querySelectorAll(".forge-chip").forEach(function (c) { c.addEventListener("click", function () { send(c.textContent); }); });

  // ── STT ──
  if (STT) {
    micBtn.addEventListener("click", function () {
      if (listening) { recog && recog.stop(); return; }
      recog = new STT(); recog.lang = "en-US"; recog.interimResults = false; recog.maxAlternatives = 1;
      listening = true; micBtn.classList.add("on");
      recog.onresult = function (e) { var t = e.results[0][0].transcript; input.value = t; send(t); };
      recog.onerror = function () {};
      recog.onend = function () { listening = false; micBtn.classList.remove("on"); };
      try { recog.start(); } catch (e) { listening = false; micBtn.classList.remove("on"); }
    });
  }
})();

document.addEventListener('DOMContentLoaded', () => {
  // --- STATE VARIABLES ---
  let lastTime = 0;
  
  // 3D Sphere Variables (Hero Canvas)
  let spherePoints = [];
  let sphereAngleX = 0;
  let sphereAngleY = 0;

  // 3D Sphere Variables (Card Canvas)
  let cardPoints = [];
  let cardAngleX = 0;
  let cardAngleY = 0;



  // Services Interactive Visual variables
  let activeServiceIndex = 0;
  const serviceCanvas = document.getElementById('canvas-service-visual');
  const serviceCtx = serviceCanvas ? serviceCanvas.getContext('2d') : null;
  let serviceAngleX = 0;
  let serviceAngleY = 0;

  // --- ELEMENT REFERENCES ---
  const loader = document.getElementById('loader');
  const loadProgress = document.getElementById('load-progress');
  const appContainer = document.getElementById('app');
  const glitchContainer = document.getElementById('glitch-streaks');
  
  // Hero Canvas
  const heroCanvas = document.getElementById('canvas-3d');
  const heroCtx = heroCanvas ? heroCanvas.getContext('2d') : null;
  
  // Card Canvas
  const cardCanvas = document.getElementById('canvas-card-graphic');
  const cardCtx = cardCanvas ? cardCanvas.getContext('2d') : null;

  // Hero Actions
  const ctaBtn = document.getElementById('cta-btn');

  // --- 1. INTRO LOADING PROCESS ---
  function startLoader() {
    let progress = 0;
    const duration = 2000; // 2 seconds loader
    const intervalTime = 30;
    const increment = 100 / (duration / intervalTime);

    const timer = setInterval(() => {
      progress += increment + (Math.random() * 2);
      if (progress >= 100) {
        progress = 100;
        clearInterval(timer);
        setTimeout(completeLoading, 200);
      }
      loadProgress.textContent = `${Math.floor(progress)}%`;
    }, intervalTime);
  }

  function completeLoading() {
    loader.classList.add('fade-out');
    setTimeout(() => {
      appContainer.style.opacity = 1;
    }, 400);
  }

  // --- 2. GLITCH STREAKS GENERATOR ---
  function createGlitchStreak() {
    if (document.hidden) return;
    
    const streak = document.createElement('div');
    streak.classList.add('glitch-streak');
    
    const topPos = Math.random() * 90 + 5;
    const scaleY = Math.random() * 2 + 1;
    const width = Math.random() * 150 + 80;
    const animDuration = Math.random() * 1.5 + 1.5;

    streak.style.top = `${topPos}%`;
    streak.style.transform = `scaleY(${scaleY})`;
    streak.style.width = `${width}px`;
    streak.style.animationDuration = `${animDuration}s`;
    
    glitchContainer.appendChild(streak);
    
    setTimeout(() => {
      streak.remove();
    }, animDuration * 1000);
  }
  
  setInterval(createGlitchStreak, 800);

  // --- 3. 3D SPHERES INITIALIZATION ---
  function generateSpherePoints(count, radius) {
    const points = [];
    for (let i = 0; i < count; i++) {
      const y = 1 - (i / (count - 1)) * 2;
      const radiusAtY = Math.sqrt(1 - y * y);
      
      const goldenAngle = Math.PI * (3 - Math.sqrt(5));
      const theta = goldenAngle * i;
      
      const x = Math.cos(theta) * radiusAtY;
      const z = Math.sin(theta) * radiusAtY;
      
      points.push({
        x: x * radius,
        y: y * radius,
        z: z * radius
      });
    }
    return points;
  }

  spherePoints = generateSpherePoints(550, 160);
  cardPoints = generateSpherePoints(350, 95);

  // --- 4. SERVICES INTERACTIVE 3D SHAPES ---
  // Define 3D wireframe geometries
  const geometries = {
    // 0: Cube
    cube: {
      vertices: [
        {x:-30, y:-30, z:-30}, {x:30, y:-30, z:-30}, {x:30, y:30, z:-30}, {x:-30, y:30, z:-30},
        {x:-30, y:-30, z:30},  {x:30, y:-30, z:30},  {x:30, y:30, z:30},  {x:-30, y:30, z:30}
      ],
      edges: [
        [0,1], [1,2], [2,3], [3,0],
        [4,5], [5,6], [6,7], [7,4],
        [0,4], [1,5], [2,6], [3,7]
      ]
    },
    // 1: Octahedron
    octahedron: {
      vertices: [
        {x:0, y:-45, z:0}, {x:0, y:45, z:0},
        {x:-35, y:0, z:-35}, {x:35, y:0, z:-35},
        {x:35, y:0, z:35}, {x:-35, y:0, z:35}
      ],
      edges: [
        [0,2], [0,3], [0,4], [0,5],
        [1,2], [1,3], [1,4], [1,5],
        [2,3], [3,4], [4,5], [5,2]
      ]
    },
    // 2: Tetrahedron
    tetrahedron: {
      vertices: [
        {x:0, y:-40, z:0},
        {x:-35, y:25, z:-35},
        {x:35, y:25, z:-35},
        {x:0, y:25, z:45}
      ],
      edges: [
        [0,1], [0,2], [0,3],
        [1,2], [2,3], [3,1]
      ]
    },
    // 3: Double Cone / Hexagonal Bipyramid
    prism: {
      vertices: [
        {x:0, y:-45, z:0}, {x:0, y:45, z:0},
        {x:-30, y:0, z:-20}, {x:0, y:0, z:-35}, {x:30, y:0, z:-20},
        {x:30, y:0, z:20}, {x:0, y:0, z:35}, {x:-30, y:0, z:20}
      ],
      edges: [
        [0,2], [0,3], [0,4], [0,5], [0,6], [0,7],
        [1,2], [1,3], [1,4], [1,5], [1,6], [1,7],
        [2,3], [3,4], [4,5], [5,6], [6,7], [7,2]
      ]
    },
    // 4: Cylinder / Node cluster
    nodes: {
      vertices: [
        {x:-25, y:-25, z:0}, {x:25, y:-25, z:0}, {x:0, y:-25, z:25},
        {x:-25, y:25, z:0}, {x:25, y:25, z:0}, {x:0, y:25, z:25},
        {x:0, y:0, z:-30}, {x:0, y:0, z:30}
      ],
      edges: [
        [0,1], [1,2], [2,0], [3,4], [4,5], [5,3],
        [0,3], [1,4], [2,5], [0,6], [1,6], [2,6], [3,7], [4,7], [5,7]
      ]
    }
  };

  const serviceItems = document.querySelectorAll('#track01-list .service-item');
  const previewPanels = document.querySelectorAll('#services .service-preview-panel');
  serviceItems.forEach(item => {
    item.addEventListener('mouseenter', () => {
      serviceItems.forEach(el => el.classList.remove('active'));
      previewPanels.forEach(el => el.classList.remove('active'));
      item.classList.add('active');
      const idx = item.getAttribute('data-index');
      const panel = document.getElementById(`service-preview-${idx}`);
      if (panel) panel.classList.add('active');
      activeServiceIndex = parseInt(idx);
    });
  });

  const t2Items = document.querySelectorAll('#track02-list .service-item');
  const t2Panels = document.querySelectorAll('#track02 .service-preview-panel');
  t2Items.forEach(item => {
    item.addEventListener('mouseenter', () => {
      t2Items.forEach(el => el.classList.remove('active'));
      t2Panels.forEach(el => el.classList.remove('active'));
      item.classList.add('active');
      const idx = item.getAttribute('data-t2-index');
      const panel = document.getElementById(`t2-preview-${idx}`);
      if (panel) panel.classList.add('active');
    });
  });



  // Resizing function
  function resizeCanvases() {
    const dpr = window.devicePixelRatio || 1;
    
    // Hero Canvas
    if (heroCanvas && heroCtx) {
      const rect = heroCanvas.getBoundingClientRect();
      heroCanvas.width = rect.width * dpr;
      heroCanvas.height = rect.height * dpr;
      heroCtx.scale(dpr, dpr);
    }

    // Card Canvas
    if (cardCanvas) {
      const cardRect = cardCanvas.getBoundingClientRect();
      cardCanvas.width = cardRect.width * dpr;
      cardCanvas.height = cardRect.height * dpr;
      cardCtx.scale(dpr, dpr);
    }

    // Services visual Canvas
    if (serviceCanvas) {
      const sRect = serviceCanvas.parentElement.getBoundingClientRect();
      serviceCanvas.width = sRect.width * dpr;
      serviceCanvas.height = sRect.height * dpr;
      serviceCtx.scale(dpr, dpr);
    }


  }

  window.addEventListener('resize', resizeCanvases);
  setTimeout(resizeCanvases, 100);

  // Math Helper Rotation Matrices
  function rotateY(point, angle) {
    const cos = Math.cos(angle);
    const sin = Math.sin(angle);
    return {
      x: point.x * cos - point.z * sin,
      y: point.y,
      z: point.x * sin + point.z * cos
    };
  }

  function rotateX(point, angle) {
    const cos = Math.cos(angle);
    const sin = Math.sin(angle);
    return {
      x: point.x,
      y: point.y * cos - point.z * sin,
      z: point.y * sin + point.z * cos
    };
  }

  // --- 7. RENDER LOOP ---
  function animate(timestamp) {
    if (!lastTime) lastTime = timestamp;
    const delta = timestamp - lastTime;
    lastTime = timestamp;

    if (heroCanvas && heroCtx) {
      const width = heroCanvas.width / (window.devicePixelRatio || 1);
      const height = heroCanvas.height / (window.devicePixelRatio || 1);
      const centerX = width / 2;
      const centerY = height / 2;

      heroCtx.clearRect(0, 0, width, height);

      // Draw central glowing blue aura inside canvas
      const glowGrad = heroCtx.createRadialGradient(centerX, centerY, 10, centerX, centerY, 300);
      glowGrad.addColorStop(0, 'rgba(144, 170, 207, 0.08)');
      glowGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
      heroCtx.fillStyle = glowGrad;
      heroCtx.fillRect(0, 0, width, height);

      // Constant rotation loops
      sphereAngleX += 0.0005;
      sphereAngleY += 0.001;

      // Sort points by Z (depth)
      const rotatedPoints = spherePoints.map(p => {
        let r = rotateY(p, sphereAngleY);
        r = rotateX(r, sphereAngleX);
        return r;
      });
      rotatedPoints.sort((a, b) => a.z - b.z);

      // Draw 3D points
      const fov = 400;
      rotatedPoints.forEach(p => {
        const scale = fov / (fov + p.z);
        const screenX = centerX + p.x * scale;
        const screenY = centerY + p.y * scale;

        const zOffset = 160;
        const depth = (p.z + zOffset) / (2 * zOffset);
        const size = 0.8 + depth * 2.2;
        const opacity = 0.08 + depth * 0.82;

        heroCtx.beginPath();
        heroCtx.arc(screenX, screenY, size, 0, Math.PI * 2);
        
        if (depth > 0.75) {
          heroCtx.fillStyle = `rgba(163, 191, 250, ${opacity})`;
        } else {
          heroCtx.fillStyle = `rgba(148, 163, 184, ${opacity})`;
        }
        heroCtx.fill();
      });
    }

    // --- Draw Card Canvas Graphic ---
    if (cardCanvas) {
      const cardWidth = cardCanvas.width / (window.devicePixelRatio || 1);
      const cardHeight = cardCanvas.height / (window.devicePixelRatio || 1);
      const cardCX = cardWidth / 2;
      const cardCY = cardHeight / 2;

      cardCtx.clearRect(0, 0, cardWidth, cardHeight);

      cardAngleX += 0.001;
      cardAngleY += 0.002;

      const cardRotated = cardPoints.map(p => {
        let r = rotateY(p, cardAngleY);
        r = rotateX(r, cardAngleX);
        return r;
      });
      cardRotated.sort((a, b) => a.z - b.z);

      const cardFov = 300;
      cardRotated.forEach(p => {
        const scale = cardFov / (cardFov + p.z);
        const screenX = cardCX + p.x * scale;
        const screenY = cardCY + p.y * scale;

        const zOffset = 95;
        const depth = (p.z + zOffset) / (2 * zOffset);
        const size = 0.5 + depth * 1.5;
        const opacity = 0.05 + depth * 0.7;

        cardCtx.beginPath();
        cardCtx.arc(screenX, screenY, size, 0, Math.PI * 2);
        cardCtx.fillStyle = `rgba(255, 255, 255, ${opacity})`;
        cardCtx.fill();
      });
    }

    // --- Draw Services Visual Canvas (Cube, Octahedron, etc.) ---
    if (serviceCanvas && serviceCtx) {
      const sw = serviceCanvas.width / (window.devicePixelRatio || 1);
      const sh = serviceCanvas.height / (window.devicePixelRatio || 1);
      const scx = sw / 2;
      const scy = sh / 2;

      serviceCtx.clearRect(0, 0, sw, sh);

      // Draw subtle backing glow
      const sGlow = serviceCtx.createRadialGradient(scx, scy, 5, scx, scy, 160);
      sGlow.addColorStop(0, 'rgba(59, 130, 246, 0.07)');
      sGlow.addColorStop(1, 'rgba(0,0,0,0)');
      serviceCtx.fillStyle = sGlow;
      serviceCtx.fillRect(0,0,sw,sh);

      // Rotate shape
      serviceAngleX += 0.004;
      serviceAngleY += 0.007;

      // Select active shape keys
      const shapeKeys = ['cube', 'octahedron', 'tetrahedron', 'prism', 'nodes'];
      const activeShapeKey = shapeKeys[activeServiceIndex] || 'cube';
      const shape = geometries[activeShapeKey];

      // Rotate vertices
      const rotVertices = shape.vertices.map(v => {
        let r = rotateY(v, serviceAngleY);
        r = rotateX(r, serviceAngleX);
        return r;
      });

      // Project vertices
      const projected = rotVertices.map(v => {
        const scale = 250 / (250 + v.z);
        return {
          x: scx + v.x * scale,
          y: scy + v.y * scale,
          z: v.z
        };
      });

      // Draw edges in glass blue line art
      serviceCtx.strokeStyle = 'rgba(59, 130, 246, 0.65)';
      serviceCtx.lineWidth = 1.2;
      
      shape.edges.forEach(edge => {
        const p1 = projected[edge[0]];
        const p2 = projected[edge[1]];
        
        // Depth shading for edges
        const avgZ = (p1.z + p2.z) / 2;
        const opacity = 0.2 + (1 - (avgZ + 45) / 90) * 0.65;
        serviceCtx.strokeStyle = `rgba(59, 130, 246, ${opacity})`;
        
        serviceCtx.beginPath();
        serviceCtx.moveTo(p1.x, p1.y);
        serviceCtx.lineTo(p2.x, p2.y);
        serviceCtx.stroke();
      });

      // Draw nodes/points
      projected.forEach(p => {
        const depth = (p.z + 45) / 90;
        const size = 1.5 + (1 - depth) * 2;
        const opacity = 0.3 + (1 - depth) * 0.7;
        
        serviceCtx.beginPath();
        serviceCtx.arc(p.x, p.y, size, 0, Math.PI * 2);
        serviceCtx.fillStyle = `rgba(147, 197, 253, ${opacity})`;
        serviceCtx.fill();
      });
    }



    animationFrameId = requestAnimationFrame(animate);
  }

  requestAnimationFrame(animate);



  // --- 9. INTERACTION ACTIONS & PARALLAX ---
  function showToast(message) {
    const oldToast = document.querySelector('.glass-toast');
    if (oldToast) oldToast.remove();

    const toast = document.createElement('div');
    toast.className = 'glass-toast';
    toast.innerHTML = message;
    
    Object.assign(toast.style, {
      position: 'fixed',
      bottom: '100px',
      left: '50%',
      transform: 'translateX(-50%) translateY(20px)',
      background: 'rgba(15, 23, 42, 0.85)',
      border: '1px solid rgba(255, 255, 255, 0.1)',
      color: '#ffffff',
      padding: '12px 24px',
      borderRadius: '12px',
      fontSize: '0.85rem',
      letterSpacing: '0.02em',
      zIndex: '10000',
      backdropFilter: 'blur(10px)',
      boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
      opacity: '0',
      transition: 'opacity 0.4s ease, transform 0.4s ease',
      pointerEvents: 'none'
    });

    document.body.appendChild(toast);
    
    setTimeout(() => {
      toast.style.opacity = '1';
      toast.style.transform = 'translateX(-50%) translateY(0)';
    }, 50);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(-50%) translateY(-20px)';
      setTimeout(() => toast.remove(), 400);
    }, 2500);
  }

  ctaBtn.addEventListener('click', () => {
    showToast("Redirecting to client onboard form...");
  });

  const footerCtaBtn = document.querySelector('.footer-cta-btn');
  if (footerCtaBtn) {
    footerCtaBtn.addEventListener('click', () => {
      showToast("Redirecting to contact form...");
    });
  }



  const heroSection = document.getElementById('hero');
  const heroContent = document.querySelector('.hero-content');
  const scrollDownLink = document.getElementById('scroll-down-link');
  
  window.addEventListener('scroll', () => {
    const scrollY = window.scrollY;
    const vh = window.innerHeight;
    
    if (scrollY < vh) {
      const progress = scrollY / vh;
      heroContent.style.opacity = 1 - progress * 1.5;
      heroContent.style.transform = `translateY(${-20 - progress * 50}px) scale(${1 - progress * 0.05})`;
      if (scrollDownLink) {
        scrollDownLink.style.opacity = 1 - progress * 2.5;
      }
    }
  });

  // --- 10. SCROLL REVEAL OBSERVER ---
  const revealElements = document.querySelectorAll('.reveal');
  const revealObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('revealed');
        observer.unobserve(entry.target);
      }
    });
  }, {
    threshold: 0.08,
    rootMargin: '0px 0px -40px 0px'
  });

  revealElements.forEach(el => {
    revealObserver.observe(el);
  });



  // --- 14. PAGE TRANSITIONS FADE IN/OUT ---
  window.addEventListener('pageshow', () => {
    document.body.classList.add('loaded');
  });

  const transitionLinks = document.querySelectorAll('a[href="tracks.html"], a[href="dashboard.html"], a[href="index.html"], .about-learn-more-link, .contact-faq-btn');
  transitionLinks.forEach(link => {
    link.addEventListener('click', (e) => {
      const href = link.getAttribute('href');
      if (href && (href.includes('tracks.html') || href.includes('dashboard.html') || href.includes('index.html'))) {
        e.preventDefault();
        document.body.classList.remove('loaded');
        setTimeout(() => {
          window.location.href = href;
        }, 300);
      }
    });
  });

  // --- SCATTER TEXT ANIMATION (Lavender Band) ---
  const scatterLetters = document.querySelectorAll('#scatter-text .scatter-letter');
  const lavenderBand = document.querySelector('.lavender-transition-band');

  function scatterAll() {
    scatterLetters.forEach(letter => {
      const rx = (Math.random() - 0.5) * 300;
      const ry = (Math.random() - 0.5) * 120;
      const rot = (Math.random() - 0.5) * 120;
      letter.style.transform = `translate(${rx}px, ${ry}px) rotate(${rot}deg)`;
      letter.style.opacity = '0';
    });
  }

  function gatherAll() {
    scatterLetters.forEach((letter, i) => {
      setTimeout(() => {
        letter.style.transform = 'translate(0,0) rotate(0deg)';
        letter.style.opacity = '1';
      }, i * 40);
    });
  }

  if (lavenderBand && scatterLetters.length) {
    scatterAll();
    const scatterObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) { gatherAll(); }
        else { scatterAll(); }
      });
    }, { threshold: 0.35 });
    scatterObserver.observe(lavenderBand);
  }

  // --- FAQ ACCORDION ---
  document.querySelectorAll('.faq-trigger').forEach(trigger => {
    trigger.addEventListener('click', () => {
      const item = trigger.closest('.faq-item');
      const wasActive = item.classList.contains('active');
      document.querySelectorAll('.faq-item').forEach(i => i.classList.remove('active'));
      if (!wasActive) item.classList.add('active');
    });
  });

  // --- DEMO SECTION INTERACTION ---
  const demoBtn = document.getElementById('demo-analyze-btn');
  const demoInput = document.getElementById('demo-handle-input');
  const demoScore = document.getElementById('demo-score');
  if (demoBtn && demoInput) {
    demoBtn.addEventListener('click', () => {
      const handle = demoInput.value.trim() || '@creator';
      demoBtn.textContent = 'Analysing…';
      demoBtn.disabled = true;
      let score = 70 + Math.floor(Math.random() * 28);
      setTimeout(() => {
        if (demoScore) demoScore.textContent = score;
        demoBtn.textContent = 'Analyse';
        demoBtn.disabled = false;
        demoBtn.innerHTML = 'Analyse <svg viewBox="0 0 24 24" width="16" height="16"><path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>';
      }, 1800);
    });
  }

  // --- PLATFORM LAUNCH LOADING SCREEN ---
  window.launchPlatform = function() {
    // Create full-screen overlay
    const overlay = document.createElement('div');
    overlay.id = 'launch-overlay';
    Object.assign(overlay.style, {
      position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
      background: '#01050e', zIndex: '99999', display: 'flex',
      flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      opacity: '0', transition: 'opacity 0.3s ease'
    });

    overlay.innerHTML = `
      <div style="text-align:center;max-width:480px;padding:40px;">
        <svg viewBox="0 0 100 100" style="width:64px;height:64px;color:#4F8EF7;margin-bottom:28px;animation:spin 2s linear infinite;">
          <circle cx="50" cy="50" r="16" stroke="currentColor" stroke-width="1.5" fill="none"/>
          <circle cx="50" cy="28" r="12" stroke="currentColor" stroke-width="1.2" fill="none" opacity="0.5"/>
          <circle cx="69" cy="39" r="12" stroke="currentColor" stroke-width="1.2" fill="none" opacity="0.5"/>
          <circle cx="69" cy="61" r="12" stroke="currentColor" stroke-width="1.2" fill="none" opacity="0.5"/>
          <circle cx="50" cy="72" r="12" stroke="currentColor" stroke-width="1.2" fill="none" opacity="0.5"/>
          <circle cx="31" cy="61" r="12" stroke="currentColor" stroke-width="1.2" fill="none" opacity="0.5"/>
          <circle cx="31" cy="39" r="12" stroke="currentColor" stroke-width="1.2" fill="none" opacity="0.5"/>
        </svg>
        <div style="font-family:'DM Sans',sans-serif;font-size:1.1rem;font-weight:500;color:#f1f5f9;margin-bottom:8px;" id="launch-status">Booting Creatrix AI Engine...</div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:#4F8EF7;margin-bottom:32px;" id="launch-pct">0%</div>
        <div style="width:320px;height:3px;background:rgba(255,255,255,0.08);border-radius:100px;overflow:hidden;">
          <div id="launch-bar" style="height:100%;width:0%;background:linear-gradient(90deg,#4F8EF7,#A78BFA);border-radius:100px;transition:width 0.3s ease;"></div>
        </div>
      </div>
    `;

    // Add spin animation
    const style = document.createElement('style');
    style.textContent = '@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }';
    document.head.appendChild(style);
    document.body.appendChild(overlay);

    // Fade in overlay
    requestAnimationFrame(() => { overlay.style.opacity = '1'; });

    const steps = [
      { pct: 20, msg: 'Booting Creatrix AI Engine...' },
      { pct: 40, msg: 'Loading Influencer Intelligence Models...' },
      { pct: 60, msg: 'Connecting Trend Discovery Feeds...' },
      { pct: 80, msg: 'Preparing Viral Content Engine...' },
      { pct: 100, msg: 'Welcome to Creatrix AI ✓' }
    ];

    let i = 0;
    const bar = document.getElementById('launch-bar');
    const statusEl = document.getElementById('launch-status');
    const pctEl = document.getElementById('launch-pct');

    const tick = () => {
      if (i >= steps.length) {
        setTimeout(() => {
          overlay.style.opacity = '0';
          setTimeout(() => window.location.href = 'dashboard.html', 300);
        }, 400);
        return;
      }
      const step = steps[i++];
      bar.style.width = step.pct + '%';
      statusEl.textContent = step.msg;
      pctEl.textContent = step.pct + '%';
      setTimeout(tick, 480);
    };
    tick();
  };

  startLoader();
});

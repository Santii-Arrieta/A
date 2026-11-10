/* Línea de tiempo compartida por index.html (16:9) y vertical.html (9:16).
   Todo es determinista: posiciones fijas por formato, sin azar ni reloj. */
(function () {
  const root = document.getElementById("root");
  const PORT = root.classList.contains("port");
  const W = PORT ? 1080 : 1920;
  const H = PORT ? 1920 : 1080;
  const NS = "http://www.w3.org/2000/svg";
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));
  const hash = (n) => {
    const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
    return x - Math.floor(x);
  };

  /* ───────── layout por formato ───────── */
  // [id, left, top, rotación, borde de entrada, widget destino]
  const ITEMS = PORT
    ? [
        ["i-paper1", 50, 170, -8, "left", 3],
        ["i-sheet", 500, 120, 4, "top", 1],
        ["i-paper2", 650, 430, 9, "right", 3],
        ["i-chat1", 60, 600, -3, "left", 0],
        ["i-map", 480, 800, 3, "right", 2],
        ["i-folder", 60, 900, -6, "left", 3],
        ["i-tractor", 620, 1180, 0, "right", 2],
        ["i-chat2", 90, 1230, 2, "bottom", 0],
        ["i-chat3", 150, 1400, -2, "bottom", 0],
      ]
    : [
        ["i-paper1", 170, 110, -8, "left", 3],
        ["i-sheet", 1230, 80, 4, "top", 1],
        ["i-chat1", 470, 190, -3, "top", 0],
        ["i-map", 760, 420, 3, "bottom", 2],
        ["i-folder", 1470, 520, -6, "right", 3],
        ["i-tractor", 140, 520, 0, "left", 2],
        ["i-chat2", 900, 820, 2, "bottom", 0],
        ["i-chat3", 1100, 650, -2, "right", 0],
        ["i-paper2", 1530, 300, 9, "right", 3],
      ];
  const ARROWS = PORT
    ? [
        [120, 520, 500, 300, 300, 1100, 900, 1300],
        [990, 620, 600, 900, 900, 1300, 200, 1470],
        [540, 300, 200, 700, 900, 900, 620, 1480],
        [80, 1320, 400, 1000, 700, 1100, 1000, 880],
      ]
    : [
        [300, 720, 700, 300, 1100, 900, 1500, 260],
        [1660, 900, 1300, 600, 800, 980, 420, 380],
        [900, 110, 1000, 500, 600, 700, 980, 990],
        [1200, 980, 1400, 500, 1700, 620, 1830, 400],
      ];
  const DASH = PORT ? { l: 50, t: 600, w: 980, h: 940 } : { l: 300, t: 270, w: 1320, h: 740 };
  const WAVE_BASE = PORT ? 0.8 : 0.74;

  // centros de las 4 celdas del panel (misma geometría que .dash-grid en reel.css)
  const gx = DASH.l + 3 + 26;
  const gy = DASH.t + 3 + 84 + 26;
  const cw = (DASH.w - 6 - 52 - 22) / 2;
  const ch = (DASH.h - 6 - 84 - 52 - 22) / 2;
  const CELL = [0, 1, 2, 3].map((i) => ({
    x: gx + (i % 2) * (cw + 22) + cw / 2,
    y: gy + Math.floor(i / 2) * (ch + 22) + ch / 2,
  }));

  /* ───────── fondo ───────── */
  const furrows = $("#furrows");
  const waves = $("#waves");
  const wipeSvg = $("#wipe-svg");
  [furrows, waves].forEach((s) => s.setAttribute("viewBox", `0 0 ${W} ${H}`));

  const horizon = H * (PORT ? 0.6 : 0.52);
  const vpX = W / 2;
  const furrowPaths = [];
  for (let i = -14; i <= 14; i++) {
    const p = document.createElementNS(NS, "path");
    const bx = vpX + i * (W / 9);
    p.setAttribute("d", `M${vpX + i * 6} ${horizon} L${bx} ${H + 20}`);
    furrows.appendChild(p);
    furrowPaths.push(p);
  }
  for (let j = 1; j <= 6; j++) {
    const p = document.createElementNS(NS, "path");
    const y = horizon + (H - horizon) * Math.pow(j / 6, 1.8);
    p.setAttribute("d", `M0 ${y} L${W} ${y}`);
    furrows.appendChild(p);
    furrowPaths.push(p);
  }

  const WAVES = [
    { a: 34, k: 0.0042, s: 0.55, off: 0, w: 2.5, o: 0.55, c: "#ffc600" },
    { a: 26, k: 0.0055, s: -0.42, off: 26, w: 1.8, o: 0.38, c: "#d3b73b" },
    { a: 40, k: 0.0031, s: 0.33, off: 52, w: 1.4, o: 0.26, c: "#ffc600" },
    { a: 20, k: 0.0068, s: -0.6, off: 80, w: 1.2, o: 0.18, c: "#d3b73b" },
  ];
  const wavePaths = WAVES.map((wv) => {
    const p = document.createElementNS(NS, "path");
    p.setAttribute("stroke", wv.c);
    p.setAttribute("stroke-width", wv.w);
    p.setAttribute("opacity", wv.o);
    waves.appendChild(p);
    return p;
  });
  function drawWaves(t) {
    const tc = Math.min(t, 57.8); // últimos 2 s quietos
    WAVES.forEach((wv, i) => {
      const base = H * WAVE_BASE + wv.off;
      let d = "";
      for (let x = -40; x <= W + 40; x += 30) {
        const y =
          base +
          wv.a * Math.sin(x * wv.k + tc * wv.s + i * 1.7) +
          wv.a * 0.35 * Math.sin(x * wv.k * 2.3 - tc * wv.s * 0.8 + i);
        d += (x === -40 ? "M" : "L") + x + " " + y.toFixed(1) + " ";
      }
      wavePaths[i].setAttribute("d", d);
    });
  }
  drawWaves(0);

  /* cortina de transición: relleno de panel con bordes de onda dorada */
  const WW = W + 260;
  const mover = $("#wipe-mover");
  mover.style.left = "-130px";
  mover.style.width = WW + "px";
  wipeSvg.setAttribute("viewBox", `0 0 ${WW} ${H}`);
  wipeSvg.setAttribute("preserveAspectRatio", "none");
  function edge(x0, dir) {
    let d = "";
    for (let y = 0; y <= H; y += 20) {
      const x = x0 + dir * 45 * Math.sin(y * 0.012);
      d += (y === 0 ? "M" : "L") + x.toFixed(1) + " " + y + " ";
    }
    return d;
  }
  const leftEdge = edge(85, 1);
  const rightEdge = edge(WW - 85, -1);
  const fill = document.createElementNS(NS, "path");
  fill.setAttribute("class", "wfill");
  // contorno cerrado: borde izq. de arriba a abajo + borde der. de abajo a arriba
  let rightRev = "";
  for (let y = H; y >= 0; y -= 20) {
    const x = WW - 85 - 45 * Math.sin(y * 0.012);
    rightRev += "L" + x.toFixed(1) + " " + y + " ";
  }
  fill.setAttribute("d", leftEdge + rightRev + "Z");
  wipeSvg.appendChild(fill);
  [leftEdge, rightEdge].forEach((d) => {
    const p = document.createElementNS(NS, "path");
    p.setAttribute("class", "wedge");
    p.setAttribute("d", d);
    wipeSvg.appendChild(p);
  });

  /* flechas cruzadas del caos */
  const arrowsSvg = $("#arrows");
  arrowsSvg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  const arrowGroups = ARROWS.map((a) => {
    const g = document.createElementNS(NS, "g");
    const p = document.createElementNS(NS, "path");
    p.setAttribute("d", `M${a[0]} ${a[1]} C${a[2]} ${a[3]}, ${a[4]} ${a[5]}, ${a[6]} ${a[7]}`);
    const ang = Math.atan2(a[7] - a[5], a[6] - a[4]);
    const hx = (r) => a[6] - 30 * Math.cos(ang + r);
    const hy = (r) => a[7] - 30 * Math.sin(ang + r);
    const head = document.createElementNS(NS, "path");
    head.setAttribute("class", "arrow-head");
    head.setAttribute("d", `M${hx(0.5)} ${hy(0.5)} L${a[6]} ${a[7]} L${hx(-0.5)} ${hy(-0.5)}`);
    g.appendChild(p);
    g.appendChild(head);
    arrowsSvg.appendChild(g);
    return { g, p };
  });

  /* posiciones iniciales de los elementos sueltos */
  ITEMS.forEach(([id, l, t]) => {
    const el = document.getElementById(id);
    el.style.left = l + "px";
    el.style.top = t + "px";
  });

  /* ───────── timeline ───────── */
  const tl = gsap.timeline({ paused: true });
  const IN = "power3.out";
  const OUT = "power2.in";

  // fondo vivo: ondas recalculadas en cada cuadro
  const clock = { t: 0 };
  tl.to(clock, { t: 60, duration: 60, ease: "none", onUpdate: () => drawWaves(clock.t) }, 0);

  function show(sel, t) {
    tl.set(sel, { opacity: 1 }, t);
  }
  function hide(sel, t) {
    tl.set(sel, { opacity: 0 }, t);
  }
  function wipe(t) {
    tl.set("#wipe", { opacity: 1 }, t - 0.26);
    tl.fromTo(mover, { x: -WW }, { x: 0, duration: 0.25, ease: OUT, immediateRender: false }, t - 0.25);
    tl.to(mover, { x: WW, duration: 0.25, ease: IN }, t);
    tl.set("#wipe", { opacity: 0 }, t + 0.26);
  }
  function words(sel, t, stagger = 0.1, y = 34) {
    tl.fromTo(
      sel,
      { opacity: 0, y },
      { opacity: 1, y: 0, duration: 0.6, ease: IN, stagger },
      t
    );
  }

  /* ESCENA 1 · 0–6 */
  furrowPaths.forEach((p) => {
    const len = p.getTotalLength();
    p.style.strokeDasharray = len;
    p.style.strokeDashoffset = len;
  });
  tl.to(furrowPaths, { strokeDashoffset: 0, duration: 1.6, ease: IN, stagger: 0.02 }, 0);
  tl.fromTo("#waves", { opacity: 0 }, { opacity: 1, duration: 1.4, ease: "power1.out" }, 0.2);
  show("#s1", 0);
  tl.fromTo("#s1-rule", { scaleX: 0 }, { scaleX: 1, duration: 0.6, ease: IN }, 0.6);
  words("#s1-title .word", 0.9, 0.1);
  wipe(6.0);
  hide("#s1", 6.0);

  /* ESCENA 2 · 6–16 · caos (rápido y denso) */
  show("#chaos", 6.0);
  const FROM = {
    left: { x: -W * 0.8, y: 0 },
    right: { x: W * 0.8, y: 0 },
    top: { x: 0, y: -H * 0.7 },
    bottom: { x: 0, y: H * 0.7 },
  };
  ITEMS.forEach(([id, , , rot, from], i) => {
    const el = "#" + id;
    const t0 = 6.15 + i * 0.09 + (i > 4 ? 0.35 : 0);
    tl.fromTo(
      el,
      { x: FROM[from].x, y: FROM[from].y, rotation: rot * 3, opacity: 0 },
      { x: 0, y: 0, rotation: rot, opacity: 1, duration: 0.55, ease: IN },
      t0
    );
    // deriva nerviosa hasta el congelamiento
    tl.to(
      el,
      {
        x: (hash(i) - 0.5) * 70,
        y: (hash(i + 9) - 0.5) * 60,
        rotation: rot + (hash(i + 3) - 0.5) * 6,
        duration: 15.0 - (t0 + 0.6),
        ease: "sine.inOut",
      },
      t0 + 0.6
    );
  });
  arrowGroups.forEach((a, i) => {
    tl.fromTo(a.g, { opacity: 0 }, { opacity: 0.85, duration: 0.3, ease: IN }, 8.3 + i * 0.1);
    tl.fromTo(a.p, { strokeDashoffset: 0 }, { strokeDashoffset: -260, duration: 7.7, ease: "none" }, 8.3);
  });
  tl.fromTo("#counter", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.5, ease: IN }, 9.7);
  $$("#counter div").forEach((d, i) => {
    tl.fromTo(d, { opacity: 0, x: -24 }, { opacity: 1, x: 0, duration: 0.45, ease: IN }, 10.0 + i * 1.4);
  });
  // leve temblor de cámara al final del caos
  for (let k = 0; k < 16; k++) {
    const decay = 1 - k / 16;
    tl.to(
      "#chaos-shake",
      { x: (hash(k + 40) - 0.5) * 18 * decay, y: (hash(k + 80) - 0.5) * 12 * decay, duration: 0.05, ease: "none" },
      15.0 + k * 0.05
    );
  }
  tl.to("#chaos-shake", { x: 0, y: 0, duration: 0.05, ease: "none" }, 15.8);

  /* ESCENA 3 · 16–22 · pausa */
  tl.fromTo("#freeze-dim", { opacity: 0 }, { opacity: 0.78, duration: 0.5, ease: "power2.out" }, 16.0);
  tl.fromTo("#chaos-shake", { filter: "blur(0px)" }, { filter: "blur(4px)", duration: 0.5, ease: "power2.out" }, 16.0);
  show("#s3", 16.3);
  words("#s3-title .word", 16.4, 0.1);
  tl.to("#s3-title", { opacity: 0, duration: 0.4, ease: OUT }, 21.6);

  /* ESCENA 4 · 22–34 · convergencia (calmo y ordenado) */
  tl.to("#freeze-dim", { opacity: 0, duration: 0.5, ease: OUT }, 22.0);
  tl.to("#chaos-shake", { filter: "blur(0px)", duration: 0.5, ease: OUT }, 22.0);
  tl.to(["#counter", "#arrows"], { opacity: 0, duration: 0.4, ease: OUT }, 22.0);
  show("#s4", 22.0);
  tl.fromTo("#dash", { opacity: 0, scale: 0.94 }, { opacity: 1, scale: 1, duration: 0.6, ease: IN }, 22.3);
  const GROUP_T = [23.0, 24.4, 25.8, 27.2];
  const seen = [0, 0, 0, 0];
  ITEMS.forEach(([id, l, t, , , w], i) => {
    const el = "#" + id;
    const ft = GROUP_T[w] + seen[w]++ * 0.12;
    tl.fromTo(
      el,
      {
        x: (hash(i) - 0.5) * 70,
        y: (hash(i + 9) - 0.5) * 60,
        rotation: ITEMS[i][3] + (hash(i + 3) - 0.5) * 6,
        scale: 1,
        xPercent: 0,
        yPercent: 0,
      },
      {
        x: CELL[w].x - l,
        y: CELL[w].y - t,
        xPercent: -50,
        yPercent: -50,
        rotation: 0,
        scale: 0.3,
        duration: 0.9,
        ease: "power3.inOut",
        immediateRender: false,
      },
      ft
    );
    tl.to(el, { opacity: 0, duration: 0.3, ease: OUT }, ft + 0.7);
  });
  GROUP_T.forEach((t, w) => {
    tl.fromTo("#w" + w, { opacity: 0, scale: 0.96 }, { opacity: 1, scale: 1, duration: 0.6, ease: IN }, t + 0.8);
    tl.fromTo(
      `#w${w} .row, #w${w} .w-body, #w${w} .inf-head, #w${w} .inf-sub, #w${w} .doc-line`,
      { opacity: 0, y: 12 },
      { opacity: 1, y: 0, duration: 0.45, ease: IN, stagger: 0.08 },
      t + 1.0
    );
  });
  words("#s4-text .word", 28.8, 0.08, 26);
  wipe(34.0);
  hide("#s4", 34.0);
  hide("#chaos", 34.0);

  /* ESCENA 5 · 34–46 · dos accesos */
  show("#s5", 34.0);
  tl.fromTo("#laptop", { opacity: 0, x: -70 }, { opacity: 1, x: 0, duration: 0.7, ease: IN }, 34.2);
  tl.fromTo("#phone", { opacity: 0, x: 70 }, { opacity: 1, x: 0, duration: 0.7, ease: IN }, 34.35);
  tl.fromTo(".lap-row", { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.45, ease: IN, stagger: 0.1 }, 34.8);
  tl.fromTo(".lap-doc", { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.5, ease: IN }, 35.1);
  tl.fromTo(".ph-row", { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.45, ease: IN, stagger: 0.1 }, 35.0);
  tl.fromTo("#lab-a", { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.6, ease: IN }, 35.3);
  tl.fromTo("#lab-b", { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.6, ease: IN }, 35.7);
  // la consultora recorre su lista de clientes
  const lapRows = $$(".lap-row");
  lapRows.forEach((r, i) => {
    const t = 37.5 + i * 2.2;
    tl.to(r, { backgroundColor: "rgba(255,198,0,0.14)", duration: 0.4, ease: "power1.out" }, t);
    tl.to(r, { backgroundColor: "rgba(255,198,0,0)", duration: 0.4, ease: "power1.in" }, t + 1.8);
  });
  tl.to("#s5", { opacity: 0, duration: 0.5, ease: OUT }, 45.8);

  /* ESCENA 6 · 46–54 · beneficios — cada ícono tiene su propia animación */
  show("#s6", 46.2);
  tl.fromTo(".card", { opacity: 0, y: 50 }, { opacity: 1, y: 0, duration: 0.7, ease: IN, stagger: 0.12 }, 46.3);
  function prepDraw(sel) {
    $$(sel).forEach((el) => {
      const L = el.getTotalLength();
      el.style.strokeDasharray = L;
      el.style.strokeDashoffset = L;
    });
  }
  function draw(sel, t, d, stagger = 0) {
    prepDraw(sel);
    tl.to(sel, { strokeDashoffset: 0, duration: d, ease: "power2.inOut", stagger }, t);
  }
  // k0 · historial: se dibuja el reloj, la flecha de "volver atrás" y las agujas giran hacia atrás
  draw("#k0-face", 46.6, 0.8);
  draw("#k0-arrow", 47.1, 0.45);
  tl.fromTo(["#k0-min", "#k0-hr"], { opacity: 0 }, { opacity: 1, duration: 0.3, ease: IN }, 47.0);
  tl.fromTo("#k0-min", { rotation: 0 }, { rotation: -360, svgOrigin: "60 60", duration: 1.4, ease: "power2.inOut" }, 47.2);
  tl.fromTo("#k0-hr", { rotation: 0 }, { rotation: -30, svgOrigin: "60 60", duration: 1.4, ease: "power2.inOut" }, 47.2);
  tl.to("#k0-min", { rotation: -450, svgOrigin: "60 60", duration: 5.0, ease: "none" }, 48.6);
  // k1 · informes: la hoja se dibuja y las líneas se escriben
  draw("#k1-doc", 46.7, 0.8);
  draw(".k1-line", 47.3, 0.4, 0.25);
  tl.set("#k1-l3", { strokeDasharray: "none" }, 48.4);
  tl.to("#k1-l3", { attr: { x2: 80 }, duration: 0.6, ease: "power2.inOut" }, 49.6);
  // k2 · cosecha: ejes, curva y un punto que la recorre
  draw("#k2-axes", 46.8, 0.6);
  draw("#k2-curve", 47.2, 1.4);
  const k2c = $("#k2-curve");
  const k2d = $("#k2-dot");
  const k2L = k2c.getTotalLength();
  const ride = { p: 0 };
  tl.fromTo(k2d, { opacity: 0 }, { opacity: 1, duration: 0.2, ease: IN }, 47.2);
  tl.fromTo(
    ride,
    { p: 0 },
    {
      p: 1,
      duration: 1.4,
      ease: "power2.inOut",
      onUpdate: () => {
        const pt = k2c.getPointAtLength(ride.p * k2L);
        k2d.setAttribute("cx", pt.x.toFixed(2));
        k2d.setAttribute("cy", pt.y.toFixed(2));
      },
    },
    47.2
  );
  [49.4, 51.4].forEach((t) => {
    tl.to(k2d, { attr: { r: 11 }, duration: 0.3, ease: "power2.out" }, t);
    tl.to(k2d, { attr: { r: 7 }, duration: 0.4, ease: "power2.in" }, t + 0.3);
  });
  // k3 · sin señal: suben las barras, se apagan, se tacha la señal y vuelven
  tl.fromTo(".k3-bar", { scaleY: 0 }, { scaleY: 1, transformOrigin: "50% 100%", duration: 0.4, ease: IN, stagger: 0.12 }, 47.0);
  tl.to(".k3-bar", { opacity: 0.35, duration: 0.4, ease: OUT, stagger: { each: 0.1, from: "end" } }, 48.3);
  draw("#k3-slash", 48.8, 0.5);
  tl.to(".k3-bar", { opacity: 1, duration: 0.5, ease: IN, stagger: 0.1 }, 50.6);
  wipe(54.0);
  hide("#s6", 54.0);

  /* ESCENA 5 · el lote 2B pide atención en el celular */
  [38.6, 41.6].forEach((t) => {
    tl.to("#ph-dot2", { scale: 1.7, duration: 0.3, ease: "power2.out" }, t);
    tl.to("#ph-dot2", { scale: 1, duration: 0.4, ease: "power2.in" }, t + 0.3);
  });

  /* ESCENA 7 · 54–60 · cierre con logos y QR (quieto desde 57,8 s) */
  show("#s7", 54.0);
  tl.fromTo("#logo-we", { clipPath: "inset(0% 100% 0% 0%)" }, { clipPath: "inset(0% 0% 0% 0%)", duration: 0.9, ease: "power2.inOut" }, 54.3);
  tl.fromTo("#logo-div", { scaleY: 0 }, { scaleY: 1, duration: 0.4, ease: IN }, 54.6);
  tl.fromTo("#logo-cai", { opacity: 0, scale: 0.7 }, { opacity: 1, scale: 1, duration: 0.6, ease: IN }, 54.7);
  words("#s7-title .word", 55.0, 0.1);
  tl.fromTo("#s7-sub", { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.6, ease: IN }, 55.5);
  tl.fromTo("#qr-card", { opacity: 0, scale: 0.9 }, { opacity: 1, scale: 1, duration: 0.6, ease: IN }, 55.3);
  tl.fromTo("#qr-scan", { opacity: 0 }, { opacity: 1, duration: 0.1, ease: "none" }, 55.9);
  tl.to("#qr-scan", { y: 440, duration: 0.8, ease: "power1.inOut" }, 55.9);
  tl.to("#qr-scan", { opacity: 0, duration: 0.2, ease: OUT }, 56.6);
  tl.fromTo("#cta-btn", { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.6, ease: IN }, 56.0);
  tl.fromTo("#s7-url", { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.6, ease: IN }, 56.3);

  window.__timelines = window.__timelines || {};
  window.__timelines["main"] = tl;
  tl.seek(0);
})();

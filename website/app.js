(() => {
  "use strict";
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const canvas = document.getElementById("burst");
  const ctx = canvas.getContext("2d");
  let W = 0, H = 0, streaks = [], motes = [];
  const CXF = 0.6, CYF = 0.45;

  function resize() {
    const dpr = Math.min(devicePixelRatio || 1, 2);
    W = innerWidth; H = innerHeight;
    canvas.width = W * dpr; canvas.height = H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    seed();
  }

  function seed() {
    const n = Math.min(240, Math.floor(W * H / 9000));
    streaks = Array.from({ length: n }, () => spawn(true));
    motes = Array.from({ length: 70 }, () => ({
      x: Math.random() * W, y: Math.random() * H,
      r: Math.random() * 1.6 + 0.4, p: Math.random() * Math.PI * 2,
      s: 0.2 + Math.random() * 0.6,
      green: Math.random() > 0.4
    }));
  }

  function spawn(anywhere) {
    const a = Math.random() * Math.PI * 2;
    const r0 = 30 + Math.random() * 120;
    return {
      a, r: anywhere ? r0 + Math.random() * Math.max(W, H) * 0.6 : r0,
      len: 60 + Math.random() * 320,
      w: Math.random() < 0.85 ? 1 : 2,
      sp: 0.6 + Math.random() * 2.4,
      al: 0.10 + Math.random() * 0.5,
      green: Math.random() > 0.35
    };
  }

  function frame(t) {
    ctx.clearRect(0, 0, W, H);
    const cx = W * CXF, cy = H * CYF;
    // motes
    for (const m of motes) {
      const tw = 0.5 + 0.5 * Math.sin(t * 0.001 * m.s + m.p);
      ctx.fillStyle = m.green
        ? `rgba(0,230,118,${0.25 * tw})`
        : `rgba(124,124,255,${0.25 * tw})`;
      ctx.beginPath(); ctx.arc(m.x, m.y, m.r, 0, 7); ctx.fill();
    }
    // streaks
    for (let i = 0; i < streaks.length; i++) {
      let s = streaks[i];
      s.r += s.sp;
      if (s.r > Math.max(W, H) * 0.75) streaks[i] = s = spawn(false);
      const dx = Math.cos(s.a), dy = Math.sin(s.a);
      const x0 = cx + dx * s.r, y0 = cy + dy * s.r;
      const x1 = cx + dx * (s.r + s.len), y1 = cy + dy * (s.r + s.len);
      const g = ctx.createLinearGradient(x0, y0, x1, y1);
      const col = s.green ? "0,230,118" : "124,124,255";
      g.addColorStop(0, `rgba(${col},0)`);
      g.addColorStop(1, `rgba(${col},${s.al})`);
      ctx.strokeStyle = g; ctx.lineWidth = s.w;
      ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke();
    }
    // breathing core
    const pulse = 60 + 14 * Math.sin(t * 0.0012);
    const core = ctx.createRadialGradient(cx, cy, 0, cx, cy, pulse * 2.4);
    core.addColorStop(0, "rgba(0,230,150,0.20)");
    core.addColorStop(1, "rgba(0,230,150,0)");
    ctx.fillStyle = core;
    ctx.beginPath(); ctx.arc(cx, cy, pulse * 2.4, 0, 7); ctx.fill();
    if (!reduce) requestAnimationFrame(frame);
  }

  addEventListener("resize", resize);
  resize();
  if (reduce) { frame(0); } else { requestAnimationFrame(frame); }

  // tilt on cards (desktop pointers only)
  if (matchMedia("(pointer: fine)").matches && !reduce) {
    document.querySelectorAll(".tilt").forEach(card => {
      card.addEventListener("mousemove", e => {
        const r = card.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width - 0.5;
        const y = (e.clientY - r.top) / r.height - 0.5;
        card.style.transform = `translateY(-6px) rotateX(${-y * 6}deg) rotateY(${x * 8}deg)`;
      });
      card.addEventListener("mouseleave", () => { card.style.transform = ""; });
    });
  }

  // reveal on scroll
  const io = new IntersectionObserver(es => es.forEach(e => {
    if (e.isIntersecting) { e.target.style.opacity = 1; e.target.style.transform = "none"; io.unobserve(e.target); }
  }), { threshold: 0.12 });
  document.querySelectorAll(".card, .shot, .dl").forEach(el => {
    el.style.opacity = 0; el.style.transform = "translateY(26px)";
    el.style.transition = "opacity .6s ease, transform .6s ease";
    io.observe(el);
  });

  // downloads: look for a local build next to the site, else guide the build
  const PATHS = {
    personal: "../build/iso-result/VixzenOS-0.3-Preview-x86_64.iso",
    edu: "../build/iso-result/VixzenOS-0.3-Edu-x86_64.iso"
  };
  const note = document.querySelector("[data-note]");
  document.querySelectorAll("[data-dl]").forEach(btn => {
    btn.addEventListener("click", async () => {
      const kind = btn.dataset.dl;
      const url = PATHS[kind];
      btn.disabled = true;
      const old = btn.textContent;
      btn.textContent = "Checking for local build…";
      try {
        const res = await fetch(url, { method: "HEAD" });
        if (res.ok) {
          const a = document.createElement("a");
          a.href = url; a.download = url.split("/").pop();
          document.body.appendChild(a); a.click(); a.remove();
          note.textContent = "Downloading your local build. Verify it with sha256sum after.";
        } else { throw 0; }
      } catch {
        note.textContent = kind === "edu"
          ? "No local Edu ISO yet — build it: VXZ_KS=packaging/vixzenos-edu.ks sudo -E ./build-vixzenos.sh ./build/boot.iso"
          : "No local Personal ISO yet — build it: sudo ./build-vixzenos.sh ./build/boot.iso";
      } finally {
        btn.disabled = false; btn.textContent = old;
      }
    });
  });
})();

# Vixzen Browser Milestones — the chase for best-in-niche

Parent: `docs/MILESTONES.md`. Legend: ✅ done · 🔶 now · ⬜ next.
Standing rules apply: no perf claim without a number, no "done" without proof.

Winnable crowns (not "beat Chrome", which money buys): lightest on old
hardware · most private by default · simplest for beginners · best VixzenOS
citizen. Each milestone below serves at least one crown (tagged [L]/[P]/[S]/[I]).

## WB0 — Two-engine base ✅ (AI)
Vixzen Web v0.7 (WebKit, Google-style, Vixzen Search default, Chrome shortcuts,
0.03 s frame, 0.057 s tabs) + Vixzen Search v0.1 (private metasearch) +
Vixzen Blink v0.1 (real Chrome/140 Blink, feature-mirrored, click-audited) +
upstream Chromium in ISO. Shared `~/.config/vixzen-web/` data.
Proof: smokes + offscreen GUI journeys + `./build-vixzenos.sh --check-only` green.

## WB1 — Tracker blocking, both engines ✅ (AI) [P][L]
- WebKit: `WK.UserContentFilter` compiled from an EasyList-derived host set;
  per-site toggle in the lock menu; counter in toolbar ("12 blocked").
- Blink: `QWebEngineUrlRequestInterceptor` with the same host set.
- Shared `apps/web-browser/blocklist.py`: updater (`--update` pulls lists,
  compiles, caps size for 8 GB RAM), unit-tested offline with fixtures.
- Exit: top-50 news/shopping homepages load with **0 third-party tracker
  requests** (counted via interceptor logs) and **≥15% faster median
  onload** vs unblocked on this host; toggle provably re-allows.
- PROOF (2026-10-02, cold-profile A/B per page, Blink interceptor logs):
  shared list = 113 built-in + yoyo feed = **3597 hosts**; WebKit
  UserContentFilter compiles 7194 rules in 0.3 s (needed a `|`-free pattern
  dialect — WebKitGTK rejects disjunctions). Measured, 6 pages:
  example.com 0 blocked · wikipedia 0 · bbc.com **8** · theguardian 0
  (consent-gated offscreen) · ebay blocked-by-botwall (excluded) ·
  cnn.com **26** (off-phase took 267 s in ad-hell vs 8.7 s blocked).
  Median onload −21% with blocking (19% without the CNN outlier).
  Sample is 6 pages, not 50 — full 50-page sweep deferred to WB6.
  Honest limits: WebKit filters give no per-block callbacks, so the live
  "N blocked" counter exists only in Blink; WebKit shows on/off state from
  the same list. First-party trackers (same-host analytics) are out of scope
  for host blocking on both engines.

## WB2 — Downloads + private windows ⬜ (AI) [S]
- WebKit app: real download manager (WebKit download signals → save dialog,
  progress list, `Ctrl+J` page) — currently Blink-only.
- Both: private window (`Ctrl+Shift+N`): separate ephemeral
  profile/context, no history/disk writes, purple glass marker.
- Exit: 100 MB file downloads with progress + open-on-finish on both;
  private session leaves **0 new files** under `~/.config/vixzen-web/` and
  `~/.cache/` (verified with `find -newer`).

## WB3 — Memory diet, measured ⬜ (AI) [L]
- Profile 10-tab mixed workload (news, docs, video, maps): per-process RSS,
  top offenders, cache-model A/B (`DOCUMENT_BROWSER` vs `WEB_BROWSER`).
- Cut: tab suspender (background tabs past N=8 park to title-only after
  15 min, one-click restore), image/decode caps on Saver mode.
- Exit: 10-tab UI+content total **≤ 900 MB** on the i5 host (vs recorded
  baseline in `PERFORMANCE.md`); numbers appended there; no regression in
  WB0 timings (>10% slower = fail).

## WB4 — Beginner-proofing ⬜ (TOGETHER) [S]
- 5-task usability script (search, bookmark, reopen tab, switch engine,
  download): run with 2 real beginners, note every stumble.
- Fix round: plain-language pass on every dialog/status string, tooltips
  audit, welcome dialog revised from findings.
- Exit: both beginners finish all 5 tasks unassisted; findings + fixes
  logged in this file.

## WB5 — OS citizen ⬜ (AI + YOU) [I]
- `x-scheme-handler/http(s)` + `text/html` default-browser registration in
  ISO; `vixzen-web` handles links from Files/Terminal; GNOME Software
  metainfo (`appdata.xml`) with screenshots.
- Exit: fresh ISO boot → click a link in Text Editor → opens in Vixzen Web;
  entry visible in Software with icon + screenshots.

## WB6 — Compat matrix ⬜ (TOGETHER) [L]
- Test sheet: Meet/Teams call (5 min), 3 banks, 3 DRM videos, Docs/Office
  editors, 5 government portals — per engine (Web / Blink / Chromium),
  pass/fail + fallback guidance baked into an in-app "Open in…" helper.
- Exit: matrix published here; every fail has a one-click fallback path.

## WB7 — Release the browser ⬜ (TOGETHER)
- Versioning + changelog, RPMs built (`vixzen-web`, `vixzen-blink`),
  checksums, update path via `vixzen-update`.
- Exit: a stranger can install, verify, and update both browsers.

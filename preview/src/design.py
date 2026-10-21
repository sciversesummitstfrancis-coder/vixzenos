"""VixzenOS design tokens — single source of truth for preview + future apps."""
THEMES = {
    "light": {
        "bg": "#F2F3F7", "fg": "#1A1D29", "taskbar": "#E8EAF2",
        "card": "#FFFFFF", "accent": "#4F46E5", "accent_fg": "#FFFFFF",
        "secondary": "#06B6D4", "border": "#D4D8E3",
    },
    "dark": {
        "bg": "#12141C", "fg": "#E8EAF2", "taskbar": "#1B1E2A",
        "card": "#1E2230", "accent": "#7C7CFF", "accent_fg": "#0B0C12",
        "secondary": "#22D3EE", "border": "#2E3448",
    },
}
ACCENT_NAME = "Vixzen Indigo"
# Liquid Glass (Apple-inspired, original implementation): frosted translucency,
# specular top edge, inner glow, floating surfaces. Real backdrop-blur comes
# from the compositor; GTK simulates with rgba layering, WebKit pages can use
# real `backdrop-filter`. No Apple assets copied.
LIQUID_GLASS = """
window { background: linear-gradient(160deg, #1a1d33 0%, #12141C 45%, #0a1628 100%); }
.glass-shell { background: transparent; }
.glass-sidebar { background-color: rgba(30,34,48,0.55);
  border: 1px solid rgba(255,255,255,0.16);
  border-top-color: rgba(255,255,255,0.42);
  border-left-color: rgba(255,255,255,0.24);
  border-radius: 22px;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.22),
              inset 0 -1px 0 rgba(255,255,255,0.06),
              0 8px 28px rgba(0,0,0,0.38); }
.glass-sidebar button { border-radius: 999px; min-width: 36px; min-height: 36px;
  background-color: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.10); }
.glass-sidebar button:hover { background-color: rgba(124,124,255,0.35);
  border-top-color: rgba(255,255,255,0.5);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.3), 0 0 16px rgba(124,124,255,0.45); }
.glass-tabstrip { background-color: rgba(27,30,42,0.45);
  border: 1px solid rgba(255,255,255,0.12);
  border-top-color: rgba(255,255,255,0.32);
  border-radius: 18px;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.16), 0 6px 20px rgba(0,0,0,0.30); }
.glass-tabstrip tab { border-radius: 12px; }
.glass-tabstrip tab:selected { background-color: rgba(124,124,255,0.30);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.35); }
.glass-bar { background-color: rgba(30,34,48,0.55);
  border: 1px solid rgba(255,255,255,0.14);
  border-top-color: rgba(255,255,255,0.38);
  border-radius: 20px;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.20), 0 10px 32px rgba(0,0,0,0.40); }
.glass-bar entry, .glass-omnibox { border-radius: 999px;
  background-color: rgba(10,12,20,0.55);
  border: 1px solid rgba(255,255,255,0.16);
  border-top-color: rgba(255,255,255,0.40);
  box-shadow: inset 0 1px 8px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.12);
  padding: 6px 16px; }
.glass-bar entry:focus { border-color: rgba(124,124,255,0.8);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.2), 0 0 20px rgba(124,124,255,0.5); }
.glass-bar button { border-radius: 999px; background-color: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.10); }
.glass-bar button:hover { background-color: rgba(124,124,255,0.35);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.3), 0 0 14px rgba(124,124,255,0.4); }
.glass-view { border-radius: 18px; border: 1px solid rgba(255,255,255,0.14);
  border-top-color: rgba(255,255,255,0.34);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.18), 0 12px 40px rgba(0,0,0,0.45); }
.glass-pill { background-color: rgba(30,34,48,0.55);
  border: 1px solid rgba(255,255,255,0.14);
  border-top-color: rgba(255,255,255,0.35);
  border-radius: 999px;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.18), 0 6px 18px rgba(0,0,0,0.35); }
"""
# Chrome skin (Google-Chrome look, original CSS values sampled from its
# Material You light theme): flat light surfaces, white toolbar, gray pill
# omnibox, square content edge. Styles the SAME classes as LIQUID_GLASS so
# the browser can hot-swap skins. No Google assets used.
CHROME_SKIN = """
window { background: #D4D9E3; color: #202124; }
.glass-shell { background: #D4D9E3; }
.glass-sidebar { background-color: transparent; border: none; border-radius: 0;
  box-shadow: none; }
.glass-tabstrip { background-color: #D4D9E3; border: none; border-radius: 0;
  box-shadow: none; }
.glass-tabstrip tab { border-radius: 10px 10px 0 0; }
.glass-tabstrip tab:selected { background-color: #FFFFFF; box-shadow: none; }
.glass-tabstrip tab:hover { background-color: rgba(32,33,36,0.08); }
.glass-bar { background-color: #FFFFFF; border: none; border-radius: 0;
  box-shadow: 0 1px 0 rgba(32,33,36,0.12); }
.glass-bar entry, .glass-omnibox { border-radius: 999px;
  background-color: #F1F3F4; color: #202124; border: 1px solid transparent;
  box-shadow: none; padding: 6px 16px; }
.glass-bar entry:focus { border-color: #1A73E8;
  box-shadow: 0 0 0 1px #1A73E8; background-color: #FFFFFF; }
.glass-bar button { border-radius: 999px; background-color: transparent;
  border: none; color: #5F6368; box-shadow: none; }
.glass-bar button:hover { background-color: rgba(32,33,36,0.08); box-shadow: none; }
.glass-view { border: none; border-radius: 0; box-shadow: none; }
.glass-pill { background-color: #F1F3F4; color: #5F6368; border: none;
  border-radius: 999px; box-shadow: none; }
headerbar { background-color: #FFFFFF; color: #202124; }
entry { color: #202124; }
.chrome-avatar { background: #8E24AA; color: #FFFFFF; border-radius: 999px;
  font-weight: 800; }
"""
# Insane motion for the browser (opt-in only): pulsing focus ring, glowing
# tab hover, shimmering progress. GTK4 supports @keyframes; infinite loops
# are confined to :focus/:hover so idle windows stay cheap.
INSANE_MOTION = """
@keyframes vix-pulse {
  0% { box-shadow: inset 0 1px 0 rgba(255,255,255,0.25), 0 0 6px rgba(124,124,255,0.35); }
  50% { box-shadow: inset 0 1px 0 rgba(255,255,255,0.35), 0 0 22px rgba(124,124,255,0.75); }
  100% { box-shadow: inset 0 1px 0 rgba(255,255,255,0.25), 0 0 6px rgba(124,124,255,0.35); } }
@keyframes vix-tabglow {
  0% { background-color: rgba(124,124,255,0.10); }
  50% { background-color: rgba(124,124,255,0.38); }
  100% { background-color: rgba(124,124,255,0.10); } }
.glass-bar entry:focus { animation: vix-pulse 1.4s ease-in-out infinite; }
.glass-tabstrip tab:hover { animation: vix-tabglow 1.1s ease-in-out infinite; }
.glass-sidebar button:hover { box-shadow: inset 0 1px 0 rgba(255,255,255,0.35),
  0 0 20px rgba(124,124,255,0.65); }
progressbar progress { transition-duration: 600ms; }
"""
# Liquid-glass accent pass (our own take: soft translucency + specular top
# edge + faint inner glow; real background-blur comes from the compositor /
# blur extensions. No copied assets.)
LIQUID_CARD = """
.vix-card { background-color: rgba(255,255,255,0.09);
            border: 1px solid rgba(255,255,255,0.16);
            border-top-color: rgba(255,255,255,0.38);
            border-left-color: rgba(255,255,255,0.22);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.18); }
.vix-taskbar { border-top: 1px solid rgba(255,255,255,0.16); }
button:hover { background-color: rgba(124,124,255,0.30); }
"""
ACCENTS = {
    "Vixzen Indigo": {"light": "#4F46E5", "dark": "#7C7CFF"},
    "Pulse Cyan": {"light": "#0891B2", "dark": "#22D3EE"},
    "Ember Coral": {"light": "#EA580C", "dark": "#FB923C"},
    "Neon Surge": {"light": "#00A651", "dark": "#00E676"},
}
RADIUS = 10
SPACING = 8
PERF_MODES = ("saver", "balanced", "enhanced", "insane")
WALLPAPERS = {
    "Starry Night": ("#0A0E2A", "#02040E"),
    "Vixzen Signature": ("#4F46E5", "#020617"),
    "Indigo Dusk": ("#4F46E5", "#12141C"),
    "Slate Calm": ("#334155", "#0F172A"),
    "Deep Night": ("#1E1B4B", "#020617"),
    "Neon Burst": ("#00E676", "#020806"),
}
# Real image files for host use (brand.json default stays gradient-safe).
WALLPAPER_FILES = {
    "Starry Night": "assets/wallpapers/vixzen-starry-1920x1080.png",
    "Vixzen Signature": "assets/wallpapers/vixzen-signature-1920x1080.png",
    "Indigo Dusk": "assets/wallpapers/indigo-dusk.svg",
    "Neon Burst": "assets/wallpapers/vixzen-burst-1920x1080.png",
}

def css_for(theme_name: str, perf_mode: str = "balanced",
            wallpaper: str = "Indigo Dusk", accent: str = "Vixzen Indigo") -> str:
    t = dict(THEMES[theme_name])
    t["accent"] = ACCENTS.get(accent, list(ACCENTS.values())[0])[theme_name]
    dur = {"saver": "0ms", "balanced": "150ms", "enhanced": "220ms",
           "insane": "600ms"}[perf_mode]
    if perf_mode == "insane":
        shadow = ("0 0 32px rgba(124,124,255,0.45), "
                  "0 8px 24px rgba(0,0,0,0.35)")
    else:
        shadow = "none" if perf_mode != "enhanced" else "0 4px 16px rgba(0,0,0,0.25)"
    insane_extra = ""
    if perf_mode == "insane":
        insane_extra = """
    button:hover { box-shadow: 0 0 18px rgba(124,124,255,0.6); }
    .vix-card:hover { box-shadow: 0 0 28px rgba(124,124,255,0.5); }
    .vix-accent { box-shadow: 0 0 22px rgba(124,124,255,0.55); }
    .vix-hero { box-shadow: 0 0 40px rgba(79,70,229,0.5); }
    """
    w1, w2 = WALLPAPERS.get(wallpaper, list(WALLPAPERS.values())[0])
    return f"""
    window {{ background-color: {t['bg']}; color: {t['fg']}; }}
    .vix-taskbar {{ background-color: {t['taskbar']}; border-top: 1px solid {t['border']}; }}
    .vix-card {{ background-color: {t['card']}; border: 1px solid {t['border']};
                border-radius: {RADIUS}px; box-shadow: {shadow}; }}
    .vix-accent {{ background-color: {t['accent']}; color: {t['accent_fg']};
                  border-radius: {RADIUS}px; }}
    .vix-active {{ border-bottom: 2px solid {t['accent']}; border-radius: 6px;
                  background-color: {t['card']}; }}
    .vix-hero {{ background: linear-gradient(135deg, {w1}, {w2});
                border-radius: {RADIUS}px; color: white; }}
    button, entry, list row {{ transition-duration: {dur}; }}
    {insane_extra}"""

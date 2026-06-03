"""
Design tokens — DampfrossDigital design system (Variation A · Stations).
Single source of truth for all colors, radii, type sizes, shadows, motion
constants, and theme data used across the UI.
"""
from __future__ import annotations
from PyQt6.QtGui import QColor, QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

# ── Neutrals — warm paper (light theme defaults) ───────────────────────── #
PAPER      = QColor("#f4f2ec")
SURFACE    = QColor("#ffffff")
SURFACE_2  = QColor("#fbfaf6")
SUNK       = QColor("#ece9e1")
INK        = QColor("#14171c")
INK_1      = QColor("#2a2e36")
INK_2      = QColor("#5a5f6a")
INK_3      = QColor("#8a8f99")
INK_4      = QColor("#b9bcc3")
RULE       = QColor("#e2dfd7")
RULE_SOFT  = QColor("#ecead3")

# ── Player line colors — transit map palette ───────────────────────────── #
P1 = QColor("#e23b3b")   # S1 · Red Line
P2 = QColor("#1f6fd9")   # S2 · Blue Line
P3 = QColor("#1f7a4a")   # S3 · Green Line
P4 = QColor("#e8a915")   # S4 · Yellow Line
P5 = QColor("#e76018")   # S5 · Orange Line
P6 = QColor("#7a4dd0")   # S6 · Violet Line
P7 = QColor("#0a9aa1")   # S7 · Teal Line
P8 = QColor("#d3398a")   # S8 · Magenta Line

PLAYER_COLORS = [P1, P2, P3, P4, P5, P6, P7, P8]

PLAYER_COLORS_HEX = [
    ("#e23b3b", "Rot"),
    ("#1f6fd9", "Blau"),
    ("#1f7a4a", "Grün"),
    ("#e8a915", "Gelb"),
    ("#e76018", "Orange"),
    ("#7a4dd0", "Lila"),
    ("#0a9aa1", "Türkis"),
    ("#d3398a", "Magenta"),
]

# Named player-color lookup helpers
_P_HEX  = [h for h, _ in PLAYER_COLORS_HEX]   # index 0 = P1
_P_NAME = [n for _, n in PLAYER_COLORS_HEX]

def player_color(idx_1based: int) -> QColor:
    """Return QColor for player 1-8."""
    return PLAYER_COLORS[max(0, min(7, idx_1based - 1))]

def player_hex(idx_1based: int) -> str:
    """Return hex string for player 1-8."""
    return _P_HEX[max(0, min(7, idx_1based - 1))]

def player_name(idx_1based: int) -> str:
    """Return display name for player 1-8."""
    return _P_NAME[max(0, min(7, idx_1based - 1))]

# ── Player tints (for soft backgrounds / badges / halos) ──────────────── #
P1_TINT = QColor("#fcdede")
P2_TINT = QColor("#dde9fb")
P3_TINT = QColor("#dbece2")
P4_TINT = QColor("#fbecc4")
P5_TINT = QColor("#fbdec8")
P6_TINT = QColor("#e6dcfa")
P7_TINT = QColor("#cfeced")
P8_TINT = QColor("#fadbeb")

PLAYER_TINTS = [P1_TINT, P2_TINT, P3_TINT, P4_TINT,
                P5_TINT, P6_TINT, P7_TINT, P8_TINT]

def player_tint(idx_1based: int) -> QColor:
    return PLAYER_TINTS[max(0, min(7, idx_1based - 1))]

# ── Map terrain ────────────────────────────────────────────────────────── #
TERRAIN_PLAIN    = QColor("#faf8f2")
TERRAIN_FOREST   = QColor("#d9e7d1")
TERRAIN_MOUNTAIN = QColor("#d8cebd")
TERRAIN_WATER    = QColor("#cee0ed")
TERRAIN_DESERT   = QColor("#ecd6a8")
TERRAIN_SWAMP    = QColor("#c9c8b1")
RIVER            = QColor("#5ea4d6")
COAST            = QColor("#b9d2e3")

TERRAIN_COLORS: dict[str, QColor] = {
    "plain":    TERRAIN_PLAIN,
    "forest":   TERRAIN_FOREST,
    "mountain": TERRAIN_MOUNTAIN,
    "water":    TERRAIN_WATER,
    "desert":   TERRAIN_DESERT,
    "swamp":    TERRAIN_SWAMP,
}

# ── Semantic ───────────────────────────────────────────────────────────── #
SUCCESS = QColor("#1f7a4a")
WARN    = QColor("#e8a915")
DANGER  = QColor("#e23b3b")
INFO    = QColor("#1f6fd9")

# ── Radius constants (px) ──────────────────────────────────────────────── #
R_1    = 4
R_2    = 8
R_3    = 12
R_4    = 16
R_PILL = 999

# ── Shadow definitions — (offset_x, offset_y, blur, spread, color_hex, alpha) #
# Stored as tuples; rendered via widget stylesheet or custom QPainter.
SH_0 = "0 1px 0 rgba(20,23,28,.04)"
SH_1 = "0 1px 2px rgba(20,23,28,.06), 0 1px 1px rgba(20,23,28,.04)"
SH_2 = "0 4px 16px rgba(20,23,28,.08), 0 1px 2px rgba(20,23,28,.04)"
SH_3 = "0 16px 40px rgba(20,23,28,.14), 0 2px 4px rgba(20,23,28,.06)"

# ── Motion — duration in ms ────────────────────────────────────────────── #
DUR_SNAP  = 120
DUR_BASE  = 220
DUR_GLIDE = 420
DUR_TRAIN = 900

# ── Map metrics ────────────────────────────────────────────────────────── #
HEX_SIZE_DEFAULT = 56    # px outer radius (design reference)
TRACK_WIDTH      = 7     # px
TRACK_STROKE     = 2     # px (casing overlap each side)

# ── Pre-computed color-mix() equivalents ──────────────────────────────────#
# color-mix(in srgb, var(--ink) 92%, transparent) → ink at 92% opacity
HUD_BG = QColor(20, 23, 28, int(0.92 * 255))       # dark pill background
HUD_DIVIDER = QColor(244, 242, 236, int(0.25 * 255))  # paper at 25% on dark
HUD_TURN_TEXT = QColor(244, 242, 236, int(0.65 * 255))  # paper at 65% on dark

# color-mix(in srgb, var(--pN) 6%, var(--surface)) for active player card bg:
# applied per-player at runtime — see active_player_bg()
# color-mix(in srgb, var(--pN) 30%, var(--rule)) for active player card border:
# applied per-player at runtime — see active_player_border()

def active_player_bg(player_color_hex: str) -> QColor:
    """Surface color tinted 6% with the player color (active card background)."""
    c = QColor(player_color_hex)
    # blend: 94% white + 6% player
    r = int(255 * 0.94 + c.red()   * 0.06)
    g = int(255 * 0.94 + c.green() * 0.06)
    b = int(255 * 0.94 + c.blue()  * 0.06)
    return QColor(r, g, b)

def active_player_border(player_color_hex: str) -> QColor:
    """Rule color tinted 30% with player color (active card border)."""
    c = QColor(player_color_hex)
    r_base = RULE
    r = int(r_base.red()   * 0.70 + c.red()   * 0.30)
    g = int(r_base.green() * 0.70 + c.green() * 0.30)
    b = int(r_base.blue()  * 0.70 + c.blue()  * 0.30)
    return QColor(r, g, b)

# ── Hex strings for Qt stylesheets ────────────────────────────────────────#
S_PAPER     = "#f4f2ec"
S_SURFACE   = "#ffffff"
S_SURFACE_2 = "#fbfaf6"
S_SUNK      = "#ece9e1"
S_INK       = "#14171c"
S_INK_1     = "#2a2e36"
S_INK_2     = "#5a5f6a"
S_INK_3     = "#8a8f99"
S_INK_4     = "#b9bcc3"
S_RULE      = "#e2dfd7"
S_RULE_SOFT = "#ecead3"

S_P1 = "#e23b3b"; S_P2 = "#1f6fd9"; S_P3 = "#1f7a4a"; S_P4 = "#e8a915"
S_P5 = "#e76018"; S_P6 = "#7a4dd0"; S_P7 = "#0a9aa1"; S_P8 = "#d3398a"

S_P1_TINT = "#fcdede"; S_P2_TINT = "#dde9fb"; S_P3_TINT = "#dbece2"
S_P4_TINT = "#fbecc4"; S_P5_TINT = "#fbdec8"; S_P6_TINT = "#e6dcfa"
S_P7_TINT = "#cfeced"; S_P8_TINT = "#fadbeb"

_S_P_HEX   = [S_P1, S_P2, S_P3, S_P4, S_P5, S_P6, S_P7, S_P8]
_S_P_TINTS = [S_P1_TINT, S_P2_TINT, S_P3_TINT, S_P4_TINT,
              S_P5_TINT, S_P6_TINT, S_P7_TINT, S_P8_TINT]

def s_player(idx_1based: int) -> str:
    return _S_P_HEX[max(0, min(7, idx_1based - 1))]

def s_player_tint(idx_1based: int) -> str:
    return _S_P_TINTS[max(0, min(7, idx_1based - 1))]

S_TERRAIN_PLAIN    = "#faf8f2"
S_TERRAIN_FOREST   = "#d9e7d1"
S_TERRAIN_MOUNTAIN = "#d8cebd"
S_TERRAIN_WATER    = "#cee0ed"
S_TERRAIN_DESERT   = "#ecd6a8"
S_TERRAIN_SWAMP    = "#c9c8b1"
S_RIVER            = "#5ea4d6"
S_COAST            = "#b9d2e3"

S_SUCCESS = "#1f7a4a"
S_WARN    = "#e8a915"
S_DANGER  = "#e23b3b"
S_INFO    = "#1f6fd9"

# ── Theme data — overrides applied by set_theme() ─────────────────────── #
_THEMES: dict[str, dict] = {
    "light": {
        "S_PAPER": "#f4f2ec", "S_SURFACE": "#ffffff", "S_SURFACE_2": "#fbfaf6",
        "S_SUNK": "#ece9e1",
        "S_INK": "#14171c", "S_INK_1": "#2a2e36", "S_INK_2": "#5a5f6a",
        "S_INK_3": "#8a8f99", "S_INK_4": "#b9bcc3",
        "S_RULE": "#e2dfd7", "S_RULE_SOFT": "#ecead3",
        "S_TERRAIN_PLAIN": "#faf8f2", "S_TERRAIN_FOREST": "#d9e7d1",
        "S_TERRAIN_MOUNTAIN": "#d8cebd", "S_TERRAIN_WATER": "#cee0ed",
        "S_TERRAIN_DESERT": "#ecd6a8", "S_TERRAIN_SWAMP": "#c9c8b1",
        "S_RIVER": "#5ea4d6", "S_COAST": "#b9d2e3",
        "S_P1": "#e23b3b", "S_P2": "#1f6fd9", "S_P3": "#1f7a4a", "S_P4": "#e8a915",
        "S_P5": "#e76018", "S_P6": "#7a4dd0", "S_P7": "#0a9aa1", "S_P8": "#d3398a",
    },
    "dark": {
        "S_PAPER": "#0f1218", "S_SURFACE": "#161a22", "S_SURFACE_2": "#1b202a",
        "S_SUNK": "#0a0d12",
        "S_INK": "#f1efe9", "S_INK_1": "#d4d2cb", "S_INK_2": "#9aa0ac",
        "S_INK_3": "#6c727e", "S_INK_4": "#3f4551",
        "S_RULE": "#262b36", "S_RULE_SOFT": "#1d212a",
        "S_TERRAIN_PLAIN": "#1a1f29", "S_TERRAIN_FOREST": "#1d2a23",
        "S_TERRAIN_MOUNTAIN": "#2a241c", "S_TERRAIN_WATER": "#142434",
        "S_TERRAIN_DESERT": "#2c2516", "S_TERRAIN_SWAMP": "#232218",
        "S_RIVER": "#4f86b3", "S_COAST": "#2b3f50",
        "S_P1": "#ff5c5c", "S_P2": "#4f93f0", "S_P3": "#4ba879", "S_P4": "#f3bf3a",
        "S_P5": "#ff7e3f", "S_P6": "#9c79e9", "S_P7": "#34b8bd", "S_P8": "#ec5fa3",
    },
    "sepia": {
        "S_PAPER": "#efe3ca", "S_SURFACE": "#f7ecd2", "S_SURFACE_2": "#f2e4c2",
        "S_SUNK": "#e2d2b1",
        "S_INK": "#2a1d09", "S_INK_1": "#463318", "S_INK_2": "#76603e",
        "S_INK_3": "#a48c63", "S_INK_4": "#c4b18a",
        "S_RULE": "#d2bf95", "S_RULE_SOFT": "#dfcfa6",
        "S_TERRAIN_PLAIN": "#f7ecd2", "S_TERRAIN_FOREST": "#cbd6a8",
        "S_TERRAIN_MOUNTAIN": "#d4c089", "S_TERRAIN_WATER": "#c8d8c9",
        "S_TERRAIN_DESERT": "#e6c986", "S_TERRAIN_SWAMP": "#b8b083",
        "S_RIVER": "#6b9b86", "S_COAST": "#b6c5a8",
        "S_P1": "#e23b3b", "S_P2": "#1f6fd9", "S_P3": "#1f7a4a", "S_P4": "#e8a915",
        "S_P5": "#e76018", "S_P6": "#7a4dd0", "S_P7": "#0a9aa1", "S_P8": "#d3398a",
    },
}

_current_theme: str = "light"

def current_theme() -> str:
    return _current_theme

def theme_tokens(name: str = "light") -> dict:
    """Return the token dict for a theme name (light/dark/sepia)."""
    return _THEMES.get(name, _THEMES["light"])

def set_theme(name: str) -> None:
    """
    Switch global theme. Updates all module-level S_* variables so that widgets
    built after the switch use the new values. Widgets already constructed must
    rebuild their stylesheets; they should connect to QApplication's custom
    theme_changed signal or call their own refresh method.
    """
    global _current_theme
    global S_PAPER, S_SURFACE, S_SURFACE_2, S_SUNK
    global S_INK, S_INK_1, S_INK_2, S_INK_3, S_INK_4
    global S_RULE, S_RULE_SOFT
    global S_TERRAIN_PLAIN, S_TERRAIN_FOREST, S_TERRAIN_MOUNTAIN
    global S_TERRAIN_WATER, S_TERRAIN_DESERT, S_TERRAIN_SWAMP
    global S_RIVER, S_COAST
    global S_P1, S_P2, S_P3, S_P4, S_P5, S_P6, S_P7, S_P8
    global PAPER, SURFACE, SURFACE_2, SUNK, INK, INK_1, INK_2, INK_3, INK_4
    global RULE, RULE_SOFT
    global TERRAIN_PLAIN, TERRAIN_FOREST, TERRAIN_MOUNTAIN
    global TERRAIN_WATER, TERRAIN_DESERT, TERRAIN_SWAMP, RIVER, COAST
    global HUD_BG, HUD_DIVIDER, HUD_TURN_TEXT

    t = _THEMES.get(name, _THEMES["light"])
    _current_theme = name

    # Update string vars
    S_PAPER     = t["S_PAPER"];    S_SURFACE   = t["S_SURFACE"]
    S_SURFACE_2 = t["S_SURFACE_2"]; S_SUNK    = t["S_SUNK"]
    S_INK       = t["S_INK"];      S_INK_1    = t["S_INK_1"]
    S_INK_2     = t["S_INK_2"];    S_INK_3    = t["S_INK_3"]
    S_INK_4     = t["S_INK_4"];    S_RULE     = t["S_RULE"]
    S_RULE_SOFT = t["S_RULE_SOFT"]
    S_TERRAIN_PLAIN    = t["S_TERRAIN_PLAIN"]
    S_TERRAIN_FOREST   = t["S_TERRAIN_FOREST"]
    S_TERRAIN_MOUNTAIN = t["S_TERRAIN_MOUNTAIN"]
    S_TERRAIN_WATER    = t["S_TERRAIN_WATER"]
    S_TERRAIN_DESERT   = t["S_TERRAIN_DESERT"]
    S_TERRAIN_SWAMP    = t["S_TERRAIN_SWAMP"]
    S_RIVER     = t["S_RIVER"];    S_COAST    = t["S_COAST"]
    S_P1 = t["S_P1"]; S_P2 = t["S_P2"]; S_P3 = t["S_P3"]; S_P4 = t["S_P4"]
    S_P5 = t["S_P5"]; S_P6 = t["S_P6"]; S_P7 = t["S_P7"]; S_P8 = t["S_P8"]

    # Update QColor vars
    PAPER      = QColor(S_PAPER);    SURFACE    = QColor(S_SURFACE)
    SURFACE_2  = QColor(S_SURFACE_2); SUNK      = QColor(S_SUNK)
    INK        = QColor(S_INK);      INK_1      = QColor(S_INK_1)
    INK_2      = QColor(S_INK_2);    INK_3      = QColor(S_INK_3)
    INK_4      = QColor(S_INK_4);    RULE       = QColor(S_RULE)
    RULE_SOFT  = QColor(S_RULE_SOFT)
    TERRAIN_PLAIN    = QColor(S_TERRAIN_PLAIN)
    TERRAIN_FOREST   = QColor(S_TERRAIN_FOREST)
    TERRAIN_MOUNTAIN = QColor(S_TERRAIN_MOUNTAIN)
    TERRAIN_WATER    = QColor(S_TERRAIN_WATER)
    TERRAIN_DESERT   = QColor(S_TERRAIN_DESERT)
    TERRAIN_SWAMP    = QColor(S_TERRAIN_SWAMP)
    RIVER = QColor(S_RIVER);  COAST = QColor(S_COAST)

    ink = QColor(S_INK)
    paper = QColor(S_PAPER)
    HUD_BG       = QColor(ink.red(), ink.green(), ink.blue(), int(0.92 * 255))
    HUD_DIVIDER  = QColor(paper.red(), paper.green(), paper.blue(), int(0.25 * 255))
    HUD_TURN_TEXT= QColor(paper.red(), paper.green(), paper.blue(), int(0.65 * 255))


# ── Font loading ──────────────────────────────────────────────────────────#
_fonts_loaded = False

def ensure_fonts() -> None:
    """
    Load Geist + Geist Mono from ~/.cache/dampfross/fonts/ if present.
    Falls back gracefully to system sans-serif if fonts are not cached.
    Call once from main() before creating the QApplication.
    """
    global _fonts_loaded
    if _fonts_loaded:
        return
    import pathlib
    import platformdirs
    font_dir = pathlib.Path(platformdirs.user_cache_dir("dampfross")) / "fonts"
    loaded = 0
    if font_dir.exists():
        for ttf in font_dir.glob("*.ttf"):
            if QFontDatabase.addApplicationFont(str(ttf)) >= 0:
                loaded += 1
    _fonts_loaded = True
    if loaded:
        print(f"[fonts] loaded {loaded} font files from {font_dir}")


# ── Accessibility state ───────────────────────────────────────────────────#
# These module globals are read at call time — update then trigger a UI
# refresh to propagate changes.  Rendering code (paintEvent) picks them up
# on the very next frame automatically.

A_CVD_MODE:        int   = 0      # 0=none 1=deuteranopia 2=protanopia 3=tritanopia
A_HIGH_CONTRAST:   bool  = False
A_FONT_SCALE:      float = 1.0    # 0→0.85  1→1.0  2→1.15
A_BOLD_LABELS:     bool  = False
A_REDUCE_MOTION:   bool  = False  # checked live by animation code
A_REDUCE_PAN:      bool  = False  # checked live by showreel / auto-pan code
A_DISABLE_BLINK:   bool  = False  # checked live by fade / crossfade code
A_EXTENDED_FOCUS:  bool  = False

# ── Okabe-Ito CVD-safe player palette ────────────────────────────────────#
# Distinguishable for deuteranopia, protanopia, and tritanopia alike.
_CVD_PLAYER_COLORS_HEX = [
    ("#E69F00", "Orange"),
    ("#0072B2", "Blau"),
    ("#009E73", "Blaugrün"),
    ("#F0E442", "Gelb"),
    ("#D55E00", "Vermilion"),
    ("#CC79A7", "Rosarot"),
    ("#56B4E9", "Himmelblau"),
    ("#000000", "Schwarz"),
]

_DEFAULT_PLAYER_COLORS_HEX = [
    ("#e23b3b", "Rot"),
    ("#1f6fd9", "Blau"),
    ("#1f7a4a", "Grün"),
    ("#e8a915", "Gelb"),
    ("#e76018", "Orange"),
    ("#7a4dd0", "Lila"),
    ("#0a9aa1", "Türkis"),
    ("#d3398a", "Magenta"),
]


def _tint_hex(color_hex: str, alpha: float = 0.12) -> str:
    """Blend color_hex (alpha) over white → tint as hex string."""
    c = QColor(color_hex)
    r = int(255 * (1 - alpha) + c.red()   * alpha)
    g = int(255 * (1 - alpha) + c.green() * alpha)
    b = int(255 * (1 - alpha) + c.blue()  * alpha)
    return QColor(r, g, b).name()


def apply_accessibility(prefs: dict) -> None:
    """
    Apply all Barrierefreiheit preferences at once.  Call after loading or
    changing any accessibility pref; follow up with a full UI refresh
    (app_stylesheet + refresh_theme on all screens).
    """
    global A_CVD_MODE, A_HIGH_CONTRAST, A_FONT_SCALE, A_BOLD_LABELS
    global A_REDUCE_MOTION, A_REDUCE_PAN, A_DISABLE_BLINK, A_EXTENDED_FOCUS
    global S_P1, S_P2, S_P3, S_P4, S_P5, S_P6, S_P7, S_P8
    global PLAYER_COLORS, PLAYER_COLORS_HEX
    global _S_P_HEX, _S_P_TINTS, _P_HEX, _P_NAME
    global P1_TINT, P2_TINT, P3_TINT, P4_TINT, P5_TINT, P6_TINT, P7_TINT, P8_TINT
    global PLAYER_TINTS

    A_CVD_MODE       = int(prefs.get("color_vision", 0))
    A_HIGH_CONTRAST  = bool(prefs.get("high_contrast", False))
    A_FONT_SCALE     = {0: 0.85, 1: 1.0, 2: 1.15}.get(
                           int(prefs.get("font_size", 1)), 1.0)
    A_BOLD_LABELS    = bool(prefs.get("bold_labels", False))
    A_REDUCE_MOTION  = bool(prefs.get("reduce_motion", False))
    A_REDUCE_PAN     = bool(prefs.get("reduce_pan", False))
    A_DISABLE_BLINK  = bool(prefs.get("disable_blink", False))
    A_EXTENDED_FOCUS = bool(prefs.get("extended_focus", False))

    # ── Player color palette ──────────────────────────────────────────── #
    palette = _CVD_PLAYER_COLORS_HEX if A_CVD_MODE > 0 \
              else _DEFAULT_PLAYER_COLORS_HEX
    hexes = [h for h, _ in palette]

    # Mutate all lists in place so every existing reference stays valid.
    tint_hexes = [_tint_hex(h) for h in hexes]
    _S_P_HEX[:]   = hexes
    _S_P_TINTS[:] = tint_hexes
    _P_HEX[:]     = hexes          # used by player_hex()
    _P_NAME[:]    = [n for _, n in palette]
    PLAYER_COLORS[:]     = [QColor(h) for h in hexes]
    PLAYER_COLORS_HEX[:] = list(palette)

    (S_P1, S_P2, S_P3, S_P4, S_P5, S_P6, S_P7, S_P8) = hexes
    (P1_TINT, P2_TINT, P3_TINT, P4_TINT,
     P5_TINT, P6_TINT, P7_TINT, P8_TINT) = [QColor(t) for t in tint_hexes]
    PLAYER_TINTS[:] = [QColor(t) for t in tint_hexes]

    # ── Also update game.state palette so color picker reflects CVD mode ─ #
    try:
        import dampfross.game.state as _gs
        _gs.PLAYER_COLORS[:] = list(palette)
    except Exception:
        pass

    # ── Application font scaling ──────────────────────────────────────── #
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            f = app.font()
            f.setPointSize(max(8, round(12 * A_FONT_SCALE)))
            if A_BOLD_LABELS:
                f.setWeight(QFont.Weight(500))
            app.setFont(f)
    except Exception:
        pass


def font_display(size_pt: int, weight: int = 600) -> QFont:
    """Return a display/heading font (Geist or fallback)."""
    f = QFont("Geist")
    if not f.exactMatch():
        f = QFont("Inter")
    f.setPointSize(max(6, round(size_pt * A_FONT_SCALE)))
    if A_BOLD_LABELS:
        weight = min(900, weight + 100)
    f.setWeight(QFont.Weight(weight))
    return f


def font_body(size_pt: int, weight: int = 400) -> QFont:
    """Return a body font."""
    f = QFont("Geist")
    if not f.exactMatch():
        f = QFont()
    f.setPointSize(max(6, round(size_pt * A_FONT_SCALE)))
    if A_BOLD_LABELS:
        weight = min(900, max(weight, 500))
    f.setWeight(QFont.Weight(weight))
    return f


def font_mono(size_pt: int, weight: int = 500) -> QFont:
    """Return a monospace font (Geist Mono or fallback)."""
    for family in ("Geist Mono", "IBM Plex Mono", "JetBrains Mono",
                   "Fira Code", "Courier New"):
        f = QFont(family)
        if f.exactMatch():
            break
    else:
        f = QFont()
        f.setStyleHint(QFont.StyleHint.Monospace)
    f.setPointSize(max(6, round(size_pt * A_FONT_SCALE)))
    if A_BOLD_LABELS:
        weight = min(900, max(weight, 600))
    f.setWeight(QFont.Weight(weight))
    return f


# ── Application-level stylesheet ─────────────────────────────────────────#

def app_stylesheet() -> str:
    """
    Global QApplication stylesheet.
    Covers scrollbars, tooltips, focus rings, and accessibility overrides.
    """
    focus_extra = ""
    if A_EXTENDED_FOCUS:
        focus_extra = f"""
QPushButton:focus, QLineEdit:focus, QSpinBox:focus,
QComboBox:focus, QScrollArea:focus, QAbstractButton:focus {{
    outline: 2px solid {S_INK_1};
    outline-offset: 2px;
}}
*:focus {{
    border: 2px solid {S_INK_1};
}}
"""

    hc_extra = ""
    if A_HIGH_CONTRAST:
        hc_extra = f"""
QLabel {{ color: {S_INK}; }}
QPushButton {{ border: 2px solid {S_INK_2}; }}
QFrame[frameShape="4"], QFrame[frameShape="5"] {{ color: {S_INK_2}; }}
"""

    return f"""
QScrollBar:vertical {{
    background: {S_PAPER}; width: 10px; border: none;
}}
QScrollBar::handle:vertical {{
    background: {S_RULE}; border-radius: 5px; min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {S_PAPER}; height: 10px; border: none;
}}
QScrollBar::handle:horizontal {{
    background: {S_RULE}; border-radius: 5px; min-width: 24px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QToolTip {{
    background: {S_INK}; color: {S_PAPER};
    border: none; border-radius: 6px;
    padding: 6px 10px; font-size: 12px;
}}
{focus_extra}
{hc_extra}
"""

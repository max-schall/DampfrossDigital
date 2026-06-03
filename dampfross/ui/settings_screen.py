"""
Options screen — left tab rail + scrollable content pane.
Tabs: Aussehen · Gameplay · Steuerung · Audio · Barrierefreiheit
"""
from __future__ import annotations
import json
import pathlib

import platformdirs
from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QPen, QPainterPath
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QStackedWidget, QVBoxLayout, QWidget,
)

import dampfross.ui.design_tokens as dt
from dampfross.ui.components import SegmentedControl, Toggle

_PREFS_PATH = pathlib.Path(platformdirs.user_config_dir("dampfross")) / "prefs.json"
_PREFS: dict | None = None


def _load_prefs() -> dict:
    try:
        return json.loads(_PREFS_PATH.read_text())
    except Exception:
        return {}


def _save_prefs(prefs: dict) -> None:
    _PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PREFS_PATH.write_text(json.dumps(prefs, indent=2))


def _get_prefs() -> dict:
    global _PREFS
    if _PREFS is None:
        _PREFS = _load_prefs()
    return _PREFS


def _set_pref(key: str, val) -> None:
    p = _get_prefs()
    p[key] = val
    _save_prefs(p)


def get_prefs() -> dict:
    """Public accessor for the current prefs dict (used by main_window)."""
    return _get_prefs()


# ── Shared helpers ────────────────────────────────────────────────────── #

def _hsep(soft: bool = False) -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    color = dt.S_RULE_SOFT if soft else dt.S_RULE
    f.setStyleSheet(f"border:none;background:{color};max-height:1px;")
    return f


def _panel_frame() -> QFrame:
    f = QFrame()
    f.setStyleSheet(
        f"QFrame{{background:{dt.S_SURFACE};border:1px solid {dt.S_RULE};"
        f"border-radius:10px;}}"
    )
    return f


def _section_head(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    f = dt.font_display(11)
    f.setWeight(QFont.Weight(700))
    lbl.setFont(f)
    lbl.setStyleSheet(
        f"color:{dt.S_INK_3};background:transparent;letter-spacing:0.12em;"
    )
    return lbl


def _page_title(title: str, sub: str) -> QVBoxLayout:
    col = QVBoxLayout()
    col.setSpacing(4)
    t = QLabel(title)
    ft = dt.font_display(32)
    ft.setWeight(QFont.Weight(700))
    t.setFont(ft)
    t.setStyleSheet(f"color:{dt.S_INK};background:transparent;letter-spacing:-0.02em;")
    col.addWidget(t)
    s = QLabel(sub)
    s.setFont(dt.font_body(14))
    s.setStyleSheet(f"color:{dt.S_INK_2};background:transparent;")
    s.setWordWrap(True)
    col.addWidget(s)
    return col


# ── Setting row: toggle ───────────────────────────────────────────────── #

class _ToggleRow(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, label: str, sub: str, value: bool = True, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        self.setMinimumHeight(56)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 14, 20, 14)
        lay.setSpacing(12)

        col = QVBoxLayout()
        col.setSpacing(2)
        lbl = QLabel(label)
        fl = dt.font_body(14)
        fl.setWeight(QFont.Weight(600))
        lbl.setFont(fl)
        lbl.setStyleSheet(f"color:{dt.S_INK};background:transparent;")
        col.addWidget(lbl)
        sub_lbl = QLabel(sub)
        sub_lbl.setFont(dt.font_mono(11))
        sub_lbl.setStyleSheet(f"color:{dt.S_INK_3};background:transparent;")
        col.addWidget(sub_lbl)
        lay.addLayout(col, 1)

        self._t = Toggle(value)
        self._t.toggled.connect(self.toggled)
        lay.addWidget(self._t, 0, Qt.AlignmentFlag.AlignVCenter)


# ── Setting row: segmented control ───────────────────────────────────── #

class _SegRow(QWidget):
    changed = pyqtSignal(int)

    def __init__(self, label: str, sub: str, options: list[str],
                 selected: int = 0, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        self.setMinimumHeight(56)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 14, 20, 14)
        lay.setSpacing(12)

        col = QVBoxLayout()
        col.setSpacing(2)
        lbl = QLabel(label)
        fl = dt.font_body(14)
        fl.setWeight(QFont.Weight(600))
        lbl.setFont(fl)
        lbl.setStyleSheet(f"color:{dt.S_INK};background:transparent;")
        col.addWidget(lbl)
        sub_lbl = QLabel(sub)
        sub_lbl.setFont(dt.font_mono(11))
        sub_lbl.setStyleSheet(f"color:{dt.S_INK_3};background:transparent;")
        col.addWidget(sub_lbl)
        lay.addLayout(col, 1)

        seg = SegmentedControl(options, selected)
        seg.changed.connect(self.changed)
        lay.addWidget(seg, 0, Qt.AlignmentFlag.AlignVCenter)


def _rows_panel(*rows) -> QFrame:
    """Wrap a sequence of row widgets into a rounded panel with separators."""
    panel = _panel_frame()
    lay = QVBoxLayout(panel)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)
    for i, row in enumerate(rows):
        lay.addWidget(row)
        if i < len(rows) - 1:
            lay.addWidget(_hsep(soft=True))
    return panel


# ── Theme card (Aussehen) ─────────────────────────────────────────────── #

class _ColorDot(QWidget):
    def __init__(self, color_hex: str, size: int = 10, parent=None):
        super().__init__(parent)
        self._color = QColor(color_hex)
        self.setFixedSize(size, size)

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(self._color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(self.rect())


class _ThemeCard(QWidget):
    clicked = pyqtSignal(str)

    def __init__(self, theme_id: str, label: str, bg: str, ink: str, parent=None):
        super().__init__(parent)
        self._id = theme_id
        self._bg = bg
        self._ink = ink
        self._selected = False
        self.setFixedWidth(190)
        self.setFixedHeight(110)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._build_ui(label, theme_id)
        self._apply_style()

    def _build_ui(self, label: str, sub: str) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 12)
        lay.setSpacing(0)

        dots_row = QHBoxLayout()
        dots_row.setSpacing(5)
        dots_row.setContentsMargins(0, 0, 0, 10)
        for idx in (2, 3, 4):
            dots_row.addWidget(_ColorDot(dt.player_hex(idx), 12))
        dots_row.addStretch()
        lay.addLayout(dots_row)

        self._label = QLabel(label)
        fl = dt.font_display(16)
        fl.setWeight(QFont.Weight(600))
        self._label.setFont(fl)
        self._label.setStyleSheet(f"color:{self._ink};background:transparent;")
        lay.addWidget(self._label)

        self._sub = QLabel(sub.upper())
        self._sub.setFont(dt.font_mono(9))
        self._sub.setStyleSheet(
            f"color:{self._ink};background:transparent;"
            f"letter-spacing:0.08em;opacity:0.55;"
        )
        lay.addWidget(self._sub)

    def _apply_style(self) -> None:
        # Background only — border is painted in paintEvent for sharper control.
        self.setStyleSheet(
            f"_ThemeCard{{background:{self._bg}; border-radius:12px;}}"
        )
        self.update()

    def set_selected(self, sel: bool) -> None:
        if self._selected != sel:
            self._selected = sel
            self._apply_style()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        r = self.rect()
        radius = 12.0

        # Background fill (stylesheet sets it, but repaint it here for clean layering)
        path = QPainterPath()
        path.addRoundedRect(0, 0, r.width(), r.height(), radius, radius)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(self._bg)))
        p.drawPath(path)

        if self._selected:
            # Thick accent ring — drawn inside the card boundary
            pen = QPen(QColor(dt.S_INFO), 3.0)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            inset = 1.5
            p.drawRoundedRect(
                QRectF(inset, inset,
                       r.width() - 2 * inset, r.height() - 2 * inset),
                radius - 1, radius - 1,
            )
            # Small filled check-dot in the top-right corner
            dot_r = 7.0
            cx = r.width() - dot_r - 6
            cy = dot_r + 6
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(dt.S_INFO)))
            p.drawEllipse(QRectF(cx - dot_r, cy - dot_r, dot_r * 2, dot_r * 2))
            # Checkmark inside dot
            pen2 = QPen(QColor("#ffffff"), 1.5)
            pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen2.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen2)
            p.setBrush(Qt.BrushStyle.NoBrush)
            ck = QPainterPath()
            ck.moveTo(cx - 3.5, cy)
            ck.lineTo(cx - 1, cy + 2.5)
            ck.lineTo(cx + 4, cy - 3)
            p.drawPath(ck)
        else:
            pen = QPen(QColor(dt.S_RULE), 1.0)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(
                QRectF(0.5, 0.5, r.width() - 1.0, r.height() - 1.0),
                radius, radius,
            )

        p.end()

    def mousePressEvent(self, _) -> None:
        self.clicked.emit(self._id)


# ═══════════════════════════════════════════════════════════════════════ #
#  Tab content pages                                                      #
# ═══════════════════════════════════════════════════════════════════════ #

def _scroll_page(inner: QWidget) -> QScrollArea:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
    scroll.setWidget(inner)
    return scroll


# ── Aussehen ─────────────────────────────────────────────────────────── #

class _Aussehen(QWidget):
    theme_changed = pyqtSignal(str)
    pref_changed  = pyqtSignal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        self._theme = "light"
        lay = QVBoxLayout(self)
        lay.setContentsMargins(48, 40, 48, 48)
        lay.setSpacing(0)

        lay.addLayout(_page_title(
            "Aussehen",
            "Farbschema, Animationen und Layout-Dichte — gespeichert pro Gerät.",
        ))
        lay.addSpacing(36)

        # Farbschema
        lay.addWidget(_section_head("Farbschema"))
        lay.addSpacing(12)
        themes_row = QHBoxLayout()
        themes_row.setSpacing(10)
        _THEMES = [
            ("light", "Paper",  "#f4f2ec", "#14171c"),
            ("dark",  "Slate",  "#0f1218", "#f1efe9"),
            ("sepia", "Atlas",  "#efe3ca", "#2a1d09"),
        ]
        self._cards: dict[str, _ThemeCard] = {}
        for tid, lbl, bg, ink in _THEMES:
            c = _ThemeCard(tid, lbl, bg, ink)
            c.clicked.connect(self._on_theme)
            self._cards[tid] = c
            themes_row.addWidget(c)
        themes_row.addStretch()
        lay.addLayout(themes_row)
        lay.addSpacing(32)

        # Darstellung
        lay.addWidget(_section_head("Darstellung"))
        lay.addSpacing(12)
        r_anim  = _SegRow("Animationsgeschwindigkeit", "Züge, Übergänge & Würfelwurf",
                          ["Reduziert", "Normal", "Schnell"],
                          selected=_get_prefs().get("anim_speed", 1))
        r_hud   = _SegRow("HUD-Skalierung", "Größe von Panels und Beschriftungen",
                          ["Kompakt", "Normal", "Groß"],
                          selected=_get_prefs().get("hud_scale", 1))
        r_names = _ToggleRow("Spieler-Namensschilder", "Namen über den Zugmarken einblenden",
                             value=_get_prefs().get("show_name_labels", True))
        r_ferry = _ToggleRow("Fährlinien hervorheben", "Gebaute Fähren deutlicher darstellen",
                             value=_get_prefs().get("highlight_ferries", True))
        r_anim.changed.connect(lambda v: self._on_pref("anim_speed", v))
        r_hud.changed.connect(lambda v: self._on_pref("hud_scale", v))
        r_names.toggled.connect(lambda v: self._on_pref("show_name_labels", v))
        r_ferry.toggled.connect(lambda v: self._on_pref("highlight_ferries", v))
        lay.addWidget(_rows_panel(r_anim, r_hud, r_names, r_ferry))

        lay.addStretch()
        self._select("light")

    def _on_pref(self, key: str, val) -> None:
        _set_pref(key, val)
        self.pref_changed.emit(key, val)

    def _on_theme(self, tid: str) -> None:
        self._select(tid)
        dt.set_theme(tid)
        _set_pref("theme", tid)
        self.theme_changed.emit(tid)
        self.pref_changed.emit("theme", tid)

    def _select(self, tid: str) -> None:
        self._theme = tid
        for k, c in self._cards.items():
            c.set_selected(k == tid)

    def load_prefs(self) -> None:
        t = _get_prefs().get("theme", "light")
        if t in self._cards:
            self._select(t)
            dt.set_theme(t)


# ── Gameplay ─────────────────────────────────────────────────────────── #

class _Gameplay(QWidget):
    pref_changed = pyqtSignal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(48, 40, 48, 48)
        lay.setSpacing(0)

        lay.addLayout(_page_title(
            "Gameplay",
            "KI-Verhalten und In-Game-Anzeigen.",
        ))
        lay.addSpacing(36)

        # KI
        lay.addWidget(_section_head("Künstliche Intelligenz"))
        lay.addSpacing(12)
        r_diff    = _SegRow("KI-Schwierigkeit",
                            "Bestimmt, wie aggressiv und vorausschauend die KI plant",
                            ["Leicht", "Normal", "Schwer"],
                            selected=_get_prefs().get("ai_difficulty", 1))
        r_speed   = _SegRow("KI-Zuggeschwindigkeit",
                            "Wartezeit bevor die KI ihre Aktion ausführt",
                            ["Langsam", "Normal", "Sofort"],
                            selected=_get_prefs().get("ai_speed", 1))
        r_explain = _ToggleRow("KI-Entscheidungen erklären",
                               "Zeigt kurze Begründungen über dem Spielfeld (Debug)",
                               value=_get_prefs().get("ai_explain", False))
        r_diff.changed.connect(lambda v: self._on_pref("ai_difficulty", v))
        r_speed.changed.connect(lambda v: self._on_pref("ai_speed", v))
        r_explain.toggled.connect(lambda v: self._on_pref("ai_explain", v))
        lay.addWidget(_rows_panel(r_diff, r_speed, r_explain))
        lay.addSpacing(28)

        # In-Game-Anzeige
        lay.addWidget(_section_head("In-Game-Anzeige"))
        lay.addSpacing(12)
        r_alltracks  = _ToggleRow("Gleise aller Spieler anzeigen",
                                  "Andere Netze während des eigenen Zugs einblenden",
                                  value=_get_prefs().get("show_all_tracks", True))
        r_anim_build = _ToggleRow("Züge nach Zugabschluss animieren",
                                  "Bauvorgang visuell nachverfolgen",
                                  value=_get_prefs().get("animate_build", True))
        r_overlay    = _ToggleRow("Rundenstand-Overlay",
                                  "Kleines Score-Widget während der Betriebsphase",
                                  value=_get_prefs().get("round_overlay", True))
        r_notif      = _ToggleRow("Verbindungs-Benachrichtigung",
                                  "Meldung, wenn alle Städte verbunden sind",
                                  value=_get_prefs().get("connection_notification", True))
        r_alltracks.toggled.connect(lambda v: self._on_pref("show_all_tracks", v))
        r_anim_build.toggled.connect(lambda v: self._on_pref("animate_build", v))
        r_overlay.toggled.connect(lambda v: self._on_pref("round_overlay", v))
        r_notif.toggled.connect(lambda v: self._on_pref("connection_notification", v))
        lay.addWidget(_rows_panel(r_alltracks, r_anim_build, r_overlay, r_notif))

        lay.addStretch()

    def _on_pref(self, key: str, val) -> None:
        _set_pref(key, val)
        self.pref_changed.emit(key, val)


# ── Steuerung ────────────────────────────────────────────────────────── #

class _Steuerung(QWidget):
    pref_changed = pyqtSignal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(48, 40, 48, 48)
        lay.setSpacing(0)

        lay.addLayout(_page_title(
            "Steuerung",
            "Maus, Tastatur und Touch-Gesten für die Kartennavigation.",
        ))
        lay.addSpacing(36)

        # Maus & Touchpad
        lay.addWidget(_section_head("Maus & Touchpad"))
        lay.addSpacing(12)
        r_zoom    = _ToggleRow("Mausrad-Zoom",
                               "Karte mit dem Scrollrad vergrößern und verkleinern",
                               value=_get_prefs().get("mouse_zoom", True))
        r_invert  = _ToggleRow("Zoom-Richtung umkehren",
                               "Scrollrichtung für Zoom invertieren",
                               value=_get_prefs().get("zoom_invert", False))
        r_midpan  = _ToggleRow("Mittelklick zum Verschieben",
                               "Gehaltenes Mittelklick verschiebt die Karte",
                               value=_get_prefs().get("middle_click_pan", True))
        r_sens    = _SegRow("Scroll-Empfindlichkeit",
                            "Stärke der Zoombewegung pro Mausradumdrehung",
                            ["Gering", "Normal", "Hoch"],
                            selected=_get_prefs().get("scroll_sensitivity", 1))
        r_inertia = _ToggleRow("Kameraträgheit",
                               "Sanftes Ausrollen nach schnellen Kamerabewegungen",
                               value=_get_prefs().get("camera_inertia", False))
        r_zoom.toggled.connect(lambda v: self._on_pref("mouse_zoom", v))
        r_invert.toggled.connect(lambda v: self._on_pref("zoom_invert", v))
        r_midpan.toggled.connect(lambda v: self._on_pref("middle_click_pan", v))
        r_sens.changed.connect(lambda v: self._on_pref("scroll_sensitivity", v))
        r_inertia.toggled.connect(lambda v: self._on_pref("camera_inertia", v))
        lay.addWidget(_rows_panel(r_zoom, r_invert, r_midpan, r_sens, r_inertia))
        lay.addSpacing(28)

        # Tastatur
        lay.addWidget(_section_head("Tastatur"))
        lay.addSpacing(12)
        r_kbd    = _ToggleRow("Tastaturkürzel aktiv",
                              "Shortcuts für häufige Aktionen (Tab, Leertaste, …)",
                              value=_get_prefs().get("keyboard_shortcuts", True))
        r_tab    = _ToggleRow("[Tab] → Punktestand",
                              "Scoreboard-Overlay mit Tab-Taste ein- und ausblenden",
                              value=_get_prefs().get("tab_scoreboard", True))
        r_space  = _ToggleRow("[Leertaste] → Würfeln / Weiter",
                              "Wichtige Aktionen auch mit der Leertaste bestätigen",
                              value=_get_prefs().get("space_confirm", True))
        r_arrows = _ToggleRow("Pfeiltasten-Navigation",
                              "Karte mit den Pfeiltasten verschieben",
                              value=_get_prefs().get("arrow_navigation", False))
        r_kbd.toggled.connect(lambda v: self._on_pref("keyboard_shortcuts", v))
        r_tab.toggled.connect(lambda v: self._on_pref("tab_scoreboard", v))
        r_space.toggled.connect(lambda v: self._on_pref("space_confirm", v))
        r_arrows.toggled.connect(lambda v: self._on_pref("arrow_navigation", v))
        lay.addWidget(_rows_panel(r_kbd, r_tab, r_space, r_arrows))
        lay.addSpacing(28)

        # Touch
        lay.addWidget(_section_head("Touch (experimentell)"))
        lay.addSpacing(12)
        r_pinch = _ToggleRow("Zwei-Finger-Zoom",
                             "Pinch-Geste zum Zoomen auf Touchscreens",
                             value=_get_prefs().get("touch_pinch_zoom", True))
        r_touch = _ToggleRow("Einzel-Finger-Kameraverschiebung",
                             "Karte mit einem Finger verschieben (deaktiviert Klick-Bau)",
                             value=_get_prefs().get("touch_pan", False))
        r_pinch.toggled.connect(lambda v: self._on_pref("touch_pinch_zoom", v))
        r_touch.toggled.connect(lambda v: self._on_pref("touch_pan", v))
        lay.addWidget(_rows_panel(r_pinch, r_touch))

        lay.addStretch()

    def _on_pref(self, key: str, val) -> None:
        _set_pref(key, val)
        self.pref_changed.emit(key, val)


# ── Audio ─────────────────────────────────────────────────────────────── #

class _Audio(QWidget):
    pref_changed = pyqtSignal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(48, 40, 48, 48)
        lay.setSpacing(0)

        lay.addLayout(_page_title(
            "Audio",
            "Soundeffekte, Musik und Ereignis-Töne.",
        ))
        lay.addSpacing(36)

        # Soundeffekte
        lay.addWidget(_section_head("Soundeffekte"))
        lay.addSpacing(12)
        r_sfx    = _ToggleRow("Soundeffekte aktivieren",
                              "Alle Spielklänge ein- oder ausschalten",
                              value=_get_prefs().get("sfx_enabled", True))
        r_sfxvol = _SegRow("Lautstärke Soundeffekte",
                           "Relative Lautstärke der Spielgeräusche",
                           ["Leise", "Mittel", "Laut"],
                           selected=_get_prefs().get("sfx_volume", 1))
        r_sfx.toggled.connect(lambda v: self._on_pref("sfx_enabled", v))
        r_sfxvol.changed.connect(lambda v: self._on_pref("sfx_volume", v))
        lay.addWidget(_rows_panel(r_sfx, r_sfxvol))
        lay.addSpacing(28)

        # Hintergrundmusik
        lay.addWidget(_section_head("Hintergrundmusik"))
        lay.addSpacing(12)
        r_music    = _ToggleRow("Hintergrundmusik abspielen",
                                "Atmosphärische Musik während des Spiels",
                                value=_get_prefs().get("music_enabled", False))
        r_musicvol = _SegRow("Lautstärke Musik",
                             "Lautstärke der Hintergrundmusik",
                             ["Leise", "Mittel", "Laut"],
                             selected=_get_prefs().get("music_volume", 0))
        r_musicmenu = _ToggleRow("Musik im Menü",
                                 "Musik auch im Hauptmenü und auf dem Ergebnisbildschirm",
                                 value=_get_prefs().get("music_menu", False))
        r_music.toggled.connect(lambda v: self._on_pref("music_enabled", v))
        r_musicvol.changed.connect(lambda v: self._on_pref("music_volume", v))
        r_musicmenu.toggled.connect(lambda v: self._on_pref("music_menu", v))
        lay.addWidget(_rows_panel(r_music, r_musicvol, r_musicmenu))
        lay.addSpacing(28)

        # Ereignis-Töne
        lay.addWidget(_section_head("Ereignis-Töne"))
        lay.addSpacing(12)
        r_dice  = _ToggleRow("Würfelton",
                             "Ton beim Würfeln und beim Anzeigen des Ergebnisses",
                             value=_get_prefs().get("sfx_dice", True))
        r_build = _ToggleRow("Gleis-Bauton",
                             "Klick-Sound beim Platzieren eines Gleissegments",
                             value=_get_prefs().get("sfx_build", True))
        r_ferry = _ToggleRow("Fähren-Klang",
                             "Bootsgeräusch beim Überqueren einer Fährstrecke",
                             value=_get_prefs().get("sfx_ferry", True))
        r_dice.toggled.connect(lambda v: self._on_pref("sfx_dice", v))
        r_build.toggled.connect(lambda v: self._on_pref("sfx_build", v))
        r_ferry.toggled.connect(lambda v: self._on_pref("sfx_ferry", v))
        lay.addWidget(_rows_panel(r_dice, r_build, r_ferry))

        lay.addStretch()

    def _on_pref(self, key: str, val) -> None:
        _set_pref(key, val)
        self.pref_changed.emit(key, val)


# ── Barrierefreiheit ─────────────────────────────────────────────────── #

class _Barriere(QWidget):
    pref_changed = pyqtSignal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(48, 40, 48, 48)
        lay.setSpacing(0)

        lay.addLayout(_page_title(
            "Barrierefreiheit",
            "Anpassungen für Sehen, Bewegung und Bedienung.",
        ))
        lay.addSpacing(36)

        # Sehen
        lay.addWidget(_section_head("Sehen"))
        lay.addSpacing(12)
        r_cvd  = _SegRow("Farbwahrnehmungsanpassung",
                         "Optimiert Spielerfarben für verschiedene Farbsehschwächen",
                         ["Aus", "Deuteranopie", "Protanopie", "Tritanopie"],
                         selected=_get_prefs().get("color_vision", 0))
        r_hc   = _ToggleRow("Kontrast erhöhen",
                            "Deutlichere Ränder und stärkere Farb-Kontraste",
                            value=_get_prefs().get("high_contrast", False))
        r_fs   = _SegRow("Schriftgröße",
                         "Skaliert Labels, Hinweise und Panel-Texte",
                         ["Klein", "Normal", "Groß"],
                         selected=_get_prefs().get("font_size", 1))
        r_bold = _ToggleRow("Fettdruck für Labels",
                            "Alle Beschriftungen in mittlerer Schriftstärke",
                            value=_get_prefs().get("bold_labels", False))
        r_cvd.changed.connect(lambda v: self._on_pref("color_vision", v))
        r_hc.toggled.connect(lambda v: self._on_pref("high_contrast", v))
        r_fs.changed.connect(lambda v: self._on_pref("font_size", v))
        r_bold.toggled.connect(lambda v: self._on_pref("bold_labels", v))
        lay.addWidget(_rows_panel(r_cvd, r_hc, r_fs, r_bold))
        lay.addSpacing(28)

        # Bewegung
        lay.addWidget(_section_head("Bewegung"))
        lay.addSpacing(12)
        r_red_motion = _ToggleRow("Animationen reduzieren",
                                  "Deaktiviert nicht-wesentliche Bewegtbilder und Übergänge",
                                  value=_get_prefs().get("reduce_motion", False))
        r_red_pan    = _ToggleRow("Kamera-Schwenkung reduzieren",
                                  "Weniger Auto-Pan beim Spieler- oder Phasenwechsel",
                                  value=_get_prefs().get("reduce_pan", False))
        r_no_blink   = _ToggleRow("Blinkende Elemente deaktivieren",
                                  "Puls- und Blink-Animationen für alle UI-Elemente aus",
                                  value=_get_prefs().get("disable_blink", False))
        r_red_motion.toggled.connect(lambda v: self._on_pref("reduce_motion", v))
        r_red_pan.toggled.connect(lambda v: self._on_pref("reduce_pan", v))
        r_no_blink.toggled.connect(lambda v: self._on_pref("disable_blink", v))
        lay.addWidget(_rows_panel(r_red_motion, r_red_pan, r_no_blink))
        lay.addSpacing(28)

        # Bedienung
        lay.addWidget(_section_head("Bedienung"))
        lay.addSpacing(12)
        r_focus  = _ToggleRow("Erweiterte Fokusanzeige",
                              "Größerer, besser sichtbarer Fokusrahmen für Tastaturnavigation",
                              value=_get_prefs().get("extended_focus", False))
        r_tips   = _ToggleRow("Tooltips dauerhaft anzeigen",
                              "Steuerungs-Hinweise auch ohne Hover einblenden",
                              value=_get_prefs().get("persistent_tooltips", False))
        r_screen = _ToggleRow("Screenreader-Unterstützung",
                              "Optimiert Reihenfolge und Labels für AT-Software",
                              value=_get_prefs().get("screenreader", False))
        r_focus.toggled.connect(lambda v: self._on_pref("extended_focus", v))
        r_tips.toggled.connect(lambda v: self._on_pref("persistent_tooltips", v))
        r_screen.toggled.connect(lambda v: self._on_pref("screenreader", v))
        lay.addWidget(_rows_panel(r_focus, r_tips, r_screen))

        lay.addStretch()

    def _on_pref(self, key: str, val) -> None:
        _set_pref(key, val)
        self.pref_changed.emit(key, val)


# ═══════════════════════════════════════════════════════════════════════ #
#  Left tab rail                                                          #
# ═══════════════════════════════════════════════════════════════════════ #

_TABS = [
    ("Aussehen",         "○"),
    ("Gameplay",         "○"),
    ("Steuerung",        "○"),
    ("Audio",            "○"),
    ("Barrierefreiheit", "○"),
]


class _TabRail(QWidget):
    tab_clicked  = pyqtSignal(int)
    back_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(230)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            f"_TabRail{{background:{dt.S_SURFACE_2};"
            f"border-right:1px solid {dt.S_RULE};}}"
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 24, 16, 24)
        lay.setSpacing(0)

        back = QPushButton("← Zurück")
        back.setFont(dt.font_mono(11))
        back.setFixedHeight(36)
        back.setCursor(Qt.CursorShape.PointingHandCursor)
        back.setStyleSheet(
            f"QPushButton{{background:transparent;color:{dt.S_INK_2};"
            f"border:none;border-radius:8px;text-align:left;"
            f"font-size:12px;padding:0 10px;}}"
            f"QPushButton:hover{{background:{dt.S_SUNK};color:{dt.S_INK_1};}}"
        )
        back.clicked.connect(self.back_clicked)
        lay.addWidget(back)
        lay.addSpacing(20)

        eyebrow = QLabel("OPTIONEN")
        eyebrow.setFont(dt.font_mono(10))
        eyebrow.setStyleSheet(
            f"color:{dt.S_INK_3};background:transparent;letter-spacing:0.12em;"
        )
        lay.addWidget(eyebrow)
        lay.addSpacing(10)

        self._btns: list[QPushButton] = []
        self._active = 0
        for i, (name, _) in enumerate(_TABS):
            btn = QPushButton(name)
            btn.setFont(dt.font_display(14))
            btn.setFixedHeight(40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self._on_click(idx))
            self._btns.append(btn)
            lay.addWidget(btn)
            lay.addSpacing(2)

        lay.addStretch()
        self._refresh()

    def _on_click(self, idx: int) -> None:
        self._active = idx
        self._refresh()
        self.tab_clicked.emit(idx)

    def _refresh(self) -> None:
        for i, btn in enumerate(self._btns):
            active = (i == self._active)
            btn.setStyleSheet(
                f"QPushButton{{border:0;"
                f"background:{'transparent' if not active else dt.S_SUNK};"
                f"text-align:left;"
                f"color:{dt.S_INK if active else dt.S_INK_2};"
                f"font-weight:{'700' if active else '500'};"
                f"padding:0 10px;"
                f"border-radius:8px;}}"
                f"QPushButton:hover{{background:{dt.S_SUNK};"
                f"color:{dt.S_INK_1};}}"
            )

    def set_active(self, idx: int) -> None:
        if 0 <= idx < len(self._btns):
            self._active = idx
            self._refresh()


# ═══════════════════════════════════════════════════════════════════════ #
#  Public screen widget                                                   #
# ═══════════════════════════════════════════════════════════════════════ #

class SettingsScreen(QWidget):
    theme_changed = pyqtSignal(str)
    back_clicked  = pyqtSignal()
    pref_changed  = pyqtSignal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{dt.S_PAPER};")
        self._build_ui()
        self._aussehen.load_prefs()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._rail = _TabRail()
        self._rail.tab_clicked.connect(self._on_tab)
        self._rail.back_clicked.connect(self.back_clicked)
        root.addWidget(self._rail)

        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background:transparent;")

        self._aussehen  = _Aussehen()
        self._gameplay  = _Gameplay()
        self._steuerung = _Steuerung()
        self._audio     = _Audio()
        self._barriere  = _Barriere()

        self._aussehen.theme_changed.connect(self.theme_changed)
        for page in (self._aussehen, self._gameplay, self._steuerung,
                     self._audio, self._barriere):
            page.pref_changed.connect(self.pref_changed)

        for page in (self._aussehen, self._gameplay, self._steuerung,
                     self._audio, self._barriere):
            self._stack.addWidget(_scroll_page(page))

        root.addWidget(self._stack, 1)

    def refresh_theme(self) -> None:
        self.setStyleSheet(f"background:{dt.S_PAPER};")

    def _on_tab(self, idx: int) -> None:
        self._stack.setCurrentIndex(idx)

    def show_tab(self, idx: int) -> None:
        self._rail.set_active(idx)
        self._stack.setCurrentIndex(idx)

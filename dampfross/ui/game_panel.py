"""
Game HUD panel (right rail, 320 px) + BuildPromptOverlay for the map.
All game-logic lives in MainWindow; this file handles only signals and display.
"""
from __future__ import annotations
from PyQt6.QtCore import Qt, QEvent, QObject, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QPen
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

import dampfross.ui.design_tokens as dt


# ── Module-level helpers ──────────────────────────────────────────────── #

def _eyebrow(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setFont(dt.font_mono(10))
    lbl.setStyleSheet(
        f"color:{dt.S_INK_2};background:transparent;letter-spacing:0.08em;"
    )
    return lbl


def _hsep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"border:none;background:{dt.S_RULE};max-height:1px;")
    return f


def _btn_primary(text: str) -> QPushButton:
    b = QPushButton(text)
    b.setFont(dt.font_body(13))
    b.setStyleSheet(
        f"QPushButton{{background:{dt.S_INK};color:{dt.S_SURFACE};"
        f"border:none;border-radius:8px;font-size:13px;font-weight:600;"
        f"padding:10px 18px;text-align:left;}}"
        f"QPushButton:hover{{background:{dt.S_INK_1};}}"
        f"QPushButton:disabled{{background:{dt.S_SUNK};color:{dt.S_INK_4};}}"
    )
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def _btn_secondary(text: str) -> QPushButton:
    b = QPushButton(text)
    b.setFont(dt.font_body(13))
    b.setStyleSheet(
        f"QPushButton{{background:{dt.S_SURFACE};color:{dt.S_INK};"
        f"border:1px solid {dt.S_RULE};border-radius:8px;"
        f"font-size:13px;font-weight:500;padding:10px 14px;text-align:left;}}"
        f"QPushButton:hover{{background:{dt.S_SUNK};}}"
        f"QPushButton:disabled{{color:{dt.S_INK_4};border-color:{dt.S_RULE};}}"
    )
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def _btn_ghost(text: str) -> QPushButton:
    b = QPushButton(text)
    b.setFont(dt.font_body(13))
    b.setStyleSheet(
        f"QPushButton{{background:transparent;color:{dt.S_INK_2};"
        f"border:none;border-radius:8px;"
        f"font-size:13px;font-weight:500;padding:10px 14px;text-align:left;}}"
        f"QPushButton:hover{{background:{dt.S_SUNK};color:{dt.S_INK_1};}}"
    )
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def _btn_danger(text: str) -> QPushButton:
    b = QPushButton(text)
    b.setFont(dt.font_body(13))
    b.setStyleSheet(
        f"QPushButton{{background:transparent;color:{dt.S_DANGER};"
        f"border:1px solid #fcdede;border-radius:8px;"
        f"font-size:13px;font-weight:500;padding:10px 14px;text-align:left;}}"
        f"QPushButton:hover{{background:#fcdede;}}"
    )
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


# ── Small colored dot ─────────────────────────────────────────────────── #

class _Dot(QWidget):
    def __init__(self, color_hex: str = "#888", size: int = 12, parent=None):
        super().__init__(parent)
        self._color = QColor(color_hex)
        self.setFixedSize(size, size)

    def set_color(self, hex_color: str) -> None:
        self._color = QColor(hex_color)
        self.update()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(self._color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(self.rect())


# ── Checklist step ────────────────────────────────────────────────────── #

class _StepCircle(QWidget):
    def __init__(self, number: int, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self._number = number
        self._done = False
        self._active = False

    def set_state(self, done: bool, active: bool) -> None:
        if self._done != done or self._active != active:
            self._done = done
            self._active = active
            self.update()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)
        if self._done:
            p.setBrush(QBrush(QColor(dt.S_P3)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(r)
            pen = QPen(QColor("#ffffff"), 1.5)
            p.setPen(pen)
            f = QFont()
            f.setPixelSize(9)
            f.setWeight(QFont.Weight(700))
            p.setFont(f)
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, "✓")
        else:
            p.setBrush(QBrush(QColor(dt.S_SURFACE)))
            border = dt.S_INK if self._active else dt.S_INK_4
            p.setPen(QPen(QColor(border), 1.5))
            p.drawEllipse(r)
            p.setPen(QPen(QColor(dt.S_INK if self._active else dt.S_INK_3)))
            f = QFont()
            f.setPixelSize(9)
            p.setFont(f)
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, str(self._number))


class _StepRow(QWidget):
    def __init__(self, number: int, title: str, sub: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(10)

        self._circle = _StepCircle(number)
        layout.addWidget(self._circle, 0, Qt.AlignmentFlag.AlignTop)

        col = QVBoxLayout()
        col.setSpacing(2)
        col.setContentsMargins(0, 0, 0, 0)

        self._title = QLabel(title)
        self._title.setFont(dt.font_body(14))
        self._title.setStyleSheet(
            f"color:{dt.S_INK};background:transparent;font-size:14px;font-weight:500;"
        )
        col.addWidget(self._title)

        self._sub = QLabel(sub.upper())
        self._sub.setFont(dt.font_mono(10))
        self._sub.setStyleSheet(
            f"color:{dt.S_INK_3};background:transparent;letter-spacing:0.06em;"
        )
        col.addWidget(self._sub)
        layout.addLayout(col, 1)

    def refresh(self, done: bool, active: bool, sub: str = "") -> None:
        self._circle.set_state(done, active)
        weight = "600" if active else "500"
        color  = dt.S_INK_2 if done else dt.S_INK
        self._title.setStyleSheet(
            f"color:{color};background:transparent;"
            f"font-size:14px;font-weight:{weight};"
        )
        if sub:
            self._sub.setText(sub.upper())


# ── "This turn" checklist panel ───────────────────────────────────────── #

class _TurnPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame{{background:{dt.S_SURFACE};border:1px solid {dt.S_RULE};"
            f"border-radius:8px;}}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(0)

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Dieser Zug")
        f = dt.font_display(14)
        f.setWeight(QFont.Weight(600))
        title.setFont(f)
        title.setStyleSheet(f"color:{dt.S_INK};background:transparent;")
        head.addWidget(title)
        head.addStretch()
        self._sub = QLabel("Netz")
        self._sub.setFont(dt.font_mono(10))
        self._sub.setStyleSheet(f"color:{dt.S_INK_3};background:transparent;")
        head.addWidget(self._sub)
        layout.addLayout(head)
        layout.addSpacing(10)
        layout.addWidget(_hsep())
        layout.addSpacing(10)

        self._steps = [
            _StepRow(1, "Würfeln",              "würfeln"),
            _StepRow(2, "Startkante wählen",    "Karte klicken"),
            _StepRow(3, "Abschnitte legen",     "0 von 0 gelegt"),
            _StepRow(4, "Zug beenden",          "oder passen"),
        ]
        for step in self._steps:
            layout.addWidget(step)
            layout.addSpacing(2)

    def refresh(self, gs) -> None:
        rolled    = gs.build_rolled
        has_start = gs.build_last is not None
        total     = gs.build_pts_total
        used      = gs.build_pts_used
        placing   = rolled and has_start
        all_used  = placing and (used >= total > 0)

        self._steps[0].refresh(
            done=rolled, active=not rolled,
            sub=f"Gewürfelt: {total} — {total} Felder" if rolled else "würfeln",
        )
        self._steps[1].refresh(
            done=has_start, active=(rolled and not has_start),
            sub="gewählt" if has_start else "Karte klicken",
        )
        self._steps[2].refresh(
            done=all_used, active=(placing and not all_used),
            sub=f"{used} von {total} gelegt" if rolled else "0 von 0 gelegt",
        )
        self._steps[3].refresh(done=False, active=False)


# ── "Your line" stats panel ───────────────────────────────────────────── #

class _StatsPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame{{background:{dt.S_SURFACE};border:1px solid {dt.S_RULE};"
            f"border-radius:8px;}}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(0)

        rows = [("STRECKEN GELEGT", "—"), ("STÄDTE ERREICHT", "—"), ("NETZPUNKTE", "+0")]
        self._vals: list[QLabel] = []
        for i, (label, default) in enumerate(rows):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(label)
            lbl.setFont(dt.font_mono(11))
            lbl.setStyleSheet(f"color:{dt.S_INK_3};background:transparent;")
            val = QLabel(default)
            val.setFont(dt.font_mono(11))
            val.setStyleSheet(
                f"color:{dt.S_INK};background:transparent;font-weight:600;"
            )
            val.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(val)
            self._vals.append(val)
            layout.addLayout(row)
            if i < len(rows) - 1:
                layout.addSpacing(8)
                layout.addWidget(_hsep())
                layout.addSpacing(8)

    def refresh(self, segments: int, cities: int, net_pts: int,
                player_hex: str = "") -> None:
        self._vals[0].setText(str(segments))
        self._vals[1].setText(str(cities))
        pts_color = player_hex if player_hex else dt.S_INK
        self._vals[2].setStyleSheet(
            f"color:{pts_color};background:transparent;font-weight:600;"
        )
        self._vals[2].setText(f"+{net_pts}")


# ── Build-prompt overlay (floats on top of the map) ───────────────────── #

class BuildPromptOverlay(QWidget):
    """Floating build-context card.  Add as child of the map widget;
    parent must call reposition() from its resizeEvent.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(280)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            f"BuildPromptOverlay{{"
            f"  background:{dt.S_SURFACE};border:1px solid {dt.S_RULE};"
            f"  border-radius:12px;"
            f"}}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(0)

        # Player dot + eyebrow row
        dot_row = QHBoxLayout()
        dot_row.setSpacing(8)
        dot_row.setContentsMargins(0, 0, 0, 10)
        self._dot = _Dot("#888", 12)
        dot_row.addWidget(self._dot)
        self._eyebrow_lbl = QLabel("Linie S2 · Spieler")
        self._eyebrow_lbl.setFont(dt.font_mono(11))
        self._eyebrow_lbl.setStyleSheet(
            f"color:{dt.S_INK_3};background:transparent;letter-spacing:0.08em;"
        )
        dot_row.addWidget(self._eyebrow_lbl)
        dot_row.addStretch()
        layout.addLayout(dot_row)

        # Headline
        self._headline = QLabel("5 Abschnitte legen")
        f_head = dt.font_display(22)
        f_head.setWeight(QFont.Weight(600))
        self._headline.setFont(f_head)
        self._headline.setStyleSheet(
            f"color:{dt.S_INK};background:transparent;"
        )
        self._headline.setWordWrap(True)
        layout.addWidget(self._headline)
        layout.addSpacing(8)

        # Description
        self._desc = QLabel(
            "Klicke eine freie Hexkante neben deinem Netz. "
            "Berge kosten 3, Wälder kosten 2."
        )
        self._desc.setFont(dt.font_body(13))
        self._desc.setStyleSheet(
            f"color:{dt.S_INK_2};background:transparent;"
        )
        self._desc.setWordWrap(True)
        layout.addWidget(self._desc)
        layout.addSpacing(14)

        # Progress bar
        prog_row = QHBoxLayout()
        prog_row.setSpacing(6)
        prog_row.setContentsMargins(0, 0, 0, 0)
        self._prog_bg = QWidget()
        self._prog_bg.setFixedHeight(6)
        self._prog_bg.setStyleSheet(
            f"background:{dt.S_RULE};border-radius:3px;"
        )
        self._prog_fill = QWidget(self._prog_bg)
        self._prog_fill.setFixedHeight(6)
        self._prog_fill.setStyleSheet(
            f"background:{dt.S_P2};border-radius:3px;"
        )
        prog_row.addWidget(self._prog_bg, 1)
        self._prog_lbl = QLabel("0 / 5")
        self._prog_lbl.setFont(dt.font_mono(12))
        self._prog_lbl.setStyleSheet(
            f"color:{dt.S_INK_2};background:transparent;"
        )
        prog_row.addWidget(self._prog_lbl)
        layout.addLayout(prog_row)
        self.adjustSize()

    def reposition(self) -> None:
        self.move(24, 24)

    def refresh(self, gs) -> None:
        if not gs.build_rolled:
            self.hide()
            return
        self.show()
        cp = gs.current_player
        color = cp.color_hex
        total = gs.build_pts_total
        used  = gs.build_pts_used
        remaining = gs.build_pts_remaining

        self._dot.set_color(color)
        # Derive player line index from color string
        p_idx = next(
            (i + 1 for i, c in enumerate(dt.PLAYER_COLORS)
             if c.name() == QColor(color).name()),
            1,
        )
        self._eyebrow_lbl.setText(f"Linie S{p_idx} · {cp.name}".upper())

        word = "Abschnitt" if remaining == 1 else "Abschnitte"
        self._headline.setText(f"Noch {remaining} {word} legen")

        frac = (used / total) if total else 0.0
        track_w = self._prog_bg.width()
        if track_w > 0:
            self._prog_fill.setGeometry(0, 0, max(0, int(track_w * frac)), 6)
        self._prog_fill.setStyleSheet(
            f"background:{color};border-radius:3px;"
        )
        self._prog_lbl.setText(f"{used} / {total}")
        self.adjustSize()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Update fill width when widget resizes
        frac_text = self._prog_lbl.text()
        try:
            used, total = (int(x.strip()) for x in frac_text.split("/"))
            frac = (used / total) if total else 0.0
        except (ValueError, ZeroDivisionError):
            frac = 0.0
        track_w = self._prog_bg.width()
        if track_w > 0:
            self._prog_fill.setGeometry(0, 0, max(0, int(track_w * frac)), 6)


# ── Route-hover event filter ──────────────────────────────────────────── #

class _RouteHoverFilter(QObject):
    """Installed on each route-option button; emits hover signals into GamePanel."""
    def __init__(self, emit_enter, emit_leave, parent=None):
        super().__init__(parent)
        self._enter = emit_enter
        self._leave = emit_leave

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.Type.Enter:
            self._enter()
        elif event.type() == QEvent.Type.Leave:
            self._leave()
        return False


# ── Main GamePanel (right rail, 320 px) ───────────────────────────────── #

class GamePanel(QWidget):
    # ── Signals — MainWindow connects these ─────────────────────────── #
    roll_build        = pyqtSignal()
    end_turn          = pyqtSignal()
    declare_end_build = pyqtSignal()
    undo_last         = pyqtSignal()
    delete_plan       = pyqtSignal()
    roll_start        = pyqtSignal()
    roll_dest         = pyqtSignal()
    join_journey      = pyqtSignal(bool)
    select_route      = pyqtSignal(int)   # route option index
    cooperate_with    = pyqtSignal(int)   # partner player_idx
    advance           = pyqtSignal()
    next_journey      = pyqtSignal()
    route_hover       = pyqtSignal(list)  # list[(r,c)] on enter, [] on leave
    propose_alliance  = pyqtSignal(int)   # target player_idx
    respond_alliance  = pyqtSignal(bool)  # accept
    draw_custom_route   = pyqtSignal()    # enter custom-route drawing mode
    confirm_custom_route = pyqtSignal()   # confirm drawn route
    cancel_custom_route  = pyqtSignal()   # cancel custom drawing

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(320)
        self.setStyleSheet(
            f"GamePanel{{background:{dt.S_SURFACE_2};"
            f"border-left:1px solid {dt.S_RULE};}}"
        )
        self._build_ui()

    def refresh_theme(self) -> None:
        self.setStyleSheet(
            f"GamePanel{{background:{dt.S_SURFACE_2};"
            f"border-left:1px solid {dt.S_RULE};}}"
        )

    def apply_prefs(self, prefs: dict) -> None:
        if "hud_scale" in prefs:
            self.setFixedWidth({0: 260, 1: 320, 2: 390}.get(int(prefs["hud_scale"]), 320))

    # ------------------------------------------------------------------ #
    # Layout                                                               #
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        outer.addWidget(scroll)

        content = QWidget()
        content.setStyleSheet("background:transparent;")
        scroll.setWidget(content)

        root = QVBoxLayout(content)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(0)

        # ── BUILD PHASE VIEW ─────────────────────────────────────────── #
        self._build_view = QWidget()
        self._build_view.setStyleSheet("background:transparent;")
        bv = QVBoxLayout(self._build_view)
        bv.setContentsMargins(0, 0, 0, 0)
        bv.setSpacing(0)

        self._turn_panel = _TurnPanel()
        bv.addWidget(self._turn_panel)
        bv.addSpacing(24)

        self._actions_eyebrow = _eyebrow("Aktionen")
        bv.addWidget(self._actions_eyebrow)
        bv.addSpacing(10)

        self._btn_roll      = _btn_primary("Würfeln  →")
        self._btn_undo      = _btn_ghost("↩  Rückgängig")
        self._btn_clear     = _btn_danger("✕  Plan löschen")
        self._btn_pass      = _btn_ghost("Verbleibende Felder passen")
        self._btn_end_turn  = _btn_primary("Zug beenden  →")
        self._btn_end_build = _btn_danger("Aufbauphase beenden  →")

        self._btn_roll.clicked.connect(self.roll_build)
        self._btn_undo.clicked.connect(self.undo_last)
        self._btn_clear.clicked.connect(self.delete_plan)
        self._btn_pass.clicked.connect(self.end_turn)
        self._btn_end_turn.clicked.connect(self.end_turn)
        self._btn_end_build.clicked.connect(self.declare_end_build)

        for w in (self._btn_roll,
                  self._btn_undo, self._btn_clear,
                  self._btn_pass, self._btn_end_turn, self._btn_end_build):
            bv.addWidget(w)
            bv.addSpacing(8)

        bv.addSpacing(16)
        self._line_eyebrow = _eyebrow("Deine Linie · S?")
        bv.addWidget(self._line_eyebrow)
        bv.addSpacing(10)
        self._stats_panel = _StatsPanel()
        bv.addWidget(self._stats_panel)

        root.addWidget(self._build_view)

        # ── OPERATE PHASE VIEW ───────────────────────────────────────── #
        self._operate_view = QWidget()
        self._operate_view.setStyleSheet("background:transparent;")
        ov = QVBoxLayout(self._operate_view)
        ov.setContentsMargins(0, 0, 0, 0)
        ov.setSpacing(0)

        self._phase_lbl = QLabel("RENNPHASE")
        self._phase_lbl.setFont(dt.font_mono(10))
        self._phase_lbl.setStyleSheet(
            f"color:{dt.S_INK_2};background:transparent;letter-spacing:0.08em;"
        )
        ov.addWidget(self._phase_lbl)
        ov.addSpacing(4)

        self._heat_lbl = QLabel("Rennen 1")
        f = dt.font_display(22)
        f.setWeight(QFont.Weight(600))
        self._heat_lbl.setFont(f)
        self._heat_lbl.setStyleSheet(f"color:{dt.S_INK};background:transparent;")
        ov.addWidget(self._heat_lbl)
        ov.addSpacing(16)

        # Info card
        info_frame = QFrame()
        info_frame.setStyleSheet(
            f"QFrame{{background:{dt.S_SURFACE};border:1px solid {dt.S_RULE};"
            f"border-radius:8px;}}"
        )
        info_l = QVBoxLayout(info_frame)
        info_l.setContentsMargins(14, 12, 14, 12)
        self._info_lbl = QLabel("")
        self._info_lbl.setFont(dt.font_body(13))
        self._info_lbl.setStyleSheet(f"color:{dt.S_INK_1};background:transparent;")
        self._info_lbl.setWordWrap(True)
        info_l.addWidget(self._info_lbl)
        ov.addWidget(info_frame)
        ov.addSpacing(16)

        # Route-select dynamic area
        self._route_select_frame = QFrame()
        self._route_select_frame.setStyleSheet(
            f"QFrame{{background:{dt.S_SURFACE};border:1px solid {dt.S_RULE};"
            f"border-radius:8px;}}"
        )
        self._route_select_layout = QVBoxLayout(self._route_select_frame)
        self._route_select_layout.setContentsMargins(14, 12, 14, 12)
        self._route_select_layout.setSpacing(6)
        self._route_select_frame.hide()
        ov.addWidget(self._route_select_frame)
        ov.addSpacing(8)
        self._route_select_btns: list = []   # cleared each refresh

        # Operate action buttons
        _prim  = (
            f"QPushButton{{background:{dt.S_INK};color:{dt.S_SURFACE};"
            f"border:none;border-radius:8px;font-size:13px;font-weight:600;"
            f"padding:10px 18px;}}"
            f"QPushButton:hover{{background:{dt.S_INK_1};}}"
            f"QPushButton:disabled{{background:{dt.S_SUNK};color:{dt.S_INK_4};}}"
        )
        _sec   = (
            f"QPushButton{{background:{dt.S_SURFACE};color:{dt.S_INK};"
            f"border:1px solid {dt.S_RULE};border-radius:8px;"
            f"font-size:13px;font-weight:500;padding:10px 18px;}}"
            f"QPushButton:hover{{background:{dt.S_SUNK};}}"
        )
        _dng   = (
            f"QPushButton{{background:transparent;color:{dt.S_DANGER};"
            f"border:1px solid #fcdede;border-radius:8px;"
            f"font-size:13px;font-weight:500;padding:10px 18px;}}"
            f"QPushButton:hover{{background:#fcdede;}}"
        )

        def _op_btn(label: str, style: str, signal=None) -> QPushButton:
            b = QPushButton(label)
            b.setFont(dt.font_body(13))
            b.setStyleSheet(style)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.hide()
            if signal:
                b.clicked.connect(signal)
            ov.addWidget(b)
            ov.addSpacing(8)
            return b

        self._roll_start_btn    = _op_btn("Startbahnhof würfeln", _sec,  self.roll_start)
        self._roll_dest_btn     = _op_btn("Ziel würfeln",        _sec,  self.roll_dest)
        self._join_btn          = _op_btn("Mitfahren",            _prim, lambda: self.join_journey.emit(True))
        self._skip_btn          = _op_btn("Passen",               _dng,  lambda: self.join_journey.emit(False))
        self._accept_alliance_btn = _op_btn("Allianz annehmen",   _prim, lambda: self.respond_alliance.emit(True))
        self._decline_alliance_btn = _op_btn("Allianz ablehnen",  _dng,  lambda: self.respond_alliance.emit(False))
        self._advance_btn       = _op_btn("Zug vorrücken  →",    _sec,  self.advance)
        self._next_btn          = _op_btn("Nächstes Rennen  →",  _prim, self.next_journey)

        # Alliance proposal frame (shown during normal participate)
        self._alliance_frame = QFrame()
        self._alliance_frame.setStyleSheet(
            f"QFrame{{background:{dt.S_SURFACE};border:1px solid {dt.S_RULE};"
            f"border-radius:8px;}}"
        )
        self._alliance_layout = QVBoxLayout(self._alliance_frame)
        self._alliance_layout.setContentsMargins(14, 12, 14, 12)
        self._alliance_layout.setSpacing(6)
        self._alliance_frame.hide()
        ov.addWidget(self._alliance_frame)
        ov.addSpacing(8)
        self._alliance_btns: list = []

        # Custom route drawing frame
        self._custom_route_frame = QFrame()
        self._custom_route_frame.setStyleSheet(
            f"QFrame{{background:{dt.S_SURFACE};border:1px solid {dt.S_RULE};"
            f"border-radius:8px;}}"
        )
        cr_l = QVBoxLayout(self._custom_route_frame)
        cr_l.setContentsMargins(14, 12, 14, 12)
        cr_l.setSpacing(8)
        self._custom_info_lbl = QLabel("Klicke Felder auf der Karte,\num die Route zu zeichnen.")
        self._custom_info_lbl.setFont(dt.font_body(12))
        self._custom_info_lbl.setStyleSheet(f"color:{dt.S_INK_1};background:transparent;")
        self._custom_info_lbl.setWordWrap(True)
        cr_l.addWidget(self._custom_info_lbl)
        self._confirm_custom_btn = QPushButton("Route bestätigen")
        self._confirm_custom_btn.setFont(dt.font_body(13))
        self._confirm_custom_btn.setStyleSheet(
            f"QPushButton{{background:{dt.S_INK};color:{dt.S_SURFACE};"
            f"border:none;border-radius:6px;font-weight:600;padding:8px 14px;}}"
            f"QPushButton:hover{{background:{dt.S_INK_1};}}"
            f"QPushButton:disabled{{background:{dt.S_SUNK};color:{dt.S_INK_4};}}"
        )
        self._confirm_custom_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._confirm_custom_btn.clicked.connect(self.confirm_custom_route)
        cr_l.addWidget(self._confirm_custom_btn)
        self._cancel_custom_btn = QPushButton("Abbrechen")
        self._cancel_custom_btn.setFont(dt.font_body(12))
        self._cancel_custom_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{dt.S_DANGER};"
            f"border:1px solid #fcdede;border-radius:6px;padding:6px 12px;}}"
            f"QPushButton:hover{{background:#fcdede;}}"
        )
        self._cancel_custom_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_custom_btn.clicked.connect(self.cancel_custom_route)
        cr_l.addWidget(self._cancel_custom_btn)
        self._custom_route_frame.hide()
        ov.addWidget(self._custom_route_frame)
        ov.addSpacing(8)

        # Custom drawing state (panel-side)
        self._custom_drawing: bool = False
        self._custom_route_len: int = 0
        self._custom_dest_reached: bool = False

        root.addWidget(self._operate_view)
        root.addStretch()

        # ── Player list (always visible at bottom) ───────────────────── #
        root.addWidget(_hsep())
        root.addSpacing(12)
        self._list_w = QWidget()
        self._list_w.setStyleSheet("background:transparent;")
        self._list_l = QVBoxLayout(self._list_w)
        self._list_l.setContentsMargins(0, 0, 0, 0)
        self._list_l.setSpacing(3)
        root.addWidget(self._list_w)

        # Start in build view
        self._build_view.show()
        self._operate_view.hide()

    # ------------------------------------------------------------------ #
    # Button-visibility helper (operate phase)                             #
    # ------------------------------------------------------------------ #

    def _show_op(self, *buttons) -> None:
        for b in (self._roll_start_btn, self._roll_dest_btn,
                  self._join_btn, self._skip_btn,
                  self._accept_alliance_btn, self._decline_alliance_btn,
                  self._advance_btn, self._next_btn):
            b.setVisible(b in buttons)
        self._route_select_frame.hide()
        self._alliance_frame.hide()
        self._custom_route_frame.hide()

    def _rebuild_route_select(self, gs) -> None:
        """Populate the route-select frame for the current player's turn."""
        # Clear old buttons
        for b in self._route_select_btns:
            b.setParent(None)
            b.deleteLater()
        self._route_select_btns.clear()
        while self._route_select_layout.count():
            item = self._route_select_layout.takeAt(0)
            if w := item.widget():
                w.setParent(None)

        j = gs.journey
        if j is None or j.route_select_idx >= len(j.participating):
            return

        pidx = j.participating[j.route_select_idx]
        player = gs.players[pidx]
        opts = j.route_options.get(pidx, [])

        # Header
        hdr = QLabel(f"{player.name} — wähle deine Route")
        hdr.setFont(dt.font_body(13))
        hdr.setStyleSheet(
            f"color:{dt.S_INK};background:transparent;font-weight:600;"
        )
        hdr.setWordWrap(True)
        self._route_select_layout.addWidget(hdr)

        _sec = (
            f"QPushButton{{background:{dt.S_SURFACE};color:{dt.S_INK};"
            f"border:1px solid {dt.S_RULE};border-radius:6px;"
            f"font-size:12px;padding:8px 12px;text-align:left;}}"
            f"QPushButton:hover{{background:{dt.S_SUNK};}}"
        )
        _coop = (
            f"QPushButton{{background:transparent;color:{dt.S_INK_2};"
            f"border:1px solid {dt.S_RULE};border-radius:6px;"
            f"font-size:12px;padding:8px 12px;text-align:left;}}"
            f"QPushButton:hover{{background:{dt.S_SUNK};}}"
        )

        # Route option buttons
        labels = ("A", "B", "C")
        from ..game import rules as gr
        for i, route in enumerate(opts):
            info = gr.describe_route(gs, pidx, route)
            lbl = labels[i] if i < len(labels) else str(i + 1)
            desc = (f"Route {lbl}: {info['hops']} Felder"
                    f"  ·  {info['fees']} Geb."
                    f"  ·  {info['own_pct']}% eigen")
            btn = QPushButton(desc)
            btn.setFont(dt.font_body(12))
            btn.setStyleSheet(_sec)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            idx = i
            btn.clicked.connect(lambda _, ii=idx: self.select_route.emit(ii))
            filt = _RouteHoverFilter(
                lambda r=route: self.route_hover.emit(list(r)),
                lambda: self.route_hover.emit([]),
                parent=btn,
            )
            btn.installEventFilter(filt)
            self._route_select_layout.addWidget(btn)
            self._route_select_btns.append(btn)

        # Cooperation buttons — only for players who already chose their route
        already_selected = [
            pp for pp in j.participating[:j.route_select_idx]
            if pp in j.routes
        ]
        if already_selected:
            sep = QLabel("Kooperieren:")
            sep.setFont(dt.font_mono(10))
            sep.setStyleSheet(
                f"color:{dt.S_INK_3};background:transparent;letter-spacing:0.06em;"
            )
            self._route_select_layout.addWidget(sep)
            for pp in already_selected:
                partner = gs.players[pp]
                btn = QPushButton(f"Route von {partner.name} übernehmen")
                btn.setFont(dt.font_body(12))
                btn.setStyleSheet(_coop)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda _, pp=pp: self.cooperate_with.emit(pp))
                self._route_select_layout.addWidget(btn)
                self._route_select_btns.append(btn)

        # Custom route option
        draw_btn = QPushButton("Eigene Route zeichnen…")
        draw_btn.setFont(dt.font_body(12))
        draw_btn.setStyleSheet(_coop)
        draw_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        draw_btn.clicked.connect(self.draw_custom_route)
        self._route_select_layout.addWidget(draw_btn)
        self._route_select_btns.append(draw_btn)

        self._route_select_frame.show()

    def _rebuild_alliance_propose(self, gs) -> None:
        """Populate the alliance-proposal frame for the current player."""
        for b in self._alliance_btns:
            b.setParent(None)
            b.deleteLater()
        self._alliance_btns.clear()
        while self._alliance_layout.count():
            item = self._alliance_layout.takeAt(0)
            if w := item.widget():
                w.setParent(None)

        j = gs.journey
        if j is None:
            return

        already_allied = {
            p for pair in j.alliances
            for p in pair if gs.player_idx in pair
        }

        eligible = [
            i for i in range(len(gs.players))
            if i != gs.player_idx
            and i not in already_allied
            and (gs.player_idx, i) not in j.declined_proposals
        ]
        if not eligible:
            return

        _coop = (
            f"QPushButton{{background:transparent;color:{dt.S_INK_2};"
            f"border:1px solid {dt.S_RULE};border-radius:6px;"
            f"font-size:12px;padding:8px 12px;text-align:left;}}"
            f"QPushButton:hover{{background:{dt.S_SUNK};}}"
        )

        hdr = QLabel("Allianz vorschlagen:")
        hdr.setFont(dt.font_mono(10))
        hdr.setStyleSheet(
            f"color:{dt.S_INK_3};background:transparent;letter-spacing:0.06em;"
        )
        self._alliance_layout.addWidget(hdr)

        for pidx in eligible:
            partner = gs.players[pidx]
            btn = QPushButton(f"Allianz mit {partner.name}")
            btn.setFont(dt.font_body(12))
            btn.setStyleSheet(_coop)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, pp=pidx: self.propose_alliance.emit(pp))
            self._alliance_layout.addWidget(btn)
            self._alliance_btns.append(btn)

        self._alliance_frame.show()

    # ------------------------------------------------------------------ #
    # Public refresh API                                                   #
    # ------------------------------------------------------------------ #

    def refresh_build(self, gs) -> None:
        self._build_view.show()
        self._operate_view.hide()

        cp = gs.current_player
        p_idx = next(
            (i + 1 for i, c in enumerate(dt.PLAYER_COLORS)
             if c.name() == QColor(cp.color_hex).name()),
            1,
        )
        self._line_eyebrow.setText(f"Deine Linie · S{p_idx}".upper())
        self._turn_panel.refresh(gs)

        rolled    = gs.build_rolled
        has_start = gs.build_last is not None
        remaining = gs.build_pts_remaining
        total     = gs.build_pts_total
        has_pending = len(gs.pending_log) > 0

        # Button visibility for build phase
        self._btn_roll.setVisible(not rolled)
        self._btn_undo.setVisible(has_pending)
        self._btn_clear.setVisible(has_pending)
        placing_done = rolled and total > 0 and remaining == 0
        self._btn_pass.setVisible(rolled and not placing_done)
        self._btn_end_turn.setVisible(placing_done)
        self._btn_end_build.setVisible(
            gs.cities_connected_since is not None and not placing_done
        )

        # Stats
        segments = len(cp.track_edges)
        cities   = len(cp.connected_cities)
        net_pts  = segments * 4
        self._stats_panel.refresh(segments, cities, net_pts, cp.color_hex)

        self._rebuild_list(gs)

    def set_custom_route_mode(self, drawing: bool,
                               route_len: int = 0,
                               dest_reached: bool = False) -> None:
        self._custom_drawing    = drawing
        self._custom_route_len  = route_len
        self._custom_dest_reached = dest_reached

    def set_actions_visible(self, visible: bool) -> None:
        """Hide all interactive buttons when it's not the local player's turn.
        Pass True to restore (refresh_build/refresh_operate already set
        the correct per-state visibility, so True is a no-op)."""
        if visible:
            return
        for w in (self._actions_eyebrow,
                  self._btn_roll, self._btn_undo, self._btn_clear,
                  self._btn_pass, self._btn_end_turn, self._btn_end_build,
                  self._roll_start_btn, self._roll_dest_btn,
                  self._join_btn, self._skip_btn,
                  self._accept_alliance_btn, self._decline_alliance_btn,
                  self._advance_btn, self._next_btn):
            w.setVisible(False)
        self._alliance_frame.hide()
        self._custom_route_frame.hide()

    def refresh_operate(self, gs) -> None:
        self._build_view.hide()
        self._operate_view.show()

        sub = gs.operate_sub
        j   = gs.journey

        self._heat_lbl.setText(f"Rennen {gs.journey_number + 1}")

        if sub == "roll_start":
            self._info_lbl.setText("Würfeln für Startbahnhof.")
            self._show_op(self._roll_start_btn)

        elif sub == "roll_dest":
            sc = j.start_city if j else None
            txt = (f"Start: {sc['name']} ({sc['number']})\n" if sc else "")
            txt += "Würfeln für Zielbahnhof."
            self._info_lbl.setText(txt)
            self._show_op(self._roll_dest_btn)

        elif sub == "participate":
            if j and j.pending_alliance_from is not None:
                sc, dc = j.start_city, j.dest_city
                proposer = gs.players[j.pending_alliance_from]
                txt = (
                    f"Route: {sc['name']} → {dc['name']}\n"
                    f"{proposer.name} schlägt eine Allianz vor!\n"
                    f"Alliierte zahlen sich keine Streckengebühren."
                )
                self._info_lbl.setText(txt)
                self._show_op(self._accept_alliance_btn, self._decline_alliance_btn)
            else:
                if j:
                    sc, dc = j.start_city, j.dest_city
                    n = len(gs.players)
                    decided_n = len(j.decided)
                    txt = (
                        f"Route: {sc['name']} → {dc['name']}\n"
                        f"Entscheidung {decided_n + 1} von {n}\n"
                        f"{gs.current_player.name}, möchtest du mitfahren?"
                    )
                    self._info_lbl.setText(txt)
                self._show_op(self._join_btn, self._skip_btn)
                if j:
                    self._rebuild_alliance_propose(gs)

        elif sub == "route_select":
            if self._custom_drawing:
                if j:
                    sc, dc = j.start_city, j.dest_city
                    self._info_lbl.setText(
                        f"Route: {sc['name']} → {dc['name']}\n"
                        f"Klicke Felder auf der Karte."
                    )
                self._show_op()
                steps = max(0, self._custom_route_len - 1)
                txt = "Klicke Felder auf der Karte,\num die Route zu zeichnen."
                if steps > 0:
                    txt += f"\n{steps} {'Feld' if steps == 1 else 'Felder'} bisher"
                if self._custom_dest_reached:
                    txt += "\n✓ Ziel erreicht!"
                self._custom_info_lbl.setText(txt)
                self._confirm_custom_btn.setEnabled(self._custom_dest_reached)
                self._custom_route_frame.show()
            else:
                if j:
                    sc, dc = j.start_city, j.dest_city
                    n_sel = j.route_select_idx
                    n_tot = len(j.participating)
                    txt = (
                        f"Route: {sc['name']} → {dc['name']}\n"
                        f"Routenwahl {n_sel + 1} von {n_tot}"
                    )
                    self._info_lbl.setText(txt)
                self._show_op()   # hides static buttons; frame shown by _rebuild
                self._rebuild_route_select(gs)

        elif sub == "travel":
            if j:
                remaining = [p for p in j.participating if p not in j.arrived_order]
                cur_name = gs.current_player.name if gs.player_idx in remaining else ""
                lines = ["Rennen läuft\n"]
                for pidx in j.participating:
                    pl    = gs.players[pidx]
                    pos   = j.positions.get(pidx, 0)
                    route = j.routes.get(pidx, [])
                    total = max(1, len(route) - 1)
                    done  = pidx in j.arrived_order
                    rank  = (j.arrived_order.index(pidx) + 1) if done else None
                    status = f"#{rank} angekommen" if done else f"{pos} / {total}"
                    arrow = " ←" if pidx == gs.player_idx and not done else ""
                    lines.append(f"  {pl.name}: {status}{arrow}")
                self._info_lbl.setText("\n".join(lines))
                if remaining:
                    self._advance_btn.setText(
                        f"{cur_name} würfeln  →" if cur_name else "Zug vorrücken  →"
                    )
                    self._show_op(self._advance_btn)
                else:
                    self._show_op(self._next_btn)
            else:
                self._show_op(self._next_btn)

        elif sub == "post_journey":
            if j:
                lines = ["Ergebnisse:\n"]
                for rank, pidx in enumerate(j.arrived_order, 1):
                    prize = 20 if rank == 1 else (10 if rank == 2 else 0)
                    lines.append(f"  {rank}. {gs.players[pidx].name}  +{prize}")
                if not j.arrived_order:
                    lines.append("Keine Ankünfte.")
                self._info_lbl.setText("\n".join(lines))
            self._show_op(self._next_btn)

        elif sub == "winner":
            self._info_lbl.setText(
                f"{gs.winner.name} gewinnt!\n"
                f"Endstand: {gs.winner.money}"
            )
            self._show_op()

        self._rebuild_list(gs)

    # ------------------------------------------------------------------ #
    # Player list                                                          #
    # ------------------------------------------------------------------ #

    def _rebuild_list(self, gs) -> None:
        while self._list_l.count():
            item = self._list_l.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, p in enumerate(gs.players):
            active = (i == gs.player_idx and gs.winner is None)
            row = QWidget()
            row.setStyleSheet("background:transparent;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 2, 0, 2)
            rl.setSpacing(6)

            dot = _Dot(p.color_hex, 10)
            rl.addWidget(dot, 0, Qt.AlignmentFlag.AlignVCenter)

            name_lbl = QLabel(p.name)
            name_lbl.setFont(dt.font_body(12))
            name_lbl.setStyleSheet(
                f"color:{dt.S_INK if active else dt.S_INK_3};"
                f"background:transparent;"
                + ("font-weight:600;" if active else "")
            )
            rl.addWidget(name_lbl, 1)

            money_lbl = QLabel(str(p.money))
            money_lbl.setFont(dt.font_mono(11))
            money_lbl.setStyleSheet(f"color:{dt.S_INK_2};background:transparent;")
            money_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            rl.addWidget(money_lbl)

            self._list_l.addWidget(row)

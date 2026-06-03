"""
Race phase screen — 56px header + 2-col body (320px standings | map).
Matches the RaceScreen layout from screens.jsx.
"""
from __future__ import annotations
from typing import Sequence

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QPen
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QSizePolicy, QSpacerItem, QVBoxLayout, QWidget,
)

import dampfross.ui.design_tokens as dt
from dampfross.ui.components import Badge, Chip, DieWidget


# ── Helpers ───────────────────────────────────────────────────────────── #

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


def _vsep() -> QWidget:
    w = QWidget()
    w.setFixedSize(1, 18)
    w.setStyleSheet(f"background:rgba(244,242,236,64);")
    return w


# ── Player standing row ───────────────────────────────────────────────── #

class _StandingRow(QWidget):
    """
    Single racer standing card — mirroring `dr-player` with left color stripe.
    state: 'leading' | 'chasing' | 'derailed' | 'finished'
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(58)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            f"_StandingRow{{background:{dt.S_SURFACE};"
            f"border:1px solid {dt.S_RULE};border-radius:8px;}}"
        )

        # Left color stripe (4 px)
        self._stripe = QWidget(self)
        self._stripe.setFixedWidth(4)
        self._stripe.setStyleSheet(
            f"background:{dt.S_INK_4};border-radius:8px 0 0 8px;"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(0)

        # Position number (28px column)
        self._pos_lbl = QLabel("01")
        self._pos_lbl.setFont(dt.font_mono(13))
        self._pos_lbl.setFixedWidth(28)
        self._pos_lbl.setStyleSheet(
            f"color:{dt.S_INK_2};background:transparent;font-weight:600;"
        )
        layout.addWidget(self._pos_lbl)

        # Name + progress
        col = QVBoxLayout()
        col.setSpacing(2)
        col.setContentsMargins(0, 0, 0, 0)
        self._name_lbl = QLabel("Player")
        f = dt.font_body(14)
        f.setWeight(QFont.Weight(600))
        self._name_lbl.setFont(f)
        self._name_lbl.setStyleSheet(f"color:{dt.S_INK};background:transparent;")
        col.addWidget(self._name_lbl)
        self._sub_lbl = QLabel("0 of 0 · ETA —")
        self._sub_lbl.setFont(dt.font_mono(10))
        self._sub_lbl.setStyleSheet(
            f"color:{dt.S_INK_3};background:transparent;letter-spacing:0.08em;"
        )
        col.addWidget(self._sub_lbl)
        layout.addLayout(col, 1)

        # State badge
        self._badge = Badge("chasing", "default")
        layout.addWidget(self._badge, 0, Qt.AlignmentFlag.AlignVCenter)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._stripe.setGeometry(0, 0, 4, self.height())

    def refresh(self, pos: int, name: str, state: str,
                progress: str, eta: str, color_hex: str) -> None:
        self._pos_lbl.setText(f"{pos:02d}")
        self._name_lbl.setText(name)
        self._sub_lbl.setText(f"{progress} · ETA {eta}".upper())
        self._stripe.setStyleSheet(
            f"background:{color_hex};border-radius:8px 0 0 8px;"
        )
        badge_variant = (
            "success" if state == "leading"
            else "danger" if state == "derailed"
            else "default"
        )
        self._badge.set_text(state)
        self._badge.set_variant(badge_variant)


# ── Heat board row ────────────────────────────────────────────────────── #

class _HeatRow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(8)

        col = QVBoxLayout()
        col.setSpacing(2)
        col.setContentsMargins(0, 0, 0, 0)
        self._heat_lbl = QLabel("Heat 1")
        self._heat_lbl.setFont(dt.font_mono(10))
        self._heat_lbl.setStyleSheet(
            f"color:{dt.S_INK_3};background:transparent;letter-spacing:0.08em;"
        )
        col.addWidget(self._heat_lbl)
        self._route_lbl = QLabel("Start → End")
        self._route_lbl.setFont(dt.font_body(13))
        self._route_lbl.setStyleSheet(
            f"color:{dt.S_INK};background:transparent;font-weight:500;"
        )
        col.addWidget(self._route_lbl)
        layout.addLayout(col, 1)

        # Right indicator: chip (done), "Live" badge (active), or "QUEUED" label
        self._chip   = Chip("—", "#888")
        self._live   = Badge("Live", "solid")
        self._queued = QLabel("QUEUED")
        self._queued.setFont(dt.font_mono(11))
        self._queued.setStyleSheet(
            f"color:{dt.S_INK_3};background:transparent;"
        )
        for w in (self._chip, self._live, self._queued):
            layout.addWidget(w, 0, Qt.AlignmentFlag.AlignVCenter)

    def refresh(self, heat_label: str, route: str, state: str,
                winner_name: str = "", winner_color: str = "") -> None:
        self._heat_lbl.setText(heat_label.upper())
        self._route_lbl.setText(route)
        self._chip.setVisible(state == "done")
        self._live.setVisible(state == "active")
        self._queued.setVisible(state == "queued")
        if state == "done" and winner_name:
            self._chip._lbl.setText(winner_name)
            self._chip.set_color(winner_color)


# ── Left rail ─────────────────────────────────────────────────────────── #

class _LeftRail(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(320)
        self.setStyleSheet(
            f"_LeftRail{{background:{dt.S_SURFACE_2};"
            f"border-right:1px solid {dt.S_RULE};}}"
        )

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
        root.setContentsMargins(16, 18, 16, 18)
        root.setSpacing(0)

        self._eyebrow_lbl = _eyebrow("Heat 1 · Live")
        root.addWidget(self._eyebrow_lbl)
        root.addSpacing(4)

        self._route_lbl = QLabel("Start → Destination")
        f = dt.font_display(24)
        f.setWeight(QFont.Weight(600))
        self._route_lbl.setFont(f)
        self._route_lbl.setStyleSheet(
            f"color:{dt.S_INK};background:transparent;letter-spacing:-0.015em;"
        )
        self._route_lbl.setWordWrap(True)
        root.addWidget(self._route_lbl)
        root.addSpacing(16)

        # Standing rows
        self._standing_rows: list[_StandingRow] = []
        self._standings_w = QWidget()
        self._standings_w.setStyleSheet("background:transparent;")
        self._standings_l = QVBoxLayout(self._standings_w)
        self._standings_l.setContentsMargins(0, 0, 0, 0)
        self._standings_l.setSpacing(8)
        root.addWidget(self._standings_w)
        root.addSpacing(24)

        # Heat board
        root.addWidget(_eyebrow("Heat board"))
        root.addSpacing(10)

        self._heat_frame = QFrame()
        self._heat_frame.setStyleSheet(
            f"QFrame{{background:{dt.S_SURFACE};border:1px solid {dt.S_RULE};"
            f"border-radius:8px;}}"
        )
        heat_l = QVBoxLayout(self._heat_frame)
        heat_l.setContentsMargins(14, 10, 14, 10)
        heat_l.setSpacing(0)

        self._heat_rows: list[_HeatRow] = []
        for i in range(3):
            if i > 0:
                heat_l.addWidget(_hsep())
            row = _HeatRow()
            self._heat_rows.append(row)
            heat_l.addWidget(row)

        root.addWidget(self._heat_frame)
        root.addStretch()

    def set_standings(self, standings: list[dict]) -> None:
        """
        standings: list of dicts with keys:
            pos, name, state, progress, eta, color_hex
        """
        # Grow or shrink standing rows
        while len(self._standing_rows) < len(standings):
            row = _StandingRow()
            self._standing_rows.append(row)
            self._standings_l.addWidget(row)
        for i, row in enumerate(self._standing_rows):
            if i < len(standings):
                d = standings[i]
                row.refresh(
                    d.get("pos", i + 1),
                    d.get("name", "?"),
                    d.get("state", "chasing"),
                    d.get("progress", "0 of 0"),
                    d.get("eta", "—"),
                    d.get("color_hex", dt.S_INK_4),
                )
                row.show()
            else:
                row.hide()

    def set_heat(self, number: int, route: str) -> None:
        self._eyebrow_lbl.setText(f"Heat {number} · Live".upper())
        self._route_lbl.setText(route)

    def set_heat_board(self, heats: list[dict]) -> None:
        """
        heats: list of dicts with keys:
            label, route, state ('done'|'active'|'queued'),
            winner_name, winner_color
        """
        for i, hr in enumerate(self._heat_rows):
            if i < len(heats):
                h = heats[i]
                hr.refresh(
                    h.get("label", f"Heat {i + 1}"),
                    h.get("route", "—"),
                    h.get("state", "queued"),
                    h.get("winner_name", ""),
                    h.get("winner_color", ""),
                )

    def refresh_theme(self) -> None:
        self.setStyleSheet(
            f"_LeftRail{{background:{dt.S_SURFACE_2};"
            f"border-right:1px solid {dt.S_RULE};}}"
        )
        self._route_lbl.setStyleSheet(
            f"color:{dt.S_INK};background:transparent;letter-spacing:-0.015em;"
        )
        self._heat_frame.setStyleSheet(
            f"QFrame{{background:{dt.S_SURFACE};border:1px solid {dt.S_RULE};"
            f"border-radius:8px;}}"
        )


# ── Race HUD pill (bottom of map) ─────────────────────────────────────── #

class _RaceHud(QWidget):
    advance_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Dark pill background drawn via stylesheet on container
        container = QWidget(self)
        container.setObjectName("hudPill")
        container.setStyleSheet(
            f"QWidget#hudPill{{"
            f"  background:rgba(20,23,28,235);"
            f"  border-radius:999px;"
            f"}}"
        )
        container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout_outer = QHBoxLayout(self)
        layout_outer.setContentsMargins(0, 0, 0, 0)
        layout_outer.addWidget(container)

        row = QHBoxLayout(container)
        row.setContentsMargins(16, 10, 10, 10)
        row.setSpacing(16)

        # Left text block
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setContentsMargins(0, 0, 0, 0)
        self._who_lbl = QLabel("Player rolls")
        self._who_lbl.setFont(dt.font_mono(10))
        self._who_lbl.setStyleSheet(
            "color:rgba(244,242,236,153);background:transparent;letter-spacing:0.08em;"
        )
        text_col.addWidget(self._who_lbl)
        self._advance_lbl = QLabel("+0 hex this turn")
        f = dt.font_display(14)
        f.setWeight(QFont.Weight(600))
        self._advance_lbl.setFont(f)
        self._advance_lbl.setStyleSheet(
            "color:rgba(244,242,236,255);background:transparent;"
        )
        text_col.addWidget(self._advance_lbl)
        row.addLayout(text_col)

        # Dice
        self._die1 = DieWidget(1)
        self._die2 = DieWidget(1)
        row.addWidget(self._die1)
        row.addWidget(self._die2)

        # Advance button
        self._advance_btn = QPushButton("Advance train")
        self._advance_btn.setFont(dt.font_body(13))
        self._advance_btn.setStyleSheet(
            f"QPushButton{{background:{dt.S_P3};color:#ffffff;"
            f"border:none;border-radius:999px;font-size:13px;font-weight:600;"
            f"padding:8px 16px;}}"
            f"QPushButton:hover{{background:#155c38;}}"
        )
        self._advance_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._advance_btn.clicked.connect(self.advance_clicked)
        row.addWidget(self._advance_btn)

    def reposition(self, parent_w: int, parent_h: int) -> None:
        self.adjustSize()
        x = (parent_w - self.width()) // 2
        y = parent_h - self.height() - 24
        self.move(x, y)

    def refresh(self, player_name: str, d1: int, d2: int,
                total: int, show_advance: bool = True) -> None:
        self._who_lbl.setText(f"{player_name} rolls".upper())
        self._advance_lbl.setText(f"+{total} hex this turn")
        self._die1.set_value(d1)
        self._die2.set_value(d2)
        self._advance_btn.setVisible(show_advance)


# ── Map panel ─────────────────────────────────────────────────────────── #

class _MapPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{dt.S_PAPER};")

        from dampfross.ui.hex_map_widget import HexMapWidget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._map = HexMapWidget(self)
        layout.addWidget(self._map)

        self._hud = _RaceHud(self)

    def set_grid(self, grid) -> None:
        self._map.set_grid(grid)

    @property
    def hud(self) -> _RaceHud:
        return self._hud

    @property
    def map_widget(self):
        return self._map

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._hud.reposition(self.width(), self.height())


# ── Header bar ────────────────────────────────────────────────────────── #

class _HeaderBar(QWidget):
    settings_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self.setStyleSheet(
            f"_HeaderBar{{background:{dt.S_SURFACE};"
            f"border-bottom:1px solid {dt.S_RULE};}}"
        )
        row = QHBoxLayout(self)
        row.setContentsMargins(20, 0, 20, 0)
        row.setSpacing(16)

        # Logo
        logo = QLabel("⬡")
        logo.setFont(dt.font_display(22))
        logo.setStyleSheet(f"color:{dt.S_INK};background:transparent;")
        row.addWidget(logo)

        # "Race phase" badge (P5 tint)
        race_badge = QLabel("Race phase")
        race_badge.setFont(dt.font_mono(10))
        race_badge.setStyleSheet(
            f"QLabel{{background:{dt.S_P5_TINT};color:{dt.S_P5};"
            f"border-radius:999px;padding:3px 8px;"
            f"font-size:10px;font-weight:500;letter-spacing:0.08em;}}"
        )
        row.addWidget(race_badge)

        self._sub_lbl = QLabel("Heat 1 of 3 · Start → End")
        self._sub_lbl.setFont(dt.font_mono(11))
        self._sub_lbl.setStyleSheet(
            f"color:{dt.S_INK_3};background:transparent;letter-spacing:0.08em;"
        )
        row.addWidget(self._sub_lbl)
        row.addStretch()

        # Timer
        self._timer_lbl = QLabel("00:00")
        self._timer_lbl.setFont(dt.font_mono(13))
        self._timer_lbl.setStyleSheet(
            f"color:{dt.S_INK_2};background:transparent;"
        )
        row.addWidget(self._timer_lbl)

        # Gear
        gear_btn = QPushButton("⚙")
        gear_btn.setFont(dt.font_body(16))
        gear_btn.setFixedSize(36, 36)
        gear_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{dt.S_INK_2};border:none;"
            f"border-radius:8px;font-size:16px;}}"
            f"QPushButton:hover{{background:{dt.S_SUNK};}}"
        )
        gear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        gear_btn.clicked.connect(self.settings_clicked)
        row.addWidget(gear_btn)

    def set_sub(self, heat_n: int, heat_total: int, route: str) -> None:
        self._sub_lbl.setText(
            f"Heat {heat_n} of {heat_total} · {route}".upper()
        )

    def set_timer(self, text: str) -> None:
        self._timer_lbl.setText(text)

    def refresh_theme(self) -> None:
        self.setStyleSheet(
            f"_HeaderBar{{background:{dt.S_SURFACE};"
            f"border-bottom:1px solid {dt.S_RULE};}}"
        )


# ── Public screen widget ──────────────────────────────────────────────── #

class RaceScreen(QWidget):
    """
    Full race-phase screen.  Signals: advance_clicked, settings_clicked.
    """
    advance_clicked  = pyqtSignal()
    settings_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{dt.S_PAPER};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._header = _HeaderBar()
        self._header.settings_clicked.connect(self.settings_clicked)
        root.addWidget(self._header)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._left  = _LeftRail()
        self._right = _MapPanel()
        self._right.hud.advance_clicked.connect(self.advance_clicked)

        body.addWidget(self._left)
        body.addWidget(self._right, 1)
        root.addLayout(body, 1)

        self._load_demo()

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    @property
    def map_widget(self):
        return self._right.map_widget

    def set_grid(self, grid) -> None:
        self._right.set_grid(grid)

    def set_heat(self, number: int, total: int, route: str) -> None:
        self._header.set_sub(number, total, route)
        self._left.set_heat(number, route)

    def set_standings(self, standings: list[dict]) -> None:
        self._left.set_standings(standings)

    def set_heat_board(self, heats: list[dict]) -> None:
        self._left.set_heat_board(heats)

    def set_dice(self, player_name: str, d1: int, d2: int,
                 show_advance: bool = True) -> None:
        total = d1 + d2
        self._right.hud.refresh(player_name, d1, d2, total, show_advance)

    def set_timer(self, text: str) -> None:
        self._header.set_timer(text)

    def refresh_theme(self) -> None:
        self.setStyleSheet(f"background:{dt.S_PAPER};")
        self._header.refresh_theme()
        self._left.refresh_theme()

    # ------------------------------------------------------------------ #
    # Demo data (matches screens.jsx mock)                                 #
    # ------------------------------------------------------------------ #

    def _load_demo(self) -> None:
        self.set_heat(2, 3, "Marienburg → Sandhafen")
        self.set_standings([
            {"pos": 1, "name": "Lukas",  "state": "leading",
             "progress": "12 of 18", "eta": "1 turn",  "color_hex": dt.S_P2},
            {"pos": 2, "name": "Mira",   "state": "chasing",
             "progress": "10 of 18", "eta": "2 turns", "color_hex": dt.S_P1},
            {"pos": 3, "name": "Pieter", "state": "chasing",
             "progress": "8 of 18",  "eta": "3 turns", "color_hex": dt.S_P4},
            {"pos": 4, "name": "Sasha",  "state": "derailed",
             "progress": "5 of 18",  "eta": "—",        "color_hex": dt.S_P7},
        ])
        self.set_heat_board([
            {"label": "Heat 1", "route": "Aschberg → Lichtenau",
             "state": "done",   "winner_name": "Mira",  "winner_color": dt.S_P1},
            {"label": "Heat 2", "route": "Marienburg → Sandhafen",
             "state": "active"},
            {"label": "Heat 3", "route": "Vossberg → Kupferstadt",
             "state": "queued"},
        ])
        self.set_dice("Lukas", 4, 3, show_advance=True)
        self.set_timer("03:21")

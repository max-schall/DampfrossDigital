"""
MapViewScreen — mid-game observer layout (screen 2).
Layout: 56px header + 3-col body (260px player list | 1fr map | 280px inspector).
Matches MapViewScreen from screens.jsx.
"""
from __future__ import annotations
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QSizePolicy, QSpacerItem, QVBoxLayout, QWidget,
)

import dampfross.ui.design_tokens as dt
from .components import (
    Badge, Chip, HudWidget, IconButton, OverlayCard, PlayerCard, SegmentedControl,
)
from .hex_map_widget import HexMapWidget


# ── inline SVG icons ──────────────────────────────────────────────────────#
_GEAR_SVG = (
    '<svg width="14" height="14" viewBox="0 0 16 16" fill="none">'
    '<circle cx="8" cy="8" r="2.2" stroke="currentColor" stroke-width="1.4"/>'
    '<path d="M8 2v1.6M8 12.4V14M2 8h1.6M12.4 8H14'
    'M3.5 3.5l1.1 1.1M11.4 11.4l1.1 1.1M12.5 3.5l-1.1 1.1M4.6 11.4l-1.1 1.1"'
    ' stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>'
    '</svg>'
)
_PLUS_SVG  = '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 3v8m-4-4h8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>'
_MINUS_SVG = '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 7h8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>'


def _icon_btn(text: str = "") -> QPushButton:
    btn = QPushButton(text)
    btn.setFixedSize(32, 32)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(
        f"QPushButton {{background:{dt.S_SURFACE}; border:1px solid {dt.S_RULE};"
        f" border-radius:8px; color:{dt.S_INK_1}; font-size:14px;}}"
        f"QPushButton:hover {{ background:{dt.S_SUNK}; }}"
    )
    return btn


def _sep_h() -> QFrame:
    f = QFrame(); f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"border:none; background:{dt.S_RULE}; max-height:1px;")
    return f


def _eyebrow(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setFont(dt.font_mono(10))
    lbl.setStyleSheet(
        f"color:{dt.S_INK_2}; background:transparent; letter-spacing:0.12em;"
    )
    return lbl


# ── Header bar ───────────────────────────────────────────────────────────#

class _HeaderBar(QWidget):
    settings_clicked = pyqtSignal()
    view_changed     = pyqtSignal(str)   # 'map' | 'standings' | 'log'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self.setStyleSheet(
            f"background:{dt.S_SURFACE}; border-bottom:1px solid {dt.S_RULE};"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(16)

        # Logo
        logo = QLabel("⬡  DampfrossDigital")
        f = dt.font_display(12)
        f.setWeight(QFont.Weight(600))
        logo.setFont(f)
        logo.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")
        layout.addWidget(logo)

        self._round_badge = Badge("Round 4 / 9 · Network phase")
        layout.addWidget(self._round_badge)

        self._session_lbl = QLabel("Sunday at Tilman's")
        self._session_lbl.setFont(dt.font_mono(10))
        self._session_lbl.setStyleSheet(
            f"color:{dt.S_INK_3}; background:transparent; letter-spacing:0.08em;"
        )
        layout.addWidget(self._session_lbl)

        layout.addStretch()

        self._view_seg = SegmentedControl(["Map", "Standings", "Log"])
        self._view_seg.changed.connect(self._on_view_changed)
        layout.addWidget(self._view_seg)

        gear = _icon_btn("⚙")
        gear.clicked.connect(self.settings_clicked)
        layout.addWidget(gear)

    def _on_view_changed(self, idx: int) -> None:
        views = ["map", "standings", "log"]
        self.view_changed.emit(views[idx])

    def set_round(self, text: str) -> None:
        self._round_badge.set_text(text)

    def set_session(self, name: str) -> None:
        self._session_lbl.setText(name)

    def refresh_theme(self) -> None:
        self.setStyleSheet(
            f"background:{dt.S_SURFACE}; border-bottom:1px solid {dt.S_RULE};"
        )


# ── Left rail ────────────────────────────────────────────────────────────#

class _LeftRail(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(260)
        self.setStyleSheet(
            f"background:{dt.S_SURFACE_2}; border-right:1px solid {dt.S_RULE};"
        )
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background:transparent;")
        outer.addWidget(scroll)

        inner = QWidget()
        inner.setStyleSheet("background:transparent;")
        scroll.setWidget(inner)
        self._layout = QVBoxLayout(inner)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(8)

        self._player_eyebrow = _eyebrow("Players · 0")
        self._layout.addWidget(self._player_eyebrow)

        self._players_col = QVBoxLayout()
        self._players_col.setSpacing(8)
        self._layout.addLayout(self._players_col)

        self._layout.addSpacing(16)
        self._layout.addWidget(_eyebrow("Race objectives"))
        self._layout.addSpacing(8)

        self._obj_col = QVBoxLayout()
        self._obj_col.setSpacing(8)
        self._layout.addLayout(self._obj_col)

        self._layout.addStretch()

    def set_players(self, players: list[dict]) -> None:
        """players = list of dicts with keys: player_idx, name, state, score, coins, trains"""
        while self._players_col.count():
            item = self._players_col.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._player_eyebrow.setText(f"PLAYERS · {len(players)}")
        for p in players:
            card = PlayerCard(
                player_idx=p.get("player_idx", 1),
                name=p.get("name", ""),
                state=p.get("state", "idle"),
                score=p.get("score", 0),
                coins=p.get("coins", 0),
                trains=p.get("trains", 0),
            )
            self._players_col.addWidget(card)

    def set_objectives(self, objectives: list[dict]) -> None:
        """objectives = list of dicts with keys: title, body, foot, tone"""
        while self._obj_col.count():
            item = self._obj_col.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for obj in objectives:
            card = OverlayCard(
                title=obj.get("title", ""),
                body=obj.get("body", ""),
                foot=obj.get("foot", ""),
                tone=obj.get("tone", "neutral"),
            )
            self._obj_col.addWidget(card)

    def refresh_theme(self) -> None:
        self.setStyleSheet(
            f"background:{dt.S_SURFACE_2}; border-right:1px solid {dt.S_RULE};"
        )


# ── Right inspector rail ─────────────────────────────────────────────────#

class _RightRail(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(280)
        self.setStyleSheet(
            f"background:{dt.S_SURFACE_2}; border-left:1px solid {dt.S_RULE};"
        )
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background:transparent;")
        outer.addWidget(scroll)

        inner = QWidget()
        inner.setStyleSheet("background:transparent;")
        scroll.setWidget(inner)
        self._layout = QVBoxLayout(inner)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(0)

        self._hex_eyebrow = _eyebrow("Hovered · —")
        self._layout.addWidget(self._hex_eyebrow)
        self._layout.addSpacing(10)

        # Tile info panel
        self._tile_panel = _TileInfoPanel()
        self._layout.addWidget(self._tile_panel)

        self._layout.addSpacing(18)
        self._layout.addWidget(_eyebrow("Recent log"))
        self._layout.addSpacing(8)

        self._log_col = QVBoxLayout()
        self._log_col.setSpacing(6)
        self._layout.addLayout(self._log_col)
        self._layout.addStretch()

    def set_hovered_hex(self, row: int, col: int, terrain: str = "plain",
                        build_cost: int = 1, race_cost: int = 1,
                        lines_through: list[int] | None = None) -> None:
        self._hex_eyebrow.setText(f"HOVERED · HEX {row}·{chr(65+col)}")
        self._tile_panel.update_info(terrain, build_cost, race_cost, lines_through or [])

    def set_log(self, entries: list[dict]) -> None:
        """entries = list of dicts: who, player_idx, what, time"""
        while self._log_col.count():
            item = self._log_col.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for e in entries:
            row_w = QWidget()
            row_w.setStyleSheet("background:transparent;")
            rl = QHBoxLayout(row_w)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(8)

            dot = QWidget()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(
                f"background:{dt.player_hex(e.get('player_idx', 1))};"
                f" border-radius:4px;"
            )
            rl.addWidget(dot, 0, Qt.AlignmentFlag.AlignTop)

            who = e.get("who", "")
            what = e.get("what", "")
            txt = QLabel(f"<b>{who}</b> {what}")
            txt.setFont(dt.font_body(12))
            txt.setStyleSheet(f"color:{dt.S_INK_1}; background:transparent;")
            txt.setWordWrap(True)
            rl.addWidget(txt, 1)

            time_lbl = QLabel(e.get("time", ""))
            time_lbl.setFont(dt.font_mono(9))
            time_lbl.setStyleSheet(f"color:{dt.S_INK_3}; background:transparent;")
            rl.addWidget(time_lbl)

            self._log_col.addWidget(row_w)

    def refresh_theme(self) -> None:
        self.setStyleSheet(
            f"background:{dt.S_SURFACE_2}; border-left:1px solid {dt.S_RULE};"
        )


class _TileInfoPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"_TileInfoPanel {{background:{dt.S_SURFACE}; border:1px solid {dt.S_RULE};"
            f" border-radius:{dt.R_3}px;}}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # header
        head = QWidget()
        head.setStyleSheet(
            f"background:{dt.S_SURFACE_2}; border-bottom:1px solid {dt.S_RULE};"
        )
        hl = QHBoxLayout(head)
        hl.setContentsMargins(16, 10, 16, 10)
        hl.setSpacing(8)
        self._title_lbl = QLabel("—")
        ft = dt.font_display(13)
        ft.setWeight(QFont.Weight(600))
        self._title_lbl.setFont(ft)
        self._title_lbl.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")
        hl.addWidget(self._title_lbl)
        self._sub_lbl = QLabel()
        self._sub_lbl.setFont(dt.font_mono(10))
        self._sub_lbl.setStyleSheet(f"color:{dt.S_INK_3}; background:transparent;")
        hl.addWidget(self._sub_lbl)
        hl.addStretch()
        layout.addWidget(head)

        # body
        body = QVBoxLayout()
        body.setContentsMargins(16, 12, 16, 12)
        body.setSpacing(8)

        self._build_row = self._make_kv("Build cost", "—")
        self._race_row  = self._make_kv("Race cost",  "—")
        self._lines_row = self._make_kv("Lines through", "—")
        body.addLayout(self._build_row[0])
        body.addLayout(self._race_row[0])
        body.addLayout(self._lines_row[0])
        layout.addLayout(body)

    def _make_kv(self, key: str, val: str) -> tuple:
        row = QHBoxLayout()
        row.setSpacing(0)
        k = QLabel(key.upper())
        k.setFont(dt.font_mono(10))
        k.setStyleSheet(f"color:{dt.S_INK_3}; background:transparent; letter-spacing:0.08em;")
        v = QLabel(val)
        v.setFont(dt.font_mono(12))
        fv = dt.font_mono(12)
        fv.setWeight(QFont.Weight(600))
        v.setFont(fv)
        v.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")
        v.setAlignment(Qt.AlignmentFlag.AlignRight)
        row.addWidget(k)
        row.addStretch()
        row.addWidget(v)
        return row, k, v

    def update_info(self, terrain: str, build_cost: int, race_cost: int,
                    lines_through: list[int]) -> None:
        self._title_lbl.setText(terrain.capitalize() + " terrain")
        self._sub_lbl.setText(terrain.upper())
        self._build_row[2].setText(f"{build_cost} coins")
        self._race_row[2].setText(f"{race_cost} turns")
        if lines_through:
            colors = "  ".join(
                f'<span style="color:{dt.player_hex(p)}">●</span>'
                for p in lines_through
            )
            self._lines_row[2].setText(colors)
        else:
            self._lines_row[2].setText("none")


# ── Map panel (center) ───────────────────────────────────────────────────#

class _MapPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.map_widget = HexMapWidget(self)
        layout.addWidget(self.map_widget)

        # Floating zoom controls (top-right)
        self._zoom_widget = _ZoomControls(self)

        # HUD
        self.hud = HudWidget(self)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        self._zoom_widget.move(w - self._zoom_widget.width() - 16, 16)
        self.hud.reposition()


class _ZoomControls(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        self.setStyleSheet(
            f"background:{dt.S_SURFACE}; border:1px solid {dt.S_RULE}; border-radius:10px;"
        )
        for label in ("+", "−", "○"):
            btn = QPushButton(label)
            btn.setFixedSize(32, 32)
            btn.setStyleSheet(
                f"QPushButton {{border:none; background:transparent; color:{dt.S_INK_1};"
                f" font-size:16px; border-radius:8px;}}"
                f"QPushButton:hover {{ background:{dt.S_SUNK}; }}"
            )
            layout.addWidget(btn)
        self.adjustSize()


# ── MapViewScreen ────────────────────────────────────────────────────────#

class MapViewScreen(QWidget):
    """
    Full mid-game observer screen.
    Public interface:
      set_players(list[dict])       → refresh player list
      set_objectives(list[dict])    → refresh race objectives
      set_log(list[dict])           → refresh action log
      set_hovered_hex(r, c, ...)    → update inspector
      set_round(text)               → update header badge
      map_widget                    → access the HexMapWidget directly
    """
    settings_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{dt.S_PAPER};")
        self._build_ui()
        self._load_demo_data()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._header = _HeaderBar(self)
        self._header.settings_clicked.connect(self.settings_clicked)
        root.addWidget(self._header)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._left  = _LeftRail(self)
        self._map   = _MapPanel(self)
        self._right = _RightRail(self)

        body.addWidget(self._left)
        body.addWidget(self._map, 1)
        body.addWidget(self._right)

        root.addLayout(body, 1)

    def _load_demo_data(self) -> None:
        self._left.set_players([
            {"player_idx": 2, "name": "Lukas",  "state": "active", "score": 128, "coins": 6, "trains": 11},
            {"player_idx": 1, "name": "Mira",   "state": "idle",   "score": 112, "coins": 4, "trains": 13},
            {"player_idx": 4, "name": "Pieter", "state": "idle",   "score": 98,  "coins": 9, "trains": 9},
            {"player_idx": 7, "name": "Sasha",  "state": "idle",   "score": 91,  "coins": 3, "trains": 14},
        ])
        self._left.set_objectives([
            {"title": "Capitals",      "body": "Connect 4 capitals",       "foot": "2 / 4 reached", "tone": "info"},
            {"title": "Coast to coast","body": "Sandhafen → Kupferstadt",  "foot": "incomplete",    "tone": "warn"},
        ])
        self._right.set_log([
            {"who": "Mira",   "player_idx": 1, "what": "laid 2 segments toward Lichtenau", "time": "00:42"},
            {"who": "Lukas",  "player_idx": 2, "what": "rolled a 4",                       "time": "00:31"},
            {"who": "Pieter", "player_idx": 4, "what": "connected Marienburg",             "time": "01:08"},
            {"who": "Sasha",  "player_idx": 7, "what": "passed turn",                      "time": "01:24"},
        ])
        self._map.hud.set_player(dt.S_P2, "Lukas · S2")
        self._map.hud.set_phase("Network · 2 of 5 left")
        self._map.hud.add_action("Undo")
        self._map.hud.add_action("End turn", accent=True)

    # ── Public API ─────────────────────────────────────────────────────── #

    @property
    def map_widget(self) -> HexMapWidget:
        return self._map.map_widget

    def set_players(self, players: list[dict]) -> None:
        self._left.set_players(players)

    def set_objectives(self, objectives: list[dict]) -> None:
        self._left.set_objectives(objectives)

    def set_log(self, entries: list[dict]) -> None:
        self._right.set_log(entries)

    def set_hovered_hex(self, row: int, col: int, terrain: str = "plain",
                        build_cost: int = 1, race_cost: int = 1,
                        lines_through: list[int] | None = None) -> None:
        self._right.set_hovered_hex(row, col, terrain, build_cost, race_cost, lines_through)

    def set_round(self, text: str) -> None:
        self._header.set_round(text)

    def set_session(self, name: str) -> None:
        self._header.set_session(name)

    def refresh_theme(self) -> None:
        self.setStyleSheet(f"background:{dt.S_PAPER};")
        self._header.refresh_theme()
        self._left.refresh_theme()
        self._right.refresh_theme()
        self._map.map_widget.refresh_theme()

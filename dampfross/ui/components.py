"""
Reusable UI components matching the DampfrossDigital design system (ds.css).
Each class mirrors the corresponding dr-* CSS component.
"""
from __future__ import annotations
import math
from PyQt6.QtCore import Qt, QRect, QRectF, QSize, QTimer, pyqtSignal
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import (
    QColor, QFont, QPainter, QPainterPath, QPen, QBrush, QPolygonF
)
from PyQt6.QtWidgets import (
    QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel,
    QSizePolicy, QVBoxLayout, QWidget, QPushButton,
)
from PyQt6.QtCore import QPropertyAnimation

import dampfross.ui.design_tokens as dt


# ── helpers ──────────────────────────────────────────────────────────────── #

def _lbl(text: str = "", size_pt: int = 11, color: str = "",
         bold: bool = False, mono: bool = False) -> QLabel:
    w = QLabel(text)
    f = dt.font_mono(size_pt) if mono else dt.font_body(size_pt)
    if bold:
        f.setWeight(QFont.Weight(600))
    w.setFont(f)
    style = f"color:{color or dt.S_INK_2}; background:transparent;"
    w.setStyleSheet(style)
    return w


def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"border:none; background:{dt.S_RULE}; max-height:1px;")
    return f


# ── Badge (dr-badge) ──────────────────────────────────────────────────────#

class Badge(QLabel):
    """
    Pill badge with optional colored dot.
    Variants: 'default' | 'solid' | 'success' | 'warn' | 'danger'
    """
    def __init__(self, text: str = "", variant: str = "default",
                 dot: bool = False, parent=None):
        super().__init__(parent)
        self._variant = variant
        self._dot = dot
        self._text_raw = text
        self._rebuild()

    def set_text(self, text: str) -> None:
        self._text_raw = text
        self._rebuild()

    def set_variant(self, variant: str) -> None:
        self._variant = variant
        self._rebuild()

    def _rebuild(self) -> None:
        dot_html = (
            f'<span style="display:inline-block;width:6px;height:6px;'
            f'border-radius:3px;background:currentColor;margin-right:5px;'
            f'vertical-align:middle;"></span>' if self._dot else ""
        )
        v = self._variant
        if v == "solid":
            bg, fg = dt.S_INK, dt.S_SURFACE
        elif v == "success":
            bg, fg = dt.S_P3_TINT, dt.S_P3
        elif v == "warn":
            bg, fg = dt.S_P4_TINT, "#8a6500"
        elif v == "danger":
            bg, fg = dt.S_P1_TINT, dt.S_P1
        else:
            bg, fg = dt.S_SUNK, dt.S_INK_1
        self.setStyleSheet(
            f"QLabel {{"
            f"  background:{bg}; color:{fg};"
            f"  border-radius:999px; padding:3px 8px;"
            f"  font-family:'Geist Mono',monospace; font-size:10px;"
            f"  font-weight:500; letter-spacing:0.08em; text-transform:uppercase;"
            f"}}"
        )
        self.setText(f"{dot_html}{self._text_raw.upper()}")


# ── Chip (dr-chip) ─────────────────────────────────────────────────────── #

class Chip(QWidget):
    """Line chip with a colored swatch dot and label text."""
    def __init__(self, text: str = "", color_hex: str = "#888", parent=None):
        super().__init__(parent)
        self._color_hex = color_hex
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 12, 5)
        layout.setSpacing(6)
        self._dot = _SwatchDot(color_hex, 10)
        layout.addWidget(self._dot)
        self._lbl = QLabel(text)
        f = dt.font_body(12)
        f.setWeight(QFont.Weight(500))
        self._lbl.setFont(f)
        layout.addWidget(self._lbl)
        self.setStyleSheet(
            f"Chip {{background:{dt.S_SURFACE}; border:1px solid {dt.S_RULE};"
            f" border-radius:999px;}} QLabel {{color:{dt.S_INK_1}; background:transparent;}}"
        )

    def set_color(self, hex_color: str) -> None:
        self._color_hex = hex_color
        self._dot.set_color(hex_color)


class _SwatchDot(QWidget):
    def __init__(self, color_hex: str, size: int = 10, parent=None):
        super().__init__(parent)
        self._color = QColor(color_hex)
        self.setFixedSize(size, size)

    def set_color(self, hex_color: str) -> None:
        self._color = QColor(hex_color)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(self._color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(self.rect())


# ── PlayerCard (dr-player) ────────────────────────────────────────────────#

class PlayerCard(QWidget):
    """
    Player identity card.
    state: 'active' | 'idle' | 'winner' | 'out'
    """
    def __init__(self, player_idx: int = 1, name: str = "Player",
                 state: str = "idle", score: int = 0,
                 coins: int = 0, trains: int = 0, parent=None):
        super().__init__(parent)
        self._player_idx = player_idx
        self._name = name
        self._state = state
        self._score = score
        self._coins = coins
        self._trains = trains

        self.setFixedHeight(72)
        self._build_ui()
        self._apply_style()

    def _build_ui(self) -> None:
        main = QHBoxLayout(self)
        main.setContentsMargins(16, 12, 14, 12)
        main.setSpacing(0)

        # 4px left stripe
        self._stripe = QFrame()
        self._stripe.setFixedWidth(4)
        self._stripe.setStyleSheet(
            f"background:{dt.player_hex(self._player_idx)}; border-radius:0;"
        )
        main.addWidget(self._stripe)
        main.addSpacing(12)

        # Avatar circle
        self._avatar = _AvatarCircle(
            self._name[:2].upper(), dt.player_hex(self._player_idx)
        )
        main.addWidget(self._avatar)
        main.addSpacing(12)

        # Name + meta
        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        info_col.setContentsMargins(0, 0, 0, 0)

        self._name_lbl = QLabel(self._name)
        f = dt.font_display(13)
        f.setWeight(QFont.Weight(600))
        self._name_lbl.setFont(f)
        self._name_lbl.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")

        self._meta_lbl = QLabel()
        self._meta_lbl.setFont(dt.font_mono(10))
        self._meta_lbl.setStyleSheet(f"color:{dt.S_INK_3}; background:transparent;")
        self._update_meta()

        info_col.addStretch()
        info_col.addWidget(self._name_lbl)
        info_col.addWidget(self._meta_lbl)
        info_col.addStretch()
        main.addLayout(info_col, 1)

        # Score + status
        score_col = QVBoxLayout()
        score_col.setSpacing(2)
        score_col.setContentsMargins(0, 0, 0, 0)
        score_col.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._score_lbl = QLabel(f"{self._score}")
        fs = dt.font_mono(18)
        fs.setWeight(QFont.Weight(600))
        self._score_lbl.setFont(fs)
        self._score_lbl.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")
        self._score_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)

        self._status_lbl = QLabel()
        self._status_lbl.setFont(dt.font_mono(9))
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._update_status()

        score_col.addStretch()
        score_col.addWidget(self._score_lbl)
        score_col.addWidget(self._status_lbl)
        score_col.addStretch()
        main.addLayout(score_col)

    def _update_meta(self) -> None:
        p = self._player_idx
        parts = [f"Line S{p}", f"{self._coins} coin", f"{self._trains} track"]
        self._meta_lbl.setText("  ·  ".join(parts).upper())

    def _update_status(self) -> None:
        s = self._state
        p_hex = dt.player_hex(self._player_idx)
        if s == "active":
            color = p_hex
            text = "● PLAYING"
        elif s == "winner":
            color = dt.S_P3
            text = "★ WINNER"
        elif s == "out":
            color = dt.S_INK_3
            text = "ELIMINATED"
        else:
            color = dt.S_INK_3
            text = "NEXT"
        self._status_lbl.setText(text)
        self._status_lbl.setStyleSheet(
            f"color:{color}; background:transparent; letter-spacing:0.08em;"
        )

    def _apply_style(self) -> None:
        s = self._state
        p = dt.player_hex(self._player_idx)
        if s == "active":
            bg = dt.active_player_bg(p).name()
            border = dt.active_player_border(p).name()
        elif s == "winner":
            bg = dt.S_SURFACE
            border = p
        else:
            bg = dt.S_SURFACE
            border = dt.S_RULE
        opacity = "0.45" if s == "out" else "1.0"
        extra = f"box-shadow: 0 0 0 2px {p} inset;" if s == "winner" else ""
        self.setStyleSheet(
            f"PlayerCard {{"
            f"  background:{bg}; border:1px solid {border};"
            f"  border-radius:{dt.R_3}px; opacity:{opacity}; {extra}"
            f"}}"
        )

    def refresh(self, name: str = None, state: str = None,
                score: int = None, coins: int = None, trains: int = None) -> None:
        if name   is not None: self._name   = name;   self._name_lbl.setText(name)
        if state  is not None: self._state  = state;  self._update_status(); self._apply_style()
        if score  is not None: self._score  = score;  self._score_lbl.setText(str(score))
        if coins  is not None: self._coins  = coins;  self._update_meta()
        if trains is not None: self._trains = trains; self._update_meta()


class _AvatarCircle(QWidget):
    def __init__(self, initials: str, color_hex: str, parent=None):
        super().__init__(parent)
        self._initials = initials
        self._color = QColor(color_hex)
        self.setFixedSize(40, 40)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(self._color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(self.rect())
        p.setPen(QColor("#ffffff"))
        f = QFont()
        f.setPixelSize(14)
        f.setWeight(QFont.Weight(700))
        p.setFont(f)
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._initials)


# ── PanelWidget (dr-panel) ────────────────────────────────────────────────#

class PanelWidget(QFrame):
    """Surface panel with optional header."""
    def __init__(self, title: str = "", sub: str = "",
                 flat: bool = False, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"PanelWidget {{"
            f"  background:{dt.S_SURFACE}; border:1px solid {dt.S_RULE};"
            f"  border-radius:{dt.R_3}px;"
            f"}}"
        )
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(0)

        if title:
            head = QWidget()
            head.setStyleSheet(
                f"background:{dt.S_SURFACE_2}; border-bottom:1px solid {dt.S_RULE};"
                f" border-radius:0;"
            )
            hl = QHBoxLayout(head)
            hl.setContentsMargins(16, 12, 16, 12)
            hl.setSpacing(8)
            title_lbl = QLabel(title)
            f = dt.font_display(13)
            f.setWeight(QFont.Weight(600))
            title_lbl.setFont(f)
            title_lbl.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")
            hl.addWidget(title_lbl)
            if sub:
                sub_lbl = QLabel(sub.upper())
                sub_lbl.setFont(dt.font_mono(10))
                sub_lbl.setStyleSheet(f"color:{dt.S_INK_3}; background:transparent;")
                hl.addWidget(sub_lbl)
            hl.addStretch()
            self._root.addWidget(head)

        self.body = QWidget()
        self.body.setStyleSheet("background:transparent;")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(16, 14, 16, 14)
        self.body_layout.setSpacing(8)
        self._root.addWidget(self.body)

    def add_row(self, widget: QWidget) -> None:
        self.body_layout.addWidget(widget)


# ── SegmentedControl (dr-seg) ─────────────────────────────────────────────#

class SegmentedControl(QWidget):
    """Pill segmented control. Emits changed(index) when selection changes."""
    changed = pyqtSignal(int)

    def __init__(self, labels: list[str], selected: int = 0, parent=None):
        super().__init__(parent)
        self._selected = selected
        self._btns: list[QPushButton] = []
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)
        self.setStyleSheet(
            f"SegmentedControl {{ background:{dt.S_SUNK}; border-radius:999px; }}"
        )
        for i, label in enumerate(labels):
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(False)
            idx = i
            btn.clicked.connect(lambda _, n=idx: self._select(n))
            self._btns.append(btn)
            layout.addWidget(btn)
        self._refresh_styles()

    def _select(self, idx: int) -> None:
        self._selected = idx
        self._refresh_styles()
        self.changed.emit(idx)

    def _refresh_styles(self) -> None:
        for i, btn in enumerate(self._btns):
            if i == self._selected:
                btn.setStyleSheet(
                    f"QPushButton {{"
                    f"  background:{dt.S_SURFACE}; color:{dt.S_INK};"
                    f"  border:1px solid {dt.S_RULE}; border-radius:999px;"
                    f"  font-size:12px; font-weight:500; padding:7px 14px;"
                    f"}}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton {{"
                    f"  background:transparent; color:{dt.S_INK_2}; border:none;"
                    f"  border-radius:999px; font-size:12px; font-weight:500;"
                    f"  padding:7px 14px;"
                    f"}}"
                    f"QPushButton:hover {{ background:{dt.S_SURFACE}; }}"
                )

    def selected_index(self) -> int:
        return self._selected

    def set_selected(self, idx: int) -> None:
        self._selected = idx
        self._refresh_styles()


# ── Toggle (dr-toggle) ────────────────────────────────────────────────────#

class Toggle(QWidget):
    """Pill toggle switch."""
    toggled = pyqtSignal(bool)

    def __init__(self, on: bool = False, parent=None):
        super().__init__(parent)
        self._on = on
        self.setFixedSize(36, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def is_on(self) -> bool:
        return self._on

    def set_on(self, value: bool) -> None:
        self._on = value
        self.update()

    def mousePressEvent(self, _) -> None:
        self._on = not self._on
        self.update()
        self.toggled.emit(self._on)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        track_color = QColor(dt.S_INK if self._on else dt.S_INK_4)
        p.setBrush(QBrush(track_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, 36, 22, 11, 11)
        knob_x = 16 if self._on else 2
        p.setBrush(QBrush(QColor("#ffffff")))
        p.drawEllipse(knob_x, 2, 18, 18)


# ── DieWidget (dr-die) ────────────────────────────────────────────────────#

# Pip grid positions (3×3 grid, indices 0–8, row-major):
# 0 1 2
# 3 4 5
# 6 7 8
_DIE_PIPS = {
    1: [4],
    2: [0, 8],
    3: [0, 4, 8],
    4: [0, 2, 6, 8],
    5: [0, 2, 4, 6, 8],
    6: [0, 2, 3, 5, 6, 8],
}


class DieWidget(QWidget):
    """46×46 engine die showing pip layout for values 1–6."""
    def __init__(self, value: int = 1, parent=None):
        super().__init__(parent)
        self._value = max(1, min(6, value))
        self.setFixedSize(46, 46)

    def set_value(self, v: int) -> None:
        self._value = max(1, min(6, v))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Card background
        p.setBrush(QBrush(QColor(dt.S_SURFACE)))
        p.setPen(QPen(QColor(dt.S_RULE), 1))
        p.drawRoundedRect(1, 1, 44, 44, 10, 10)

        # Pips (3×3 grid, 28×28 centered)
        pips = _DIE_PIPS.get(self._value, [])
        grid_x = (46 - 28) // 2      # = 9
        grid_y = (46 - 28) // 2      # = 9
        cell = 28 / 3                # ≈ 9.33
        ink = QColor(dt.S_INK)
        p.setBrush(QBrush(ink))
        p.setPen(Qt.PenStyle.NoPen)
        for idx in pips:
            row, col = divmod(idx, 3)
            cx = grid_x + col * cell + cell / 2
            cy = grid_y + row * cell + cell / 2
            r = 2.5
            p.drawEllipse(QPointF(cx, cy), r, r)


# ── HudWidget (dr-hud) ────────────────────────────────────────────────────#

class HudWidget(QWidget):
    """
    Bottom-floating HUD pill. Parent it to the map widget and call reposition()
    in the map's resizeEvent to keep it centered.
    Shows: player swatch · player name · divider · phase status · divider · actions
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 8, 8, 8)
        layout.setSpacing(10)

        self._swatch = _SwatchDot("", 12)
        layout.addWidget(self._swatch)

        self._player_lbl = QLabel()
        f = dt.font_display(13)
        f.setWeight(QFont.Weight(500))
        self._player_lbl.setFont(f)
        self._player_lbl.setStyleSheet(f"color:{dt.S_PAPER}; background:transparent;")
        layout.addWidget(self._player_lbl)

        layout.addWidget(self._make_divider())

        self._phase_lbl = QLabel()
        self._phase_lbl.setFont(dt.font_mono(10))
        phase_color = QColor(dt.S_PAPER)
        phase_color.setAlpha(int(0.65 * 255))
        self._phase_lbl.setStyleSheet(
            f"color:rgba(244,242,236,165); background:transparent;"
            f" letter-spacing:0.08em; text-transform:uppercase;"
        )
        layout.addWidget(self._phase_lbl)

        self._actions_layout = QHBoxLayout()
        self._actions_layout.setSpacing(6)
        layout.addLayout(self._actions_layout)

    def _make_divider(self) -> QWidget:
        w = QWidget()
        w.setFixedSize(1, 18)
        w.setStyleSheet("background:rgba(244,242,236,64);")
        return w

    def set_player(self, color_hex: str, name: str) -> None:
        self._swatch.set_color(color_hex)
        self._swatch._color = QColor(color_hex)
        self._swatch.update()
        self._player_lbl.setText(name)

    def set_phase(self, text: str) -> None:
        self._phase_lbl.setText(text.upper())

    def clear_actions(self) -> None:
        while self._actions_layout.count():
            item = self._actions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def add_action(self, label: str, accent: bool = False,
                   callback=None) -> QPushButton:
        btn = QPushButton(label)
        btn.setFont(dt.font_display(12))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if accent:
            btn.setStyleSheet(
                f"QPushButton {{background:{dt.S_P3}; color:#fff; border:none;"
                f" border-radius:999px; padding:6px 14px; font-weight:600;}}"
                f"QPushButton:hover {{background:#17623b;}}"
            )
        else:
            btn.setStyleSheet(
                f"QPushButton {{background:{dt.S_PAPER}; color:{dt.S_INK}; border:none;"
                f" border-radius:999px; padding:6px 14px; font-weight:500;}}"
                f"QPushButton:hover {{background:{dt.S_SURFACE};}}"
            )
        if callback:
            btn.clicked.connect(callback)
        self._actions_layout.addWidget(btn)
        return btn

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg = QColor(dt.S_INK)
        bg.setAlpha(int(0.92 * 255))
        p.setBrush(QBrush(bg))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), 999, 999)

    def reposition(self) -> None:
        """Center horizontally at bottom of parent widget."""
        if self.parent() is None:
            return
        pw, ph = self.parent().width(), self.parent().height()
        self.adjustSize()
        w, h = self.width(), self.height()
        self.move((pw - w) // 2, ph - h - 24)


# ── OverlayCard (Overlay component) ──────────────────────────────────────#

class OverlayCard(QWidget):
    """
    Small floating info card with a left-edge accent stripe.
    tone: 'neutral' | 'warn' | 'info' | 'success' | 'danger'
    """
    def __init__(self, title: str = "", body: str = "",
                 foot: str = "", tone: str = "neutral", parent=None):
        super().__init__(parent)
        self._tone = tone
        self._build_ui(title, body, foot)

    def _accent_color(self) -> str:
        return {
            "warn":    dt.S_P4,
            "info":    dt.S_P2,
            "success": dt.S_P3,
            "danger":  dt.S_P1,
        }.get(self._tone, dt.S_INK)

    def _build_ui(self, title: str, body: str, foot: str) -> None:
        self.setStyleSheet(
            f"OverlayCard {{background:{dt.S_SURFACE}; border:1px solid {dt.S_RULE};"
            f" border-radius:{dt.R_3}px;}}"
        )
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        stripe = QFrame()
        stripe.setFixedWidth(3)
        stripe.setStyleSheet(f"background:{self._accent_color()}; border-radius:0;")
        outer.addWidget(stripe)

        content = QVBoxLayout()
        content.setContentsMargins(14, 12, 14, 12)
        content.setSpacing(4)
        outer.addLayout(content)

        eyebrow = QLabel(title.upper())
        eyebrow.setFont(dt.font_mono(10))
        eyebrow.setStyleSheet(
            f"color:{dt.S_INK_2}; background:transparent; letter-spacing:0.12em;"
        )
        content.addWidget(eyebrow)

        body_lbl = QLabel(body)
        fb = dt.font_display(14)
        fb.setWeight(QFont.Weight(600))
        body_lbl.setFont(fb)
        body_lbl.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")
        content.addWidget(body_lbl)

        if foot:
            foot_lbl = QLabel(foot)
            foot_lbl.setFont(dt.font_mono(10))
            foot_lbl.setStyleSheet(f"color:{dt.S_INK_3}; background:transparent;")
            content.addWidget(foot_lbl)


# ── TurnToastWidget ──────────────────────────────────────────────────────#

class TurnToastWidget(QWidget):
    """
    Floating pill that briefly announces whose turn it is.
    Parent should be the map widget so it overlays it.
    Call show_for(name, color_hex, is_mine) to trigger.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 20, 10)
        layout.setSpacing(9)

        self._dot = QLabel("●")
        self._dot.setFont(dt.font_display(13))
        self._dot.setStyleSheet("background:transparent;")
        layout.addWidget(self._dot)

        self._text = QLabel("")
        self._text.setFont(dt.font_display(14, weight=600))
        self._text.setStyleSheet("color:#14171c; background:transparent;")
        layout.addWidget(self._text)

        self._eff = QGraphicsOpacityEffect(self)
        self._eff.setOpacity(0.0)
        self.setGraphicsEffect(self._eff)

        self._anim = QPropertyAnimation(self._eff, b"opacity", self)
        self._anim.finished.connect(self._on_anim_finished)

        self._hold = QTimer(self)
        self._hold.setSingleShot(True)
        self._hold.timeout.connect(self._fade_out)

        self._phase = "hidden"
        self.hide()

        if parent:
            parent.installEventFilter(self)

    def show_for(self, name: str, color_hex: str, is_mine: bool) -> None:
        self._text.setText("Dein Zug" if is_mine else f"{name} ist dran")
        self._dot.setStyleSheet(
            f"color:{color_hex}; background:transparent; font-size:14px;"
        )
        self.adjustSize()
        self._reposition()
        self.show()
        self.raise_()
        self._hold.stop()
        self._anim.stop()
        self._phase = "in"
        if dt.A_REDUCE_MOTION or dt.A_DISABLE_BLINK:
            self._eff.setOpacity(1.0)
            self._phase = "visible"
            self._hold.start(30_000)
        else:
            self._anim.setDuration(200)
            self._anim.setStartValue(float(self._eff.opacity()))
            self._anim.setEndValue(1.0)
            self._anim.start()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), dt.R_3, dt.R_3)
        p.fillPath(path, QColor("#E8E4DA"))

    def eventFilter(self, obj, event) -> bool:
        from PyQt6.QtCore import QEvent
        if obj is self.parent() and event.type() == QEvent.Type.Resize:
            self._reposition()
        return False

    def _reposition(self) -> None:
        p = self.parent()
        if p is None:
            return
        sh = self.sizeHint()
        x = (p.width() - sh.width()) // 2
        self.setGeometry(x, 20, sh.width(), sh.height())

    def _fade_out(self) -> None:
        self._phase = "out"
        self._anim.stop()
        if dt.A_REDUCE_MOTION or dt.A_DISABLE_BLINK:
            self._eff.setOpacity(0.0)
            self._on_anim_finished()
        else:
            self._anim.setDuration(400)
            self._anim.setStartValue(1.0)
            self._anim.setEndValue(0.0)
            self._anim.start()

    def _on_anim_finished(self) -> None:
        if self._phase == "in":
            self._phase = "visible"
            self._hold.start(30_000)
        elif self._phase == "out":
            self._phase = "hidden"
            self.hide()

    def dismiss(self) -> None:
        """Immediately start the fade-out (e.g. when the turn ends early)."""
        if self._phase in ("in", "visible"):
            self._hold.stop()
            self._fade_out()


# ── SparklineWidget (Trend component) ────────────────────────────────────#

class SparklineWidget(QWidget):
    """
    140×36 sparkline chart for scoreboard trend column.
    data: list of numeric values (6 points).
    """
    def __init__(self, data: list[float] | None = None,
                 player_idx: int = 1, parent=None):
        super().__init__(parent)
        self._data = data or [0] * 6
        self._p_idx = player_idx
        self.setFixedSize(140, 36)

    def set_data(self, data: list[float], player_idx: int = None) -> None:
        self._data = data
        if player_idx is not None:
            self._p_idx = player_idx
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        pts = self._data
        if not pts or len(pts) < 2:
            return

        w, h = self.width(), self.height()
        hi, lo = max(pts), min(pts)
        span = max(1.0, hi - lo)
        def xs(i): return 4 + i * (w - 8) / (len(pts) - 1)
        def ys(v): return h - 6 - (v - lo) / span * (h - 12)

        line_color = QColor(dt.player_hex(self._p_idx))
        tint_color = QColor(dt.s_player_tint(self._p_idx))

        # Fill area
        area = QPainterPath()
        area.moveTo(xs(0), ys(pts[0]))
        for i in range(1, len(pts)):
            area.lineTo(xs(i), ys(pts[i]))
        area.lineTo(xs(len(pts) - 1), h - 2)
        area.lineTo(xs(0), h - 2)
        area.closeSubpath()
        p.fillPath(area, QBrush(tint_color))

        # Line
        line = QPainterPath()
        line.moveTo(xs(0), ys(pts[0]))
        for i in range(1, len(pts)):
            line.lineTo(xs(i), ys(pts[i]))
        pen = QPen(line_color, 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(line)

        # End dot
        last_x, last_y = xs(len(pts) - 1), ys(pts[-1])
        p.setPen(QPen(QColor(dt.S_SURFACE), 1.5))
        p.setBrush(QBrush(line_color))
        p.drawEllipse(QPointF(last_x, last_y), 3, 3)


# ── IconButton (dr-iconbtn) ───────────────────────────────────────────────#

class IconButton(QPushButton):
    """36×36 square icon button matching dr-iconbtn."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            f"QPushButton {{"
            f"  background:{dt.S_SURFACE}; color:{dt.S_INK_1};"
            f"  border:1px solid {dt.S_RULE}; border-radius:10px;"
            f"}}"
            f"QPushButton:hover {{ background:{dt.S_SUNK}; }}"
            f"QPushButton:pressed {{ background:{dt.S_RULE}; }}"
        )


# ── Timeline row ──────────────────────────────────────────────────────────#

class TimelineWidget(QWidget):
    """Vertical timeline of (time, player_idx, who, what) events."""
    def __init__(self, events: list[dict] | None = None, parent=None):
        super().__init__(parent)
        self._events = events or []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 8, 8, 8)
        layout.setSpacing(0)
        self.setStyleSheet("background:transparent;")

        for ev in self._events:
            row = QHBoxLayout()
            row.setSpacing(10)
            row.setContentsMargins(0, 6, 0, 6)

            time_lbl = QLabel(ev.get("time", ""))
            time_lbl.setFont(dt.font_mono(10))
            time_lbl.setFixedWidth(42)
            time_lbl.setStyleSheet(f"color:{dt.S_INK_3}; background:transparent;")
            row.addWidget(time_lbl)

            who = ev.get("who", "")
            what = ev.get("what", "")
            text_lbl = QLabel(f"<b>{who}</b> {what}")
            text_lbl.setFont(dt.font_body(12))
            text_lbl.setStyleSheet(f"color:{dt.S_INK_1}; background:transparent;")
            text_lbl.setWordWrap(True)
            row.addWidget(text_lbl, 1)

            layout.addLayout(row)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Vertical line
        x = 8
        p.setPen(QPen(QColor(dt.S_RULE), 1))
        p.drawLine(x, 8, x, self.height() - 8)
        # Player dots
        if not self._events:
            return
        row_h = (self.height() - 16) / max(1, len(self._events))
        for i, ev in enumerate(self._events):
            cy = int(8 + row_h * i + row_h / 2)
            color = QColor(dt.player_hex(ev.get("player_idx", 1)))
            p.setBrush(QBrush(color))
            p.setPen(QPen(QColor(dt.S_SURFACE), 2))
            p.drawEllipse(x - 5, cy - 5, 10, 10)

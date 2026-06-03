"""
ScoreOverlay — slide-in scoreboard panel shown by pressing Tab during gameplay.

Overlays the game page with:
  • Blurred screenshot of the board (grabbed on show)
  • Semi-transparent dark scrim that fades in
  • A 480 px panel that slides in from the right edge
"""
from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve, QEvent, QPoint, QPropertyAnimation, Qt, pyqtSignal,
)
from PyQt6.QtGui import (
    QColor, QFont, QPainter, QPen, QBrush,
)
from PyQt6.QtWidgets import (
    QFrame, QGraphicsBlurEffect, QGraphicsOpacityEffect,
    QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

import dampfross.ui.design_tokens as dt


# ── helpers ──────────────────────────────────────────────────────────────── #

def _player_rank_data(gs) -> list[dict]:
    """Return player data sorted by money descending."""
    initial = _initial_money(gs)
    rows = []
    for pidx, p in enumerate(gs.players):
        bm = gs.build_money.get(pidx)
        if bm is not None:
            build_pts = bm - initial
            race_pts  = p.money - bm
        else:
            build_pts = p.money - initial
            race_pts  = 0
        rows.append({
            "pidx":       pidx,
            "name":       p.name,
            "color_hex":  p.color_hex,
            "build_pts":  build_pts,
            "race_pts":   race_pts,
            "total":      p.money,
        })
    rows.sort(key=lambda r: r["total"], reverse=True)
    return rows


def _initial_money(gs) -> int:
    """Starting capital — all players begin with the same amount (default 20)."""
    # Players all start with the same capital; reading any one player's
    # pre-build-phase money gives us the initial amount. Since we don't
    # snapshot it explicitly, use the GameState win_target ÷ scale heuristic
    # or simply return 20 as the Dampfross standard starting credit.
    return 20


# ── colour swatch ─────────────────────────────────────────────────────────── #

class _Swatch(QWidget):
    def __init__(self, color_hex: str, size: int = 14, parent=None):
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


# ── one row ───────────────────────────────────────────────────────────────── #

class _Row(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        self.setFixedHeight(52)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(0)

        # Rank
        self._rank = QLabel("1")
        self._rank.setFont(dt.font_mono(11))
        self._rank.setFixedWidth(28)
        self._rank.setStyleSheet(f"color:{dt.S_INK_3};background:transparent;font-weight:600;")
        lay.addWidget(self._rank)

        # Colour swatch + name
        self._swatch = _Swatch(dt.S_INK_4, 12)
        lay.addWidget(self._swatch, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addSpacing(10)

        self._name = QLabel("—")
        fn = dt.font_body(13)
        fn.setWeight(QFont.Weight(600))
        self._name.setFont(fn)
        self._name.setStyleSheet(f"color:{dt.S_INK};background:transparent;")
        lay.addWidget(self._name, 1)

        # Build col
        self._build = QLabel("—")
        self._build.setFont(dt.font_mono(12))
        self._build.setFixedWidth(58)
        self._build.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._build.setStyleSheet(f"color:{dt.S_INK_2};background:transparent;")
        lay.addWidget(self._build)

        # Race col
        self._race = QLabel("—")
        self._race.setFont(dt.font_mono(12))
        self._race.setFixedWidth(52)
        self._race.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._race.setStyleSheet(f"color:{dt.S_INK_2};background:transparent;")
        lay.addWidget(self._race)

        # Total col
        self._total = QLabel("—")
        ft = dt.font_mono(15)
        ft.setWeight(QFont.Weight(700))
        self._total.setFont(ft)
        self._total.setFixedWidth(52)
        self._total.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._total.setStyleSheet(f"color:{dt.S_INK};background:transparent;")
        lay.addWidget(self._total)

    def refresh(self, rank: int, d: dict, is_leader: bool) -> None:
        self._rank.setText(str(rank))
        rank_color = d["color_hex"] if is_leader else dt.S_INK_3
        self._rank.setStyleSheet(
            f"color:{rank_color};background:transparent;font-weight:700;"
        )
        self._swatch.set_color(d["color_hex"])
        self._name.setText(d["name"])
        self._build.setText(str(d["build_pts"]))
        self._race.setText(str(d["race_pts"]))
        self._total.setText(str(d["total"]))
        total_color = d["color_hex"] if is_leader else dt.S_INK
        self._total.setStyleSheet(
            f"color:{total_color};background:transparent;font-weight:700;"
        )


# ── panel ─────────────────────────────────────────────────────────────────── #

class _Panel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(480)
        self.setStyleSheet(
            f"QFrame{{background:{dt.S_SURFACE};"
            f"border-left:1px solid {dt.S_RULE};}}"
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── header ──────────────────────────────────────────────────────── #
        hdr = QWidget()
        hdr.setStyleSheet(
            f"QWidget{{background:{dt.S_SURFACE};"
            f"border-bottom:1px solid {dt.S_RULE};}}"
        )
        hdr.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        hdr.setFixedHeight(68)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(20, 0, 20, 0)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        eyebrow = QLabel("SCOREBOARD")
        eyebrow.setFont(dt.font_mono(10))
        eyebrow.setStyleSheet(f"color:{dt.S_INK_3};background:transparent;letter-spacing:0.1em;")
        title_col.addWidget(eyebrow)
        self._title = QLabel("Standings")
        f = dt.font_display(20)
        f.setWeight(QFont.Weight(700))
        self._title.setFont(f)
        self._title.setStyleSheet(f"color:{dt.S_INK};background:transparent;")
        title_col.addWidget(self._title)
        hl.addLayout(title_col, 1)

        hint = QLabel("[Tab] schließen")
        hint.setFont(dt.font_mono(10))
        hint.setStyleSheet(
            f"color:{dt.S_INK_4};background:{dt.S_SUNK};"
            f"border-radius:4px;padding:3px 8px;letter-spacing:0.06em;"
        )
        hl.addWidget(hint, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(hdr)

        # ── col headers ─────────────────────────────────────────────────── #
        col_hdr = QWidget()
        col_hdr.setStyleSheet(f"background:{dt.S_PAPER};")
        col_hdr.setFixedHeight(32)
        chl = QHBoxLayout(col_hdr)
        chl.setContentsMargins(20, 0, 20, 0)
        chl.setSpacing(0)

        def _th(text: str, w: int = 0, align=Qt.AlignmentFlag.AlignLeft) -> QLabel:
            lbl = QLabel(text.upper())
            lbl.setFont(dt.font_mono(9))
            lbl.setStyleSheet(
                f"color:{dt.S_INK_3};background:transparent;"
                f"font-weight:600;letter-spacing:0.10em;"
            )
            lbl.setAlignment(align)
            if w:
                lbl.setFixedWidth(w)
            return lbl

        chl.addWidget(_th("#", 28))
        chl.addSpacing(22)
        chl.addWidget(_th("Spieler"), 1)
        chl.addWidget(_th("Aufbau", 58, Qt.AlignmentFlag.AlignRight))
        chl.addWidget(_th("Betrieb", 52, Qt.AlignmentFlag.AlignRight))
        chl.addWidget(_th("Gesamt", 52, Qt.AlignmentFlag.AlignRight))
        root.addWidget(col_hdr)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"border:none;background:{dt.S_RULE};max-height:1px;")
        root.addWidget(sep)

        # ── scrollable rows ──────────────────────────────────────────────── #
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        root.addWidget(scroll, 1)

        body = QWidget()
        body.setStyleSheet(f"background:{dt.S_SURFACE};")
        self._body_l = QVBoxLayout(body)
        self._body_l.setContentsMargins(0, 8, 0, 8)
        self._body_l.setSpacing(0)
        scroll.setWidget(body)

        self._rows: list[_Row] = []
        for _ in range(8):
            sep2 = QFrame()
            sep2.setFrameShape(QFrame.Shape.HLine)
            sep2.setStyleSheet(
                f"border:none;background:{dt.S_RULE_SOFT};max-height:1px;"
            )
            row = _Row()
            self._rows.append(row)
            self._body_l.addWidget(sep2)
            self._body_l.addWidget(row)
        self._body_l.addStretch()

    def populate(self, gs) -> None:
        data = _player_rank_data(gs)
        # Update title with round info
        self._title.setText(
            f"Runde {gs.round_number}"
            if gs.phase == "build"
            else "Betriebsphase"
        )
        for i, row in enumerate(self._rows):
            if i < len(data):
                row.refresh(i + 1, data[i], is_leader=(i == 0))
                row.show()
            else:
                row.hide()


# ── public overlay ────────────────────────────────────────────────────────── #

class ScoreOverlay(QWidget):
    """Slide-in scoreboard overlay (Tab key toggles)."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background:transparent;")
        self.hide()

        # Blurred screenshot backdrop
        self._backdrop = QLabel(self)
        self._backdrop.setScaledContents(True)
        blur = QGraphicsBlurEffect(self._backdrop)
        blur.setBlurRadius(14)
        self._backdrop.setGraphicsEffect(blur)

        # Dark scrim on top of blur
        self._scrim = QWidget(self)
        self._scrim.setStyleSheet("background:rgba(20,23,28,0);")
        self._scrim.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Scrim opacity animation
        self._scrim_opacity = QGraphicsOpacityEffect(self._scrim)
        self._scrim_opacity.setOpacity(0.0)
        self._scrim.setGraphicsEffect(self._scrim_opacity)
        self._scrim_anim = QPropertyAnimation(self._scrim_opacity, b"opacity")
        self._scrim_anim.setDuration(200)

        # Panel
        self._panel = _Panel(self)

        # Panel slide animation
        self._slide_anim = QPropertyAnimation(self._panel, b"pos")
        self._slide_anim.setDuration(260)
        self._slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._slide_anim.finished.connect(self._on_slide_finished)

        self._hiding = False
        parent.installEventFilter(self)

    # ── keep overlay in sync with parent size ──────────────────────────────── #

    def eventFilter(self, obj, event) -> bool:
        if obj is self.parent() and event.type() == QEvent.Type.Resize:
            self._relayout()
        return False

    def _relayout(self) -> None:
        if self.parent():
            self.setGeometry(0, 0,
                             self.parent().width(), self.parent().height())
        self._backdrop.setGeometry(self.rect())
        self._scrim.setGeometry(self.rect())
        self._panel.setFixedHeight(self.height())

    def resizeEvent(self, event) -> None:
        self._relayout()

    # ── show / hide ───────────────────────────────────────────────────────── #

    def show_scoreboard(self, gs) -> None:
        self._hiding = False
        self._relayout()

        # Grab parent before showing this overlay
        parent = self.parent()
        if parent:
            self._backdrop.setPixmap(parent.grab())

        self._panel.populate(gs)

        # Position panel off-screen right initially
        panel_w = self._panel.width()
        self._panel.move(self.width(), 0)

        self.show()
        self.raise_()

        # Animate scrim in
        self._scrim_anim.stop()
        self._scrim_anim.setStartValue(0.0)
        self._scrim_anim.setEndValue(0.55)
        self._scrim_anim.start()

        # Animate panel in
        self._slide_anim.stop()
        self._slide_anim.setStartValue(QPoint(self.width(), 0))
        self._slide_anim.setEndValue(QPoint(self.width() - panel_w, 0))
        self._slide_anim.start()

    def hide_scoreboard(self) -> None:
        if self._hiding:
            return
        self._hiding = True

        panel_w = self._panel.width()

        self._scrim_anim.stop()
        self._scrim_anim.setStartValue(self._scrim_opacity.opacity())
        self._scrim_anim.setEndValue(0.0)
        self._scrim_anim.start()

        self._slide_anim.stop()
        self._slide_anim.setStartValue(self._panel.pos())
        self._slide_anim.setEndValue(QPoint(self.width(), 0))
        self._slide_anim.start()

    def _on_slide_finished(self) -> None:
        if self._hiding:
            self.hide()
            self._hiding = False

    # ── click outside panel → close ───────────────────────────────────────── #

    def mousePressEvent(self, event) -> None:
        if not self._panel.geometry().contains(event.pos()):
            self.hide_scoreboard()

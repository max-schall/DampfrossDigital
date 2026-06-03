"""
End-of-game results screen.

Shows:
  • Winner circle + name
  • Highlight cards (most races won, longest network, etc.)
  • Line graph of each player's cumulative score per journey
  • "Back to Menu" button
"""
from __future__ import annotations
import math
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF
from PyQt6.QtGui import (
    QColor, QFont, QPainter, QBrush, QPen, QPainterPath,
    QLinearGradient,
)
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

import dampfross.ui.design_tokens as dt


# ── helpers ───────────────────────────────────────────────────────────────── #

def _eyebrow(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setFont(dt.font_mono(10))
    lbl.setStyleSheet(
        f"color:{dt.S_INK_2};background:transparent;letter-spacing:0.08em;"
    )
    return lbl


def _section_head(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    f = dt.font_display(13)
    f.setWeight(QFont.Weight(600))
    lbl.setFont(f)
    lbl.setStyleSheet(
        f"color:{dt.S_INK_2};background:transparent;letter-spacing:0.10em;"
    )
    return lbl


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
        f"border-radius:8px;}}"
    )
    return f


def _btn(text: str, primary: bool = False) -> QPushButton:
    b = QPushButton(text)
    b.setFont(dt.font_body(13))
    if primary:
        b.setStyleSheet(
            f"QPushButton{{background:{dt.S_INK};color:{dt.S_SURFACE};"
            f"border:none;border-radius:8px;"
            f"font-size:13px;font-weight:600;padding:10px 20px;}}"
            f"QPushButton:hover{{background:{dt.S_INK_1};}}"
        )
    else:
        b.setStyleSheet(
            f"QPushButton{{background:{dt.S_SURFACE};color:{dt.S_INK};"
            f"border:1px solid {dt.S_RULE};border-radius:8px;"
            f"font-size:13px;font-weight:500;padding:10px 20px;}}"
            f"QPushButton:hover{{background:{dt.S_SUNK};}}"
        )
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


# ── Winner circle ─────────────────────────────────────────────────────────── #

class _WinnerCircle(QWidget):
    def __init__(self, size: int = 100, parent=None):
        super().__init__(parent)
        self._color  = QColor(dt.S_INK_4)
        self._letter = "?"
        self._font_px = size // 3
        self.setFixedSize(size, size)

    def set(self, initials: str, color_hex: str) -> None:
        self._letter = initials[:2].upper()
        self._color  = QColor(color_hex)
        self.update()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Glow ring
        glow = QColor(self._color)
        glow.setAlpha(40)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(glow))
        margin = 6
        p.drawEllipse(self.rect().adjusted(margin, margin, -margin, -margin))
        # Main circle
        p.setBrush(QBrush(self._color))
        inner = 12
        p.drawEllipse(self.rect().adjusted(inner, inner, -inner, -inner))
        # Letter
        f = QFont()
        f.setPixelSize(self._font_px)
        f.setWeight(QFont.Weight(700))
        p.setFont(f)
        p.setPen(QPen(QColor("#ffffff")))
        p.drawText(
            self.rect().adjusted(inner, inner, -inner, -inner),
            Qt.AlignmentFlag.AlignCenter,
            self._letter,
        )


# ── Highlight card ─────────────────────────────────────────────────────────── #

class _HighlightCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame{{background:{dt.S_SURFACE};border:1px solid {dt.S_RULE};"
            f"border-radius:8px;}}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(6)

        # Category + player name row
        top = QHBoxLayout()
        top.setSpacing(0)
        self._cat = QLabel("—")
        self._cat.setFont(dt.font_mono(10))
        self._cat.setStyleSheet(
            f"color:{dt.S_INK_3};background:transparent;letter-spacing:0.08em;"
        )
        top.addWidget(self._cat, 1)
        self._dot = _ColorDot(dt.S_INK_4, 10)
        top.addWidget(self._dot, 0, Qt.AlignmentFlag.AlignVCenter)
        top.addSpacing(6)
        self._player_name = QLabel("—")
        self._player_name.setFont(dt.font_body(12))
        self._player_name.setStyleSheet(f"color:{dt.S_INK_2};background:transparent;")
        top.addWidget(self._player_name)
        lay.addLayout(top)

        self._value = QLabel("—")
        fv = dt.font_display(20)
        fv.setWeight(QFont.Weight(700))
        self._value.setFont(fv)
        self._value.setStyleSheet(
            f"color:{dt.S_INK};background:transparent;letter-spacing:-0.01em;"
        )
        lay.addWidget(self._value)

    def refresh(self, category: str, player_name: str,
                color_hex: str, value: str) -> None:
        self._cat.setText(category.upper())
        self._player_name.setText(player_name)
        self._dot.set_color(color_hex)
        self._value.setText(value)


class _ColorDot(QWidget):
    def __init__(self, color_hex: str, size: int = 10, parent=None):
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


# ── Final standings table ─────────────────────────────────────────────────── #

class _StandingRow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet("background:transparent;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(10)

        self._dot = _ColorDot(dt.S_INK_4, 10)
        lay.addWidget(self._dot, 0, Qt.AlignmentFlag.AlignVCenter)

        self._name = QLabel("—")
        self._name.setFont(dt.font_body(13))
        self._name.setStyleSheet(f"color:{dt.S_INK};background:transparent;font-weight:500;")
        lay.addWidget(self._name, 1)

        self._build = QLabel("—")
        self._build.setFont(dt.font_mono(11))
        self._build.setFixedWidth(56)
        self._build.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._build.setStyleSheet(f"color:{dt.S_INK_2};background:transparent;")
        lay.addWidget(self._build)

        self._race = QLabel("—")
        self._race.setFont(dt.font_mono(11))
        self._race.setFixedWidth(52)
        self._race.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._race.setStyleSheet(f"color:{dt.S_INK_2};background:transparent;")
        lay.addWidget(self._race)

        self._total = QLabel("—")
        ft = dt.font_mono(15)
        ft.setWeight(QFont.Weight(700))
        self._total.setFont(ft)
        self._total.setFixedWidth(52)
        self._total.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._total.setStyleSheet(f"color:{dt.S_INK};background:transparent;font-weight:700;")
        lay.addWidget(self._total)

    def refresh(self, name: str, color_hex: str,
                build_pts: int, race_pts: int, total: int, is_winner: bool) -> None:
        self._dot.set_color(color_hex)
        self._name.setText(name)
        self._build.setText(str(build_pts))
        self._race.setText(str(race_pts))
        self._total.setText(str(total))
        c = color_hex if is_winner else dt.S_INK
        self._total.setStyleSheet(
            f"color:{c};background:transparent;font-weight:700;"
        )


# ── Line chart ────────────────────────────────────────────────────────────── #

class _LineChart(QWidget):
    """
    Multi-player score-over-time chart.

    series:    list of {"name": str, "color": str, "data": [int, ...]}
    labels:    x-axis tick labels, same length as data ("B1"…"BN", "J1"…"JM")
    split_idx: index of the first operate-phase point; a faint vertical line
               is drawn there to mark the build→operate transition.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._series: list[dict] = []
        self._labels: list[str] = []
        self._split_idx: int | None = None
        self.setMinimumHeight(220)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

    def set_data(self, series: list[dict], labels: list[str] | None = None,
                 split_idx: int | None = None) -> None:
        self._series = series
        self._labels = labels or [str(i) for i in range(
            max((len(s["data"]) for s in series), default=0)
        )]
        self._split_idx = split_idx
        self.update()

    def paintEvent(self, _) -> None:
        if not self._series:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W, H = self.width(), self.height()
        pad_l, pad_r, pad_t, pad_b = 52, 20, 16, 40

        all_vals = [v for s in self._series for v in s["data"]]
        if not all_vals:
            return

        n_pts   = max(len(s["data"]) for s in self._series)
        y_min   = min(all_vals)
        y_max   = max(all_vals)
        if y_max == y_min:
            y_max = y_min + 1

        chart_w = W - pad_l - pad_r
        chart_h = H - pad_t - pad_b

        def x_of(i: int) -> float:
            return pad_l + (i / max(n_pts - 1, 1)) * chart_w

        def to_px(i: int, val: float) -> QPointF:
            y = pad_t + (1.0 - (val - y_min) / (y_max - y_min)) * chart_h
            return QPointF(x_of(i), y)

        # Grid lines + y-axis labels
        p.setFont(dt.font_mono(9))
        y_steps = 4
        for k in range(y_steps + 1):
            frac = k / y_steps
            val  = y_min + frac * (y_max - y_min)
            y_px = pad_t + (1.0 - frac) * chart_h
            p.setPen(QPen(QColor(dt.S_RULE), 1))
            p.drawLine(QPointF(pad_l, y_px), QPointF(W - pad_r, y_px))
            p.setPen(QPen(QColor(dt.S_INK_3), 1))
            p.drawText(
                QRectF(0, y_px - 9, pad_l - 4, 18),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                str(int(val)),
            )

        # Build→operate phase separator
        if self._split_idx is not None and 0 < self._split_idx < n_pts:
            sep_x = x_of(self._split_idx)
            p.setPen(QPen(QColor(dt.S_INK_3), 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(sep_x, pad_t), QPointF(sep_x, pad_t + chart_h))
            p.setFont(dt.font_mono(8))
            p.setPen(QPen(QColor(dt.S_INK_3), 1))
            p.drawText(
                QRectF(sep_x + 3, pad_t, 30, 14),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                "Betrieb",
            )

        # X-axis labels — skip any that would overlap the previous drawn one
        min_label_gap = 28.0
        last_label_x  = -999.0
        p.setFont(dt.font_mono(9))
        for i, lbl in enumerate(self._labels[:n_pts]):
            cx = x_of(i)
            if cx - last_label_x >= min_label_gap:
                p.setPen(QPen(QColor(dt.S_INK_3), 1))
                p.drawText(
                    QRectF(cx - 20, pad_t + chart_h + 8, 40, 16),
                    Qt.AlignmentFlag.AlignHCenter,
                    lbl,
                )
                last_label_x = cx

        # Dot radius scales down for dense charts
        dot_r  = 3.5 if n_pts <= 20 else (2.5 if n_pts <= 40 else 1.8)
        dot_r2 = 1.8 if n_pts <= 20 else (1.2 if n_pts <= 40 else 0.8)

        # Series lines + dots
        for s in self._series:
            data   = s["data"]
            color  = QColor(s["color"])
            pts    = [to_px(i, v) for i, v in enumerate(data)]
            if not pts:
                continue

            # Filled area under the line (subtle)
            if len(pts) > 1:
                fill_color = QColor(color)
                fill_color.setAlpha(18)
                path = QPainterPath()
                path.moveTo(QPointF(pts[0].x(), pad_t + chart_h))
                path.lineTo(pts[0])
                for pt in pts[1:]:
                    path.lineTo(pt)
                path.lineTo(QPointF(pts[-1].x(), pad_t + chart_h))
                path.closeSubpath()
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(fill_color))
                p.drawPath(path)

            # Line
            pen = QPen(color, 2.2, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            path = QPainterPath()
            path.moveTo(pts[0])
            for pt in pts[1:]:
                path.lineTo(pt)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)

            # Dots
            p.setPen(Qt.PenStyle.NoPen)
            inner_c = QColor("#ffffff") if dt.current_theme() != "dark" \
                      else QColor(dt.S_SURFACE)
            for pt in pts:
                p.setBrush(QBrush(color))
                p.drawEllipse(pt, dot_r, dot_r)
                p.setBrush(QBrush(inner_c))
                p.drawEllipse(pt, dot_r2, dot_r2)

        p.end()


# ── Legend row ────────────────────────────────────────────────────────────── #

class _LegendRow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)
        lay.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._items: list[QWidget] = []
        self._lay = lay

    def set_series(self, series: list[dict]) -> None:
        for w in self._items:
            w.deleteLater()
        self._items.clear()

        for s in series:
            chip = QWidget()
            chip.setStyleSheet("background:transparent;")
            cl = QHBoxLayout(chip)
            cl.setContentsMargins(0, 0, 0, 0)
            cl.setSpacing(6)
            dot = _ColorDot(s["color"], 8)
            cl.addWidget(dot, 0, Qt.AlignmentFlag.AlignVCenter)
            lbl = QLabel(s["name"])
            lbl.setFont(dt.font_body(11))
            lbl.setStyleSheet(f"color:{dt.S_INK_2};background:transparent;")
            cl.addWidget(lbl)
            self._lay.addWidget(chip)
            self._items.append(chip)


# ── Public screen widget ──────────────────────────────────────────────────── #

class ResultsScreen(QWidget):
    """
    End-of-game results screen.
    Signal: back_clicked — go back to the main menu.
    """
    back_clicked = pyqtSignal()

    # kept for backwards compat with existing main_window wiring
    next_round_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{dt.S_PAPER};")
        self._build_ui()

    # ------------------------------------------------------------------ #
    # Layout                                                               #
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Hero band ──────────────────────────────────────────────────── #
        hero = QWidget()
        self._hero_widget = hero
        hero.setStyleSheet(
            f"QWidget{{background:{dt.S_SURFACE};"
            f"border-bottom:1px solid {dt.S_RULE};}}"
        )
        hero.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        hl = QVBoxLayout(hero)
        hl.setContentsMargins(48, 40, 48, 32)
        hl.setSpacing(0)

        # Top bar: eyebrow + back button
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 20)
        self._eyebrow = _eyebrow("Spielende")
        top_bar.addWidget(self._eyebrow, 1)
        top_bar.addStretch()
        self._back_btn = _btn("← Hauptmenü")
        self._back_btn.clicked.connect(self.back_clicked)
        self._back_btn.clicked.connect(self.next_round_clicked)
        top_bar.addWidget(self._back_btn)
        hl.addLayout(top_bar)

        # Winner row
        winner_row = QHBoxLayout()
        winner_row.setSpacing(24)
        winner_row.setContentsMargins(0, 0, 0, 0)
        self._winner_circle = _WinnerCircle(100)
        winner_row.addWidget(self._winner_circle, 0, Qt.AlignmentFlag.AlignBottom)

        winner_text = QVBoxLayout()
        winner_text.setSpacing(4)
        winner_text.setContentsMargins(0, 0, 0, 0)
        self._winner_eyebrow = QLabel("★ Gewinner")
        self._winner_eyebrow.setFont(dt.font_mono(11))
        self._winner_eyebrow.setStyleSheet(
            f"color:{dt.S_P3};background:transparent;"
            f"letter-spacing:0.08em;font-weight:600;"
        )
        winner_text.addWidget(self._winner_eyebrow)
        self._winner_name = QLabel("—")
        fh = dt.font_display(48)
        fh.setWeight(QFont.Weight(700))
        self._winner_name.setFont(fh)
        self._winner_name.setStyleSheet(
            f"color:{dt.S_INK};background:transparent;letter-spacing:-0.025em;"
        )
        winner_text.addWidget(self._winner_name)
        self._winner_sub = QLabel("—")
        self._winner_sub.setFont(dt.font_body(15))
        self._winner_sub.setStyleSheet(
            f"color:{dt.S_INK_2};background:transparent;"
        )
        winner_text.addWidget(self._winner_sub)
        winner_row.addLayout(winner_text, 1)
        hl.addLayout(winner_row)
        root.addWidget(hero)

        # ── Scrollable body ─────────────────────────────────────────────── #
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        root.addWidget(scroll, 1)

        body_w = QWidget()
        body_w.setStyleSheet("background:transparent;")
        scroll.setWidget(body_w)

        body_l = QHBoxLayout(body_w)
        body_l.setContentsMargins(48, 28, 48, 28)
        body_l.setSpacing(24)

        # ── Left column: highlights + chart ─────────────────────────────── #
        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(0)

        left.addWidget(_section_head("Highlights"))
        left.addSpacing(12)

        self._highlights_grid = QGridLayout()
        self._highlights_grid.setSpacing(10)
        self._highlight_cards: list[_HighlightCard] = []
        for i in range(4):
            card = _HighlightCard()
            self._highlight_cards.append(card)
            self._highlights_grid.addWidget(card, i // 2, i % 2)
        left.addLayout(self._highlights_grid)
        left.addSpacing(28)

        left.addWidget(_section_head("Punkteverlauf"))
        left.addSpacing(10)

        chart_panel = _panel_frame()
        chart_l = QVBoxLayout(chart_panel)
        chart_l.setContentsMargins(16, 16, 16, 8)
        chart_l.setSpacing(8)
        self._chart = _LineChart()
        chart_l.addWidget(self._chart)
        self._legend = _LegendRow()
        chart_l.addWidget(self._legend)
        left.addWidget(chart_panel)
        left.addStretch()

        left_w = QWidget()
        left_w.setStyleSheet("background:transparent;")
        left_w.setLayout(left)
        body_l.addWidget(left_w, 14)

        # ── Right column: final standings ────────────────────────────────── #
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)

        right.addWidget(_section_head("Endstand"))
        right.addSpacing(12)

        standings_panel = _panel_frame()
        standings_l = QVBoxLayout(standings_panel)
        standings_l.setContentsMargins(0, 0, 0, 0)
        standings_l.setSpacing(0)

        # Column headers
        hdr = QWidget()
        hdr.setStyleSheet(f"background:{dt.S_PAPER};border-radius:7px 7px 0 0;")
        hdr.setFixedHeight(30)
        hdrl = QHBoxLayout(hdr)
        hdrl.setContentsMargins(16, 0, 16, 0)
        hdrl.setSpacing(10)

        def _th(txt, w=0, align=Qt.AlignmentFlag.AlignLeft):
            l = QLabel(txt.upper())
            l.setFont(dt.font_mono(9))
            l.setStyleSheet(f"color:{dt.S_INK_3};background:transparent;letter-spacing:0.08em;")
            l.setAlignment(align)
            if w:
                l.setFixedWidth(w)
            return l

        hdrl.addSpacing(20)
        hdrl.addWidget(_th("Spieler"), 1)
        hdrl.addWidget(_th("Aufbau", 56, Qt.AlignmentFlag.AlignRight))
        hdrl.addWidget(_th("Betrieb", 52, Qt.AlignmentFlag.AlignRight))
        hdrl.addWidget(_th("Gesamt", 52, Qt.AlignmentFlag.AlignRight))
        standings_l.addWidget(hdr)
        standings_l.addWidget(_hsep())

        self._standing_rows: list[_StandingRow] = []
        for i in range(8):
            if i > 0:
                standings_l.addWidget(_hsep(soft=True))
            row = _StandingRow()
            self._standing_rows.append(row)
            standings_l.addWidget(row)
        right.addWidget(standings_panel)
        right.addStretch()

        right_w = QWidget()
        right_w.setStyleSheet("background:transparent;")
        right_w.setLayout(right)
        body_l.addWidget(right_w, 10)

    def refresh_theme(self) -> None:
        self.setStyleSheet(f"background:{dt.S_PAPER};")
        self._hero_widget.setStyleSheet(
            f"QWidget{{background:{dt.S_SURFACE};"
            f"border-bottom:1px solid {dt.S_RULE};}}"
        )

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def populate(self, gs) -> None:
        """Fill the screen with real GameState data."""
        winner = gs.winner
        n_players = len(gs.players)

        initial = 20   # standard Dampfross starting capital

        # Compute per-player scores
        player_data = []
        for pidx, p in enumerate(gs.players):
            bm = gs.build_money.get(pidx, p.money)
            build_pts = bm - initial
            race_pts  = p.money - bm
            player_data.append({
                "pidx":      pidx,
                "name":      p.name,
                "color":     p.color_hex,
                "build_pts": build_pts,
                "race_pts":  race_pts,
                "total":     p.money,
            })
        player_data.sort(key=lambda d: d["total"], reverse=True)

        # ── Hero ───────────────────────────────────────────────────────── #
        if winner:
            self._winner_circle.set(winner.name[:2], winner.color_hex)
            self._winner_name.setText(winner.name)
            self._winner_eyebrow.setStyleSheet(
                f"color:{winner.color_hex};background:transparent;"
                f"letter-spacing:0.08em;font-weight:600;"
            )
            pts_over_second = 0
            second = next((d for d in player_data if d["name"] != winner.name), None)
            if second:
                pts_over_second = winner.money - second["total"]
            self._winner_sub.setText(
                f"{winner.money} Kredite  ·  {pts_over_second:+d} vor dem Zweiten"
                if second else f"{winner.money} Kredite"
            )
        else:
            leader = player_data[0] if player_data else None
            if leader:
                self._winner_circle.set(leader["name"][:2], leader["color"])
                self._winner_name.setText(leader["name"])
                self._winner_sub.setText(f"{leader['total']} Kredite (führend)")

        # ── Highlights ─────────────────────────────────────────────────── #
        highlights = _compute_highlights(gs, player_data, initial)
        for i, card in enumerate(self._highlight_cards):
            if i < len(highlights):
                h = highlights[i]
                card.refresh(h["category"], h["name"], h["color"], h["value"])
                card.show()
            else:
                card.hide()

        # ── Line chart ─────────────────────────────────────────────────── #
        series = []
        labels = []
        if gs.score_history:
            hist_labels = getattr(gs, "score_history_labels", [])
            labels = hist_labels if len(hist_labels) == len(gs.score_history) \
                     else [f"J{i+1}" for i in range(len(gs.score_history))]
            # Find where the build phase ends (first "J" label index)
            split_idx = next(
                (i for i, lbl in enumerate(labels) if lbl.startswith("J")),
                None,
            )
            for pidx, p in enumerate(gs.players):
                data = [snap.get(pidx, initial) for snap in gs.score_history]
                series.append({"name": p.name, "color": p.color_hex, "data": data})
        else:
            split_idx = None
        self._chart.set_data(series, labels, split_idx=split_idx)
        self._legend.set_series(series)

        # ── Standings table ─────────────────────────────────────────────── #
        for i, row in enumerate(self._standing_rows):
            if i < len(player_data):
                d = player_data[i]
                is_win = (winner is not None and d["name"] == winner.name)
                row.refresh(
                    d["name"], d["color"],
                    d["build_pts"], d["race_pts"], d["total"],
                    is_win,
                )
                row.show()
            else:
                row.hide()


# ── Highlight computation ─────────────────────────────────────────────────── #

def _compute_highlights(gs, player_data: list[dict], initial: int) -> list[dict]:
    highlights = []

    # Most races won (count first-place arrivals across journey history)
    # We don't have per-journey winner history, so derive from score_history deltas
    race_wins: dict[int, int] = {i: 0 for i in range(len(gs.players))}
    prev = {pidx: initial for pidx in range(len(gs.players))}
    for snap in gs.score_history:
        # Who gained the most in this snapshot?
        best_gain = -1
        best_pidx = None
        for pidx in range(len(gs.players)):
            gain = snap.get(pidx, prev.get(pidx, initial)) - prev.get(pidx, initial)
            if gain > best_gain:
                best_gain = gain
                best_pidx = pidx
        if best_pidx is not None and best_gain > 0:
            race_wins[best_pidx] += 1
        prev = {pidx: snap.get(pidx, prev.get(pidx, initial))
                for pidx in range(len(gs.players))}

    if race_wins:
        best_pidx = max(race_wins, key=race_wins.get)
        p = gs.players[best_pidx]
        wins = race_wins[best_pidx]
        if wins > 0:
            highlights.append({
                "category": "Meiste Rennen gewonnen",
                "name":     p.name,
                "color":    p.color_hex,
                "value":    f"{wins} {'Rennen' if wins > 1 else 'Rennen'}",
            })

    # Longest network
    best_net = max(gs.players, key=lambda p: len(p.track_edges), default=None)
    if best_net:
        highlights.append({
            "category": "Längstes Streckennetz",
            "name":     best_net.name,
            "color":    best_net.color_hex,
            "value":    f"{len(best_net.track_edges)} Streckenabschnitte",
        })

    # Most build-phase money
    build_leader = max(
        player_data, key=lambda d: d["build_pts"], default=None
    )
    if build_leader and build_leader["build_pts"] > 0:
        highlights.append({
            "category": "Aufbauphase",
            "name":     build_leader["name"],
            "color":    build_leader["color"],
            "value":    f"{build_leader['build_pts']:+d} Kredite",
        })

    # Most race-phase money
    race_leader = max(
        player_data, key=lambda d: d["race_pts"], default=None
    )
    if race_leader and race_leader["race_pts"] > 0:
        highlights.append({
            "category": "Betriebsphase",
            "name":     race_leader["name"],
            "color":    race_leader["color"],
            "value":    f"{race_leader['race_pts']:+d} Kredite",
        })

    return highlights[:4]

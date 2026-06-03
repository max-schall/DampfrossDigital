"""
Scoreboard screen — header + table + sidebar.
Matches ScoreboardScreen from screens.jsx.
"""
from __future__ import annotations
import math
from typing import Sequence

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QPen
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)

import dampfross.ui.design_tokens as dt
from dampfross.ui.components import Badge, SegmentedControl, SparklineWidget


# ── Helpers ───────────────────────────────────────────────────────────── #

def _eyebrow(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setFont(dt.font_mono(10))
    lbl.setStyleSheet(
        f"color:{dt.S_INK_2};background:transparent;letter-spacing:0.08em;"
    )
    return lbl


def _section_head(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    f = dt.font_display(14)
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


def _btn_secondary(text: str) -> QPushButton:
    b = QPushButton(text)
    b.setFont(dt.font_body(13))
    b.setStyleSheet(
        f"QPushButton{{background:{dt.S_SURFACE};color:{dt.S_INK};"
        f"border:1px solid {dt.S_RULE};border-radius:8px;"
        f"font-size:13px;font-weight:500;padding:8px 16px;}}"
        f"QPushButton:hover{{background:{dt.S_SUNK};}}"
    )
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def _sparkline_data(seed: int) -> list[float]:
    return [8.0 + ((i * 13 + seed * 7) % 24) for i in range(6)]


# ── Avatar circle ─────────────────────────────────────────────────────── #

class _Avatar(QWidget):
    def __init__(self, initials: str, color_hex: str, size: int = 32,
                 parent=None):
        super().__init__(parent)
        self._initials = initials[:2].upper()
        self._color    = QColor(color_hex)
        self._font_px  = max(9, size // 3)
        self.setFixedSize(size, size)

    def set_color(self, hex_color: str) -> None:
        self._color = QColor(hex_color)
        self.update()

    def set_initials(self, text: str) -> None:
        self._initials = text[:2].upper()
        self.update()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(0, 0, -1, -1)
        p.setBrush(QBrush(self._color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(r)
        pen = QPen(QColor("#ffffff"))
        p.setPen(pen)
        f = QFont()
        f.setPixelSize(self._font_px)
        f.setWeight(QFont.Weight(700))
        p.setFont(f)
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, self._initials)


# ── Table header row ──────────────────────────────────────────────────── #

class _TableHeader(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(0)

        def _th(text: str, w: int = 0, align=Qt.AlignmentFlag.AlignLeft) -> QLabel:
            lbl = QLabel(text.upper())
            lbl.setFont(dt.font_mono(11))
            lbl.setStyleSheet(
                f"color:{dt.S_INK_3};background:transparent;"
                f"font-weight:500;letter-spacing:0.08em;"
            )
            lbl.setAlignment(align)
            if w:
                lbl.setFixedWidth(w)
            return lbl

        layout.addWidget(_th("#", 60))
        layout.addWidget(_th("Line · Player"), 1)
        layout.addWidget(_th("Network", 90))
        layout.addWidget(_th("Race", 80))
        layout.addWidget(_th("Trend (last 6 rounds)"), 1)
        layout.addWidget(_th("Total", 90, Qt.AlignmentFlag.AlignRight))


# ── Table data row ────────────────────────────────────────────────────── #

class _TableRow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(60)
        self.setStyleSheet("background:transparent;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(0)

        # Rank
        self._rank = QLabel("01")
        self._rank.setFont(dt.font_mono(13))
        self._rank.setFixedWidth(60)
        self._rank.setStyleSheet(
            f"color:{dt.S_INK_3};background:transparent;font-weight:600;"
        )
        layout.addWidget(self._rank)

        # Avatar + name/line
        identity = QHBoxLayout()
        identity.setSpacing(12)
        identity.setContentsMargins(0, 0, 0, 0)
        self._avatar = _Avatar("AA", dt.S_INK_4, 32)
        identity.addWidget(self._avatar, 0, Qt.AlignmentFlag.AlignVCenter)
        name_col = QVBoxLayout()
        name_col.setSpacing(2)
        name_col.setContentsMargins(0, 0, 0, 0)
        self._name_lbl = QLabel("Player")
        fn = dt.font_body(13)
        fn.setWeight(QFont.Weight(600))
        self._name_lbl.setFont(fn)
        self._name_lbl.setStyleSheet(f"color:{dt.S_INK};background:transparent;")
        name_col.addWidget(self._name_lbl)
        self._line_lbl = QLabel("Line S1")
        self._line_lbl.setFont(dt.font_mono(10))
        self._line_lbl.setStyleSheet(
            f"color:{dt.S_INK_3};background:transparent;letter-spacing:0.08em;"
        )
        name_col.addWidget(self._line_lbl)
        identity.addLayout(name_col, 1)
        layout.addLayout(identity, 1)

        # Network
        self._net = QLabel("—")
        self._net.setFont(dt.font_mono(13))
        self._net.setFixedWidth(90)
        self._net.setStyleSheet(f"color:{dt.S_INK_1};background:transparent;")
        layout.addWidget(self._net)

        # Race
        self._race = QLabel("—")
        self._race.setFont(dt.font_mono(13))
        self._race.setFixedWidth(80)
        self._race.setStyleSheet(f"color:{dt.S_INK_1};background:transparent;")
        layout.addWidget(self._race)

        # Sparkline
        self._spark = SparklineWidget(parent=self)
        layout.addWidget(self._spark, 1, Qt.AlignmentFlag.AlignVCenter)

        # Total
        self._total = QLabel("—")
        self._total.setFont(dt.font_mono(18))
        self._total.setFixedWidth(90)
        self._total.setStyleSheet(
            f"color:{dt.S_INK};background:transparent;font-weight:600;"
        )
        self._total.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._total)

    def refresh(self, rank: int, name: str, player_idx: int,
                net: int, race: int, total: int,
                spark_data: list[float], is_leader: bool = False) -> None:
        color = dt.player_hex(player_idx)
        self._rank.setText(f"{rank:02d}")
        self._rank.setStyleSheet(
            f"color:{dt.S_P3 if is_leader else dt.S_INK_3};"
            f"background:transparent;font-weight:600;"
        )
        self._avatar.set_color(color)
        self._avatar.set_initials(name[:2])
        self._name_lbl.setText(name)
        self._line_lbl.setText(f"Line S{player_idx}".upper())
        self._net.setText(str(net))
        self._race.setText(str(race))
        self._total.setText(str(total))
        self._total.setStyleSheet(
            f"color:{dt.S_P3 if is_leader else dt.S_INK};"
            f"background:transparent;font-weight:600;"
        )
        self._spark.set_data(spark_data, player_idx)


# ── Leader card (sidebar) ─────────────────────────────────────────────── #

class _LeaderCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame{{background:{dt.S_SURFACE};border:1px solid {dt.S_RULE};"
            f"border-radius:8px;}}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Panel head
        head = QHBoxLayout()
        head.setContentsMargins(18, 14, 18, 14)
        head.setSpacing(8)
        self._title_lbl = QLabel("Player is leading")
        ft = dt.font_display(14)
        ft.setWeight(QFont.Weight(600))
        self._title_lbl.setFont(ft)
        self._title_lbl.setStyleSheet(f"color:{dt.S_INK};background:transparent;")
        head.addWidget(self._title_lbl, 1)
        self._gap_lbl = QLabel("+0")
        self._gap_lbl.setFont(dt.font_mono(11))
        self._gap_lbl.setStyleSheet(f"color:{dt.S_INK_3};background:transparent;")
        head.addWidget(self._gap_lbl)
        layout.addLayout(head)
        layout.addWidget(_hsep())

        # Panel body
        body = QWidget()
        body.setStyleSheet("background:transparent;")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(18, 18, 18, 18)
        bl.setSpacing(0)

        av_row = QHBoxLayout()
        av_row.setSpacing(12)
        av_row.setContentsMargins(0, 0, 0, 14)
        self._avatar = _Avatar("AA", dt.S_P3, 48)
        av_row.addWidget(self._avatar, 0, Qt.AlignmentFlag.AlignVCenter)
        id_col = QVBoxLayout()
        id_col.setSpacing(2)
        id_col.setContentsMargins(0, 0, 0, 0)
        self._name_lbl = QLabel("Player")
        fn = dt.font_display(22)
        fn.setWeight(QFont.Weight(600))
        self._name_lbl.setFont(fn)
        self._name_lbl.setStyleSheet(f"color:{dt.S_INK};background:transparent;")
        id_col.addWidget(self._name_lbl)
        self._sub_lbl = QLabel("Line S1")
        self._sub_lbl.setFont(dt.font_mono(11))
        self._sub_lbl.setStyleSheet(
            f"color:{dt.S_INK_3};background:transparent;letter-spacing:0.08em;"
        )
        id_col.addWidget(self._sub_lbl)
        av_row.addLayout(id_col, 1)
        bl.addLayout(av_row)

        self._desc = QLabel("Leading the game.")
        self._desc.setFont(dt.font_body(13))
        self._desc.setStyleSheet(
            f"color:{dt.S_INK_2};background:transparent;"
        )
        self._desc.setWordWrap(True)
        bl.addWidget(self._desc)
        layout.addWidget(body)

    def refresh(self, name: str, player_idx: int, gap: int,
                line_sub: str = "", desc: str = "") -> None:
        color = dt.player_hex(player_idx)
        self._title_lbl.setText(f"{name} is leading")
        self._gap_lbl.setText(f"+{gap}")
        self._avatar.set_color(color)
        self._avatar.set_initials(name[:2])
        self._name_lbl.setText(name)
        self._sub_lbl.setText(
            (line_sub or f"Line S{player_idx}").upper()
        )
        if desc:
            self._desc.setText(desc)


# ── Insights panel (sidebar) ──────────────────────────────────────────── #

class _InsightsPanel(QFrame):
    def __init__(self, insights: list[str] | None = None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame{{background:{dt.S_SURFACE};border:1px solid {dt.S_RULE};"
            f"border-radius:8px;}}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Panel head
        head = QHBoxLayout()
        head.setContentsMargins(18, 14, 18, 14)
        title = QLabel("Round insights")
        ft = dt.font_display(14)
        ft.setWeight(QFont.Weight(600))
        title.setFont(ft)
        title.setStyleSheet(f"color:{dt.S_INK};background:transparent;")
        head.addWidget(title)
        layout.addLayout(head)
        layout.addWidget(_hsep())

        body = QWidget()
        body.setStyleSheet("background:transparent;")
        self._body_l = QVBoxLayout(body)
        self._body_l.setContentsMargins(18, 14, 18, 14)
        self._body_l.setSpacing(10)
        layout.addWidget(body)

        self.set_insights(insights or [])

    def set_insights(self, insights: list[str]) -> None:
        while self._body_l.count():
            item = self._body_l.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for text in insights:
            row = QWidget()
            row.setStyleSheet("background:transparent;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(10)

            dot = _InkDot()
            rl.addWidget(dot, 0, Qt.AlignmentFlag.AlignTop)
            lbl = QLabel(text)
            lbl.setFont(dt.font_body(13))
            lbl.setStyleSheet(f"color:{dt.S_INK_1};background:transparent;")
            lbl.setWordWrap(True)
            rl.addWidget(lbl, 1)
            self._body_l.addWidget(row)


class _InkDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(6, 6)
        # offset so it aligns with first line of adjacent text
        self.setContentsMargins(0, 8, 0, 0)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor(dt.S_INK_4)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(self.rect())


# ── Public screen widget ──────────────────────────────────────────────── #

class ScoreboardScreen(QWidget):
    """
    Full scoreboard screen.
    Signals: export_clicked, settings_changed(str tab).
    """
    export_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{dt.S_PAPER};")
        self._build_ui()
        self._load_demo()

    # ------------------------------------------------------------------ #
    # Layout                                                               #
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ─────────────────────────────────────────────────────── #
        header = QWidget()
        self._header_widget = header
        header.setStyleSheet(
            f"QWidget{{background:{dt.S_SURFACE};"
            f"border-bottom:1px solid {dt.S_RULE};}}"
        )
        header.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(40, 28, 40, 28)
        hl.setSpacing(0)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        title_col.setContentsMargins(0, 0, 0, 0)
        self._round_eyebrow = _eyebrow("Scoreboard · Round 6 of 9")
        title_col.addWidget(self._round_eyebrow)
        self._title = QLabel("Standings")
        f = dt.font_display(38)
        f.setWeight(QFont.Weight(600))
        self._title.setFont(f)
        self._title.setStyleSheet(
            f"color:{dt.S_INK};background:transparent;letter-spacing:-0.02em;"
        )
        title_col.addWidget(self._title)
        hl.addLayout(title_col, 1)

        controls = QHBoxLayout()
        controls.setSpacing(10)
        controls.setContentsMargins(0, 0, 0, 0)
        self._seg = SegmentedControl(["Overall", "Network", "Race"])
        controls.addWidget(self._seg)
        self._export_btn = _btn_secondary("Export round CSV")
        self._export_btn.clicked.connect(self.export_clicked)
        controls.addWidget(self._export_btn)
        hl.addLayout(controls)
        root.addWidget(header)

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
        body_l.setContentsMargins(40, 28, 40, 28)
        body_l.setSpacing(28)

        # ── Left: table panel ──────────────────────────────────────────── #
        table_panel = _panel_frame()
        table_l = QVBoxLayout(table_panel)
        table_l.setContentsMargins(0, 8, 0, 8)
        table_l.setSpacing(0)
        table_l.addWidget(_TableHeader())
        table_l.addWidget(_hsep())

        self._rows: list[_TableRow] = []
        for _ in range(6):
            sep = _hsep(soft=True)
            row = _TableRow()
            self._rows.append(row)
            table_l.addWidget(sep)
            table_l.addWidget(row)

        body_l.addWidget(table_panel, 1)

        # ── Right: sidebar (360 px) ────────────────────────────────────── #
        sidebar = QVBoxLayout()
        sidebar.setContentsMargins(0, 0, 0, 0)
        sidebar.setSpacing(14)
        sidebar.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._leader_card = _LeaderCard()
        sidebar.addWidget(self._leader_card)

        self._insights = _InsightsPanel()
        sidebar.addWidget(self._insights)
        sidebar.addStretch()

        sidebar_w = QWidget()
        sidebar_w.setStyleSheet("background:transparent;")
        sidebar_w.setFixedWidth(360)
        sidebar_w.setLayout(sidebar)
        body_l.addWidget(sidebar_w)

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def set_round(self, number: int, total: int) -> None:
        self._round_eyebrow.setText(
            f"Scoreboard · Round {number} of {total}".upper()
        )

    def set_rows(self, rows: list[dict]) -> None:
        """
        rows: list of dicts: player_idx, name, net, race, total, spark_data (opt)
        """
        for i, tr in enumerate(self._rows):
            if i < len(rows):
                r = rows[i]
                spark = r.get("spark_data") or _sparkline_data(i)
                tr.refresh(
                    rank=i + 1,
                    name=r["name"],
                    player_idx=r["player_idx"],
                    net=r["net"],
                    race=r["race"],
                    total=r["total"],
                    spark_data=spark,
                    is_leader=(i == 0),
                )
                tr.show()
            else:
                tr.hide()

    def set_leader(self, name: str, player_idx: int, gap: int,
                   line_sub: str = "", desc: str = "") -> None:
        self._leader_card.refresh(name, player_idx, gap, line_sub, desc)

    def set_insights(self, insights: list[str]) -> None:
        self._insights.set_insights(insights)

    def refresh_theme(self) -> None:
        self.setStyleSheet(f"background:{dt.S_PAPER};")
        self._header_widget.setStyleSheet(
            f"QWidget{{background:{dt.S_SURFACE};"
            f"border-bottom:1px solid {dt.S_RULE};}}"
        )
        self._title.setStyleSheet(
            f"color:{dt.S_INK};background:transparent;letter-spacing:-0.02em;"
        )

    # ------------------------------------------------------------------ #
    # Demo data                                                            #
    # ------------------------------------------------------------------ #

    def _load_demo(self) -> None:
        self.set_round(6, 9)
        self.set_rows([
            {"player_idx": 3, "name": "Hannah", "net": 84, "race": 58, "total": 142},
            {"player_idx": 2, "name": "Lukas",  "net": 76, "race": 52, "total": 128},
            {"player_idx": 1, "name": "Mira",   "net": 62, "race": 50, "total": 112},
            {"player_idx": 4, "name": "Pieter", "net": 58, "race": 40, "total": 98},
            {"player_idx": 7, "name": "Sasha",  "net": 53, "race": 38, "total": 91},
            {"player_idx": 5, "name": "Otto",   "net": 40, "race": 24, "total": 64},
        ])
        self.set_leader(
            "Hannah", 3, 14,
            "Line S3 · Vossberg Green",
            "Won heats 1 & 3, built the longest stretch through the Aschberg ridge, "
            "and is the only player to connect both capitals.",
        )
        self.set_insights([
            "Mira built the most segments (9) this round.",
            "Sasha derailed twice — 6 race pts forfeit.",
            "Pieter is closest to the Coast-to-coast bonus.",
        ])

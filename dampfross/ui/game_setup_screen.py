"""
Game setup screen — full-page, design-system aligned.
Replaces the old GameSetupDialog.
"""
from __future__ import annotations
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QSpinBox,
    QVBoxLayout, QWidget,
)
from PyQt6.QtGui import QCursor

import dampfross.ui.design_tokens as dt
from ..game.state import PLAYER_COLORS, WIN_TARGETS


def _maps_dir() -> Path:
    """'maps/' folder next to the project root, or home as fallback."""
    d = Path(__file__).parent.parent.parent / "maps"
    return d if d.is_dir() else Path.home()


# ── small helpers ────────────────────────────────────────────────────────── #

def _eyebrow(text: str) -> QLabel:
    l = QLabel(text)
    l.setFont(dt.font_mono(10))
    l.setStyleSheet(
        f"color:{dt.S_INK_3}; background:transparent; letter-spacing:0.12em;"
    )
    return l


def _rule() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"border:none; background:{dt.S_RULE}; max-height:1px;")
    return f


def _field_ss() -> str:
    return (
        f"QLineEdit {{"
        f"  background:{dt.S_SURFACE}; color:{dt.S_INK};"
        f"  border:1px solid {dt.S_RULE}; border-radius:{dt.R_2}px;"
        f"  font-size:14px; padding:8px 12px;"
        f"}}"
        f"QLineEdit:focus {{ border-color:{dt.S_INK_3}; }}"
    )


def _spin_ss() -> str:
    return (
        f"QSpinBox {{"
        f"  background:{dt.S_SURFACE}; color:{dt.S_INK};"
        f"  border:1px solid {dt.S_RULE}; border-radius:{dt.R_2}px;"
        f"  font-size:14px; padding:7px 10px; min-width:80px;"
        f"}}"
        f"QSpinBox::up-button, QSpinBox::down-button {{"
        f"  width:22px; border:none; background:transparent;"
        f"}}"
    )


# ── Color swatch picker ──────────────────────────────────────────────────── #

class _ColorPicker(QWidget):
    """Row of 8 circular color buttons — one per player color."""
    color_changed = pyqtSignal(str)

    def __init__(self, initial_idx: int = 0, parent=None):
        super().__init__(parent)
        self._sel = initial_idx
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._btns: list[QPushButton] = []
        for i, (hx, _) in enumerate(PLAYER_COLORS):
            btn = QPushButton(parent=self)
            btn.setFixedSize(22, 22)
            btn.setCheckable(True)
            btn.setChecked(i == initial_idx)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{"
                f"  background:{hx}; border-radius:11px;"
                f"  border:2px solid transparent;"
                f"}}"
                f"QPushButton:checked {{"
                f"  border:2px solid {dt.S_INK};"
                f"}}"
            )
            # default arg captures i at definition time
            btn.clicked.connect(lambda _checked, idx=i: self._on_btn(idx))
            layout.addWidget(btn)
            self._btns.append(btn)
        layout.addStretch()

    def _on_btn(self, idx: int) -> None:
        self._btns[self._sel].setChecked(False)
        self._sel = idx
        self._btns[self._sel].setChecked(True)
        self.color_changed.emit(PLAYER_COLORS[idx][0])

    def current_hex(self) -> str:
        return PLAYER_COLORS[self._sel][0]


# ── Player row ───────────────────────────────────────────────────────────── #

class _PlayerRow(QWidget):
    def __init__(self, number: int, initial_color_idx: int, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"_PlayerRow {{"
            f"  background:{dt.S_SURFACE}; border:1px solid {dt.S_RULE};"
            f"  border-radius:{dt.R_2}px;"
            f"}}"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        num_lbl = QLabel(str(number))
        num_lbl.setFont(dt.font_mono(11))
        num_lbl.setStyleSheet(f"color:{dt.S_INK_4}; background:transparent;")
        num_lbl.setFixedWidth(18)
        layout.addWidget(num_lbl)

        self._name = QLineEdit(f"Spieler {number}")
        self._name.setFont(dt.font_body(14))
        self._name.setStyleSheet(_field_ss())
        layout.addWidget(self._name, 1)

        self._picker = _ColorPicker(initial_color_idx, parent=self)
        layout.addWidget(self._picker)

        self._bot_cb = QCheckBox("Bot")
        self._bot_cb.setFont(dt.font_mono(11))
        self._bot_cb.setStyleSheet(
            f"color:{dt.S_INK_2}; background:transparent;"
        )
        layout.addWidget(self._bot_cb)

    def name(self) -> str:
        return self._name.text().strip() or self._name.placeholderText()

    def color_hex(self) -> str:
        return self._picker.current_hex()

    def is_bot(self) -> bool:
        return self._bot_cb.isChecked()


# ── Map selection card ───────────────────────────────────────────────────── #

class _MapCard(QWidget):
    path_changed = pyqtSignal(object)   # Path | None

    def __init__(self, parent=None):
        super().__init__(parent)
        self._path: Path | None = None
        self._apply_style(selected=False)
        self.setMinimumHeight(96)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._name_lbl = QLabel("Keine Karte gewählt")
        self._name_lbl.setFont(dt.font_body(14, weight=500))
        self._name_lbl.setStyleSheet(f"color:{dt.S_INK_3}; background:transparent;")
        self._name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._name_lbl)

        browse_btn = QPushButton("Kartendatei durchsuchen…")
        browse_btn.setFont(dt.font_body(13))
        browse_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background:{dt.S_SURFACE}; color:{dt.S_INK};"
            f"  border:1px solid {dt.S_RULE}; border-radius:{dt.R_PILL}px;"
            f"  padding:7px 18px; font-size:13px; font-weight:500;"
            f"}}"
            f"QPushButton:hover {{ background:{dt.S_SUNK}; }}"
        )
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.clicked.connect(self._browse)
        layout.addWidget(browse_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _apply_style(self, selected: bool) -> None:
        border = f"2px solid {dt.S_SUCCESS}" if selected else f"2px dashed {dt.S_RULE}"
        self.setStyleSheet(
            f"_MapCard {{"
            f"  background:{dt.S_SURFACE}; border:{border};"
            f"  border-radius:{dt.R_3}px;"
            f"}}"
        )

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Spielkarte öffnen", str(_maps_dir()),
            "DampfrossMap Dateien (*.dmpfmap)"
        )
        if not path:
            return
        self._path = Path(path)
        self._name_lbl.setText(self._path.name)
        self._name_lbl.setFont(dt.font_body(14, weight=600))
        self._name_lbl.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")
        self._apply_style(selected=True)
        self.path_changed.emit(self._path)

    def map_path(self) -> Path | None:
        return self._path


# ── Option toggle row ───────────────────────────────────────────────────── #

class _OptionToggle(QWidget):
    """A labeled on/off toggle row with an info-tooltip on the ℹ badge."""
    toggled = pyqtSignal(bool)

    def __init__(self, label: str, tooltip: str,
                 checked: bool = False, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        lbl = QLabel(label)
        lbl.setFont(dt.font_body(14))
        lbl.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")
        layout.addWidget(lbl, 1)

        info = QLabel("ℹ")
        info.setFont(dt.font_mono(11))
        info.setStyleSheet(f"color:{dt.S_INK_3}; background:transparent;")
        info.setToolTip(tooltip)
        info.setCursor(QCursor(Qt.CursorShape.WhatsThisCursor))
        layout.addWidget(info)

        self._btn = QPushButton("AUS")
        self._btn.setCheckable(True)
        self._btn.setChecked(checked)
        self._btn.setFixedSize(52, 26)
        self._btn.setFont(dt.font_mono(10))
        self._btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style(checked)
        self._btn.toggled.connect(self._on_toggled)
        layout.addWidget(self._btn)

    def _apply_style(self, on: bool) -> None:
        if on:
            self._btn.setText("EIN")
            self._btn.setStyleSheet(
                f"QPushButton{{background:{dt.S_P2};color:#ffffff;"
                f"border:none;border-radius:13px;"
                f"font-size:10px;font-weight:700;letter-spacing:0.05em;}}"
            )
        else:
            self._btn.setText("AUS")
            self._btn.setStyleSheet(
                f"QPushButton{{background:{dt.S_RULE};color:{dt.S_INK_3};"
                f"border:none;border-radius:13px;"
                f"font-size:10px;font-weight:600;letter-spacing:0.05em;}}"
                f"QPushButton:hover{{background:{dt.S_SUNK};}}"
            )

    def _on_toggled(self, checked: bool) -> None:
        self._apply_style(checked)
        self.toggled.emit(checked)

    def is_checked(self) -> bool:
        return self._btn.isChecked()


# ── Settings row (label + spin) ─────────────────────────────────────────── #

class _SettingRow(QWidget):
    def __init__(self, label: str, lo: int, hi: int, value: int,
                 suffix: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        lbl = QLabel(label)
        lbl.setFont(dt.font_body(14))
        lbl.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")
        layout.addWidget(lbl, 1)

        self._spin = QSpinBox()
        self._spin.setRange(lo, hi)
        self._spin.setValue(value)
        if suffix:
            self._spin.setSuffix(f"  {suffix}")
        self._spin.setFont(dt.font_mono(13))
        self._spin.setStyleSheet(_spin_ss())
        layout.addWidget(self._spin)

    def value(self) -> int:
        return self._spin.value()

    def set_value(self, v: int) -> None:
        self._spin.setValue(v)


# ── Main screen ──────────────────────────────────────────────────────────── #

class GameSetupScreen(QWidget):
    start_clicked = pyqtSignal()
    back_clicked  = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{dt.S_PAPER};")
        self._player_rows: list[_PlayerRow] = []
        self._count = 0
        self._build_ui()

    # ── construction ──────────────────────────────────────────────────── #

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._header_widget = self._make_header()
        root.addWidget(self._header_widget)
        root.addWidget(_rule())

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet(f"background:{dt.S_PAPER};")
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._body_w = QWidget()
        self._body_w.setStyleSheet(f"background:{dt.S_PAPER};")
        body_l = QVBoxLayout(self._body_w)
        body_l.setContentsMargins(0, 0, 0, 0)
        body_l.setSpacing(0)

        self._center = QWidget()
        self._center.setStyleSheet(f"background:{dt.S_PAPER};")
        self._center.setMaximumWidth(680)
        # keep local aliases for the rest of _build_ui
        scroll = self._scroll
        body_w = self._body_w
        center = self._center
        center_l = QVBoxLayout(center)
        center_l.setContentsMargins(48, 40, 48, 48)
        center_l.setSpacing(32)

        center_l.addWidget(self._make_map_section())
        center_l.addWidget(self._make_players_section())
        center_l.addWidget(self._make_settings_section())
        center_l.addWidget(self._make_options_section())
        center_l.addWidget(self._make_start_btn())

        body_l.addWidget(center, alignment=Qt.AlignmentFlag.AlignHCenter)
        body_l.addStretch()

        scroll.setWidget(body_w)
        root.addWidget(scroll, 1)

    def _make_header(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(56)
        w.setStyleSheet(f"background:{dt.S_SURFACE};")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(16, 0, 24, 0)
        layout.setSpacing(16)

        back = QPushButton("◀  Hauptmenü")
        back.setFont(dt.font_body(13))
        back.setStyleSheet(
            f"QPushButton {{ background:{dt.S_SURFACE}; color:{dt.S_INK_2};"
            f"  border:1px solid {dt.S_RULE}; border-radius:{dt.R_1}px;"
            f"  padding:5px 14px; }}"
            f"QPushButton:hover {{ background:{dt.S_SUNK}; color:{dt.S_INK}; }}"
        )
        back.setCursor(Qt.CursorShape.PointingHandCursor)
        back.clicked.connect(self.back_clicked)
        layout.addWidget(back)

        eyebrow = QLabel("EIN DIGITALES DAMPFROSS")
        eyebrow.setFont(dt.font_mono(10))
        eyebrow.setStyleSheet(
            f"color:{dt.S_INK_3}; background:transparent; letter-spacing:0.12em;"
        )
        layout.addWidget(eyebrow)
        layout.addStretch()

        title = QLabel("Neues Spiel")
        title.setFont(dt.font_display(15, weight=600))
        title.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")
        layout.addWidget(title)

        return w

    def _make_map_section(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        layout.addWidget(_eyebrow("KARTE"))

        headline = QLabel("Karte wählen")
        headline.setFont(dt.font_display(28, weight=600))
        headline.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")
        layout.addWidget(headline)

        self._map_card = _MapCard()
        self._map_card.path_changed.connect(self._on_map_selected)
        layout.addWidget(self._map_card)

        return w

    def _make_players_section(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)

        # Header row: eyebrow+headline left, stepper right
        hdr = QHBoxLayout()

        lbl_col = QVBoxLayout()
        lbl_col.setSpacing(4)
        lbl_col.addWidget(_eyebrow("SPIELER"))
        headline = QLabel("Wer spielt?")
        headline.setFont(dt.font_display(28, weight=600))
        headline.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")
        lbl_col.addWidget(headline)
        hdr.addLayout(lbl_col, 1)

        # Stepper
        _STEP = (
            f"QPushButton {{"
            f"  background:{dt.S_SURFACE}; color:{dt.S_INK};"
            f"  border:1px solid {dt.S_RULE}; font-size:18px; font-weight:600;"
            f"  padding:0; width:36px; height:36px;"
            f"}}"
            f"QPushButton:hover {{ background:{dt.S_SUNK}; }}"
            f"QPushButton:disabled {{ color:{dt.S_INK_4}; }}"
        )
        self._dec_btn = QPushButton("−")
        self._dec_btn.setFixedSize(36, 36)
        self._dec_btn.setStyleSheet(
            _STEP + f"QPushButton {{ border-radius:0;"
            f"  border-top-left-radius:{dt.R_2}px;"
            f"  border-bottom-left-radius:{dt.R_2}px; }}"
        )
        self._dec_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._dec_btn.clicked.connect(lambda: self._set_count(self._count - 1))

        self._count_lbl = QLabel("3")
        self._count_lbl.setFont(dt.font_mono(14, weight=600))
        self._count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._count_lbl.setStyleSheet(
            f"color:{dt.S_INK}; background:{dt.S_SURFACE};"
            f"border-top:1px solid {dt.S_RULE}; border-bottom:1px solid {dt.S_RULE};"
            f"padding:0 14px; min-width:32px; min-height:36px; max-height:36px;"
        )

        self._inc_btn = QPushButton("+")
        self._inc_btn.setFixedSize(36, 36)
        self._inc_btn.setStyleSheet(
            _STEP + f"QPushButton {{ border-radius:0;"
            f"  border-top-right-radius:{dt.R_2}px;"
            f"  border-bottom-right-radius:{dt.R_2}px; }}"
        )
        self._inc_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._inc_btn.clicked.connect(lambda: self._set_count(self._count + 1))

        stepper = QWidget()
        stepper.setStyleSheet("background:transparent;")
        sl = QHBoxLayout(stepper)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(0)
        sl.addWidget(self._dec_btn)
        sl.addWidget(self._count_lbl)
        sl.addWidget(self._inc_btn)
        hdr.addWidget(stepper, alignment=Qt.AlignmentFlag.AlignBottom)

        outer.addLayout(hdr)

        self._rows_container = QWidget()
        self._rows_container.setStyleSheet("background:transparent;")
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(6)
        outer.addWidget(self._rows_container)

        self._set_count(3)
        return w

    def _make_settings_section(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        layout.addWidget(_eyebrow("SPIELEINSTELLUNGEN"))

        headline = QLabel("Regeln")
        headline.setFont(dt.font_display(28, weight=600))
        headline.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")
        layout.addWidget(headline)

        card = QWidget()
        card.setStyleSheet(
            f"background:{dt.S_SURFACE}; border:1px solid {dt.S_RULE};"
            f"border-radius:{dt.R_3}px;"
        )
        card_l = QVBoxLayout(card)
        card_l.setContentsMargins(16, 14, 16, 14)
        card_l.setSpacing(0)

        self._capital_row = _SettingRow("Startkapital", 1, 999, 20, "Einh.")
        card_l.addWidget(self._capital_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(
            f"border:none; background:{dt.S_RULE_SOFT}; max-height:1px; margin:4px 0;"
        )
        card_l.addWidget(sep)

        self._win_row = _SettingRow("Gewinnziel", 50, 999, 250, "Einh.")
        card_l.addWidget(self._win_row)

        layout.addWidget(card)
        return w

    def _make_options_section(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        layout.addWidget(_eyebrow("OPTIONEN"))

        headline = QLabel("Spielregeln")
        headline.setFont(dt.font_display(28, weight=600))
        headline.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")
        layout.addWidget(headline)

        card = QWidget()
        card.setStyleSheet(
            f"background:{dt.S_SURFACE}; border:1px solid {dt.S_RULE};"
            f"border-radius:{dt.R_3}px;"
        )
        card_l = QVBoxLayout(card)
        card_l.setContentsMargins(16, 14, 16, 14)
        card_l.setSpacing(0)

        _TIP_SHARED_ROLL = (
            "Einer würfelt – alle bauen gleich viel.\n\n"
            "In jeder Runde würfelt ein Spieler (rotierend). "
            "Alle Spieler erhalten genau diese Baupunkte. "
            "Erst wenn alle an der Reihe waren, würfelt der nächste Spieler.\n\n"
            "Runde 1 ist ausgenommen: Jeder würfelt noch einmal selbst, "
            "um seinen Startbahnhof zu bestimmen."
        )
        self._opt_shared_roll = _OptionToggle(
            "Alle bekommen die gleichen Würfelpunkte",
            _TIP_SHARED_ROLL,
        )
        card_l.addWidget(self._opt_shared_roll)

        layout.addWidget(card)
        return w

    def _make_start_btn(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.addStretch()

        self._start_btn = QPushButton("Spiel starten  →")
        self._start_btn.setFont(dt.font_display(15, weight=600))
        self._start_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background:{dt.S_INK}; color:{dt.S_SURFACE}; border:none;"
            f"  border-radius:{dt.R_PILL}px; padding:13px 28px;"
            f"  min-height:48px; min-width:180px;"
            f"}}"
            f"QPushButton:hover {{ background:{dt.S_INK_1}; }}"
            f"QPushButton:pressed {{ background:{dt.S_INK_2}; }}"
            f"QPushButton:disabled {{ background:{dt.S_RULE}; color:{dt.S_INK_3}; }}"
        )
        self._start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self.start_clicked)
        layout.addWidget(self._start_btn)
        return w

    # ── logic ──────────────────────────────────────────────────────────── #

    def _set_count(self, n: int) -> None:
        n = max(2, min(6, n))
        self._count = n
        self._count_lbl.setText(str(n))
        self._dec_btn.setEnabled(n > 2)
        self._inc_btn.setEnabled(n < 6)

        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
                item.widget().deleteLater()
        self._player_rows.clear()

        for i in range(n):
            row = _PlayerRow(i + 1, i % len(PLAYER_COLORS))
            self._rows_layout.addWidget(row)
            self._player_rows.append(row)

        if hasattr(self, "_win_row"):
            self._win_row.set_value(WIN_TARGETS.get(n, 250))

    def _on_map_selected(self, _path: object) -> None:
        self._start_btn.setEnabled(True)

    # ── public API ─────────────────────────────────────────────────────── #

    def map_path(self) -> Path | None:
        return self._map_card.map_path()

    def player_configs(self) -> list[dict]:
        return [
            {"name": row.name(), "color": row.color_hex(), "is_bot": row.is_bot()}
            for row in self._player_rows
        ]

    def starting_capital(self) -> int:
        return self._capital_row.value()

    def win_target(self) -> int:
        return self._win_row.value()

    def game_options(self) -> dict:
        return {"shared_roll": self._opt_shared_roll.is_checked()}

    def refresh_theme(self) -> None:
        self.setStyleSheet(f"background:{dt.S_PAPER};")
        self._header_widget.setStyleSheet(f"background:{dt.S_SURFACE};")
        self._scroll.setStyleSheet(f"background:{dt.S_PAPER};")
        self._body_w.setStyleSheet(f"background:{dt.S_PAPER};")
        self._center.setStyleSheet(f"background:{dt.S_PAPER};")

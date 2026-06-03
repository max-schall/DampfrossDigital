"""
LobbyScreen — internet multiplayer lobby.

Flow
────
Host:
  1. Pick own name/color, total player count, map, capital, win target
  2. Click "Create Lobby" → starts WebSocket server + ngrok → URL shown
  3. Clients connect → slots fill in
  4. Click "Start Game" → game_ready emitted

Client:
  1. Enter URL + own name/color
  2. Click "Connect"
  3. Lobby shows who is in — wait for host to start
  4. When game_ready fires, main window transitions to game
"""
from __future__ import annotations
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QSpinBox, QStackedWidget, QVBoxLayout, QWidget,
    QSizePolicy,
)

import dampfross.ui.design_tokens as dt
from ..game.state import PLAYER_COLORS, WIN_TARGETS
from ..net.bridge import NetworkBridge
from .game_setup_screen import _OptionToggle


# ─── helpers ──────────────────────────────────────────────────────────────── #

def _eyebrow(text: str) -> QLabel:
    l = QLabel(text)
    l.setFont(dt.font_mono(10))
    l.setStyleSheet(f"color:{dt.S_INK_3}; background:transparent; letter-spacing:0.12em;")
    return l


def _rule() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"border:none; background:{dt.S_RULE}; max-height:1px;")
    return f


def _field_ss() -> str:
    return (
        f"QLineEdit {{ background:{dt.S_SURFACE}; color:{dt.S_INK};"
        f" border:1px solid {dt.S_RULE}; border-radius:{dt.R_2}px;"
        f" font-size:14px; padding:8px 12px; }}"
        f"QLineEdit:focus {{ border-color:{dt.S_INK_3}; }}"
    )


def _btn_primary() -> str:
    return (
        f"QPushButton {{ background:{dt.S_INK}; color:{dt.S_SURFACE}; border:none;"
        f" border-radius:999px; font-size:14px; font-weight:600;"
        f" padding:11px 24px; min-height:44px; }}"
        f"QPushButton:hover {{ background:{dt.S_INK_1}; }}"
        f"QPushButton:disabled {{ background:{dt.S_RULE}; color:{dt.S_INK_3}; }}"
    )


def _btn_secondary() -> str:
    return (
        f"QPushButton {{ background:{dt.S_SURFACE}; color:{dt.S_INK};"
        f" border:1px solid {dt.S_RULE}; border-radius:999px; font-size:14px;"
        f" font-weight:600; padding:11px 24px; min-height:44px; }}"
        f"QPushButton:hover {{ background:{dt.S_SUNK}; }}"
    )


def _spin_ss() -> str:
    return (
        f"QSpinBox {{ background:{dt.S_SURFACE}; color:{dt.S_INK};"
        f" border:1px solid {dt.S_RULE}; border-radius:{dt.R_2}px;"
        f" font-size:14px; padding:7px 10px; min-width:80px; }}"
        f"QSpinBox::up-button, QSpinBox::down-button {{ width:22px; border:none; background:transparent; }}"
    )


# ─── Color picker (same pattern as game_setup_screen) ─────────────────────── #

class _ColorPicker(QWidget):
    color_changed = pyqtSignal(str)

    def __init__(self, initial_idx: int = 0, parent=None):
        super().__init__(parent)
        self._sel = initial_idx
        self._taken: set[str] = set()
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
                f"QPushButton {{ background:{hx}; border-radius:11px;"
                f" border:2px solid transparent; }}"
                f"QPushButton:checked {{ border:2px solid {dt.S_INK}; }}"
            )
            btn.clicked.connect(lambda _checked, idx=i: self._on_btn(idx))
            layout.addWidget(btn)
            self._btns.append(btn)
        layout.addStretch()

    def _on_btn(self, idx: int) -> None:
        if PLAYER_COLORS[idx][0] in self._taken:
            return
        self._btns[self._sel].setChecked(False)
        self._sel = idx
        self._btns[self._sel].setChecked(True)
        self.color_changed.emit(PLAYER_COLORS[idx][0])

    def set_taken(self, taken: set[str]) -> None:
        """Disable color buttons that are already claimed by other players."""
        self._taken = set(taken)
        for i, (hx, _) in enumerate(PLAYER_COLORS):
            is_taken = hx in taken and i != self._sel
            self._btns[i].setEnabled(not is_taken)
            self._btns[i].setStyleSheet(
                f"QPushButton {{ background:{hx}; border-radius:11px;"
                f" border:2px solid transparent;"
                f" {'opacity:0.3;' if is_taken else ''} }}"
                f"QPushButton:checked {{ border:2px solid {dt.S_INK}; }}"
                f"QPushButton:disabled {{ background:{hx}; border-radius:11px;"
                f" border:2px solid transparent; opacity:0.3; }}"
            )
        # If currently selected color became taken, pick the first free one
        if PLAYER_COLORS[self._sel][0] in taken:
            for i, (hx, _) in enumerate(PLAYER_COLORS):
                if hx not in taken:
                    self._on_btn(i)
                    break

    def current_hex(self) -> str:
        return PLAYER_COLORS[self._sel][0]


# ─── Map card (stripped down) ─────────────────────────────────────────────── #

class _MapCard(QWidget):
    path_changed = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._path: Path | None = None
        self._apply_style(False)
        self.setMinimumHeight(80)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._lbl = QLabel("Keine Karte gewählt")
        self._lbl.setFont(dt.font_body(13, weight=500))
        self._lbl.setStyleSheet(f"color:{dt.S_INK_3}; background:transparent;")
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._lbl)

        btn = QPushButton("Durchsuchen…")
        btn.setFont(dt.font_body(12))
        btn.setStyleSheet(
            f"QPushButton {{ background:{dt.S_SURFACE}; color:{dt.S_INK};"
            f" border:1px solid {dt.S_RULE}; border-radius:{dt.R_PILL}px;"
            f" padding:5px 14px; }}"
            f"QPushButton:hover {{ background:{dt.S_SUNK}; }}"
        )
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self._browse)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _apply_style(self, selected: bool) -> None:
        border = f"2px solid {dt.S_SUCCESS}" if selected else f"2px dashed {dt.S_RULE}"
        self.setStyleSheet(
            f"_MapCard {{ background:{dt.S_SURFACE}; border:{border};"
            f" border-radius:{dt.R_3}px; }}"
        )

    def _browse(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        d = Path(__file__).parent.parent.parent / "maps"
        start = str(d) if d.is_dir() else str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self, "Karte wählen", start, "DampfrossMap (*.dmpfmap)"
        )
        if not path:
            return
        self._path = Path(path)
        self._lbl.setText(self._path.name)
        self._lbl.setFont(dt.font_body(13, weight=600))
        self._lbl.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")
        self._apply_style(True)
        self.path_changed.emit(self._path)

    def map_path(self) -> Path | None:
        return self._path


# ─── Player slot display row ──────────────────────────────────────────────── #

class _SlotRow(QWidget):
    def __init__(self, slot: int, label: str, color: str = "#888888", parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"background:{dt.S_SURFACE}; border:1px solid {dt.S_RULE};"
            f" border-radius:{dt.R_2}px;"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        dot = QLabel("●")
        dot.setStyleSheet(f"color:{color}; background:transparent; font-size:14px;")
        layout.addWidget(dot)
        self._dot = dot

        self._lbl = QLabel(label)
        self._lbl.setFont(dt.font_body(13))
        self._lbl.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")
        layout.addWidget(self._lbl, 1)

    def update(self, label: str, color: str) -> None:
        self._lbl.setText(label)
        self._dot.setStyleSheet(f"color:{color}; background:transparent; font-size:14px;")


# ─── Host panel ───────────────────────────────────────────────────────────── #

class _HostPanel(QWidget):
    create_lobby_clicked = pyqtSignal()
    start_game_clicked   = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{dt.S_PAPER};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(20)

        layout.addWidget(_eyebrow("MULTIPLAYER · HOST"))
        h = QLabel("Spiel hosten")
        h.setFont(dt.font_display(28, weight=600))
        h.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")
        layout.addWidget(h)

        layout.addWidget(_rule())

        # Name
        layout.addWidget(self._row("Dein Name", 0))
        self._name = QLineEdit("Spieler 1")
        self._name.setFont(dt.font_body(14))
        self._name.setStyleSheet(_field_ss())
        layout.addWidget(self._name)

        # Color
        layout.addWidget(self._row("Deine Farbe", 0))
        self._color = _ColorPicker(0)
        layout.addWidget(self._color)

        # Player count
        layout.addWidget(self._row("Anzahl Spieler", 0))
        self._player_count = QSpinBox()
        self._player_count.setRange(2, 6)
        self._player_count.setValue(2)
        self._player_count.setFont(dt.font_mono(13))
        self._player_count.setStyleSheet(_spin_ss())
        layout.addWidget(self._player_count)

        # Remote slots
        layout.addWidget(self._row("Remote-Spieler-Slots", 0))
        self._remote_slots = QSpinBox()
        self._remote_slots.setRange(1, 5)
        self._remote_slots.setValue(1)
        self._remote_slots.setFont(dt.font_mono(13))
        self._remote_slots.setStyleSheet(_spin_ss())
        layout.addWidget(self._remote_slots)

        # Map
        layout.addWidget(self._row("Karte", 0))
        self._map_card = _MapCard()
        self._map_card.path_changed.connect(self._on_map_selected)
        layout.addWidget(self._map_card)

        # Capital / win target
        caps_row = QHBoxLayout()
        caps_row.setSpacing(16)

        cap_col = QVBoxLayout()
        cap_col.setSpacing(4)
        cap_col.addWidget(self._row("Startkapital", 0))
        self._capital = QSpinBox()
        self._capital.setRange(1, 999)
        self._capital.setValue(20)
        self._capital.setFont(dt.font_mono(13))
        self._capital.setStyleSheet(_spin_ss())
        cap_col.addWidget(self._capital)
        caps_row.addLayout(cap_col)

        win_col = QVBoxLayout()
        win_col.setSpacing(4)
        win_col.addWidget(self._row("Gewinnziel", 0))
        self._win = QSpinBox()
        self._win.setRange(50, 999)
        self._win.setValue(250)
        self._win.setFont(dt.font_mono(13))
        self._win.setStyleSheet(_spin_ss())
        win_col.addWidget(self._win)
        caps_row.addLayout(win_col)

        layout.addLayout(caps_row)

        # Options
        layout.addWidget(self._row("Optionen", 0))
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
        layout.addWidget(self._opt_shared_roll)

        layout.addWidget(_rule())

        # URL area (hidden until lobby created)
        self._url_card = QWidget()
        self._url_card.setStyleSheet(
            f"background:{dt.S_SURFACE}; border:1px solid {dt.S_RULE};"
            f" border-radius:{dt.R_2}px;"
        )
        url_lay = QVBoxLayout(self._url_card)
        url_lay.setContentsMargins(12, 10, 12, 10)
        url_lay.setSpacing(4)
        lbl = QLabel("Teile diese URL mit anderen Spielern:")
        lbl.setFont(dt.font_body(12))
        lbl.setStyleSheet(f"color:{dt.S_INK_2}; background:transparent;")
        url_lay.addWidget(lbl)
        self._url_field = QLineEdit()
        self._url_field.setReadOnly(True)
        self._url_field.setFont(dt.font_mono(12))
        self._url_field.setStyleSheet(_field_ss())
        url_lay.addWidget(self._url_field)
        self._url_card.hide()
        layout.addWidget(self._url_card)

        # Slot list
        self._slots_label = QLabel("Spieler:")
        self._slots_label.setFont(dt.font_body(13, weight=600))
        self._slots_label.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")
        self._slots_label.hide()
        layout.addWidget(self._slots_label)

        self._slots_container = QWidget()
        self._slots_container.setStyleSheet("background:transparent;")
        self._slots_layout = QVBoxLayout(self._slots_container)
        self._slots_layout.setContentsMargins(0, 0, 0, 0)
        self._slots_layout.setSpacing(4)
        self._slots_container.hide()
        layout.addWidget(self._slots_container)
        self._slot_rows: list[_SlotRow] = []
        self._slot_data: dict[int, dict] = {}

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        self._create_btn = QPushButton("Lobby erstellen  →")
        self._create_btn.setFont(dt.font_display(14, weight=600))
        self._create_btn.setStyleSheet(_btn_primary())
        self._create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._create_btn.clicked.connect(self.create_lobby_clicked)
        btn_row.addWidget(self._create_btn)

        self._start_btn = QPushButton("Spiel starten  →")
        self._start_btn.setFont(dt.font_display(14, weight=600))
        self._start_btn.setStyleSheet(_btn_primary())
        self._start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self.start_game_clicked)
        self._start_btn.hide()
        btn_row.addWidget(self._start_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    @staticmethod
    def _row(text: str, _: int) -> QLabel:
        l = QLabel(text)
        l.setFont(dt.font_body(12, weight=500))
        l.setStyleSheet(f"color:{dt.S_INK_2}; background:transparent;")
        return l

    def _on_map_selected(self, _: object) -> None:
        pass  # map card validated in LobbyScreen

    # ── Public API ──────────────────────────────────────────────────────── #

    def name(self) -> str:
        return self._name.text().strip() or "Player 1"

    def color(self) -> str:
        return self._color.current_hex()

    def player_count(self) -> int:
        return self._player_count.value()

    def remote_slots(self) -> int:
        return min(self._remote_slots.value(), self._player_count.value() - 1)

    def map_path(self) -> Path | None:
        return self._map_card.map_path()

    def capital(self) -> int:
        return self._capital.value()

    def win_target(self) -> int:
        return self._win.value()

    def game_options(self) -> dict:
        return {"shared_roll": self._opt_shared_roll.is_checked()}

    def set_url(self, url: str) -> None:
        self._url_field.setText(url)
        self._url_card.show()
        self._create_btn.hide()
        self._start_btn.show()
        self._slots_label.show()
        self._slots_container.show()

    def set_start_enabled(self, enabled: bool) -> None:
        self._start_btn.setEnabled(enabled)

    def add_slot(self, slot: int, label: str, color: str) -> None:
        self._slot_data[slot] = {"name": label, "color": color}
        while len(self._slot_rows) < slot + 1:
            sr = _SlotRow(len(self._slot_rows), "Warte…", "#888888")
            self._slots_layout.addWidget(sr)
            self._slot_rows.append(sr)
        self._slot_rows[slot].update(label, color)
        # Disable taken colors on the host's own picker
        taken = {v["color"] for v in self._slot_data.values()}
        self._color.set_taken(taken - {self._color.current_hex()})

    def init_host_slot(self, name: str, color: str) -> None:
        """Show the host's own slot immediately."""
        self._slot_data[0] = {"name": name, "color": color}
        sr = _SlotRow(0, f"{name} (du)", color)
        self._slots_layout.addWidget(sr)
        self._slot_rows.append(sr)

    def slot_data(self) -> dict:
        """Return {slot: {name, color}} for all joined players."""
        return dict(self._slot_data)


# ─── Client panel ─────────────────────────────────────────────────────────── #

class _ClientPanel(QWidget):
    connect_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{dt.S_PAPER};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(20)

        layout.addWidget(_eyebrow("MULTIPLAYER · BEITRETEN"))
        h = QLabel("Spiel beitreten")
        h.setFont(dt.font_display(28, weight=600))
        h.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")
        layout.addWidget(h)

        layout.addWidget(_rule())

        layout.addWidget(self._lbl("Host-URL (wss://…)"))
        self._url = QLineEdit()
        self._url.setFont(dt.font_mono(13))
        self._url.setStyleSheet(_field_ss())
        self._url.setPlaceholderText("wss://xxxxxxxx.ngrok-free.app")
        layout.addWidget(self._url)

        layout.addWidget(self._lbl("Dein Name"))
        self._name = QLineEdit("Spieler 2")
        self._name.setFont(dt.font_body(14))
        self._name.setStyleSheet(_field_ss())
        layout.addWidget(self._name)

        layout.addWidget(self._lbl("Deine Farbe"))
        self._color = _ColorPicker(1)
        layout.addWidget(self._color)

        layout.addWidget(_rule())

        # Status
        self._status = QLabel("")
        self._status.setFont(dt.font_body(13))
        self._status.setStyleSheet(f"color:{dt.S_INK_2}; background:transparent;")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        # Slot list
        self._slots_container = QWidget()
        self._slots_container.setStyleSheet("background:transparent;")
        self._slots_layout = QVBoxLayout(self._slots_container)
        self._slots_layout.setContentsMargins(0, 0, 0, 0)
        self._slots_layout.setSpacing(4)
        layout.addWidget(self._slots_container)
        self._slot_rows: dict[int, _SlotRow] = {}
        self._slot_colors: dict[int, str] = {}   # slot → color hex

        layout.addStretch()

        self._connect_btn = QPushButton("Verbinden  →")
        self._connect_btn.setFont(dt.font_display(14, weight=600))
        self._connect_btn.setStyleSheet(_btn_primary())
        self._connect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._connect_btn.clicked.connect(self.connect_clicked)
        layout.addWidget(self._connect_btn, alignment=Qt.AlignmentFlag.AlignLeft)

    @staticmethod
    def _lbl(text: str) -> QLabel:
        l = QLabel(text)
        l.setFont(dt.font_body(12, weight=500))
        l.setStyleSheet(f"color:{dt.S_INK_2}; background:transparent;")
        return l

    def host_url(self) -> str:
        return self._url.text().strip()

    def name(self) -> str:
        return self._name.text().strip() or "Player 2"

    def color(self) -> str:
        return self._color.current_hex()

    def set_status(self, text: str, is_error: bool = False) -> None:
        color = dt.S_DANGER if is_error else dt.S_INK_2
        self._status.setStyleSheet(f"color:{color}; background:transparent;")
        self._status.setText(text)

    def set_connected(self) -> None:
        self._connect_btn.setEnabled(False)
        self._url.setEnabled(False)
        self._name.setEnabled(False)
        self.set_status("Verbunden — warte auf Host…")

    def update_slot(self, slot: int, name: str, color: str) -> None:
        self._slot_colors[slot] = color
        if slot not in self._slot_rows:
            row = _SlotRow(slot, name, color)
            self._slots_layout.addWidget(row)
            self._slot_rows[slot] = row
        else:
            self._slot_rows[slot].update(name, color)
        # Disable taken colors, keeping the current selection free
        taken = set(self._slot_colors.values()) - {self._color.current_hex()}
        self._color.set_taken(taken)

    def my_color(self) -> str:
        return self._color.current_hex()


# ─── Mode selection ───────────────────────────────────────────────────────── #

class _ModeSelect(QWidget):
    host_clicked = pyqtSignal()
    join_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{dt.S_PAPER};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(56, 80, 56, 80)
        layout.setSpacing(0)
        layout.addStretch()

        layout.addWidget(_eyebrow("MULTIPLAYER"))
        h = QLabel("Übers Internet spielen")
        h.setFont(dt.font_display(36, weight=600))
        h.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")
        layout.addWidget(h)

        layout.addSpacing(8)
        sub = QLabel(
            "Ein Spieler hostet — andere verbinden sich mit der Host-URL.\n"
            "Der Host benötigt ein kostenloses ngrok-Konto für den Tunnel."
        )
        sub.setFont(dt.font_body(14))
        sub.setStyleSheet(f"color:{dt.S_INK_2}; background:transparent;")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        layout.addSpacing(32)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        host_btn = QPushButton("Spiel hosten  →")
        host_btn.setFont(dt.font_display(15, weight=600))
        host_btn.setStyleSheet(_btn_primary())
        host_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        host_btn.clicked.connect(self.host_clicked)
        btn_row.addWidget(host_btn)

        join_btn = QPushButton("Spiel beitreten")
        join_btn.setFont(dt.font_display(15, weight=600))
        join_btn.setStyleSheet(_btn_secondary())
        join_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        join_btn.clicked.connect(self.join_clicked)
        btn_row.addWidget(join_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)
        layout.addStretch()


# ─── Main LobbyScreen ─────────────────────────────────────────────────────── #

_PAGE_MODE   = 0
_PAGE_HOST   = 1
_PAGE_CLIENT = 2


class LobbyScreen(QWidget):
    """
    Signals
    -------
    back_clicked            — user wants to return to main menu
    host_game_ready(bridge, player_configs, map_path, capital, win_target)
    client_game_ready(bridge, player_configs)   — player_configs from host
    """
    back_clicked       = pyqtSignal()
    host_game_ready    = pyqtSignal(object, list, str, int, int, dict)
    client_game_ready  = pyqtSignal(object, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{dt.S_PAPER};")
        self._bridge: NetworkBridge | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header bar
        self._header_widget = self._make_header()
        root.addWidget(self._header_widget)
        root.addWidget(_rule())

        # Scrollable body
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet(f"background:{dt.S_PAPER};")
        # keep local aliases for the rest of __init__
        scroll = self._scroll

        self._body = QWidget()
        self._body.setStyleSheet(f"background:{dt.S_PAPER};")
        body = self._body
        body_l = QVBoxLayout(body)
        body_l.setContentsMargins(0, 0, 0, 0)

        self._center = QWidget()
        self._center.setStyleSheet(f"background:{dt.S_PAPER};")
        center = self._center
        center.setMaximumWidth(600)
        center_l = QVBoxLayout(center)
        center_l.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget()
        self._mode_select = _ModeSelect()
        self._host_panel  = _HostPanel()
        self._client_panel = _ClientPanel()

        self._stack.addWidget(self._mode_select)
        self._stack.addWidget(self._host_panel)
        self._stack.addWidget(self._client_panel)

        center_l.addWidget(self._stack)
        body_l.addWidget(center, alignment=Qt.AlignmentFlag.AlignHCenter)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        # Wire mode select
        self._mode_select.host_clicked.connect(
            lambda: self._stack.setCurrentIndex(_PAGE_HOST))
        self._mode_select.join_clicked.connect(
            lambda: self._stack.setCurrentIndex(_PAGE_CLIENT))

        # Wire host panel
        self._host_panel.create_lobby_clicked.connect(self._on_create_lobby)
        self._host_panel.start_game_clicked.connect(self._on_start_game)

        # Wire client panel
        self._client_panel.connect_clicked.connect(self._on_connect)

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
            f" border:1px solid {dt.S_RULE}; border-radius:{dt.R_1}px;"
            f" padding:5px 14px; }}"
            f"QPushButton:hover {{ background:{dt.S_SUNK}; color:{dt.S_INK}; }}"
        )
        back.setCursor(Qt.CursorShape.PointingHandCursor)
        back.clicked.connect(self._on_back)
        layout.addWidget(back)

        layout.addStretch()
        title = QLabel("Mehrspieler")
        title.setFont(dt.font_display(15, weight=600))
        title.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")
        layout.addWidget(title)
        return w

    # ── Host flow ────────────────────────────────────────────────────────── #

    def _on_create_lobby(self) -> None:
        hp = self._host_panel
        if hp.map_path() is None:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Karte fehlt", "Bitte zuerst eine Kartendatei auswählen.")
            return

        self._bridge = NetworkBridge(
            role="host",
            port=8765,
            name=hp.name(),
            color=hp.color(),
        )
        self._bridge.tunnel_url_ready.connect(self._on_tunnel_url)
        self._bridge.player_joined.connect(self._on_player_joined_host)
        self._bridge.player_left.connect(self._on_player_left)
        self._bridge.error_received.connect(self._on_bridge_error)
        self._bridge.start()

        hp.init_host_slot(hp.name(), hp.color())

    def _on_tunnel_url(self, url: str) -> None:
        self._host_panel.set_url(url)
        self._host_panel.set_start_enabled(True)  # host can always start alone (bots fill)

    def _on_player_joined_host(self, slot: int, name: str, color: str) -> None:
        self._host_panel.add_slot(slot, name, color)

    def _on_player_left(self, slot: int) -> None:
        pass  # could update UI; skip for now

    def _on_start_game(self) -> None:
        hp = self._host_panel
        bridge = self._bridge
        if bridge is None or hp.map_path() is None:
            return

        total   = hp.player_count()
        remote  = hp.remote_slots()
        capital = hp.capital()
        win_tgt = hp.win_target()

        # Build player config list using actual joined names/colors.
        # Slots without a joined client get bot entries.
        from ..game.state import PLAYER_COLORS as _PC
        slot_data = hp.slot_data()
        used_colors: set[str] = set()
        configs: list[dict] = []

        def _free_color(preferred: str) -> str:
            if preferred not in used_colors:
                return preferred
            return next((hx for hx, _ in _PC if hx not in used_colors), preferred)

        for i in range(total):
            if i in slot_data:
                color = _free_color(slot_data[i]["color"])
                used_colors.add(color)
                configs.append({
                    "name":   slot_data[i]["name"],
                    "color":  color,
                    "is_bot": False,
                    "slot":   i,
                })
            elif i <= remote:
                color = _free_color(_PC[i % len(_PC)][0])
                used_colors.add(color)
                configs.append({
                    "name":   f"Remote {i}",
                    "color":  color,
                    "is_bot": False,
                    "slot":   i,
                })
            else:
                color = _free_color(_PC[i % len(_PC)][0])
                used_colors.add(color)
                configs.append({
                    "name":   f"Bot {i - remote}",
                    "color":  color,
                    "is_bot": True,
                    "slot":   i,
                })

        # Send map + game_start to clients
        with open(hp.map_path(), "rb") as f:
            map_bytes = f.read()
        bridge.broadcast_map(map_bytes)
        bridge.broadcast_game_start(configs)

        self.host_game_ready.emit(
            bridge, configs, str(hp.map_path()), capital, win_tgt,
            hp.game_options(),
        )

    # ── Client flow ──────────────────────────────────────────────────────── #

    def _on_connect(self) -> None:
        cp = self._client_panel
        url = cp.host_url()
        if not url:
            cp.set_status("Bitte Host-URL eingeben.", is_error=True)
            return

        self._bridge = NetworkBridge(
            role="client",
            host_url=url,
            name=cp.name(),
            color=cp.color(),
        )
        self._bridge.my_slot_assigned.connect(self._on_my_slot_assigned)
        self._bridge.player_joined.connect(self._on_player_joined_client)
        self._bridge.game_started.connect(self._on_client_game_started)
        self._bridge.error_received.connect(self._on_bridge_error)
        self._bridge.map_received.connect(self._on_map_received)
        self._bridge.start()

        cp.set_connected()
        self._pending_map_bytes: bytes | None = None
        self._pending_player_configs: list | None = None

    def _on_my_slot_assigned(self, slot: int) -> None:
        self._client_panel.set_status(f"Verbunden als Slot {slot + 1} — warte auf Host…")

    def _on_player_joined_client(self, slot: int, name: str, color: str) -> None:
        self._client_panel.update_slot(slot, name, color)

    def _on_map_received(self, data: bytes) -> None:
        self._pending_map_bytes = data
        self._maybe_start_client_game()

    def _on_client_game_started(self, player_configs: list) -> None:
        self._pending_player_configs = player_configs
        self._maybe_start_client_game()

    def _maybe_start_client_game(self) -> None:
        if self._pending_map_bytes and self._pending_player_configs:
            # Must set before emitting — slot runs synchronously in same thread
            self._bridge._pending_map_bytes = self._pending_map_bytes
            self.client_game_ready.emit(
                self._bridge,
                self._pending_player_configs,
            )

    def _on_bridge_error(self, msg: str) -> None:
        if self._stack.currentIndex() == _PAGE_CLIENT:
            self._client_panel.set_status(f"Error: {msg}", is_error=True)
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Netzwerkfehler", msg)

    def _on_back(self) -> None:
        if self._bridge is not None:
            self._bridge.stop()
            self._bridge = None
        self.back_clicked.emit()

    def reset(self) -> None:
        """Return to mode selection, clean up bridge."""
        if self._bridge:
            self._bridge.stop()
            self._bridge = None
        self._stack.setCurrentIndex(_PAGE_MODE)
        self._pending_map_bytes = None
        self._pending_player_configs = None

    def refresh_theme(self) -> None:
        self.setStyleSheet(f"background:{dt.S_PAPER};")
        self._header_widget.setStyleSheet(f"background:{dt.S_SURFACE};")
        self._scroll.setStyleSheet(f"background:{dt.S_PAPER};")
        self._body.setStyleSheet(f"background:{dt.S_PAPER};")
        self._center.setStyleSheet(f"background:{dt.S_PAPER};")

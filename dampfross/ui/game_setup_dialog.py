from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from ..game.state import PLAYER_COLORS, WIN_TARGETS

_SS_DLG  = "QDialog{background:#0e1a0e;color:#c0d0c0;}"
_SS_EDIT = ("QLineEdit{background:#1e2e1e;color:#c0d0c0;"
            "border:1px solid #2e4e2e;border-radius:3px;padding:3px 6px;}")
_SS_SPIN = ("QSpinBox{background:#1e2e1e;color:#c0d0c0;"
            "border:1px solid #2e4e2e;border-radius:3px;padding:3px 6px;}")
_SS_COMBO= ("QComboBox{background:#1e2e1e;color:#c0d0c0;"
            "border:1px solid #2e4e2e;border-radius:3px;padding:3px 8px;}"
            "QComboBox::drop-down{border:none;}"
            "QComboBox QAbstractItemView{background:#1e2e1e;color:#c0d0c0;}")
_SS_BTN  = ("QPushButton{background:#1e2e1e;color:#8ab88a;"
            "border:1px solid #2e4e2e;border-radius:4px;padding:5px 14px;}"
            "QPushButton:hover{background:#263a26;}")
_SS_LBL  = "color:#8ab88a;font-size:11px;background:transparent;"
_SS_SEP  = "border:none;background:#2a3a2a;max-height:1px;"


def _sep():
    f = QFrame(); f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(_SS_SEP); return f


class GameSetupDialog(QDialog):
    """
    Setup dialog: choose players (name + color), map file,
    starting capital, and win target.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dampfross — Neues Spiel")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setStyleSheet(_SS_DLG)
        self._map_path: Path | None = None
        self._player_rows: list = []
        self._build_ui()

    # ------------------------------------------------------------------ #

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setSpacing(10)

        # Title
        t = QLabel("Neues Spiel")
        t.setStyleSheet("font-size:17px;font-weight:bold;color:#a8d8a8;background:transparent;")
        outer.addWidget(t)
        outer.addWidget(_sep())

        # Map file row
        mf = QWidget(); ml = QHBoxLayout(mf); ml.setContentsMargins(0,0,0,0)
        ml.addWidget(QLabel("Spielkarte:"))
        self._map_lbl = QLabel("(keine gewählt)")
        self._map_lbl.setStyleSheet("color:#606860;background:transparent;")
        self._map_lbl.setMinimumWidth(200)
        ml.addWidget(self._map_lbl, 1)
        browse = QPushButton("Suchen…")
        browse.setStyleSheet(_SS_BTN)
        browse.clicked.connect(self._browse_map)
        ml.addWidget(browse)
        outer.addWidget(mf)
        outer.addWidget(_sep())

        # Player count
        pc_w = QWidget(); pc_l = QHBoxLayout(pc_w); pc_l.setContentsMargins(0,0,0,0)
        pc_l.addWidget(QLabel("Spieleranzahl:"))
        self._n_spin = QSpinBox()
        self._n_spin.setStyleSheet(_SS_SPIN)
        self._n_spin.setRange(2, 6); self._n_spin.setValue(3)
        self._n_spin.valueChanged.connect(self._rebuild_rows)
        pc_l.addWidget(self._n_spin); pc_l.addStretch()
        outer.addWidget(pc_w)

        # Player rows area
        self._rows_widget = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_widget)
        self._rows_layout.setContentsMargins(0,0,0,0)
        self._rows_layout.setSpacing(3)
        outer.addWidget(self._rows_widget)
        outer.addWidget(_sep())

        # Starting capital + win target
        form = QFormLayout(); form.setSpacing(6)

        self._capital = QSpinBox()
        self._capital.setStyleSheet(_SS_SPIN)
        self._capital.setRange(1, 999); self._capital.setValue(20)
        self._capital.setSuffix("  Einheiten")
        form.addRow("Startkapital:", self._capital)

        self._win_tgt = QSpinBox()
        self._win_tgt.setStyleSheet(_SS_SPIN)
        self._win_tgt.setRange(50, 999); self._win_tgt.setValue(250)
        self._win_tgt.setSuffix("  Einheiten")
        form.addRow("Gewinnziel:", self._win_tgt)

        outer.addLayout(form)
        self._n_spin.valueChanged.connect(self._update_win_target)

        # OK / Cancel
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.setStyleSheet(
            "QDialogButtonBox QPushButton{" + _SS_BTN[12:] +
            "QDialogButtonBox QPushButton:hover{background:#263a26;}"
        )
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        outer.addWidget(btns)

        self._rebuild_rows(self._n_spin.value())

    # ------------------------------------------------------------------ #

    def _browse_map(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Spielkarte öffnen", str(Path.home()),
            "DampfrossMap Dateien (*.dmpfmap)"
        )
        if path:
            self._map_path = Path(path)
            self._map_lbl.setText(Path(path).name)
            self._map_lbl.setStyleSheet("color:#a0d0a0;background:transparent;")

    def _rebuild_rows(self, count: int):
        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._player_rows.clear()

        hdr = QWidget(); hl = QHBoxLayout(hdr)
        hl.setContentsMargins(4, 1, 4, 1); hl.setSpacing(8)
        for txt, stretch in [("#", 0), ("Name", 1), ("Farbe", 0)]:
            l = QLabel(txt); l.setStyleSheet(_SS_LBL)
            hl.addWidget(l, stretch)
        self._rows_layout.addWidget(hdr)

        for i in range(count):
            row = QWidget()
            row.setStyleSheet("QWidget{background:#111e11;border-radius:3px;}")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(6, 4, 6, 4); rl.setSpacing(8)

            num = QLabel(str(i + 1))
            num.setFixedWidth(14)
            num.setStyleSheet("color:#607860;background:transparent;")
            rl.addWidget(num)

            name_e = QLineEdit(f"Spieler {i + 1}")
            name_e.setStyleSheet(_SS_EDIT); name_e.setMinimumWidth(140)
            rl.addWidget(name_e, 1)

            color_c = QComboBox()
            color_c.setStyleSheet(_SS_COMBO); color_c.setFixedWidth(110)
            for hx, label in PLAYER_COLORS:
                color_c.addItem(label, hx)
            color_c.setCurrentIndex(i % len(PLAYER_COLORS))
            rl.addWidget(color_c)

            self._rows_layout.addWidget(row)
            self._player_rows.append((name_e, color_c))

        self.adjustSize()

    def _update_win_target(self, count: int):
        self._win_tgt.setValue(WIN_TARGETS.get(count, 250))

    def _on_accept(self):
        if self._map_path is None:
            QMessageBox.warning(self, "Keine Karte",
                                "Bitte zuerst eine Spielkarte auswählen.")
            return
        self.accept()

    # ------------------------------------------------------------------ #
    # Result accessors                                                     #
    # ------------------------------------------------------------------ #

    def map_path(self) -> Path:
        return self._map_path

    def player_configs(self) -> list[dict]:
        return [
            {"name": ne.text().strip() or f"Spieler {i+1}",
             "color": cc.currentData()}
            for i, (ne, cc) in enumerate(self._player_rows)
        ]

    def starting_capital(self) -> int:
        return self._capital.value()

    def win_target(self) -> int:
        return self._win_tgt.value()

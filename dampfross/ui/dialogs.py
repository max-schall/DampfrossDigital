import random

from PyQt6.QtCore import Qt, QPointF, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


from ..core.grid_builder import DEFAULT_GRID_W, DEFAULT_GRID_H


# ── Dice animation ─────────────────────────────────────────────────────────── #

_TL = (0.27, 0.27)
_TR = (0.73, 0.27)
_ML = (0.27, 0.50)
_MR = (0.73, 0.50)
_BL = (0.27, 0.73)
_BR = (0.73, 0.73)
_CC = (0.50, 0.50)

_DOT_POSITIONS: dict[int, list] = {
    1: [_CC],
    2: [_TR, _BL],
    3: [_TR, _CC, _BL],
    4: [_TL, _TR, _BL, _BR],
    5: [_TL, _TR, _CC, _BL, _BR],
    6: [_TL, _ML, _BL, _TR, _MR, _BR],
}

# Milliseconds between animation frames (fast → slow)
_ROLL_FRAMES = [30, 30, 35, 35, 40, 48, 58, 72, 92, 118, 152, 195, 248]


class _DieWidget(QWidget):
    """Draws a single die face (value 1–6)."""

    def __init__(self, value: int = 1, bg: QColor | None = None, parent=None):
        super().__init__(parent)
        self._value = value
        self._bg = bg or QColor(0xFA, 0xF8, 0xF0)
        self.setFixedSize(84, 84)

    def set_value(self, v: int) -> None:
        self._value = max(1, min(6, v))
        self.update()

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        pad, r_px = 4, 11

        # Soft shadow
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(20, 23, 28, 30))
        p.drawRoundedRect(pad + 1, pad + 3, w - 2*pad, h - 2*pad, r_px, r_px)

        # Face
        p.setBrush(self._bg)
        p.drawRoundedRect(pad, pad, w - 2*pad, h - 2*pad, r_px, r_px)

        # Border
        p.setPen(QPen(QColor(0xCC, 0xC5, 0xB5), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(pad, pad, w - 2*pad, h - 2*pad, r_px, r_px)

        # Dots
        dot_r = w * 0.082
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0x1A, 0x1D, 0x24))
        inner_w = w - 2*pad
        inner_h = h - 2*pad
        for fx, fy in _DOT_POSITIONS.get(self._value, [_CC]):
            cx = pad + fx * inner_w
            cy = pad + fy * inner_h
            p.drawEllipse(QPointF(cx, cy), dot_r, dot_r)


class DiceRollDialog(QDialog):
    """
    Animated dice overlay.  Pass the final (d1, d2) values; the dialog
    tumbles through random faces then settles on the result.
    Call .exec() — it auto-closes 1.5 s after settling.
    """

    def __init__(self, d1: int, d2: int, label: str = "",
                 die1_bg: QColor | None = None,
                 die2_bg: QColor | None = None,
                 parent=None):
        super().__init__(parent)
        self._final = (d1, d2)
        self._frame = 0
        self._done  = False

        self.setModal(True)
        self.setWindowTitle("")
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._build_ui(label, die1_bg, die2_bg)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._tick)

        # reduce_motion: skip animation, show result instantly then auto-close
        import dampfross.ui.design_tokens as _dt
        if _dt.A_REDUCE_MOTION:
            self._die1.set_value(self._final[0])
            self._die2.set_value(self._final[1])
            self._sum_lbl.setText(f"= {self._final[0] + self._final[1]}")
            self._hint.setVisible(True)
            self._done = True
            QTimer.singleShot(800, self.accept)
        else:
            self._timer.start(_ROLL_FRAMES[0])

    # ------------------------------------------------------------------ #

    def _build_ui(self, label: str,
                  die1_bg: QColor | None, die2_bg: QColor | None) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)

        if label:
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                "color:#5a5f6a; font-size:12px; font-weight:600;"
                "background:transparent; letter-spacing:0.06em;"
                "text-transform:uppercase;"
            )
            root.addWidget(lbl)

        dice_row = QHBoxLayout()
        dice_row.setSpacing(20)
        dice_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._die1 = _DieWidget(random.randint(1, 6), bg=die1_bg)
        self._die2 = _DieWidget(random.randint(1, 6), bg=die2_bg)

        plus = QLabel("+")
        plus.setStyleSheet(
            "color:#8a8f99; font-size:22px; font-weight:300;"
            "background:transparent;"
        )
        dice_row.addWidget(self._die1)
        dice_row.addWidget(plus)
        dice_row.addWidget(self._die2)
        root.addLayout(dice_row)

        self._sum_lbl = QLabel("")
        self._sum_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sum_lbl.setStyleSheet(
            "color:#14171c; font-size:32px; font-weight:700;"
            "background:transparent;"
        )
        root.addWidget(self._sum_lbl)

        self._hint = QLabel("Klicken zum Fortfahren")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setStyleSheet(
            "color:#b9bcc3; font-size:11px; background:transparent;"
        )
        self._hint.setVisible(False)
        root.addWidget(self._hint)

        self.adjustSize()

    def _tick(self) -> None:
        self._frame += 1
        if self._frame >= len(_ROLL_FRAMES):
            self._die1.set_value(self._final[0])
            self._die2.set_value(self._final[1])
            self._sum_lbl.setText(f"= {self._final[0] + self._final[1]}")
            self._hint.setVisible(True)
            self._done = True
            QTimer.singleShot(1500, self.accept)
        else:
            self._die1.set_value(random.randint(1, 6))
            self._die2.set_value(random.randint(1, 6))
            self._timer.start(_ROLL_FRAMES[self._frame])

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self._done:
            self._timer.stop()
            self.accept()
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(6, 6, -6, -6)

        # Drop shadow
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(20, 23, 28, 50))
        p.drawRoundedRect(rect.adjusted(0, 4, 2, 4), 18, 18)

        # Card
        p.setBrush(QColor(0xFA, 0xF8, 0xF2))
        p.setPen(QPen(QColor(0xE2, 0xDF, 0xD7), 1.5))
        p.drawRoundedRect(rect, 18, 18)


class _SuggestWorker(QThread):
    """Fetch region geometry and emit a suggested (grid_w, grid_h) pair."""
    suggested      = pyqtSignal(int, int)
    geom_ready     = pyqtSignal(object)   # emits the shapely geometry for caching
    failed         = pyqtSignal()

    def __init__(self, query: str, target_land: int = 850):
        super().__init__()
        self._query       = query
        self._target_land = target_land

    def run(self):
        try:
            from ..core.region_fetcher import RegionFetcher
            from ..core.grid_builder import suggest_grid_size
            geom, _ = RegionFetcher().fetch(self._query)
            self.geom_ready.emit(geom)
            w, h = suggest_grid_size(geom, self._target_land)
            self.suggested.emit(w, h)
        except Exception:
            import traceback
            traceback.print_exc()
            self.failed.emit()


class LoadRegionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Region laden")
        self.setModal(True)
        self.setFixedSize(420, 250)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setSpacing(10)

        self._edit = QLineEdit()
        self._edit.setPlaceholderText("z.B.  Deutschland,  Bayern,  New York City")
        self._edit.returnPressed.connect(self._accept_if_nonempty)
        self._edit.editingFinished.connect(self._start_suggestion)
        form.addRow("Region:", self._edit)

        self._spin_target = QSpinBox()
        self._spin_target.setRange(50, 10_000)
        self._spin_target.setValue(850)
        self._spin_target.setSingleStep(50)
        self._spin_target.setSuffix("  Landfelder")
        form.addRow("Zielgröße:", self._spin_target)

        self._spin_w = QSpinBox()
        self._spin_w.setRange(10, 4000)
        self._spin_w.setValue(DEFAULT_GRID_W)
        self._spin_w.setSuffix("  Felder")
        form.addRow("Max. Breite:", self._spin_w)

        self._spin_h = QSpinBox()
        self._spin_h.setRange(10, 4000)
        self._spin_h.setValue(DEFAULT_GRID_H)
        self._spin_h.setSuffix("  Felder")
        form.addRow("Max. Höhe:", self._spin_h)

        self._hint = QLabel("")
        self._hint.setStyleSheet("color: #708070; font-size: 11px;")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignRight)
        form.addRow("", self._hint)

        layout.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._accept_if_nonempty)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._worker: _SuggestWorker | None = None
        self._cached_geom = None   # shapely geometry from last successful fetch
        self._suggestion_applied = False
        self._user_overrode = False

        # Manual spin changes mark the user as having overridden the auto-values.
        self._spin_w.valueChanged.connect(self._on_manual_spin)
        self._spin_h.valueChanged.connect(self._on_manual_spin)
        # Target changes recalculate immediately from the cached geometry.
        self._spin_target.valueChanged.connect(self._on_target_changed)

    # ------------------------------------------------------------------

    def _on_manual_spin(self):
        if self._suggestion_applied:
            self._user_overrode = True
            self._hint.setText("(manuell)")

    def _on_target_changed(self, target: int):
        """Recalculate width/height from cached geometry when target changes."""
        if self._cached_geom is None:
            return
        from ..core.grid_builder import suggest_grid_size
        w, h = suggest_grid_size(self._cached_geom, target)
        self._user_overrode = False   # target change resets the manual override
        self._apply_suggestion(w, h)

    def _start_suggestion(self):
        query = self._edit.text().strip()
        if not query:
            return
        if self._worker and self._worker.isRunning():
            self._worker.suggested.disconnect()
            self._worker.geom_ready.disconnect()
            self._worker.failed.disconnect()
            self._worker.quit()

        self._suggestion_applied = False
        self._user_overrode = False
        self._hint.setText("Rastergröße berechnen…")
        self._worker = _SuggestWorker(query, self._spin_target.value())
        self._worker.geom_ready.connect(self._on_geom_ready)
        self._worker.suggested.connect(self._apply_suggestion)
        self._worker.failed.connect(self._on_suggestion_failed)
        self._worker.start()

    def _on_geom_ready(self, geom):
        self._cached_geom = geom

    def _apply_suggestion(self, w: int, h: int):
        if not self.isVisible() or self._user_overrode:
            return
        for spin in (self._spin_w, self._spin_h):
            spin.blockSignals(True)
        self._spin_w.setValue(w)
        self._spin_h.setValue(h)
        for spin in (self._spin_w, self._spin_h):
            spin.blockSignals(False)
        self._suggestion_applied = True
        target = self._spin_target.value()
        self._hint.setText(f"auto-vorgeschlagen für ≈{target} Landfelder  ({w} × {h})")

    def _on_suggestion_failed(self):
        if self.isVisible():
            self._hint.setText("")

    # ------------------------------------------------------------------

    def _accept_if_nonempty(self):
        if self._edit.text().strip():
            self.accept()

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(500)
        super().closeEvent(event)

    def region_name(self) -> str:
        return self._edit.text().strip()

    def grid_size(self) -> tuple[int, int]:
        return self._spin_w.value(), self._spin_h.value()


class CityEditDialog(QDialog):
    """Place a new city or rename / delete an existing one."""

    def __init__(self, city_name: str, is_new: bool = False, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Stadt platzieren" if is_new else "Stadt bearbeiten")
        self.setModal(True)
        self.setFixedSize(280, 110)
        self._deleted = False

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._edit = QLineEdit(city_name)
        self._edit.selectAll()
        self._edit.returnPressed.connect(self.accept)
        form.addRow("Name:", self._edit)
        layout.addLayout(form)

        btns = QDialogButtonBox()
        ok = btns.addButton("Platzieren" if is_new else "Umbenennen",
                            QDialogButtonBox.ButtonRole.AcceptRole)
        ok.clicked.connect(self.accept)
        if not is_new:
            d = btns.addButton("Stadt löschen",
                               QDialogButtonBox.ButtonRole.DestructiveRole)
            d.clicked.connect(self._on_delete)
        btns.addButton(QDialogButtonBox.StandardButton.Cancel).clicked.connect(self.reject)
        layout.addWidget(btns)

    def _on_delete(self):
        self._deleted = True
        self.accept()

    def city_name(self) -> str:
        return self._edit.text().strip()

    def was_deleted(self) -> bool:
        return self._deleted


class ProgressDialog(QDialog):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(400, 110)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint
        )

        layout = QVBoxLayout(self)

        self._label = QLabel("Initialisierung…")
        layout.addWidget(self._label)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        layout.addWidget(self._bar)

    def update_progress(self, pct: int, msg: str) -> None:
        self._label.setText(msg)
        self._bar.setValue(pct)

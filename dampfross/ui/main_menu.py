"""
Title screen / main menu — matches TitleScreen from screens.jsx.
Layout: 2-col (branding left + map preview right), border divider.
"""
from __future__ import annotations
import pathlib
import random
import threading

from PyQt6.QtCore import Qt, QElapsedTimer, QPointF, QRect, QRectF, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import (
    QColor, QFont, QPainter, QPen, QPixmap,
)
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget,
)

import dampfross.ui.design_tokens as dt
from dampfross.game.state import PLAYER_COLORS


# ── Logo mark ────────────────────────────────────────────────────────────#

class _LogoMark(QWidget):
    """
    Black disc · white hub · black pinion · 8 coloured spokes.

    Geometry (all radii as fraction of half-size):
      outer disc  : 0.92
      white hub   : 0.36
      black pinion: 0.18
      spoke start : 0.50  (gap after hub)
      spoke end   : 0.75  (gap before outer edge)
    """

    _COLORS = [hx for hx, _ in PLAYER_COLORS]  # 8 player colours, order preserved

    def __init__(self, size: int = 28, parent=None):
        super().__init__(parent)
        self._sz = size
        self.setFixedSize(size, size)

    def paintEvent(self, _) -> None:
        import math
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = cy = self._sz / 2.0
        r_outer  = cx * 0.92
        r_white  = cx * 0.36
        r_pinion = cx * 0.18
        r0_spoke = cx * 0.50   # inner end of each spoke
        r1_spoke = cx * 0.75   # outer end of each spoke
        w_spoke  = cx * 0.13   # stroke width

        # Outer black disc
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#111111"))
        p.drawEllipse(QRectF(cx - r_outer, cy - r_outer, r_outer * 2, r_outer * 2))

        # 8 coloured spokes — start at 0° (right), step 45° clockwise
        pen = QPen()
        pen.setStyle(Qt.PenStyle.SolidLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setWidthF(w_spoke)
        for i, color in enumerate(self._COLORS):
            angle = math.radians(i * 45.0)
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            pen.setColor(QColor(color))
            p.setPen(pen)
            p.drawLine(
                QPointF(cx + r0_spoke * cos_a, cy + r0_spoke * sin_a),
                QPointF(cx + r1_spoke * cos_a, cy + r1_spoke * sin_a),
            )

        # White hub
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(QRectF(cx - r_white, cy - r_white, r_white * 2, r_white * 2))

        # Black pinion (centre dot)
        p.setBrush(QColor("#111111"))
        p.drawEllipse(QRectF(cx - r_pinion, cy - r_pinion, r_pinion * 2, r_pinion * 2))

        p.end()


# ── Shared button styles ─────────────────────────────────────────────────#

def _btn_primary() -> str:
    return (
        f"QPushButton {{"
        f"  background:{dt.S_INK}; color:{dt.S_SURFACE}; border:none;"
        f"  border-radius:24px; font-size:15px; font-weight:600;"
        f"  letter-spacing:-0.005em; padding:0 26px; min-width:180px;"
        f"}}"
        f"QPushButton:hover {{ background:{dt.S_INK_1}; }}"
        f"QPushButton:pressed {{ background:{dt.S_INK_2}; }}"
    )


def _btn_secondary() -> str:
    return (
        f"QPushButton {{"
        f"  background:{dt.S_INK_1}; color:#ffffff; border:none;"
        f"  border-radius:24px; font-size:15px; font-weight:600;"
        f"  letter-spacing:-0.005em; padding:0 26px; min-width:180px;"
        f"}}"
        f"QPushButton:hover {{ background:{dt.S_INK}; }}"
        f"QPushButton:pressed {{ background:#000000; }}"
    )


def _btn_ghost() -> str:
    return (
        f"QPushButton {{"
        f"  background:transparent; color:{dt.S_INK_2}; border:none;"
        f"  border-radius:16px; font-size:13px; font-weight:500;"
        f"  padding:0 14px; min-width:80px;"
        f"}}"
        f"QPushButton:hover {{ background:{dt.S_SUNK}; color:{dt.S_INK_1}; }}"
    )


def _btn_danger() -> str:
    return (
        f"QPushButton {{"
        f"  background:{dt.S_DANGER}; color:#ffffff; border:none;"
        f"  border-radius:24px; font-size:15px; font-weight:600;"
        f"  letter-spacing:-0.005em; padding:0 26px; min-width:180px;"
        f"}}"
        f"QPushButton:hover {{ background:#c52d2d; }}"
        f"QPushButton:pressed {{ background:#a82626; }}"
    )


# ── Main widget ──────────────────────────────────────────────────────────#

class MainMenuWidget(QWidget):
    new_game_clicked     = pyqtSignal()
    load_region_clicked  = pyqtSignal()
    open_map_clicked     = pyqtSignal()
    play_clicked         = pyqtSignal()   # kept for compat (= new_game)
    multiplayer_clicked  = pyqtSignal()
    options_clicked      = pyqtSignal()
    exit_clicked         = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{dt.S_PAPER};")
        self._build_ui()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._branding = _BrandingColumn(self)
        self._branding.new_game_clicked.connect(self.new_game_clicked)
        self._branding.new_game_clicked.connect(self.play_clicked)   # alias
        self._branding.load_region_clicked.connect(self.load_region_clicked)
        self._branding.open_map_clicked.connect(self.open_map_clicked)
        self._branding.multiplayer_clicked.connect(self.multiplayer_clicked)
        self._branding.options_clicked.connect(self.options_clicked)
        self._branding.exit_clicked.connect(self.exit_clicked)
        root.addWidget(self._branding)  # fixed width — never shrinks

        div = QFrame()
        div.setFixedWidth(1)
        div.setStyleSheet(f"background:{dt.S_RULE};")
        root.addWidget(div)

        self._right = _PreviewColumn(self)
        root.addWidget(self._right, stretch=1)  # absorbs all remaining space

    def set_preview_grid(self, grid) -> None:
        """Pass a loaded HexGrid to show on the right panel map preview."""
        self._right.set_grid(grid)

    def refresh_theme(self) -> None:
        self.setStyleSheet(f"background:{dt.S_PAPER};")
        self._branding.refresh_theme()


class _BrandingColumn(QWidget):
    new_game_clicked    = pyqtSignal()
    load_region_clicked = pyqtSignal()
    open_map_clicked    = pyqtSignal()
    multiplayer_clicked = pyqtSignal()
    options_clicked     = pyqtSignal()
    exit_clicked        = pyqtSignal()

    def paintEvent(self, event) -> None:
        """Fill the panel before any child is drawn — bypasses system theme."""
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(dt.S_PAPER))
        p.end()
        super().paintEvent(event)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{dt.S_PAPER};")
        self.setFixedWidth(580)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 48, 56, 40)
        layout.setSpacing(0)

        # ── Logo row (fills full width) ──────────────────────────────────── #
        logo_row = QHBoxLayout()
        logo_row.setSpacing(0)

        logo_mark = _LogoMark(54, self)
        logo_row.addWidget(logo_mark,
                           alignment=Qt.AlignmentFlag.AlignVCenter)
        logo_row.addSpacing(14)

        self._logo_lbl = QLabel("DampfrossDigital")
        self._logo_lbl.setFont(dt.font_display(36, 700))
        self._logo_lbl.setFixedHeight(54)
        self._logo_lbl.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")
        self._logo_lbl.setSizePolicy(QSizePolicy.Policy.Expanding,
                                     QSizePolicy.Policy.Fixed)
        logo_row.addWidget(self._logo_lbl,
                           alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(logo_row)

        layout.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

        # ── Display headline ─────────────────────────────────────────────── #
        self._headline_lbl = QLabel("Lay the lines.\nRace the rails.")
        self._headline_lbl.setFont(dt.font_display(52, 600))
        self._headline_lbl.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")
        self._headline_lbl.setWordWrap(False)
        layout.addWidget(self._headline_lbl)

        layout.addSpacing(28)

        # ── Buttons ──────────────────────────────────────────────────────── #
        self._btn_styles: list = []
        for text, style_fn, signal in [
            ("Lokales Spiel",        _btn_primary,    self.new_game_clicked),
            ("Online Spiel",         _btn_primary,    self.multiplayer_clicked),
            ("Karte erstellen",      _btn_secondary,  self.load_region_clicked),
            ("Kartendatei öffnen…",  _btn_secondary,  self.open_map_clicked),
            ("Optionen",             _btn_secondary,  self.options_clicked),
            ("Beenden",              _btn_danger,     self.exit_clicked),
        ]:
            btn = QPushButton(text)
            btn.setFont(dt.font_display(15))
            btn.setStyleSheet(style_fn())
            btn.setFixedHeight(48)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(signal)
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignLeft)
            layout.addSpacing(10)
            self._btn_styles.append((btn, style_fn))

        layout.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

        # ── Version (plain, bottom) ──────────────────────────────────────── #
        self._version_lbl = QLabel("v0.1 · alpha")
        self._version_lbl.setFont(dt.font_mono(10))
        self._version_lbl.setStyleSheet(f"color:{dt.S_INK_3}; background:transparent;")
        layout.addWidget(self._version_lbl)

    def refresh_theme(self) -> None:
        self.setStyleSheet(f"background:{dt.S_PAPER};")
        self.update()
        self._logo_lbl.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")
        self._headline_lbl.setStyleSheet(f"color:{dt.S_INK}; background:transparent;")
        self._version_lbl.setStyleSheet(f"color:{dt.S_INK_3}; background:transparent;")
        for btn, style_fn in self._btn_styles:
            btn.setStyleSheet(style_fn())


class _PreviewColumn(QWidget):
    """Right side — animated map showreel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._showreel = _MapShowreel(self)
        layout.addWidget(self._showreel)

    def set_grid(self, _grid) -> None:
        pass  # showreel manages its own slides


class _MapShowreel(QWidget):
    """
    Slow-panning Ken Burns slideshow of hex-map overviews with cross-fades.

    Maps are loaded from the maps/ directory in a background thread.
    QPixmap creation happens on the main thread (polled via QTimer).
    """

    _TICK_MS    = 16      # ~60 fps repaint trigger
    _DISPLAY_MS = 10_000  # ms each slide is shown (including fade-out start)
    _FADE_MS    = 2_000   # ms for cross-fade between slides
    _CROP_FRAC  = 0.65    # fraction of source shown per axis (lower = more zoom)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)

        self._slides: list[QPixmap] = []
        # Per-slide pan trajectory: (x0, y0, x1, y1) in [0, 1] pan-range fractions
        self._pan_dirs: list[tuple[float, float, float, float]] = []

        # Animation timing: all position is computed from the wall clock at
        # paint time — no accumulated state that can drift between timer ticks.
        self._clock = QElapsedTimer()
        self._clock.start()
        self._anim_start_ms: int = 0   # clock value when animation began

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(self._TICK_MS)
        self._anim_timer.timeout.connect(self.update)  # just trigger repaint

        # Grids loaded by the worker thread, consumed on the main thread.
        self._pending_grids: list = []
        self._lock = threading.Lock()

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(250)
        self._poll_timer.timeout.connect(self._consume_pending)
        self._poll_timer.start()

        threading.Thread(target=self._load_worker, daemon=True).start()

    # ── background loading ──────────────────────────────────────────────── #

    def _load_worker(self) -> None:
        maps_dir = pathlib.Path(__file__).parent.parent.parent / "maps"
        paths = [p for p in maps_dir.glob("*.dmpfmap")
                 if p.stem.lower() != "test"]
        random.shuffle(paths)
        from ..core.map_file import load_map
        for path in paths:
            try:
                grid = load_map(path)
                with self._lock:
                    self._pending_grids.append(grid)
            except Exception:
                pass

    def _consume_pending(self) -> None:
        """Pick up any grids the worker has finished loading and make slides."""
        with self._lock:
            grids = self._pending_grids[:]
            self._pending_grids.clear()

        for grid in grids:
            pix = self._render_slide(grid)
            if pix is not None and not pix.isNull():
                self._add_slide(pix)

        if self._slides and not self._anim_timer.isActive():
            self._anim_start_ms = self._clock.elapsed()
            self._anim_timer.start()

    @staticmethod
    def _make_example_tracks(grid) -> list:
        """
        Generate 3 realistic hub-and-spoke player networks for the showreel.

        Each player picks a hub city then Dijkstra-routes (terrain-cost weighted)
        to 2–3 additional cities, building tracks incrementally from the growing
        network — just like a real player would.
        """
        import heapq
        import random as _rnd
        from ..core.hex_grid import _NBRS_ODD, _NBRS_EVEN

        COLORS = ["#e23b3b", "#1f6fd9", "#1f7a4a"]  # P1 red, P2 blue, P3 green
        cities = list(grid.cities)
        if len(cities) < 4:
            return []

        rng = _rnd.Random(grid.cells.shape[0] * 997 + grid.cells.shape[1])
        is_mtn = grid.is_mountainous

        def is_land(r, c):
            if not grid.is_valid(r, c):
                return False
            return bool(grid.cells[r, c] or
                        (grid.other_land is not None and grid.other_land[r, c]))

        def edge_cost(r, c, nr, nc) -> int:
            # Terrain cost only — skips the expensive river-segment intersection
            # check (acceptable approximation for a showreel render).
            m1 = is_mtn is not None and is_mtn[r, c]
            m2 = is_mtn is not None and is_mtn[nr, nc]
            if m1 and m2:  return 5
            if m1 or m2:   return 3
            return 1

        def dijkstra(starts: set, goal: tuple) -> list | None:
            """Terrain-cost Dijkstra with parent-dict reconstruction (no path in heap)."""
            dist:   dict = {s: 0 for s in starts}
            parent: dict = {s: None for s in starts}
            settled: set = set()
            counter = 0
            heap = [(0, counter, s) for s in starts]
            while heap:
                cost, _, node = heapq.heappop(heap)
                if node in settled:
                    continue
                settled.add(node)
                if node == goal:
                    path = []
                    cur: tuple | None = goal
                    while cur is not None:
                        path.append(cur)
                        cur = parent[cur]
                    path.reverse()
                    return path
                r, c = node
                for dr, dc in (_NBRS_ODD if r % 2 else _NBRS_EVEN):
                    nr, nc = r + dr, c + dc
                    nb = (nr, nc)
                    if nb in settled or not is_land(nr, nc):
                        continue
                    new_cost = cost + edge_cost(r, c, nr, nc)
                    if new_cost < dist.get(nb, float('inf')):
                        dist[nb] = new_cost
                        parent[nb] = node
                        counter += 1
                        heapq.heappush(heap, (new_cost, counter, nb))
            return None

        # Split map into thirds (left/centre/right) so players don't all start
        # in the same region.
        cols = grid.cells.shape[1]
        def col_band(city):
            return int(city["col"] * 3 / cols)

        by_band = [[], [], []]
        for c in cities:
            by_band[col_band(c)].append(c)
        for band in by_band:
            rng.shuffle(band)

        tracks = []
        used_hubs: set = set()
        for i, color in enumerate(COLORS):
            # Pick hub from the corresponding band (or any remaining city)
            band = by_band[i % 3]
            hub = None
            for candidate in band:
                rc = (candidate["row"], candidate["col"])
                if rc not in used_hubs:
                    hub = candidate
                    used_hubs.add(rc)
                    break
            if hub is None:
                continue

            hub_rc = (hub["row"], hub["col"])
            network_nodes: set = {hub_rc}
            edges: set = set()

            # Pick 2–3 target cities that are reasonably far from the hub
            targets = [c for c in cities
                       if (c["row"], c["col"]) not in used_hubs
                       and abs(c["row"] - hub["row"]) + abs(c["col"] - hub["col"]) > 4]
            rng.shuffle(targets)
            targets = targets[:rng.randint(2, 3)]

            for target in targets:
                trc = (target["row"], target["col"])
                # Route from the current network to the target city
                path = dijkstra(network_nodes, trc)
                if path:
                    for j in range(len(path) - 1):
                        edges.add(frozenset((path[j], path[j + 1])))
                    network_nodes.update(path)
                used_hubs.add(trc)

            if edges:
                tracks.append((color, edges))
        return tracks

    @staticmethod
    def _render_slide(grid) -> "QPixmap | None":
        """Render a supersampled (2×) hex-map screenshot with example tracks.

        Rendering at 2× then downsampling eliminates jagged hex-fill edges
        without touching _paint_polygons' internal AA toggle.
        """
        import math
        from .hex_map_widget import HexMapWidget
        if grid.cells.shape[0] < 6 or grid.cells.shape[1] < 6:
            return None

        RENDER_W, RENDER_H = 1600, 1200
        SS = 2                              # supersample for sub-pixel sharpness
        INT_W, INT_H = RENDER_W * SS, RENDER_H * SS
        SQRT3 = math.sqrt(3)
        rows, cols = grid.cells.shape

        # Cover hex_size at 2× internal resolution
        sw = INT_W / (cols * SQRT3)
        sh = INT_H / ((rows - 1) * 1.5 + 2.0)
        hex_size = max(sw, sh)

        widget = HexMapWidget()
        widget.set_grid(grid)
        widget._hex_size = hex_size
        widget._pan_x = 0.0
        widget._pan_y = 0.0
        fw = int(widget._grid_w()) + 1
        fh = int(widget._grid_h()) + 1
        widget._export_rect = QRect(0, 0, fw, fh)
        widget.set_player_tracks(_MapShowreel._make_example_tracks(grid))

        full_pix = QPixmap(fw, fh)
        painter = QPainter(full_pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        widget._paint_polygons(painter, aa_fills=True)
        painter.end()
        widget.deleteLater()

        # Crop centre INT_W×INT_H then downsample 2× → smooth supersampling
        ox = max(0, (fw - INT_W) // 2)
        oy = max(0, (fh - INT_H) // 2)
        cropped = full_pix.copy(ox, oy,
                                min(INT_W, fw - ox),
                                min(INT_H, fh - oy))
        return cropped.scaled(RENDER_W, RENDER_H,
                              Qt.AspectRatioMode.IgnoreAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)

    # ── slide management ────────────────────────────────────────────────── #

    def _add_slide(self, pix: QPixmap) -> None:
        # Start in safe central 50 % of the pan range; drift 10–15 % so the
        # movement is perceptible but never snaps to a map edge.
        x0 = random.uniform(0.25, 0.75)
        y0 = random.uniform(0.25, 0.75)
        dx = random.uniform(0.10, 0.15) * (1 if random.random() > 0.5 else -1)
        dy = random.uniform(0.10, 0.15) * (1 if random.random() > 0.5 else -1)
        x1 = max(0.15, min(0.85, x0 + dx))
        y1 = max(0.15, min(0.85, y0 + dy))
        self._slides.append(pix)
        self._pan_dirs.append((x0, y0, x1, y1))

    # ── painting ────────────────────────────────────────────────────────── #

    @staticmethod
    def _smoothstep(t: float) -> float:
        t = max(0.0, min(1.0, t))
        return t * t * (3.0 - 2.0 * t)

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        w, h = self.width(), self.height()

        if not self._slides:
            p.fillRect(self.rect(), QColor(dt.S_PAPER))
            return

        # reduce_motion or reduce_pan: show first slide at static centre, no animation
        if dt.A_REDUCE_MOTION or dt.A_REDUCE_PAN:
            self._draw_slide(p, 0, 0.5, w, h)
            return

        n = len(self._slides)
        total = self._DISPLAY_MS + self._FADE_MS

        elapsed = max(0, self._clock.elapsed() - self._anim_start_ms)
        slot    = elapsed // total
        t_ms    = elapsed - slot * total
        idx     = int(slot) % n
        next_idx = (idx + 1) % n

        # disable_blink: no cross-fade, hard-cut between slides
        if dt.A_DISABLE_BLINK:
            self._draw_slide(p, idx, self._smoothstep(
                min(1.0, t_ms / self._DISPLAY_MS)), w, h)
            return

        fade_t = 0.0
        if t_ms > self._DISPLAY_MS:
            fade_t = self._smoothstep(
                (t_ms - self._DISPLAY_MS) / self._FADE_MS
            )

        pan_t = self._smoothstep(min(1.0, t_ms / self._DISPLAY_MS))

        if fade_t < 1.0:
            p.setOpacity(1.0 - fade_t)
            self._draw_slide(p, idx, pan_t, w, h)

        if fade_t > 0.0 and n > 1:
            p.setOpacity(fade_t)
            self._draw_slide(p, next_idx, 0.0, w, h)

        p.setOpacity(1.0)

    def _draw_slide(self, p: QPainter, idx: int,
                    pan_t: float, w: int, h: int) -> None:
        pix = self._slides[idx]
        pw, ph = float(pix.width()), float(pix.height())
        if pw == 0 or ph == 0:
            return

        # Crop rect preserving widget aspect ratio — all floats for sub-pixel pan.
        widget_ar = w / h
        source_ar = pw / ph
        if source_ar > widget_ar:
            crop_h = ph * self._CROP_FRAC
            crop_w = crop_h * widget_ar
        else:
            crop_w = pw * self._CROP_FRAC
            crop_h = crop_w / widget_ar

        crop_w = max(1.0, min(crop_w, pw))
        crop_h = max(1.0, min(crop_h, ph))

        pan_range_x = pw - crop_w
        pan_range_y = ph - crop_h

        x0, y0, x1, y1 = self._pan_dirs[idx]
        fx = x0 + (x1 - x0) * pan_t
        fy = y0 + (y1 - y0) * pan_t

        # Float source rect → Qt bilinear-interpolates between source pixels,
        # giving truly smooth sub-pixel panning even at tiny movement rates.
        src = QRectF(fx * pan_range_x, fy * pan_range_y, crop_w, crop_h)
        dst = QRectF(0, 0, w, h)
        p.drawPixmap(dst, pix, src)


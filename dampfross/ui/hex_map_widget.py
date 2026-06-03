import functools
import math

import numpy as np
from PyQt6.QtCore import QPointF, QRect, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QFontMetricsF, QImage, QPainter, QPainterPath,
    QPen, QPixmap, QPolygonF,
)
from PyQt6.QtWidgets import QWidget

from ..core.hex_grid import HexGrid, SQRT3
from .design_tokens import (
    TERRAIN_PLAIN, TERRAIN_MOUNTAIN, TERRAIN_WATER,
    TERRAIN_FOREST, TERRAIN_DESERT, TERRAIN_SWAMP,
    RIVER, COAST,
    INK, INK_1, INK_2, INK_3, RULE, SUNK, PAPER, SURFACE,
)

# ── palette ──────────────────────────────────────────────────────────── #
_SEA        = TERRAIN_WATER
_LAND       = TERRAIN_PLAIN
_OTHER_LAND = QColor(232, 228, 218)   # slightly warmer grey for non-game land
_SELECTED   = QColor(232, 169,  21)   # amber accent (close to --p4)
_HOVER_LAND = QColor(242, 240, 228)
_HOVER_OTHER= QColor(218, 214, 204)
_BORDER_CLR = INK_2
_RIVER_CLR  = RIVER
_BG         = PAPER                       # warm paper background

_MOUNTAIN   = TERRAIN_MOUNTAIN
_FOREST     = TERRAIN_FOREST
_DESERT     = TERRAIN_DESERT
_SWAMP      = TERRAIN_SWAMP
_HILL       = (216, 206, 189)            # same as RGB tuple for overview
_CITY_RING       = QColor(226,  59,  59)      # --danger / --p1
_CITY_RING_START = QColor( 31, 122,  74)      # green — departure city
_CITY_RING_DEST  = QColor(220, 140,  10)      # amber — arrival city
_CITY_RING_DIM   = QColor(160, 155, 145, 90)  # greyed-out during journey
_CITY_OVW        = (180,  30,  30)
_CITY_NUM        = QColor( 20,  23,  28)      # --ink
_CITY_NUM_DIM    = QColor(160, 155, 145)
_CITY_SHAD       = QColor(255, 255, 255, 200)

_POLY_THRESH = 2.8
_MIN_HEX     = 0.25
_MAX_HEX     = 80.0

# Pre-darkened border colors (avoids QColor.darker() per hex per frame)
_LAND_BORDER   = _LAND.darker(135)
_MTN_BORDER    = _MOUNTAIN.darker(135)
_FOREST_BORDER = _FOREST.darker(130)
_DESERT_BORDER = _DESERT.darker(125)
_SWAMP_BORDER  = _SWAMP.darker(125)


def _refresh_module_colors() -> None:
    """Re-read all terrain/bg colors from the currently active design_tokens theme."""
    import dampfross.ui.design_tokens as _dt
    global _SEA, _LAND, _OTHER_LAND, _BG, _BORDER_CLR, _RIVER_CLR
    global _MOUNTAIN, _FOREST, _DESERT, _SWAMP
    global _LAND_BORDER, _MTN_BORDER, _FOREST_BORDER, _DESERT_BORDER, _SWAMP_BORDER
    global _HOVER_LAND, _HOVER_OTHER, _HILL
    global _CITY_NUM, _CITY_NUM_DIM

    _SEA        = _dt.TERRAIN_WATER
    _LAND       = _dt.TERRAIN_PLAIN
    _MOUNTAIN   = _dt.TERRAIN_MOUNTAIN
    _FOREST     = _dt.TERRAIN_FOREST
    _DESERT     = _dt.TERRAIN_DESERT
    _SWAMP      = _dt.TERRAIN_SWAMP
    _BG         = _dt.PAPER
    _BORDER_CLR = _dt.INK_2
    _RIVER_CLR  = _dt.RIVER

    _LAND_BORDER   = _LAND.darker(135)
    _MTN_BORDER    = _MOUNTAIN.darker(135)
    _FOREST_BORDER = _FOREST.darker(130)
    _DESERT_BORDER = _DESERT.darker(125)
    _SWAMP_BORDER  = _SWAMP.darker(125)

    _OTHER_LAND  = _dt.SUNK
    _HOVER_LAND  = _dt.TERRAIN_PLAIN.lighter(108)
    _HOVER_OTHER = _dt.SUNK.lighter(106)
    _HILL        = (_dt.TERRAIN_MOUNTAIN.red(),
                    _dt.TERRAIN_MOUNTAIN.green(),
                    _dt.TERRAIN_MOUNTAIN.blue())
    _CITY_NUM     = _dt.INK
    _CITY_NUM_DIM = _dt.INK_3

# Bucket indices for fill_paths / border_paths
_B_LAND    = 0
_B_MTN     = 1
_B_OTHER   = 2
_B_SEL     = 3
_B_FOREST  = 4
_B_DESERT  = 5
_B_SWAMP   = 6
_N_BUCKETS = 7


def _seg_dist(px: float, py: float,
              ax: float, ay: float, bx: float, by: float) -> float:
    """Distance from point (px,py) to segment (ax,ay)-(bx,by)."""
    dx, dy = bx - ax, by - ay
    d2 = dx * dx + dy * dy
    if d2 == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / d2))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


@functools.lru_cache(maxsize=64)
def _corner_offsets(s: float) -> tuple:
    """6 (dx, dy) corner offsets for a pointy-top hex of outer radius s, cached by size."""
    return tuple(
        (s * math.cos(math.radians(30 + 60 * i)),
         s * math.sin(math.radians(30 + 60 * i)))
        for i in range(6)
    )


class HexMapWidget(QWidget):
    hex_selected     = pyqtSignal(int, int, int)
    hex_painted      = pyqtSignal(int, int, str)   # row, col, brush
    corner_clicked   = pyqtSignal(int, int, int)   # row, col, corner_idx  (ferry mode)
    escape_pressed   = pyqtSignal()
    enter_pressed    = pyqtSignal()
    game_hex_clicked = pyqtSignal(int, int)        # row, col  (game build mode)
    ferry_line_clicked = pyqtSignal(int)           # ferry_idx (game build mode)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumSize(400, 300)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        from PyQt6.QtGui import QKeySequence, QShortcut
        _sc = QShortcut(QKeySequence("Ctrl+S"), self)
        _sc.activated.connect(self._save_screenshot)

        self.hex_grid: HexGrid | None = None
        self._overview: QPixmap | None = None

        self._hex_size = 1.0
        self._pan_x = 0.0
        self._pan_y = 0.0
        self._drag_origin = None
        self._drag_pan_start = (0.0, 0.0)
        self._hovered: tuple[int, int] | None = None

        # Paint mode
        self.paint_mode:   bool = False
        self.active_brush: str  = "plain"
        self._last_painted: tuple[int, int] | None = None

        # Ferry building mode
        self.ferry_mode: bool = False
        self._ferry_delete_mode: bool = False
        self._ferry_wip:      list         = []   # (row, col) hex-center waypoints
        self._ferry_hover_hex: tuple | None = None  # (row, col) hovered tile

        self._export_rect: QRect | None = None  # set during off-screen render

        # Base-layer pixmap cache: everything except the hover highlight.
        # Blitted on every frame; rebuilt only when structural state changes.
        self._base_pixmap: QPixmap | None = None
        self._base_gen:    int = 0   # bumped by _invalidate_base()
        self._cached_gen:  int = -1

        # Game mode
        self.game_mode: str | None = None    # "build" | None
        # list of (color_hex_str, set_of_frozenset_edges)
        self._player_tracks: list = []
        # (r,c) of the current build endpoint (pulsing highlight)
        self._build_endpoint: tuple | None = None
        # set of (r,c) hexes reachable/highlighted during game
        self._game_reachable: set = set()
        # list of (color_hex, (r,c)) for train position overlays
        self._train_positions: list = []
        # Pending (this-turn, dotted) edges for current player
        self._pending_color: str = ""
        self._pending_edges: set = set()
        self._pending_costs: dict = {}   # frozenset(edge) → int cost
        # Journey highlight: (row, col) of start/dest cities, or None
        self._journey_start: tuple | None = None
        self._journey_dest:  tuple | None = None
        # Ferry ownership: {ferry_idx: color_hex_str} for built ferries only
        self._ferry_owners: dict = {}
        # Route previews during route-select phase: [(route, color_hex, alpha), ...]
        self._route_previews: list = []
        # Route hover overlay: (route, color_hex, start_rc, end_rc) or None
        self._route_hover_data: tuple | None = None
        # Active ferry-crossing boat animation: {ferry_idx, t, color_hex} or None
        self._boat_anim: dict | None = None

        # Zoom / scroll prefs (updated by apply_prefs)
        self._zoom_enabled: bool  = True
        self._zoom_invert:  bool  = False
        self._zoom_factor:  float = 1.15

        # Overlay display prefs
        self._show_player_names: bool = True
        self._highlight_ferries: bool = True

    # ── cache control ───────────────────────────────────────────────── #

    def _invalidate_base(self) -> None:
        """Mark the base-layer cache as stale. Call whenever any static state changes."""
        self._base_gen += 1

    def _save_screenshot(self) -> None:
        import datetime
        import pathlib
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = pathlib.Path.home() / "dampfross_screenshots" / f"map_{ts}.png"
        path.parent.mkdir(exist_ok=True)
        self.grab().save(str(path))
        print(f"[screenshot] {path}")

    # ── public ──────────────────────────────────────────────────────── #

    def set_grid(self, grid: HexGrid) -> None:
        self.hex_grid = grid
        self._overview = _build_overview(grid)
        self._hovered = None
        self._invalidate_base()
        self.fit_to_view()

    def set_river_count(self, n: int) -> None:
        if self.hex_grid is not None:
            self.hex_grid.river_count = n
            self._invalidate_base()
            self.update()

    def fit_to_view(self) -> None:
        if self.hex_grid is None:
            return
        w, h = self.width(), self.height()
        sw = w * 0.94 / (self.hex_grid.cols * SQRT3)
        sh = h * 0.94 / ((self.hex_grid.rows - 1) * 1.5 + 2.0)
        self._hex_size = max(_MIN_HEX, min(sw, sh))
        self._pan_x = (w - self._grid_w()) / 2.0
        self._pan_y = (h - self._grid_h()) / 2.0
        self._invalidate_base()
        self.update()

    def set_paint_mode(self, enabled: bool) -> None:
        self.paint_mode = enabled
        self._last_painted = None
        self._update_cursor()

    def set_brush(self, brush: str) -> None:
        self.active_brush = brush

    def refresh_overview(self) -> None:
        if self.hex_grid is not None:
            self._overview = _build_overview(self.hex_grid)
            self._invalidate_base()

    def set_ferry_mode(self, enabled: bool) -> None:
        self.ferry_mode = enabled
        if not enabled:
            self._ferry_wip = []
            self._ferry_hover_hex = None
            self._ferry_delete_mode = False
        self._update_cursor()

    def set_ferry_delete_mode(self, enabled: bool) -> None:
        self._ferry_delete_mode = enabled
        if enabled:
            self._ferry_wip = []
            self._ferry_hover_hex = None
        self._update_cursor()
        self._invalidate_base()
        self.update()

    def set_ferry_wip(self, waypoints: list) -> None:
        self._ferry_wip = list(waypoints)
        self._invalidate_base()
        self.update()

    def _update_cursor(self) -> None:
        if self.ferry_mode or self.paint_mode or self.game_mode:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _corner_pos(self, row: int, col: int, ci: int) -> tuple[float, float]:
        """Screen position of corner ci of hex (row, col)."""
        ctr = self._to_screen(row, col)
        return HexGrid.hex_corners(ctr.x(), ctr.y(), self._hex_size)[ci]

    def _nearest_corner(self, sx: float, sy: float):
        """Return (row, col, corner_idx) of the nearest hex corner to screen (sx,sy)."""
        row, col = self._to_hex(sx, sy)
        if self.hex_grid is None or not self.hex_grid.is_valid(row, col):
            return None, None, None
        ctr = self._to_screen(row, col)
        corners = HexGrid.hex_corners(ctr.x(), ctr.y(), self._hex_size)
        ci = min(range(6), key=lambda i: math.hypot(corners[i][0] - sx, corners[i][1] - sy))
        return row, col, ci

    def _ferry_pts(self, wps: list) -> list[tuple[float, float]]:
        """Convert ferry waypoints to screen positions (all hex centers).
        Accepts both (r,c) and legacy (r,c,ci) tuples."""
        result = []
        for wp in wps:
            r, c = wp[0], wp[1]
            ctr = self._to_screen(r, c)
            result.append((ctr.x(), ctr.y()))
        return result

    def _ferry_hit_test(self, sx: float, sy: float) -> int:
        """Return ferry index if screen point (sx,sy) is close to a ferry line, else -1.

        Clicks within the endpoint land-tile interiors do not count: the first and
        last segments are shortened inward so only the over-water portion of the
        spline is a valid hit target.
        """
        g = self.hex_grid
        if g is None:
            return -1
        threshold  = max(7.0, self._hex_size * 0.44)
        # Exclude the portion of each endpoint segment that lies inside the land
        # hex — roughly the inner radius of the hex (≈ 0.866 * hex_size).
        land_margin = self._hex_size * 0.82

        for fidx, ferry in enumerate(getattr(g, "ferries", [])):
            wps = ferry.get("waypoints", [])
            if len(wps) < 2:
                continue
            pts = self._ferry_pts(wps)
            n = len(pts)
            for i in range(n - 1):
                ax, ay = pts[i]
                bx, by = pts[i + 1]

                # Shorten the start of the first segment away from the land hex
                if i == 0:
                    vx = pts[1][0] - pts[0][0]
                    vy = pts[1][1] - pts[0][1]
                    d  = math.hypot(vx, vy)
                    if d > land_margin:
                        ax = pts[0][0] + vx * (land_margin / d)
                        ay = pts[0][1] + vy * (land_margin / d)

                # Shorten the end of the last segment away from the land hex
                if i == n - 2:
                    vx = pts[-2][0] - pts[-1][0]
                    vy = pts[-2][1] - pts[-1][1]
                    d  = math.hypot(vx, vy)
                    if d > land_margin:
                        bx = pts[-1][0] + vx * (land_margin / d)
                        by = pts[-1][1] + vy * (land_margin / d)

                if _seg_dist(sx, sy, ax, ay, bx, by) <= threshold:
                    return fidx
        return -1

    def set_game_mode(self, mode: str | None) -> None:
        self.game_mode = mode
        self._update_cursor()
        self._invalidate_base()
        self.update()

    def set_player_tracks(self, tracks: list) -> None:
        """tracks = list of (color_hex_str, set_of_frozenset_edges)"""
        self._player_tracks = tracks
        self._invalidate_base()
        self.update()

    def set_build_endpoint(self, rc: tuple | None) -> None:
        self._build_endpoint = rc
        self._invalidate_base()
        self.update()

    def set_game_reachable(self, hexes: set) -> None:
        self._game_reachable = hexes
        self._invalidate_base()
        self.update()

    def set_train_positions(self, positions: list) -> None:
        """positions = list of (color_hex_str, (row, col))"""
        self._train_positions = positions
        self._invalidate_base()
        self.update()

    def set_pending_edges(self, color_hex: str, edges: set,
                          costs: dict | None = None) -> None:
        """Edges placed this turn — drawn dotted; cleared on turn end.
        costs: optional dict mapping frozenset(edge) → int build cost."""
        self._pending_color = color_hex
        self._pending_edges = edges
        self._pending_costs = costs or {}
        self._invalidate_base()
        self.update()

    def set_route_previews(self, previews: list) -> None:
        """previews: [(route: list[(r,c)], color_hex: str, alpha: int 0-255), ...]
        Pass [] to clear.  Drawn above terrain, below city labels."""
        self._route_previews = list(previews)
        self._invalidate_base()
        self.update()

    def set_route_hover_overlay(self, route: list, color_hex: str = "",
                                start_rc: tuple | None = None,
                                end_rc: tuple | None = None) -> None:
        """Show a dimming overlay with the hovered route + start/dest highlighted.
        Pass route=[] to clear.  Drawn in the hover layer (no base-cache rebuild)."""
        if route:
            self._route_hover_data = (route, color_hex, start_rc, end_rc)
        else:
            self._route_hover_data = None
        self.update()

    def set_ferry_owners(self, owners: dict) -> None:
        """owners: {ferry_idx: color_hex_str} for built ferries (absent = unbuilt)."""
        self._ferry_owners = {k: v for k, v in owners.items() if v is not None}
        self._invalidate_base()
        self.update()

    def set_boat_animation(self, ferry_idx: int, t: float, color_hex: str) -> None:
        """Set the active ferry-crossing boat at normalized position t (0–1)."""
        self._boat_anim = {"ferry_idx": ferry_idx, "t": t, "color_hex": color_hex}
        self._invalidate_base()
        self.update()

    def clear_boat_animation(self) -> None:
        self._boat_anim = None
        self._invalidate_base()
        self.update()

    def set_journey_highlight(self,
                              start_rc: tuple | None,
                              dest_rc:  tuple | None) -> None:
        """Highlight start/dest cities during a race; pass None to clear."""
        self._journey_start = start_rc
        self._journey_dest  = dest_rc
        self._invalidate_base()
        self.update()

    def render_for_export(self, target_hex_px: float = 40.0, crop_hexes: int = 1) -> QPixmap:
        """Render the map to an off-screen QPixmap and crop by crop_hexes on every side."""
        g = self.hex_grid
        if g is None:
            return QPixmap()

        old_size = self._hex_size
        old_px, old_py = self._pan_x, self._pan_y
        old_er  = self._export_rect
        old_hov = self._hovered
        old_sel = g.selected

        self._hex_size   = target_hex_px
        self._pan_x      = 0.0
        self._pan_y      = 0.0
        self._hovered    = None
        g.selected       = None

        full_w = int(self._grid_w()) + 1
        full_h = int(self._grid_h()) + 1
        self._export_rect = QRect(0, 0, full_w, full_h)

        pix = QPixmap(full_w, full_h)
        painter = QPainter(pix)
        self._paint_polygons(painter)
        painter.end()

        self._hex_size    = old_size
        self._pan_x, self._pan_y = old_px, old_py
        self._export_rect = old_er
        self._hovered     = old_hov
        g.selected        = old_sel

        if crop_hexes > 0:
            cx = int(crop_hexes * SQRT3 * target_hex_px)
            cy = int(crop_hexes * 1.5  * target_hex_px)
            w, h = full_w - 2 * cx, full_h - 2 * cy
            if w > 0 and h > 0:
                pix = pix.copy(cx, cy, w, h)

        return pix

    # ── coords ──────────────────────────────────────────────────────── #

    def _grid_w(self):
        return self.hex_grid.cols * self._hex_size * SQRT3 if self.hex_grid else 0.0

    def _grid_h(self):
        return ((self.hex_grid.rows - 1) * self._hex_size * 1.5 + self._hex_size * 2.0
                if self.hex_grid else 0.0)

    def _to_screen(self, row, col) -> QPointF:
        lx, ly = HexGrid.hex_center(row, col, self._hex_size)
        return QPointF(lx + self._pan_x, ly + self._pan_y)

    def _to_hex(self, sx, sy):
        return HexGrid.pixel_to_hex(sx - self._pan_x, sy - self._pan_y, self._hex_size)

    # ── paint ───────────────────────────────────────────────────────── #

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), _BG)
        if self.hex_grid is None:
            return
        if self._hex_size < _POLY_THRESH:
            self._paint_overview(p)
            return

        game_clip = None
        if self.game_mode:
            s = self._hex_size
            cx = SQRT3 * s
            cy = 1.5 * s
            game_clip = QRect(
                int(self._pan_x + cx), int(self._pan_y + cy),
                int(self._grid_w() - 2 * cx), int(self._grid_h() - 2 * cy),
            )

        # Rebuild base-layer cache if stale
        if self._base_gen != self._cached_gen:
            self._base_pixmap = self._build_base_cache()
            self._cached_gen  = self._base_gen

        # Cache is in screen space — blit at origin, not at pan offset
        if game_clip is not None:
            p.setClipRect(game_clip)
        p.drawPixmap(0, 0, self._base_pixmap)

        # Fast per-frame overlay: only the hovered hex + ferry WIP preview
        self._paint_hover_overlay(p, game_clip)
        p.setClipping(False)

    def _build_base_cache(self) -> QPixmap:
        """Render only the visible viewport into a same-sized, DPR-aware QPixmap.

        Blitting at (0,0) in screen space (not at pan offset) keeps it sharp at
        any zoom level and avoids building enormous off-screen pixmaps.
        """
        vw = max(1, self.width())
        vh = max(1, self.height())
        dpr = self.devicePixelRatioF()

        # Physical pixel dimensions so the pixmap is never upscaled on HiDPI.
        pix = QPixmap(int(vw * dpr), int(vh * dpr))
        pix.setDevicePixelRatio(dpr)
        pix.fill(Qt.GlobalColor.transparent)

        cp = QPainter(pix)
        cp.setRenderHint(QPainter.RenderHint.Antialiasing)
        # pan/zoom are already baked into _paint_polygons screen coordinates;
        # the resulting pixmap is in screen space and must be blitted at (0,0).
        self._paint_polygons(cp, game_clip=None)
        cp.end()
        return pix

    def _paint_hover_overlay(self, p: QPainter, game_clip) -> None:
        """Draw only the hovered hex and ferry WIP — called every frame, very fast."""
        g  = self.hex_grid
        s  = self._hex_size
        hov = self._hovered

        def _restore():
            if game_clip is not None:
                p.setClipRect(game_clip)
            else:
                p.setClipping(False)

        if hov is not None:
            hr, hc = hov
            if g.is_valid(hr, hc):
                is_region = bool(g.cells[hr, hc])
                colour = _HOVER_LAND if is_region else _HOVER_OTHER
                _restore()
                lx, ly = HexGrid.hex_center(hr, hc, s)
                cx, cy = lx + self._pan_x, ly + self._pan_y
                offsets = _corner_offsets(s)
                poly = QPolygonF([QPointF(cx + dx, cy + dy) for dx, dy in offsets])
                p.setPen(QPen(colour, 0.8))
                p.setBrush(QBrush(colour))
                p.drawPolygon(poly)

        # Game build mode — hover preview segment
        if (self.game_mode == "build" and self._build_endpoint is not None
                and hov is not None and hov in self._game_reachable):
            _restore()
            self._draw_build_preview(p, self._build_endpoint, hov)

        # Route hover: dimming overlay + highlighted route + city labels
        if self._route_hover_data is not None:
            _restore()
            self._draw_route_hover_overlay(p, game_clip)

        # Ferry WIP preview (position changes with hover corner snap)
        if self.ferry_mode and s >= _POLY_THRESH:
            _restore()
            self._draw_ferry_wip(p, s)

    def _paint_overview(self, p: QPainter) -> None:
        if self._overview is None:
            return
        gw, gh = self._grid_w(), self._grid_h()
        p.drawPixmap(int(self._pan_x), int(self._pan_y), int(gw), int(gh), self._overview)
        if self.hex_grid.selected is not None:
            row, col = self.hex_grid.selected
            sx = self._pan_x + col / self.hex_grid.cols * gw
            sy = self._pan_y + row / self.hex_grid.rows * gh
            pw = max(2.0, gw / self.hex_grid.cols)
            ph = max(2.0, gh / self.hex_grid.rows)
            p.fillRect(int(sx), int(sy), int(pw), int(ph), _SELECTED)

    def _paint_polygons(self, p: QPainter, game_clip: QRect | None = None,
                        vr_override: QRect | None = None,
                        aa_fills: bool = False) -> None:
        """
        Render the full base scene (no hover highlight).
        Called by _build_base_cache() with pan=0; also used by render_for_export.
        aa_fills=True keeps antialiasing on for hex fills (slower, but used for
        off-screen renders where quality matters more than frame time).
        """
        g = self.hex_grid
        s = self._hex_size

        def _restore_clip():
            if game_clip is not None:
                p.setClipRect(game_clip)
            else:
                p.setClipping(False)

        # Visible hex range (full grid when building the cache)
        if vr_override is not None:
            vr = vr_override
            rmin, rmax = 0, g.rows - 1
            cmin, cmax = 0, g.cols - 1
        else:
            vr = self._export_rect if self._export_rect is not None else self.rect()
            r0, c0 = self._to_hex(float(vr.left()),  float(vr.top()))
            r1, c1 = self._to_hex(float(vr.right()), float(vr.bottom()))
            rmin, rmax = max(0, r0 - 1), min(g.rows - 1, r1 + 1)
            cmin, cmax = max(0, c0 - 1), min(g.cols - 1, c1 + 1)

        if game_clip is not None:
            p.setClipRect(game_clip)

        # ── Step 1: sea background ────────────────────────────────────── #
        gw, gh = self._grid_w(), self._grid_h()
        p.fillRect(int(self._pan_x), int(self._pan_y), int(gw) + 1, int(gh) + 1, _SEA)

        # ── Step 1b: ferry lines (drawn under terrain so land tiles cover them) #
        ferries = getattr(g, "ferries", [])
        if ferries:
            self._draw_ferries(p, ferries, s)

        # ── Step 2: non-sea hexes — batched by color ──────────────────── #
        # One QPainterPath per color bucket; fill all at once, then stroke borders.
        offsets   = _corner_offsets(s)
        px, py    = self._pan_x, self._pan_y
        sel       = g.selected
        is_mtn    = g.is_mountainous
        other     = g.other_land
        t_over    = getattr(g, "terrain_overrides", {})

        fill_paths   = [QPainterPath() for _ in range(_N_BUCKETS)]
        border_paths = [QPainterPath() for _ in range(_N_BUCKETS)]
        # glyph_centers: list of (cx, cy, bucket) for drawing glyphs later
        glyph_centers: list[tuple[float, float, int]] = []

        for row in range(rmin, rmax + 1):
            row_cells = g.cells[row]
            row_other = other[row] if other is not None else None
            for col in range(cmin, cmax + 1):
                is_region = row_cells[col]
                is_other  = row_other is not None and row_other[col]
                if not is_region and not is_other:
                    continue

                if sel == (row, col):
                    bucket = _B_SEL
                elif is_region:
                    t = t_over.get((row, col))
                    if t == "forest":
                        bucket = _B_FOREST
                    elif t == "desert":
                        bucket = _B_DESERT
                    elif t == "swamp":
                        bucket = _B_SWAMP
                    elif is_mtn is not None and is_mtn[row, col]:
                        bucket = _B_MTN
                    else:
                        bucket = _B_LAND
                else:
                    bucket = _B_OTHER

                lx, ly = HexGrid.hex_center(row, col, s)
                cx, cy = lx + px, ly + py
                poly = QPolygonF([QPointF(cx + dx, cy + dy) for dx, dy in offsets])
                fill_paths[bucket].addPolygon(poly)
                fill_paths[bucket].closeSubpath()
                if bucket not in (_B_OTHER, _B_SEL):
                    border_paths[bucket].addPolygon(poly)
                    border_paths[bucket].closeSubpath()
                if bucket in (_B_MTN, _B_FOREST, _B_DESERT, _B_SWAMP) and s >= 8.0:
                    glyph_centers.append((cx, cy, bucket))

        # Fill pass — AA off by default: large flat polygons rarely need it and
        # antialiasing fillPath is ~13× slower. Caller may pass aa_fills=True
        # for off-screen renders where quality matters more than frame time.
        if not aa_fills:
            p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        p.setPen(Qt.PenStyle.NoPen)
        _FILL_COLORS = (
            _LAND, _MOUNTAIN, _OTHER_LAND, _SELECTED,
            _FOREST, _DESERT, _SWAMP,
        )
        for bucket, color in enumerate(_FILL_COLORS):
            path = fill_paths[bucket]
            if not path.isEmpty():
                p.fillPath(path, QBrush(color))

        # Border pass — AA on: thin 1px lines need AA to look clean
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setBrush(Qt.BrushStyle.NoBrush)
        _BORDER_COLORS = (
            _LAND_BORDER, _MTN_BORDER, None, None,
            _FOREST_BORDER, _DESERT_BORDER, _SWAMP_BORDER,
        )
        for bucket, pen_color in enumerate(_BORDER_COLORS):
            if pen_color is None:
                continue
            path = border_paths[bucket]
            if not path.isEmpty():
                p.setPen(QPen(pen_color, 1.0))
                p.drawPath(path)

        # ── Step 3: terrain glyphs ───────────────────────────────────── #
        if glyph_centers and s >= 8.0:
            self._draw_terrain_glyphs(p, glyph_centers, s)

        # ── Step 4: (rivers moved to step 6b — after city rings) ────────── #

        # ── Step 5: region border ─────────────────────────────────────── #
        if len(g.border_segs):
            lw = max(1.5, s * 0.42)
            p.setPen(QPen(_BORDER_CLR, lw, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.setBrush(Qt.BrushStyle.NoBrush)
            self._draw_segs(p, g.border_segs)

        # ── Step 6: city rings ────────────────────────────────────────────── #
        # Labels deferred to step 7b so they always render above ferry lines.
        city_labels: list = []   # [(cx, cy, number, name, dim)]
        if g.cities and s >= 4:
            journey_active = (self._journey_start is not None
                              or self._journey_dest is not None)
            lw_city = max(2.5, s * 0.45)
            lw_hi   = max(3.0, s * 0.55)
            p.setBrush(Qt.BrushStyle.NoBrush)
            for city in g.cities:
                cr, cc = city["row"], city["col"]
                if not (rmin <= cr <= rmax and cmin <= cc <= cmax):
                    continue
                lx, ly = HexGrid.hex_center(cr, cc, s)
                cx, cy = lx + px, ly + py
                poly = QPolygonF([QPointF(cx + dx, cy + dy) for dx, dy in offsets])

                is_start = (cr, cc) == self._journey_start
                is_dest  = (cr, cc) == self._journey_dest

                if is_start:
                    fill = QColor(_CITY_RING_START)
                    fill.setAlphaF(0.18)
                    p.setBrush(QBrush(fill))
                    p.setPen(QPen(_CITY_RING_START, lw_hi,
                                  Qt.PenStyle.SolidLine,
                                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                    p.drawPolygon(poly)
                    p.setBrush(Qt.BrushStyle.NoBrush)
                elif is_dest:
                    fill = QColor(_CITY_RING_DEST)
                    fill.setAlphaF(0.18)
                    p.setBrush(QBrush(fill))
                    p.setPen(QPen(_CITY_RING_DEST, lw_hi,
                                  Qt.PenStyle.SolidLine,
                                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                    p.drawPolygon(poly)
                    p.setBrush(Qt.BrushStyle.NoBrush)
                elif journey_active:
                    p.setPen(QPen(_CITY_RING_DIM, lw_city,
                                  Qt.PenStyle.SolidLine,
                                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                    p.drawPolygon(poly)
                else:
                    p.setPen(QPen(_CITY_RING, lw_city,
                                  Qt.PenStyle.SolidLine,
                                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                    p.drawPolygon(poly)

                if s >= 7:
                    dim = journey_active and not is_start and not is_dest
                    city_labels.append((cx, cy, city["number"], city["name"], dim))

        # ── Step 6b: rivers — drawn after city rings so they show through ── #
        if g.river_segs and g.river_count > 0:
            lw_riv = max(1.5, s * 0.38)
            p.setPen(QPen(_RIVER_CLR, lw_riv, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.setBrush(Qt.BrushStyle.NoBrush)
            n_show = min(g.river_count, len(g.river_segs))
            river_names = getattr(g, "river_names", [])
            for ri, pts in enumerate(g.river_segs[:n_show]):
                self._draw_river_polyline(p, pts)
                rname = river_names[ri] if ri < len(river_names) else ""
                if rname and s >= 10:
                    self._draw_river_name(p, pts, rname, s, px, py)

        # Step 7 intentionally empty — city labels deferred to step 13 so
        # they always render above tracks and trains.

        # (Step 8 — ferry WIP — moved to _paint_hover_overlay)

        # ── Step 8b: route previews (route-select phase) ─────────────── #
        if self._route_previews:
            _restore_clip()
            lw_prev = max(3.0, s * 0.32)
            for route, color_hex, alpha in self._route_previews:
                clr = QColor(color_hex)
                clr.setAlpha(alpha)
                pen = QPen(clr, lw_prev, Qt.PenStyle.SolidLine,
                           Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                for i in range(len(route) - 1):
                    lx1, ly1 = HexGrid.hex_center(route[i][0],   route[i][1],   s)
                    lx2, ly2 = HexGrid.hex_center(route[i+1][0], route[i+1][1], s)
                    p.drawLine(QPointF(lx1 + px, ly1 + py), QPointF(lx2 + px, ly2 + py))

        # ── Step 9: game — reachable hex highlight ────────────────────── #
        if self._game_reachable:
            _restore_clip()
            hi_brush = QBrush(QColor(255, 255, 120, 55))
            hi_path  = QPainterPath()
            for (hr, hc) in self._game_reachable:
                if not (rmin <= hr <= rmax and cmin <= hc <= cmax):
                    continue
                lx, ly = HexGrid.hex_center(hr, hc, s)
                cx, cy = lx + px, ly + py
                poly = QPolygonF([QPointF(cx + dx, cy + dy) for dx, dy in offsets])
                hi_path.addPolygon(poly)
                hi_path.closeSubpath()
            if not hi_path.isEmpty():
                p.setPen(Qt.PenStyle.NoPen)
                p.fillPath(hi_path, hi_brush)

        # ── Step 10: game — player tracks ─────────────────────────────── #
        if self._player_tracks:
            _restore_clip()
            self._draw_player_tracks(p, s)

        # ── Step 11: game — build endpoint ring ──────────────────────── #
        if self._build_endpoint is not None:
            _restore_clip()
            er, ec = self._build_endpoint
            lx, ly = HexGrid.hex_center(er, ec, s)
            cx, cy = lx + px, ly + py
            r_ring = max(4.0, s * 0.55)
            p.setPen(QPen(QColor(255, 230, 80, 220), max(2.0, s * 0.18)))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), r_ring, r_ring)

        # ── Step 12: game — train position circles ────────────────────── #
        if self._train_positions:
            _restore_clip()
            self._draw_trains(p, s)

        # ── Step 12b: ferry-crossing boat animation ────────────────────── #
        if self._boat_anim is not None:
            _restore_clip()
            self._draw_ferry_boat(p, s)

        # ── Step 13: city labels — always above tracks and trains ─────── #
        if city_labels:
            _restore_clip()
            for cx, cy, num, name, dim in city_labels:
                self._draw_city_label(p, cx, cy, s, num, name, dimmed=dim)

    # ── route hover overlay ───────────────────────────────────────── #

    def _draw_route_hover_overlay(self, p: QPainter, game_clip) -> None:
        """Grey-dim the whole map, then draw the hovered route + start/dest on top."""
        if self._route_hover_data is None:
            return
        route, color_hex, start_rc, end_rc = self._route_hover_data
        g = self.hex_grid
        if g is None:
            return
        s   = self._hex_size
        px  = self._pan_x
        py  = self._pan_y
        gw  = self._grid_w()
        gh  = self._grid_h()
        offsets = _corner_offsets(s)

        if game_clip is not None:
            p.setClipRect(game_clip)
        else:
            p.setClipping(False)

        # Semi-transparent dark overlay over the entire map grid
        p.fillRect(int(px), int(py), int(gw) + 1, int(gh) + 1,
                   QColor(20, 20, 20, 155))

        # Route line in player colour
        if route and len(route) >= 2:
            lw = max(4.0, s * 0.42)
            clr = QColor(color_hex)
            clr.setAlpha(235)
            p.setPen(QPen(clr, lw, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.setBrush(Qt.BrushStyle.NoBrush)
            for i in range(len(route) - 1):
                lx1, ly1 = HexGrid.hex_center(route[i][0],   route[i][1],   s)
                lx2, ly2 = HexGrid.hex_center(route[i+1][0], route[i+1][1], s)
                p.drawLine(QPointF(lx1 + px, ly1 + py), QPointF(lx2 + px, ly2 + py))

        # Start and dest city hexes highlighted above the dimming layer
        lw_hi = max(3.0, s * 0.55)
        for rc, ring_clr in ((start_rc, _CITY_RING_START), (end_rc, _CITY_RING_DEST)):
            if rc is None:
                continue
            cr, cc = rc
            lx, ly = HexGrid.hex_center(cr, cc, s)
            cx, cy = lx + px, ly + py
            poly = QPolygonF([QPointF(cx + dx, cy + dy) for dx, dy in offsets])
            fill = QColor(ring_clr)
            fill.setAlphaF(0.40)
            p.setBrush(QBrush(fill))
            p.setPen(QPen(ring_clr, lw_hi,
                          Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.drawPolygon(poly)
        p.setBrush(Qt.BrushStyle.NoBrush)

        # City labels for start and dest above everything
        if s >= 7:
            for rc in (start_rc, end_rc):
                if rc is None:
                    continue
                cr, cc = rc
                city = next(
                    (c for c in g.cities if c["row"] == cr and c["col"] == cc), None
                )
                if city:
                    lx, ly = HexGrid.hex_center(cr, cc, s)
                    self._draw_city_label(p, lx + px, ly + py, s,
                                         city["number"], city["name"], dimmed=False)

    # ── ferries ───────────────────────────────────────────────────── #

    def _draw_ferries(self, p: QPainter, ferries: list, s: float) -> None:
        lw_base  = max(4.0, s * 0.50)   # ferry base width (wider than player track)
        lw_track = max(2.5, s * 0.28)   # same as player track width
        blue_grey = QColor(0xb3, 0xcf, 0xd5)

        for fidx, ferry in enumerate(ferries):
            wps = ferry.get("waypoints", [])
            if len(wps) < 2:
                continue
            pts = self._ferry_pts(wps)
            qpath = self._catmull_rom_path(pts)

            if self._highlight_ferries:
                glow = QColor(0xb3, 0xcf, 0xd5, 55)
                p.setPen(QPen(glow, lw_base * 3.5, Qt.PenStyle.SolidLine,
                              Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPath(qpath)

            # Base: always solid blue-grey
            p.setPen(QPen(blue_grey, lw_base, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(qpath)

            # Built overlay: narrow dotted line in owner color
            color_hex = self._ferry_owners.get(fidx)
            if color_hex is not None:
                p.setPen(QPen(QColor(color_hex), lw_track, Qt.PenStyle.DotLine,
                              Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                p.drawPath(qpath)

    def _draw_ferry_wip(self, p: QPainter, s: float) -> None:
        """Draw the in-progress ferry route and hovered-hex indicator."""
        gold = QColor(255, 210, 60)

        # Hover ring on the tile the cursor is over
        if self._ferry_hover_hex and not self._ferry_delete_mode:
            hr, hc = self._ferry_hover_hex
            ctr = self._to_screen(hr, hc)
            ring_r = max(4.0, s * 0.42)
            p.setPen(QPen(QColor(255, 210, 60, 170), max(1.5, s * 0.18)))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(ctr, ring_r, ring_r)

        pts = self._ferry_pts(self._ferry_wip)
        if not pts:
            return

        # Waypoint dots
        dot_r = max(3.5, s * 0.35)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(255, 210, 60, 220)))
        for x, y in pts:
            p.drawEllipse(QPointF(x, y), dot_r, dot_r)

        # Dashed preview spline
        if len(pts) >= 2:
            p.setPen(QPen(QColor(255, 210, 60, 200), max(1.5, s * 0.22),
                          Qt.PenStyle.DashLine,
                          Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(self._catmull_rom_path(pts))

    def _catmull_rom_path(self, pts: list) -> QPainterPath:
        """Smooth cubic spline that passes through every waypoint."""
        qpath = QPainterPath()
        if len(pts) < 2:
            return qpath
        qpath.moveTo(*pts[0])
        if len(pts) == 2:
            qpath.lineTo(*pts[1])
            return qpath
        # Duplicate endpoints so the spline touches them exactly.
        # Tension divisor 9 (vs Catmull-Rom default 6) reduces overshoot on
        # tight turns so the curve stays within the sea hex corridor.
        ext = [pts[0]] + list(pts) + [pts[-1]]
        for i in range(1, len(ext) - 2):
            p0, p1, p2, p3 = ext[i-1], ext[i], ext[i+1], ext[i+2]
            cp1x = p1[0] + (p2[0] - p0[0]) / 9
            cp1y = p1[1] + (p2[1] - p0[1]) / 9
            cp2x = p2[0] - (p3[0] - p1[0]) / 9
            cp2y = p2[1] - (p3[1] - p1[1]) / 9
            qpath.cubicTo(cp1x, cp1y, cp2x, cp2y, p2[0], p2[1])
        return qpath

    def _draw_arrowhead(self, p: QPainter,
                        tx: float, ty: float,
                        dx: float, dy: float,
                        length: float, width: float) -> None:
        l = math.hypot(dx, dy)
        if l < 1e-6:
            return
        dx /= l; dy /= l
        px, py = -dy, dx                         # perpendicular
        bx = tx - dx * length
        by = ty - dy * length
        p.drawPolygon(QPolygonF([
            QPointF(tx, ty),
            QPointF(bx + px * width, by + py * width),
            QPointF(bx - px * width, by - py * width),
        ]))

    # ── game rendering ───────────────────────────────────────────── #

    def _draw_build_preview(self, p: QPainter, a: tuple, b: tuple) -> None:
        """Semi-transparent dashed line from build endpoint to hovered hex."""
        s = self._hex_size
        ax, ay = HexGrid.hex_center(a[0], a[1], s)
        bx, by = HexGrid.hex_center(b[0], b[1], s)
        lw = max(2.5, s * 0.28)
        clr = QColor(self._pending_color) if self._pending_color else QColor(60, 60, 60)
        clr.setAlphaF(0.45)
        pen = QPen(clr, lw, Qt.PenStyle.DashLine,
                   Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.drawLine(
            QPointF(ax + self._pan_x, ay + self._pan_y),
            QPointF(bx + self._pan_x, by + self._pan_y),
        )

    def _draw_player_tracks(self, p: QPainter, s: float) -> None:
        import math as _math
        lw = max(2.5, s * 0.28)
        par_step = lw * 1.15   # perpendicular gap between parallel tracks

        # ── 1. Global edge occupancy ──────────────────────────────────── #
        # Pending edges are passed via _pending_edges and drawn separately
        # (dotted); the tracks in self._player_tracks already have them excluded.
        # edge_colors[frozenset] = [color_hex, ...] in insertion order
        edge_colors: dict = {}
        for color_hex, edges in self._player_tracks:
            for edge in edges:
                if edge not in edge_colors:
                    edge_colors[edge] = []
                if color_hex not in edge_colors[edge]:
                    edge_colors[edge].append(color_hex)

        shared_edges: set = frozenset(e for e, cl in edge_colors.items()
                                      if len(cl) > 1)

        # ── 2. Exclusive edges: continuous chain rendering per player ─── #
        for color_hex, edges in self._player_tracks:
            excl = {e for e in edges if e not in shared_edges}
            if not excl:
                continue
            color = QColor(color_hex)
            out_pen  = QPen(color.darker(180), lw + 2.0, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            fill_pen = QPen(color, lw, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            p.setBrush(Qt.BrushStyle.NoBrush)

            adj: dict = {}
            for edge in excl:
                a, b = tuple(edge)
                adj.setdefault(a, set()).add(b)
                adj.setdefault(b, set()).add(a)

            # Nodes that border a shared edge are chain anchors
            shared_border: set = set()
            for edge in (edges - excl):
                for rc in edge:
                    shared_border.add(rc)

            def _is_anchor(node: tuple) -> bool:
                return len(adj.get(node, set())) != 2 or node in shared_border

            visited: set = set()

            def _walk(start: tuple, first: tuple) -> list:
                fe = frozenset({start, first})
                visited.add(fe)
                chain = [start, first]
                cur, prev = first, start
                while True:
                    if _is_anchor(cur):
                        break
                    remaining = adj[cur] - {prev}
                    if not remaining:
                        break
                    nxt = next(iter(remaining))
                    fe2 = frozenset({cur, nxt})
                    if fe2 in visited:
                        break
                    visited.add(fe2)
                    chain.append(nxt)
                    prev, cur = cur, nxt
                return chain

            chains: list[list] = []
            anchors = [n for n in adj if _is_anchor(n)]
            for start in anchors:
                for nbr in adj[start]:
                    if frozenset({start, nbr}) not in visited:
                        chains.append(_walk(start, nbr))
            for edge in excl:
                if edge not in visited:
                    a, b = tuple(edge)
                    chains.append(_walk(a, b))

            def _chain_path(chain: list) -> QPainterPath:
                path = QPainterPath()
                fx, fy = HexGrid.hex_center(chain[0][0], chain[0][1], s)
                path.moveTo(fx + self._pan_x, fy + self._pan_y)
                for node in chain[1:]:
                    nx, ny = HexGrid.hex_center(node[0], node[1], s)
                    path.lineTo(nx + self._pan_x, ny + self._pan_y)
                return path

            p.setPen(out_pen)
            for ch in chains:
                p.drawPath(_chain_path(ch))
            p.setPen(fill_pen)
            for ch in chains:
                p.drawPath(_chain_path(ch))

            # Junction circles (degree-3+ within exclusive network only)
            junctions = {n for n, nb in adj.items() if len(nb) >= 3}
            if junctions:
                jr = max(2.0, lw * 0.9)
                p.setPen(QPen(color.darker(180), max(1.0, lw * 0.3)))
                p.setBrush(QBrush(QColor(255, 255, 255)))
                for node in junctions:
                    cx, cy = HexGrid.hex_center(node[0], node[1], s)
                    p.drawEllipse(
                        QPointF(cx + self._pan_x, cy + self._pan_y), jr, jr)

        # ── 3. Shared edges: parallel paths with miter joins ──────────── #
        # Walk connected chains of parallel edges so every player stays on
        # the same side throughout the stretch. At each interior bend the
        # miter formula places the offset point exactly where the two offset
        # lines intersect — no crossing, no gap.
        p.setBrush(Qt.BrushStyle.NoBrush)

        def _perp_of(x1, y1, x2, y2):
            dx, dy = x2 - x1, y2 - y1
            l = _math.hypot(dx, dy)
            if l < 1e-9:
                return (0.0, 1.0)
            return (-dy / l, dx / l)

        def _miter_nrm(n1, n2):
            # M = P + offset*(n1+n2)/(1+dot(n1,n2))  — the miter scale vector
            d = n1[0] * n2[0] + n1[1] * n2[1]
            denom = 1.0 + d
            if abs(denom) < 0.05:   # near anti-parallel: cap to incoming normal
                return n1
            mx, my = (n1[0] + n2[0]) / denom, (n1[1] + n2[1]) / denom
            ml = _math.hypot(mx, my)
            if ml > 3.0:            # limit spike length at acute angles
                mx, my = mx * 3.0 / ml, my * 3.0 / ml
            return (mx, my)

        # Group shared edges by ordered colour tuple (player insertion order)
        cs_to_edges: dict = {}
        for edge in shared_edges:
            cs_key = tuple(edge_colors[edge])
            cs_to_edges.setdefault(cs_key, []).append(edge)

        shared_paths: list = []        # (color_hex, [(sx,sy), ...])
        junction_circles: list = []    # (sx, sy, radius)
        cap_segs: list = []            # (QPointF, QPointF)
        parallel_terminals: set = set()  # nodes at start/end of parallel stretches

        for cs_key, cs_edges in cs_to_edges.items():
            n_cl = len(cs_key)

            cs_adj: dict = {}
            for edge in cs_edges:
                a, b = tuple(edge)
                cs_adj.setdefault(a, []).append(b)
                cs_adj.setdefault(b, []).append(a)

            cs_deg = {n: len(nb) for n, nb in cs_adj.items()}
            vis: set = set()

            def _walk(start, via):
                fe = frozenset({start, via})
                if fe in vis:
                    return []
                vis.add(fe)
                chain = [start, via]
                prev, cur = start, via
                while cs_deg.get(cur, 0) == 2:
                    nbrs = [n for n in cs_adj[cur] if n != prev]
                    if not nbrs:
                        break
                    nxt = nbrs[0]
                    fe2 = frozenset({cur, nxt})
                    if fe2 in vis:
                        break
                    vis.add(fe2)
                    chain.append(nxt)
                    prev, cur = cur, nxt
                return chain

            def _add_paths(chain):
                world = [HexGrid.hex_center(r, c, s) for r, c in chain]
                if len(world) < 2:
                    return
                for si, color_hex in enumerate(cs_key):
                    offset = (si - (n_cl - 1) / 2.0) * par_step
                    pts = []
                    for i, (wx, wy) in enumerate(world):
                        if i == 0:
                            nrm = _perp_of(*world[0], *world[1])
                        elif i == len(world) - 1:
                            nrm = _perp_of(*world[-2], *world[-1])
                        else:
                            n1 = _perp_of(*world[i - 1], wx, wy)
                            n2 = _perp_of(wx, wy, *world[i + 1])
                            nrm = _miter_nrm(n1, n2)
                        pts.append((wx + offset * nrm[0] + self._pan_x,
                                    wy + offset * nrm[1] + self._pan_y))
                    shared_paths.append((color_hex, pts))

            # Walk from terminals and junctions first
            # Sort start nodes and their first steps so the walk direction is
            # always canonical (smaller node first).  This guarantees every
            # chain for every colorset walks in the same world-space direction,
            # so slot-0 is always on the same visual side regardless of whether
            # it appears in a 2- or 3-player section.
            for start in sorted(n for n, d in cs_deg.items() if d != 2):
                for via in sorted(cs_adj[start]):
                    chain = _walk(start, via)
                    if len(chain) >= 2:
                        _add_paths(chain)

            # Any remaining edges (pure loops where every node has degree 2)
            for edge in cs_edges:
                fe = frozenset(tuple(edge))
                if fe not in vis:
                    a, b = tuple(edge)
                    start, via = (a, b) if a < b else (b, a)
                    chain = _walk(start, via)
                    if len(chain) >= 2:
                        _add_paths(chain)

            # Junction circles (degree ≥ 3)
            for node, deg in cs_deg.items():
                if deg >= 3:
                    wx, wy = HexGrid.hex_center(node[0], node[1], s)
                    r = (n_cl - 1) / 2.0 * par_step + lw
                    junction_circles.append(
                        (wx + self._pan_x, wy + self._pan_y, r))

            # Terminal caps (degree == 1)
            for node, deg in cs_deg.items():
                if deg == 1:
                    parallel_terminals.add(node)
                    via = cs_adj[node][0]
                    wx, wy = HexGrid.hex_center(node[0], node[1], s)
                    vx, vy = HexGrid.hex_center(via[0], via[1], s)
                    qx, qy = _perp_of(wx, wy, vx, vy)
                    half = (n_cl - 1) / 2.0 * par_step + lw * 0.65
                    csx, csy = wx + self._pan_x, wy + self._pan_y
                    cap_segs.append((
                        QPointF(csx + qx * half, csy + qy * half),
                        QPointF(csx - qx * half, csy - qy * half),
                    ))

        # Draw outlines then fills for all parallel paths
        for color_hex, pts in shared_paths:
            color = QColor(color_hex)
            p.setPen(QPen(color.darker(180), lw + 2.0, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            path = QPainterPath()
            path.moveTo(pts[0][0], pts[0][1])
            for x, y in pts[1:]:
                path.lineTo(x, y)
            p.drawPath(path)

        for color_hex, pts in shared_paths:
            color = QColor(color_hex)
            p.setPen(QPen(color, lw, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            path = QPainterPath()
            path.moveTo(pts[0][0], pts[0][1])
            for x, y in pts[1:]:
                path.lineTo(x, y)
            p.drawPath(path)

        # ── 3b. Terminal caps + junction circles ───────────────────────── #
        # Also cap any exclusive (single-player) edge that departs from a
        # parallel terminal — so the visual bracket wraps the single outgoing
        # line too, just like a BVG line-split marker.
        if parallel_terminals:
            for edge, colors_list in edge_colors.items():
                if len(colors_list) != 1:
                    continue   # only exclusive edges
                for node in edge:
                    if node not in parallel_terminals:
                        continue
                    other = next(ep for ep in edge if ep != node)
                    wx, wy = HexGrid.hex_center(node[0], node[1], s)
                    vx, vy = HexGrid.hex_center(other[0], other[1], s)
                    qx, qy = _perp_of(wx, wy, vx, vy)
                    half = lw * 0.65
                    csx, csy = wx + self._pan_x, wy + self._pan_y
                    cap_segs.append((
                        QPointF(csx + qx * half, csy + qy * half),
                        QPointF(csx - qx * half, csy - qy * half),
                    ))

        cap_lw = lw * 1.8
        if cap_segs:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(40, 40, 40, 210), cap_lw + 2.0,
                          Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            for c1, c2 in cap_segs:
                p.drawLine(c1, c2)
            p.setPen(QPen(QColor(255, 255, 255), cap_lw,
                          Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            for c1, c2 in cap_segs:
                p.drawLine(c1, c2)

        for cx, cy, r in junction_circles:
            p.setPen(QPen(QColor(40, 40, 40, 180), max(1.5, lw * 0.3)))
            p.setBrush(QBrush(QColor(255, 255, 255)))
            p.drawEllipse(QPointF(cx, cy), r, r)

        # ── 4. Pending (this-turn) edges — drawn dotted on top ────────── #
        if self._pending_edges and self._pending_color:
            pclr = QColor(self._pending_color)
            out_pen  = QPen(pclr.darker(180), lw + 2.0,
                            Qt.PenStyle.DotLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            fill_pen = QPen(pclr, lw,
                            Qt.PenStyle.DotLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            p.setBrush(Qt.BrushStyle.NoBrush)
            pend_segs = []
            for edge in self._pending_edges:
                a, b = tuple(edge)
                ax, ay = HexGrid.hex_center(a[0], a[1], s)
                bx, by = HexGrid.hex_center(b[0], b[1], s)
                pa2 = QPointF(ax + self._pan_x, ay + self._pan_y)
                pb2 = QPointF(bx + self._pan_x, by + self._pan_y)
                pend_segs.append((pa2, pb2))
            p.setPen(out_pen)
            for pa2, pb2 in pend_segs:
                p.drawLine(pa2, pb2)
            p.setPen(fill_pen)
            for pa2, pb2 in pend_segs:
                p.drawLine(pa2, pb2)

            # Cost badges at each pending segment midpoint
            if self._pending_costs:
                font = QFont()
                font.setPixelSize(max(10, int(s * 0.27)))
                font.setBold(True)
                p.setFont(font)
                fm = QFontMetricsF(font)
                pad_x, pad_y = 5.0, 2.0
                for edge, cost in self._pending_costs.items():
                    a, b = tuple(edge)
                    ax, ay = HexGrid.hex_center(a[0], a[1], s)
                    bx, by = HexGrid.hex_center(b[0], b[1], s)
                    mx = (ax + bx) / 2 + self._pan_x
                    my = (ay + by) / 2 + self._pan_y
                    txt = str(cost)
                    tw = fm.horizontalAdvance(txt)
                    bw = tw + pad_x * 2
                    bh = fm.height() + pad_y * 2
                    pill = QRectF(mx - bw / 2, my - bh / 2, bw, bh)
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QColor(0xFA, 0xF8, 0xF2, 230))
                    p.drawRoundedRect(pill, bh / 2, bh / 2)
                    p.setPen(QColor(0x14, 0x17, 0x1C))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.drawText(pill, Qt.AlignmentFlag.AlignCenter, txt)

    def _draw_trains(self, p: QPainter, s: float) -> None:
        r = max(4.5, s * 0.42)
        for entry in self._train_positions:
            color_hex, (tr, tc) = entry[0], entry[1]
            name = entry[2] if len(entry) > 2 else ""
            ctr = self._to_screen(tr, tc)
            color = QColor(color_hex)
            p.setBrush(QBrush(color))
            p.setPen(QPen(color.darker(160), max(1.5, s * 0.12)))
            p.drawEllipse(QPointF(ctr.x(), ctr.y()), r, r)
            # White inner dot
            p.setBrush(QBrush(QColor(255, 255, 255, 180)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(ctr.x(), ctr.y()), r * 0.38, r * 0.38)
            # Player name pill below the token
            if self._show_player_names and name and s >= 10:
                px_size = max(7, int(s * 0.36))
                fn = QFont()
                fn.setPixelSize(px_size)
                fn.setBold(True)
                p.setFont(fn)
                fm = QFontMetricsF(fn)
                tw = fm.horizontalAdvance(name) + 6
                th = fm.height() + 2
                pill = QRectF(ctr.x() - tw / 2, ctr.y() + r + 3, tw, th)
                bg = QColor(color)
                bg.setAlpha(210)
                p.setBrush(bg)
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(pill, th / 2, th / 2)
                p.setPen(QColor(255, 255, 255, 230))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawText(pill, Qt.AlignmentFlag.AlignCenter, name)

    def _draw_ferry_boat(self, p: QPainter, s: float) -> None:
        """Draw the animated boat token for an active ferry crossing."""
        anim = self._boat_anim
        if anim is None:
            return
        g = self.hex_grid
        if g is None:
            return
        ferries = getattr(g, "ferries", [])
        fidx = anim["ferry_idx"]
        if fidx >= len(ferries):
            return
        wps = ferries[fidx].get("waypoints", [])
        if len(wps) < 2:
            return

        path = self._catmull_rom_path(self._ferry_pts(wps))
        t = float(anim["t"])
        t = max(0.0, min(1.0, t))
        pos  = path.pointAtPercent(t)
        dt   = 0.02
        pos2 = path.pointAtPercent(min(1.0, t + dt))
        angle_rad = math.atan2(pos2.y() - pos.y(), pos2.x() - pos.x())
        angle_deg = math.degrees(angle_rad)

        color = QColor(anim["color_hex"])
        hull_l = max(18.0, s * 1.55)
        hull_w = max(9.0,  s * 0.80)

        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.translate(pos.x(), pos.y())
        p.rotate(angle_deg + 90)   # bow points in direction of travel

        # Drop shadow
        p.setBrush(QBrush(QColor(0, 0, 0, 45)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(-hull_w / 2 + 2, -hull_l / 2 + 2, hull_w, hull_l))

        # Hull
        p.setBrush(QBrush(color))
        p.setPen(QPen(color.darker(180), max(1.5, s * 0.13)))
        p.drawEllipse(QRectF(-hull_w / 2, -hull_l / 2, hull_w, hull_l))

        # White deck stripe
        sw = hull_w * 0.56
        sh = hull_l * 0.60
        p.setBrush(QBrush(QColor(255, 255, 255, 210)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(-sw / 2, -sh / 2, sw, sh), sw * 0.4, sw * 0.4)

        # Funnel (small filled circle near stern)
        fd = max(2.5, s * 0.20)
        p.setBrush(QBrush(color.darker(150)))
        p.drawEllipse(QPointF(0.0, hull_l * 0.15), fd, fd)

        # Bow pointer triangle
        bw = hull_w * 0.28
        bow_y = -hull_l / 2 - max(3.0, s * 0.22)
        bow_poly = QPolygonF([
            QPointF(0.0,  bow_y),
            QPointF(-bw, -hull_l * 0.32),
            QPointF( bw, -hull_l * 0.32),
        ])
        p.setBrush(QBrush(QColor(255, 255, 255, 140)))
        p.drawPolygon(bow_poly)

        p.restore()

    # ── segment drawing ──────────────────────────────────────────── #

    def _draw_segs(self, p: QPainter, segs: np.ndarray) -> None:
        if len(segs) == 0:
            return
        s, px, py = self._hex_size, self._pan_x, self._pan_y
        for x1, y1, x2, y2 in segs:
            p.drawLine(QPointF(x1 * s + px, y1 * s + py),
                       QPointF(x2 * s + px, y2 * s + py))

    def _draw_terrain_glyphs(
        self, p: QPainter,
        centers: list[tuple[float, float, int]],
        s: float,
    ) -> None:
        """
        Draw restrained terrain glyphs for mountain / forest / desert / swamp hexes.
        Each glyph is centered at (cx, cy) with scale proportional to s.
        """
        # Scale factor: glyph coords were designed at r=14 for a ~28px hex
        sc = s / 28.0
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        ink2 = QColor(INK_2)
        ink3 = QColor(INK_3)
        p3   = QColor("#1f7a4a")   # S_P3 green for forest trees
        p3.setAlphaF(0.55)
        p3_faint = QColor("#1f7a4a")
        p3_faint.setAlphaF(0.40)
        river_c = QColor(RIVER)
        surf    = QColor(SURFACE)

        def _tri(pts_local):
            return QPolygonF([QPointF(x * sc, y * sc) for x, y in pts_local])

        for cx, cy, bucket in centers:
            p.save()
            p.translate(cx, cy)

            if bucket == _B_MTN:
                # Two overlapping mountain triangles + white snow cap
                ink2.setAlphaF(0.50)
                p.setBrush(QBrush(ink2))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawPolygon(_tri([(-10, 5), (-3, -6), (4, 5)]))
                ink2.setAlphaF(0.35)
                p.setBrush(QBrush(ink2))
                p.drawPolygon(_tri([(2, 5), (8, -3), (13, 5)]))
                # Snow cap
                p.setBrush(QBrush(surf))
                p.drawPolygon(_tri([(-4, -5), (-2.5, -7), (-1, -5)]))

            elif bucket == _B_FOREST:
                # Center tree
                p.setBrush(QBrush(p3))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawPolygon(_tri([(-6, 4), (0, -5), (6, 4)]))
                # Left and right small trees
                p.setBrush(QBrush(p3_faint))
                p.drawPolygon(_tri([(-9, 4), (-12, 4), (-10.5, 1)]))
                p.drawPolygon(_tri([(9, 4), (12, 4), (10.5, 1)]))

            elif bucket == _B_DESERT:
                # 4 small dots scattered
                p.setBrush(QBrush(ink3))
                p.setPen(Qt.PenStyle.NoPen)
                for dx, dy in [(-6, -3), (2, -1), (-2, 4), (7, 3)]:
                    p.drawEllipse(
                        QPointF(dx * sc, dy * sc),
                        1.0 * sc, 1.0 * sc,
                    )

            elif bucket == _B_SWAMP:
                # 3 vertical tuft lines
                pen = QPen(ink3, max(0.8, 1.0 * sc))
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                p.setPen(pen)
                for dx in (-6, 0, 6):
                    p.drawLine(
                        QPointF(dx * sc, 3 * sc),
                        QPointF(dx * sc, -1 * sc if dx != 0 else -3 * sc),
                    )

            p.restore()

    def _draw_river_polyline(self, p: QPainter, pts: np.ndarray) -> None:
        """Draw a waypoint array as a connected polyline; NaN rows start a new subpath."""
        if len(pts) < 2:
            return
        s, px, py = self._hex_size, self._pan_x, self._pan_y
        path = QPainterPath()
        started = False
        for i in range(len(pts)):
            x, y = float(pts[i, 0]), float(pts[i, 1])
            if math.isnan(x):
                started = False
            elif not started:
                path.moveTo(x * s + px, y * s + py)
                started = True
            else:
                path.lineTo(x * s + px, y * s + py)
        p.drawPath(path)

    def _draw_river_name(self, p: QPainter, pts: np.ndarray,
                         name: str, s: float, px: float, py: float) -> None:
        """Draw river name in italic white text every 16 segments along the polyline."""
        fname = QFont()
        fname.setItalic(True)
        fname.setPixelSize(max(8, int(s * 0.26)))
        fm = QFontMetricsF(fname)
        text_w = fm.horizontalAdvance(name) + 6
        text_h = fm.height()
        rect = QRectF(-text_w / 2, -text_h / 2, text_w, text_h)

        # Collect screen-space sub-segments (split on NaN)
        subs: list = []
        sub: list = []
        for i in range(len(pts)):
            x, y = float(pts[i, 0]), float(pts[i, 1])
            if math.isnan(x):
                if sub:
                    subs.append(sub)
                    sub = []
            else:
                sub.append((x * s + px, y * s + py))
        if sub:
            subs.append(sub)

        STEP = 8
        for sub in subs:
            n = len(sub)
            j = STEP
            while j < n:
                i0 = max(0, j - STEP // 2)
                i1 = min(n - 1, j + STEP // 2)
                mx, my = sub[j]
                dx = sub[i1][0] - sub[i0][0]
                dy = sub[i1][1] - sub[i0][1]
                angle = math.degrees(math.atan2(dy, dx))
                if angle > 90:
                    angle -= 180
                elif angle < -90:
                    angle += 180

                p.save()
                p.translate(mx, my)
                p.rotate(angle)
                p.setFont(fname)
                # Dark outline
                p.setPen(QColor(10, 14, 20, 140))
                for odx, ody in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    p.drawText(rect.translated(odx, ody),
                               Qt.AlignmentFlag.AlignCenter, name)
                # White text
                p.setPen(QColor(0xFF, 0xFF, 0xFF, 210))
                p.drawText(rect, Qt.AlignmentFlag.AlignCenter, name)
                p.restore()
                j += STEP * 2

    # ── city labels ───────────────────────────────────────────────── #

    def _draw_city_label(self, p: QPainter, cx: float, cy: float,
                         s: float, number: int, name: str,
                         dimmed: bool = False) -> None:
        """Draw city number (bold, centered) and name (smaller, below) on a hex."""
        num_px   = max(7, int(s * 0.50))
        name_px  = max(5, int(s * 0.27))
        half     = s * 0.92
        ink      = _CITY_NUM_DIM if dimmed else _CITY_NUM

        fnum = QFont()
        fnum.setBold(True)
        fnum.setPixelSize(num_px)
        p.setFont(fnum)
        num_rect = QRectF(cx - half, cy - half, 2 * half, half * 1.1)
        num_str  = str(number)

        if not dimmed:
            p.setPen(_CITY_SHAD)
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                r = QRectF(num_rect.translated(dx, dy))
                p.drawText(r, Qt.AlignmentFlag.AlignCenter, num_str)
        p.setPen(ink)
        p.drawText(num_rect, Qt.AlignmentFlag.AlignCenter, num_str)

        if s >= 14 and name:
            fname = QFont()
            fname.setPixelSize(name_px)
            p.setFont(fname)
            name_rect = QRectF(cx - half, cy + s * 0.08, 2 * half, half * 0.85)
            if not dimmed:
                p.setPen(_CITY_SHAD)
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    r = QRectF(name_rect.translated(dx, dy))
                    p.drawText(r, Qt.AlignmentFlag.AlignHCenter |
                               Qt.AlignmentFlag.AlignTop, name)
            p.setPen(ink)
            p.drawText(name_rect, Qt.AlignmentFlag.AlignHCenter |
                       Qt.AlignmentFlag.AlignTop, name)

    # ── mouse / keyboard ─────────────────────────────────────────── #

    def apply_prefs(self, prefs: dict) -> None:
        """Apply persisted settings that affect map interaction."""
        if "mouse_zoom" in prefs:
            self._zoom_enabled = bool(prefs["mouse_zoom"])
        if "zoom_invert" in prefs:
            self._zoom_invert = bool(prefs["zoom_invert"])
        if "scroll_sensitivity" in prefs:
            self._zoom_factor = {0: 1.08, 1: 1.15, 2: 1.22}.get(
                int(prefs["scroll_sensitivity"]), 1.15
            )
        if "show_name_labels" in prefs:
            self._show_player_names = bool(prefs["show_name_labels"])
            self.update()
        if "highlight_ferries" in prefs:
            self._highlight_ferries = bool(prefs["highlight_ferries"])
            self._invalidate_base()
            self.update()

    def refresh_theme(self) -> None:
        _refresh_module_colors()
        if self.hex_grid is not None:
            self._overview = _build_overview(self.hex_grid)
        self._invalidate_base()
        self.update()

    def wheelEvent(self, ev) -> None:
        if not self._zoom_enabled:
            return
        delta = ev.angleDelta().y()
        if self._zoom_invert:
            delta = -delta
        f = self._zoom_factor
        factor = f if delta > 0 else (1.0 / f)
        old_size = self._hex_size
        new_size = max(_MIN_HEX, min(_MAX_HEX, old_size * factor))
        if new_size == old_size:
            return  # already at limit — don't shift the pan
        effective = new_size / old_size
        cx, cy = ev.position().x(), ev.position().y()
        self._pan_x -= (cx - self._pan_x) * (effective - 1.0)
        self._pan_y -= (cy - self._pan_y) * (effective - 1.0)
        self._hex_size = new_size
        self._invalidate_base()
        self.update()

    def mousePressEvent(self, ev) -> None:
        # Game build mode — left-click emits game_hex_clicked
        if self.game_mode and ev.button() == Qt.MouseButton.LeftButton:
            sx, sy = ev.position().x(), ev.position().y()
            fidx = self._ferry_hit_test(sx, sy)
            if fidx >= 0:
                self.ferry_line_clicked.emit(fidx)
                return
            if self.hex_grid is not None:
                row, col = self._to_hex(sx, sy)
                if self.hex_grid.is_valid(row, col):
                    self.game_hex_clicked.emit(row, col)
            return

        # Ferry mode — delete uses line hit-test; build snaps to hex center
        if self.ferry_mode:
            if ev.button() == Qt.MouseButton.LeftButton:
                if self._ferry_delete_mode:
                    sx, sy = ev.position().x(), ev.position().y()
                    fidx = self._ferry_hit_test(sx, sy)
                    if fidx >= 0:
                        self.ferry_line_clicked.emit(fidx)
                elif self.hex_grid is not None:
                    row, col = self._to_hex(ev.position().x(), ev.position().y())
                    if self.hex_grid.is_valid(row, col):
                        self.corner_clicked.emit(row, col, 0)   # ci unused
            elif ev.button() == Qt.MouseButton.RightButton:
                self.enter_pressed.emit()
            return
        # Paint mode — left-click starts a paint drag
        if ev.button() == Qt.MouseButton.LeftButton and self.paint_mode:
            self._drag_origin = ev.pos()
            self._last_painted = None
            if self.hex_grid is not None:
                row, col = self._to_hex(ev.position().x(), ev.position().y())
                if self.hex_grid.is_valid(row, col):
                    self._last_painted = (row, col)
                    self.hex_painted.emit(row, col, self.active_brush)
            return
        # Normal mode — any button starts a pan drag
        if ev.button() in (Qt.MouseButton.LeftButton,
                           Qt.MouseButton.MiddleButton,
                           Qt.MouseButton.RightButton):
            self._drag_origin = ev.pos()
            self._drag_pan_start = (self._pan_x, self._pan_y)

    def mouseMoveEvent(self, ev) -> None:
        sx, sy = ev.position().x(), ev.position().y()

        # Ferry hover — highlight hovered tile (not in delete mode)
        if self.ferry_mode:
            if self._ferry_delete_mode:
                return
            if self.hex_grid is not None:
                row, col = self._to_hex(sx, sy)
                new_hov = (row, col) if self.hex_grid.is_valid(row, col) else None
            else:
                new_hov = None
            if new_hov != self._ferry_hover_hex:
                self._ferry_hover_hex = new_hov
                self.update()
            return

        # Paint drag (city brush is click-only — no drag)
        if (self.paint_mode and self._drag_origin is not None
                and (ev.buttons() & Qt.MouseButton.LeftButton)):
            if self.active_brush != "city" and self.hex_grid is not None:
                row, col = self._to_hex(sx, sy)
                if self.hex_grid.is_valid(row, col) and (row, col) != self._last_painted:
                    self._last_painted = (row, col)
                    self.hex_painted.emit(row, col, self.active_brush)
            return

        # Normal pan drag
        if not self.paint_mode and self._drag_origin is not None:
            d = ev.pos() - self._drag_origin
            self._pan_x = self._drag_pan_start[0] + d.x()
            self._pan_y = self._drag_pan_start[1] + d.y()
            self._invalidate_base()
            self.update()
            return

        # Hover highlight
        if self._hex_size >= _POLY_THRESH and self.hex_grid is not None:
            row, col = self._to_hex(sx, sy)
            hov = (row, col) if self.hex_grid.is_valid(row, col) else None
            if hov != self._hovered:
                self._hovered = hov
                self.update()

    def mouseReleaseEvent(self, ev) -> None:
        if self.ferry_mode:
            return
        if self.paint_mode and ev.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = None
            self._last_painted = None
            return
        if self._drag_origin is None:
            return
        moved = (ev.pos() - self._drag_origin).manhattanLength()
        self._drag_origin = None
        if moved < 6 and ev.button() == Qt.MouseButton.LeftButton:
            if self.hex_grid is not None:
                row, col = self._to_hex(ev.position().x(), ev.position().y())
                if self.hex_grid.is_valid(row, col):
                    self.hex_grid.selected = (row, col)
                    self._invalidate_base()
                    self.update()
                    self.hex_selected.emit(row, col, self.hex_grid.get_id(row, col))

    def resizeEvent(self, ev) -> None:
        self._invalidate_base()
        super().resizeEvent(ev)

    def keyPressEvent(self, ev) -> None:
        k = ev.key()
        if k == Qt.Key.Key_Escape:
            self.escape_pressed.emit()
        elif k in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.enter_pressed.emit()
        elif k == Qt.Key.Key_0 and ev.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.fit_to_view()
        else:
            super().keyPressEvent(ev)


# ── overview pixmap (vectorized) ────────────────────────────────────── #

def _build_overview(grid: HexGrid) -> QPixmap:
    h, w = grid.cells.shape

    # Base: sea everywhere
    rgb = np.empty((h, w, 3), dtype=np.uint8)
    rgb[:, :] = (_SEA.red(), _SEA.green(), _SEA.blue())

    # Other land (grey)
    if grid.other_land is not None:
        m = grid.other_land
        rgb[m] = (_OTHER_LAND.red(), _OTHER_LAND.green(), _OTHER_LAND.blue())

    # Region land: white by default, light brown where mountainous
    if grid.cells.any():
        m = grid.cells
        rgb[m] = (_LAND.red(), _LAND.green(), _LAND.blue())
        if grid.is_mountainous is not None:
            mtn = grid.is_mountainous & grid.cells
            rgb[mtn] = (_HILL[0], _HILL[1], _HILL[2])

    # City markers: 3×3 dark-red blob so they're visible at low zoom
    for city in grid.cities:
        cr, cc = city["row"], city["col"]
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                nr, nc = cr + dr, cc + dc
                if 0 <= nr < h and 0 <= nc < w:
                    rgb[nr, nc] = _CITY_OVW

    img = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(img.copy())

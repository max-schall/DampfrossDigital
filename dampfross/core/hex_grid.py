import math
import numpy as np

SQRT3 = math.sqrt(3)

# ---- neighbour offsets (pointy-top, odd-row shifted right) ----
# Direction order: 0=NE, 1=E, 2=SE, 3=SW, 4=W, 5=NW
_NBRS_EVEN = [(-1, 0), (0, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
_NBRS_ODD  = [(-1, 1), (0, 1), (1, 1), (1,  0), (0, -1), (-1,  0)]

# Corner indices in screen-coords (y-down), angle = 30+60*i:
#   0=lower-right, 1=bottom, 2=lower-left, 3=upper-left, 4=top, 5=upper-right
# Edge i runs from corner i to corner (i+1)%6.
# Which edge faces each direction:  NE→4, E→5, SE→0, SW→1, W→2, NW→3
_DIR_EDGE = [4, 5, 0, 1, 2, 3]


class HexGrid:
    """
    Pointy-top hexagonal grid using offset coordinates (odd-row shift right).
    Row 0 = north, increasing row goes south. Col 0 = west.
    """

    def __init__(self, cells: np.ndarray, region_name: str = ""):
        self.cells = cells                     # bool (rows, cols) — True = region land
        self.rows, self.cols = cells.shape
        self.region_name = region_name
        self.selected: tuple[int, int] | None = None

        # Populated by grid_builder after construction
        self.other_land: np.ndarray | None = None
        self.elevation: np.ndarray | None = None    # float32, sampled
        self.elev_stride: int = 5

        # Precomputed border segments in unit space, shape (N, 4)
        self.border_segs: np.ndarray = np.empty((0, 4), dtype=np.float32)
        self.country_border_segs: list = []   # list[np.ndarray (N,2)] polylines

        # Binary mountainous flag (local relief, not absolute threshold)
        self.is_mountainous: np.ndarray | None = None   # bool, full grid shape

        # Rivers — populated by the river worker after the map is shown
        self.river_segs: list[np.ndarray] = []
        self.river_names: list[str] = []
        self.river_count: int = 0

        # Cities — populated by grid_builder
        # Each entry: {'row', 'col', 'name', 'population', 'number'}
        self.cities: list[dict] = []

        # Ferry connections between mainland and inhabited islands
        # Each entry: {'waypoints': [(r,c,ci), ...]}
        self.ferries: list[dict] = []
        # Max number of ferries a single player may own (set in map creator)
        self.max_ferries_per_player: int = 1

        # River valley mask (bool array) retained so mountain params can be
        # recomputed in real-time without re-fetching rivers.
        self.river_mask: "np.ndarray | None" = None

        # Projection metadata needed by the river worker
        self.laea_proj: str = ""
        self.hex_size_m: float = 1.0
        self.x_origin: float = 0.0
        self.y_origin: float = 0.0
        self.bbox_wgs84: tuple = (0.0, 0.0, 0.0, 0.0)  # lat_min,lon_min,lat_max,lon_max

        # Stored for live coastline recomputation (no network call needed)
        self.proj_geom = None                        # Shapely geometry in LAEA space (pre-erosion)
        self.hex_flat: "np.ndarray | None" = None   # (N, 2) hex centre coords in LAEA space

        # Per-cell terrain overrides set via the map editor brush.
        # Keys: (row, col), values: 'forest' | 'desert' | 'swamp'
        # Absence means terrain is derived from cells/is_mountainous as usual.
        self.terrain_overrides: dict = {}

    # ------------------------------------------------------------------ #
    # ID / validity                                                        #
    # ------------------------------------------------------------------ #

    def get_id(self, row: int, col: int) -> int:
        return row * self.cols + col

    def from_id(self, hex_id: int) -> tuple[int, int]:
        return divmod(hex_id, self.cols)

    def is_valid(self, row: int, col: int) -> bool:
        return 0 <= row < self.rows and 0 <= col < self.cols

    @staticmethod
    def hex_distance(row_a: int, col_a: int, row_b: int, col_b: int) -> int:
        """Cube-coordinate distance between two offset-grid hexes (odd-row right shift)."""
        qa = col_a - (row_a - (row_a & 1)) // 2
        qb = col_b - (row_b - (row_b & 1)) // 2
        return max(abs(qa - qb), abs(row_a - row_b),
                   abs(-qa - row_a + qb + row_b))

    def is_land(self, row: int, col: int) -> bool:
        return self.is_valid(row, col) and bool(self.cells[row, col])

    def elevation_at(self, row: int, col: int) -> float:
        """Return elevation (m) for hex, or NaN if unavailable."""
        if self.elevation is None:
            return float("nan")
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return float(self.elevation[row, col])
        return float("nan")

    # ------------------------------------------------------------------ #
    # Static geometry                                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def hex_center(row: int, col: int, hex_size: float) -> tuple[float, float]:
        x = (col + (row % 2) * 0.5) * hex_size * SQRT3
        y = row * hex_size * 1.5
        return x, y

    @staticmethod
    def hex_corners(cx: float, cy: float, hex_size: float) -> list[tuple[float, float]]:
        return [
            (cx + hex_size * math.cos(math.radians(30 + 60 * i)),
             cy + hex_size * math.sin(math.radians(30 + 60 * i)))
            for i in range(6)
        ]

    @staticmethod
    def pixel_to_hex(lx: float, ly: float, hex_size: float) -> tuple[int, int]:
        row_approx = ly / (hex_size * 1.5)
        best_row, best_col, best_dist = 0, 0, float("inf")
        for row in range(int(row_approx) - 1, int(row_approx) + 3):
            col_f = lx / (hex_size * SQRT3) - (row % 2) * 0.5
            col = round(col_f)
            cx, cy = HexGrid.hex_center(row, col, hex_size)
            d = (lx - cx) ** 2 + (ly - cy) ** 2
            if d < best_dist:
                best_dist, best_row, best_col = d, row, col
        return best_row, best_col

    # ------------------------------------------------------------------ #
    # Border pre-computation                                               #
    # ------------------------------------------------------------------ #

    def compute_border_segs(self) -> None:
        """Pre-compute region-border edge segments in unit space."""
        lines = []
        for r in range(self.rows):
            nbrs = _NBRS_ODD if r % 2 else _NBRS_EVEN
            for c in range(self.cols):
                if not self.cells[r, c]:
                    continue
                cx, cy = self.hex_center(r, c, 1.0)
                corners = self.hex_corners(cx, cy, 1.0)
                for d, (dr, dc) in enumerate(nbrs):
                    nr, nc = r + dr, c + dc
                    if not self.is_valid(nr, nc) or not self.cells[nr, nc]:
                        ei = _DIR_EDGE[d]
                        p1, p2 = corners[ei], corners[(ei + 1) % 6]
                        lines.append([p1[0], p1[1], p2[0], p2[1]])
        self.border_segs = (
            np.array(lines, dtype=np.float32) if lines
            else np.empty((0, 4), dtype=np.float32)
        )

    # ------------------------------------------------------------------ #
    # Polyline tracing (rivers + country borders)                         #
    # ------------------------------------------------------------------ #

    def _trace_polylines(
        self,
        input_lines: list,
        hex_size_m: float,
        x_origin: float,
        y_origin: float,
        filter_fn=None,
        add_corners: bool = True,
    ) -> list:
        """
        Core tracer.  Walks projected polylines through the hex grid and returns
        a list of (N, 2) float32 arrays — one continuous segment per array.

        Each waypoint is either the midpoint of a crossed hex edge, or a hex
        corner between two crossings.  Consecutive waypoints always share an
        endpoint (midpoint→corner, corner→corner, corner→midpoint), so drawing
        them as a QPainterPath produces a line that follows hex edges exactly.

        filter_fn(ha, hb) -> bool : if given, skip transitions where False.
        """
        step = hex_size_m / 3.0
        result: list[np.ndarray] = []

        for proj_coords in input_lines:
            pts = _resample(proj_coords, step)

            # --- pass 1: build a cycle-free hex path then derive transitions ---
            # Walking the dense resampled points near a hex corner can produce
            # triangle oscillations (A→B→C→A) that a simple reversal stack
            # cannot eliminate.  Instead we build the path directly and trim
            # back the moment any hex is revisited — this removes ALL cycles
            # regardless of length before transitions are ever created.
            hex_path: list = []   # (row, col) entries or None (gap marker)
            hex_pos:  dict = {}   # (row, col) -> index in hex_path

            for x_m, y_m in pts:
                lx = x_m - x_origin
                ly = y_origin - y_m
                row, col = self.pixel_to_hex(lx, ly, hex_size_m)

                if not self.is_valid(row, col):
                    if hex_path and hex_path[-1] is not None:
                        hex_path.append(None)
                    hex_pos = {}          # new segment — reset cycle tracking
                    continue

                h = (row, col)
                if hex_path and hex_path[-1] == h:
                    continue              # same hex as last point — skip

                if h in hex_pos:
                    # Cycle: trim everything from the first visit of h onwards
                    idx = hex_pos[h]
                    for removed in hex_path[idx:]:
                        if removed is not None:
                            hex_pos.pop(removed, None)
                    del hex_path[idx:]

                hex_pos[h] = len(hex_path)
                hex_path.append(h)

            transitions: list[tuple] = []
            for i in range(len(hex_path) - 1):
                ha, hb = hex_path[i], hex_path[i + 1]
                if ha is None or hb is None:
                    continue
                if not (self.is_valid(ha[0], ha[1]) and self.is_valid(hb[0], hb[1])):
                    continue
                ei = _shared_edge(ha, hb)
                if ei is None:
                    continue   # non-adjacent hex pair (very rare with dense step)
                if filter_fn is None or filter_fn(ha, hb):
                    transitions.append((ha, hb, ei))

            if not transitions:
                continue

            # --- pass 2: build waypoint sequence ---
            # Split into separate continuous segments when transitions jump
            # (i.e. next_ha != hb means the river left and re-entered the grid).
            segments: list[list] = [[]]

            for i, (ha, hb, ei_ha) in enumerate(transitions):
                cxa, cya = self.hex_center(ha[0], ha[1], 1.0)
                corners_ha = self.hex_corners(cxa, cya, 1.0)
                p1, p2 = corners_ha[ei_ha], corners_ha[(ei_ha + 1) % 6]
                segments[-1].append(((p1[0] + p2[0]) * 0.5,
                                      (p1[1] + p2[1]) * 0.5))

                if i + 1 < len(transitions):
                    next_ha, _next_hb, ei_hb = transitions[i + 1]
                    if next_ha == hb:
                        # Continuous — add perimeter corners through hb
                        if add_corners:
                            entry_e = _shared_edge(hb, ha)
                            if entry_e is not None and entry_e != ei_hb:
                                cxb, cyb = self.hex_center(hb[0], hb[1], 1.0)
                                corners_hb = self.hex_corners(cxb, cyb, 1.0)
                                segments[-1].extend(
                                    _corners_between(entry_e, ei_hb, corners_hb)
                                )
                    else:
                        # Gap — start a new segment
                        segments.append([])

            min_pts = 2 if not add_corners else 5
            for seg in segments:
                seg = _dezig(seg)
                if len(seg) >= min_pts:
                    result.append(np.array(seg, dtype=np.float32))

        return result

    def trace_river(
        self,
        proj_coords: list[tuple[float, float]],
        hex_size_m: float,
        x_origin: float,
        y_origin: float,
    ) -> np.ndarray:
        """
        Returns (N, 2) waypoint array in unit space.  Consecutive points follow
        hex edges exactly.  NaN rows separate disconnected sub-segments.
        """
        segs = self._trace_polylines([proj_coords], hex_size_m, x_origin, y_origin)
        if not segs:
            return np.empty((0, 2), dtype=np.float32)
        nan_row = np.full((1, 2), float("nan"), dtype=np.float32)
        parts = []
        for seg in segs:
            # Trim the leading and trailing edge-midpoints so rivers start and
            # end at corner vertices, never floating in the middle of an edge.
            if len(seg) >= 3:
                seg = seg[1:-1]
            if len(seg) < 2:
                continue
            if parts:
                parts.append(nan_row)
            parts.append(seg)
        if not parts:
            return np.empty((0, 2), dtype=np.float32)
        return np.vstack(parts)

    def trace_border_lines(
        self,
        lines: list,
        hex_size_m: float,
        x_origin: float,
        y_origin: float,
    ) -> list:
        """
        Trace projected country-border polylines, keeping only transitions that
        touch at least one other_land hex.  Returns list of (N, 2) waypoint arrays.
        """
        def _other_land(ha, hb):
            ol = self.other_land
            if ol is None:
                return False
            ha_region = self.is_valid(ha[0], ha[1]) and bool(self.cells[ha[0], ha[1]])
            hb_region = self.is_valid(hb[0], hb[1]) and bool(self.cells[hb[0], hb[1]])
            # Skip transitions entirely inside the region — those edges are the
            # black region border and shouldn't be covered by the grey line.
            if ha_region and hb_region:
                return False
            # Allow the boundary transition (one hex = region, other = outside)
            # so the grey border visually connects to the black region border.
            # The black border is drawn on top in paintEvent, so any overlap is
            # hidden.
            a = self.is_valid(ha[0], ha[1]) and bool(ol[ha[0], ha[1]])
            b = self.is_valid(hb[0], hb[1]) and bool(ol[hb[0], hb[1]])
            return a or b

        raw = self._trace_polylines(lines, hex_size_m, x_origin, y_origin,
                                    filter_fn=_other_land)
        # Drop stubs: only keep segments whose unit-space path length represents
        # at least 30 km of geographic distance.
        min_unit_len = 30_000.0 / hex_size_m
        kept = []
        for seg in raw:
            diffs = seg[1:] - seg[:-1]
            if float(np.sqrt((diffs ** 2).sum(axis=1)).sum()) >= min_unit_len:
                kept.append(seg)
        return kept


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _dezig(pts: list) -> list:
    """
    Remove A→B→A back-and-forth spikes from a waypoint list.

    For straight-through (cw==3) hex transitions, the last corner of hex N
    and the first corner of hex N+1 are physically the same point (both are
    corners of the shared edge).  The shared-edge midpoint sits between them,
    producing a visible dead-end spike: corner → midpoint → same_corner.
    This pass detects any such A→B→A pattern and removes the spike point B.
    Non-spike points are unchanged.
    """
    if len(pts) < 3:
        return pts
    out = list(pts)
    i = 0
    while i + 2 < len(out):
        ax, ay = out[i]
        cx, cy = out[i + 2]
        if abs(ax - cx) < 1e-6 and abs(ay - cy) < 1e-6:
            del out[i + 1]
            if i > 0:
                i -= 1   # recheck: removal may expose a preceding spike
        else:
            i += 1
    return out


def _corners_between(
    entry_e: int,
    exit_e: int,
    hex_corners: list,
) -> list:
    """
    Corner coordinates to visit going the short way around a hex perimeter
    from mid(entry_e) to mid(exit_e).

    On the CW perimeter: mid(e) → corner(e+1)%6 → mid(e+1) → corner(e+2)%6 ...
    CW corners from entry_e to exit_e : (entry_e+1)%6 … exit_e  (count = (exit_e-entry_e)%6)
    CCW corners from entry_e to exit_e: entry_e … (exit_e+1)%6  (count = (entry_e-exit_e)%6)
    """
    cw  = (exit_e  - entry_e) % 6
    ccw = (entry_e - exit_e)  % 6
    if cw == 0:
        return []
    if cw < ccw:
        # CW is strictly shorter — go clockwise.
        out, c = [], (entry_e + 1) % 6
        for _ in range(cw):
            out.append(hex_corners[c])
            c = (c + 1) % 6
    else:
        # CCW is shorter, or equal length (cw == ccw == 3, straight-through).
        # For the straight-through case CCW progresses monotonically toward the
        # exit without reversing direction; CW would backtrack and create a
        # visible "side arm".
        out, c = [], entry_e
        for _ in range(ccw):
            out.append(hex_corners[c])
            c = (c - 1) % 6
    return out


def _shared_edge(ha: tuple, hb: tuple) -> int | None:
    """Edge index (in ha's frame) of the face touching hb, or None if not adjacent."""
    ra, ca = ha
    dr, dc = hb[0] - ra, hb[1] - ca
    nbrs = _NBRS_ODD if ra % 2 else _NBRS_EVEN
    for d, (ndr, ndc) in enumerate(nbrs):
        if ndr == dr and ndc == dc:
            return _DIR_EDGE[d]
    return None


def _offset_to_cube(row: int, col: int) -> tuple[int, int, int]:
    q = col - (row - (row & 1)) // 2
    return q, row, -q - row


def _cube_to_offset(q: int, r: int) -> tuple[int, int]:
    return r, q + (r - (r & 1)) // 2


def _hex_line_between(ha: tuple, hb: tuple) -> list[tuple[int, int]]:
    """Return all hex coordinates on the straight cube-coord line from ha to hb (inclusive)."""
    qa, ra, sa = _offset_to_cube(ha[0], ha[1])
    qb, rb, sb = _offset_to_cube(hb[0], hb[1])
    n = max(abs(qa - qb), abs(ra - rb), abs(sa - sb))
    if n == 0:
        return [ha]
    out = []
    for i in range(n + 1):
        t = i / n
        qf = qa + t * (qb - qa)
        rf = ra + t * (rb - ra)
        sf = sa + t * (sb - sa)
        rq, rr, rs = round(qf), round(rf), round(sf)
        dq, dr, ds = abs(rq - qf), abs(rr - rf), abs(rs - sf)
        if dq > dr and dq > ds:
            rq = -rr - rs
        elif dr > ds:
            rr = -rq - rs
        else:
            rs = -rq - rr
        out.append(_cube_to_offset(rq, rr))
    return out


def _resample(coords: list[tuple], step: float) -> list[tuple[float, float]]:
    """Walk a polyline and yield points every `step` units."""
    if len(coords) < 2:
        return list(coords)
    pts = [coords[0]]
    carry = 0.0
    for i in range(len(coords) - 1):
        x0, y0 = coords[i]
        x1, y1 = coords[i + 1]
        seg_len = math.hypot(x1 - x0, y1 - y0)
        if seg_len == 0:
            continue
        t = (step - carry) / seg_len
        while t <= 1.0:
            pts.append((x0 + t * (x1 - x0), y0 + t * (y1 - y0)))
            t += step / seg_len
        carry = (1.0 - (t - step / seg_len)) * seg_len
    return pts

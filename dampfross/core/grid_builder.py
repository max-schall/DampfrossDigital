import math
from collections.abc import Callable
from pathlib import Path

import numpy as np
import platformdirs
from matplotlib.path import Path as MplPath
from pyproj import Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

from .hex_grid import HexGrid, SQRT3, _NBRS_ODD, _NBRS_EVEN
from .world_data import (fetch_world_land, fetch_elevation_batch,
                         fetch_cities_ne, fetch_country_borders_ne,
                         fetch_rivers_ne)

_ELEV_CACHE = Path(platformdirs.user_cache_dir("dampfross")) / "elevation"

DEFAULT_GRID_W = 50
DEFAULT_GRID_H = 50
_FILL = 0.88


def suggest_grid_size(
    geom: BaseGeometry, target_land: int = 850
) -> tuple[int, int]:
    """
    Return (grid_w, grid_h) so that approximately target_land hexes fall
    inside the region.

    Approach: project to LAEA, measure fill_ratio = polygon_area / bbox_area,
    then solve grid_w × grid_h = target_land / fill_ratio with the aspect
    ratio that makes hex_size equal in both dimensions (no wasted columns
    or rows on empty space).
    """
    c = geom.centroid
    laea = (f"+proj=laea +lat_0={c.y:.4f} +lon_0={c.x:.4f} "
            "+datum=WGS84 +units=m +no_defs")
    fwd = Transformer.from_crs("EPSG:4326", laea, always_xy=True)
    proj = transform(fwd.transform, geom)

    minx, miny, maxx, maxy = proj.bounds
    rw, rh = maxx - minx, maxy - miny
    if rw <= 0 or rh <= 0:
        return DEFAULT_GRID_W, DEFAULT_GRID_H

    fill = min(proj.area / (rw * rh), 0.95)
    if fill < 0.01:
        return DEFAULT_GRID_W, DEFAULT_GRID_H

    n_total = target_land / fill
    # Optimal aspect: equates hex_size from both constraints
    #   max(rw / (gw*_FILL*SQRT3), rh / (gh*_FILL*1.5)) → minimised when equal
    aspect = (rw * 1.5) / (rh * SQRT3)
    gw = max(10, min(300, round(math.sqrt(n_total * aspect))))
    gh = max(10, min(300, round(math.sqrt(n_total / aspect))))
    return gw, gh


def build_grid(
    geom: BaseGeometry,
    region_name: str = "",
    grid_w: int = DEFAULT_GRID_W,
    grid_h: int = DEFAULT_GRID_H,
    progress: Callable[[int, str], None] | None = None,
) -> HexGrid:

    def _p(pct, msg):
        if progress:
            progress(pct, msg)

    # 1. Project to LAEA
    _p(3, "Projecting to equal-area…")
    c = geom.centroid
    laea = (
        f"+proj=laea +lat_0={c.y:.4f} +lon_0={c.x:.4f} "
        "+datum=WGS84 +units=m +no_defs"
    )
    fwd = Transformer.from_crs("EPSG:4326", laea, always_xy=True)
    inv = Transformer.from_crs(laea, "EPSG:4326", always_xy=True)
    proj_geom = transform(fwd.transform, geom)

    # 2. Hex size
    _p(7, "Sizing hex grid…")
    minx, miny, maxx, maxy = proj_geom.bounds
    rw, rh = maxx - minx, maxy - miny
    hex_size_m = max(rw / (grid_w * _FILL * SQRT3), rh / (grid_h * _FILL * 1.5))

    col_offset = (grid_w - rw / (hex_size_m * SQRT3)) / 2.0
    row_offset = (grid_h - rh / (hex_size_m * 1.5)) / 2.0
    x_origin = minx - col_offset * hex_size_m * SQRT3
    y_origin = maxy + row_offset * hex_size_m * 1.5

    # 3. All hex centres
    _p(12, "Computing hex centres…")
    grid_r, grid_c = np.meshgrid(
        np.arange(grid_h, dtype=np.float64),
        np.arange(grid_w, dtype=np.float64),
        indexing="ij",
    )
    x_m = (grid_c + (grid_r % 2) * 0.5) * hex_size_m * SQRT3 + x_origin
    y_m = -grid_r * hex_size_m * 1.5 + y_origin

    # 4. Region containment
    # Erode the polygon by ~28 % of the hex radius before testing.
    # Hex centres that are only barely inside the polygon (thin coastal spurs,
    # narrow isthmuses, fjord walls thinner than a hex) get reclassified as sea.
    # This produces the bays, channels, and coastline nooks a board-game map needs.
    _p(18, "Testing region containment…")
    try:
        _eroded_geom = proj_geom.buffer(-hex_size_m * 0.28)
        region_path = (_geom_to_path(_eroded_geom)
                       if not _eroded_geom.is_empty
                       else _geom_to_path(proj_geom))
    except Exception:
        region_path = _geom_to_path(proj_geom)
    flat = np.column_stack([x_m.ravel(), y_m.ravel()])
    n = len(flat)
    chunk = 512 * 512
    mask = np.empty(n, dtype=bool)
    for i in range(math.ceil(n / chunk)):
        s, e = i * chunk, min((i + 1) * chunk, n)
        mask[s:e] = region_path.contains_points(flat[s:e])
        _p(18 + int(30 * e / n), f"Region containment… {e:,}/{n:,}")
    cells = mask.reshape(grid_h, grid_w)

    # Store for live coastline recomputation in the UI
    # (proj_geom is the pre-erosion projection; flat are the hex centres)

    # Thin-bridge removal: a morphological opening (erode then dilate) breaks
    # 1-hex-wide land connections — e.g. the Strait of Messina at coarse
    # resolution where no hex center falls in the narrow strait.
    # Only applied when erosion actually increases the component count, so
    # it never fires for regions with no such bridges.
    try:
        from scipy import ndimage as _ndi_open
        _s3o = np.ones((3, 3), dtype=bool)
        _eroded_o = _ndi_open.binary_erosion(cells, structure=_s3o)
        _, _n_orig_o  = _ndi_open.label(cells,     structure=_s3o)
        _, _n_eroded_o = _ndi_open.label(_eroded_o, structure=_s3o)
        if _n_eroded_o > _n_orig_o:
            cells = _ndi_open.binary_dilation(_eroded_o, structure=_s3o) & cells
            print(f"[cells] thin-bridge removal: "
                  f"{_n_orig_o} → {_n_eroded_o} components")
    except Exception as _exc_o:
        print(f"[cells] thin-bridge removal failed: {_exc_o}")

    grid = HexGrid(cells, region_name)
    grid.proj_geom = proj_geom
    grid.hex_flat  = flat

    # 5. World land (neighbouring countries)
    _p(50, "Fetching world land data…")
    try:
        world = fetch_world_land()
        _p(55, "Projecting world land…")
        world_proj = transform(fwd.transform, world)
        world_path = _geom_to_path(world_proj)
        _p(58, "Testing other-land containment…")
        other_mask = np.empty(n, dtype=bool)
        for i in range(math.ceil(n / chunk)):
            s, e = i * chunk, min((i + 1) * chunk, n)
            other_mask[s:e] = world_path.contains_points(flat[s:e])
        # other_land = world land that is NOT the region
        grid.other_land = other_mask.reshape(grid_h, grid_w) & ~cells
    except Exception as exc:
        print(f"[world_land] {exc}")
        grid.other_land = np.zeros((grid_h, grid_w), dtype=bool)

    # 5b. Country border lines (110m — fast, small file)
    _p(60, "Fetching country borders…")
    try:
        _cb_lons, _cb_lats = [], []
        for _cx, _cy in [(minx, miny), (minx, maxy), (maxx, miny), (maxx, maxy)]:
            _lo, _la = inv.transform(_cx, _cy)
            _cb_lons.append(_lo); _cb_lats.append(_la)
        raw_borders = fetch_country_borders_ne(
            min(_cb_lats), min(_cb_lons), max(_cb_lats), max(_cb_lons)
        )
        proj_borders = []
        for coords in raw_borders:
            lons_b = [p[0] for p in coords]
            lats_b = [p[1] for p in coords]
            xs_b, ys_b = fwd.transform(lons_b, lats_b)
            proj_borders.append(list(zip(xs_b, ys_b)))
        grid.country_border_segs = grid.trace_border_lines(
            proj_borders, hex_size_m, x_origin, y_origin
        )
    except Exception as exc:
        print(f"[country_borders] {exc}")

    # 5c. River-valley mask — hexes on or adjacent to a major river are never
    # mountain candidates (rivers run through valley floors in train games).
    _river_mask = np.zeros((grid_h, grid_w), dtype=bool)
    try:
        _lat_min_b = min(_cb_lats); _lat_max_b = max(_cb_lats)
        _lon_min_b = min(_cb_lons); _lon_max_b = max(_cb_lons)
        _raw_rivers = fetch_rivers_ne(_lat_min_b, _lon_min_b, _lat_max_b, _lon_max_b)
        for _rname, _coords in _raw_rivers[:8]:  # top 8 by length = major rivers only
            for _lon, _lat in _coords:
                _rx, _ry = fwd.transform(_lon, _lat)
                _lx, _ly = _rx - x_origin, y_origin - _ry
                _rr, _rc = HexGrid.pixel_to_hex(_lx, _ly, hex_size_m)
                if 0 <= _rr < grid_h and 0 <= _rc < grid_w:
                    _river_mask[_rr, _rc] = True
        _river_mask &= cells
    except Exception as exc:
        print(f"[rivers] mask failed: {exc}")

    # 6. Elevation — per-hex, land cells only (disk-cached per region+size).
    _p(63, "Fetching elevation data…")
    try:
        land_rows, land_cols = np.where(cells)
        elev_full = np.full((grid_h, grid_w), np.nan, dtype=np.float32)

        sx = x_m[land_rows, land_cols]
        sy = y_m[land_rows, land_cols]
        lons_arr, lats_arr = inv.transform(sx, sy)
        lats_a = np.asarray(lats_arr, dtype=np.float64)
        lons_a = np.asarray(lons_arr, dtype=np.float64)

        # Cache key: region_name + grid dims + land-cell count (catches cell-mask changes)
        _safe_name = "".join(c for c in region_name.lower() if c.isalnum() or c in "-_")
        _cache_key = f"{_safe_name}_{grid_w}x{grid_h}_{len(lats_a)}"
        _cache_file = _ELEV_CACHE / f"{_cache_key}.npz"
        _ELEV_CACHE.mkdir(parents=True, exist_ok=True)

        if _cache_file.exists():
            _p(72, "Loading cached elevation…")
            elev_flat = np.load(_cache_file)["elev"]
            print(f"[elevation] loaded from cache ({_cache_file.name})")
        else:
            def _elev_progress(done, total, extra=""):
                pct = 63 + int(12 * done / max(total, 1))
                _p(pct, f"Fetching elevation… {done}/{total}")

            elev_flat = fetch_elevation_batch(lats_a, lons_a, progress=_elev_progress)
            np.savez_compressed(_cache_file, elev=elev_flat)
            print(f"[elevation] cached to {_cache_file.name}")

        elev_full[land_rows, land_cols] = elev_flat

        grid.elevation = elev_full
        grid.elev_stride = 1
        _p(75, "Computing mountainous terrain…")
        grid.river_mask = _river_mask
        grid.is_mountainous = _compute_mountainous(grid.elevation, 1,
                                                    grid_h, grid_w, cells,
                                                    river_mask=_river_mask)
    except Exception as exc:
        print(f"[elevation] {exc}")

    # 7. Pre-compute region border segments
    _p(85, "Computing borders…")
    grid.compute_border_segs()

    # 8. Store projection metadata for the river worker (runs after map is shown)
    # Transform all 4 corners so LAEA distortion can't shrink the bbox
    _lons, _lats = [], []
    for _cx, _cy in [(minx, miny), (minx, maxy), (maxx, miny), (maxx, maxy)]:
        _lo, _la = inv.transform(_cx, _cy)
        _lons.append(_lo); _lats.append(_la)
    grid.laea_proj   = laea
    grid.hex_size_m  = hex_size_m
    grid.x_origin    = x_origin
    grid.y_origin    = y_origin
    grid.bbox_wgs84  = (min(_lats), min(_lons), max(_lats), max(_lons))

    # 9. Fetch and place cities
    _p(90, "Fetching cities…")
    try:
        lat_min_b, lon_min_b, lat_max_b, lon_max_b = grid.bbox_wgs84
        raw_cities = fetch_cities_ne(lat_min_b, lon_min_b, lat_max_b, lon_max_b)

        candidates = []
        for city in raw_cities:
            cx_m, cy_m = fwd.transform(city["lon"], city["lat"])
            lx = cx_m - x_origin
            ly = y_origin - cy_m
            row, col = HexGrid.pixel_to_hex(lx, ly, hex_size_m)
            if not grid.is_land(row, col):
                continue
            candidates.append({
                "row": row, "col": col,
                "name": city["name"],
                "population": city["population"],
            })

        # Deduplicate: two cities in same hex → keep larger
        by_hex: dict[tuple, dict] = {}
        for c in sorted(candidates, key=lambda x: x["population"], reverse=True):
            key = (c["row"], c["col"])
            if key not in by_hex:
                by_hex[key] = c
        candidates = list(by_hex.values())

        placed = _place_cities(candidates, grid, min_distance=6, max_count=36)

        # Force-place one city on each inhabited island component that got none.
        # Gap constraints may leave small island components (e.g. Orkney, Shetland)
        # cityless; we need at least one city there for ferry detection to work.
        try:
            from scipy import ndimage as _ndi
            _s3 = np.ones((3, 3), dtype=bool)
            _ilabeled, _n_icomp = _ndi.label(cells, structure=_s3)
            if _n_icomp > 1:
                _isizes = np.bincount(_ilabeled.ravel())
                _isizes[0] = 0
                _main_iid = int(np.argmax(_isizes))
                _placed_comps = {int(_ilabeled[c["row"], c["col"]]) for c in placed}
                for _cid in range(1, _n_icomp + 1):
                    if _cid == _main_iid or _cid in _placed_comps:
                        continue
                    _island_cands = [c for c in candidates
                                     if int(_ilabeled[c["row"], c["col"]]) == _cid]
                    if _island_cands:
                        _best = max(_island_cands, key=lambda c: c["population"])
                        placed.append(dict(_best))
                        print(f"[cities] island comp {_cid}: force-placed {_best['name']}")
        except Exception as _exc:
            print(f"[cities] island check failed: {_exc}")

        # Renumber north to south (row 0 = north, increasing row = south)
        placed.sort(key=lambda c: (c["row"], c["col"]))
        for i, city in enumerate(placed[:len(_CITY_NUMBERS)]):
            city["number"] = _CITY_NUMBERS[i]
        grid.cities = placed[:len(_CITY_NUMBERS)]
    except Exception as exc:
        print(f"[cities] {exc}")
        grid.cities = []

    # Cities are never mountain hexes — clear any overlap
    if grid.is_mountainous is not None:
        for city in grid.cities:
            grid.is_mountainous[city["row"], city["col"]] = False

    grid.ferries = []   # ferry routes are placed manually via the Ferries panel

    _p(98, "Done.")
    return grid


# ------------------------------------------------------------------ #

def recompute_cells(
    grid,
    erosion_pct: float = 0.28,
    bridge_kernel: int = 3,
) -> np.ndarray:
    """
    Re-derive the land/sea mask from the stored projected geometry with a new
    erosion factor and bridge-removal kernel size.  Returns a new bool array;
    does NOT modify grid in place.
    """
    from scipy import ndimage

    proj_geom  = grid.proj_geom
    hex_flat   = grid.hex_flat
    hex_size_m = grid.hex_size_m
    rows, cols = grid.rows, grid.cols

    if proj_geom is None or hex_flat is None:
        return grid.cells.copy()

    erosion_m = hex_size_m * erosion_pct
    try:
        if erosion_m > 0:
            eroded = proj_geom.buffer(-erosion_m)
            path = (_geom_to_path(eroded) if not eroded.is_empty
                    else _geom_to_path(proj_geom))
        else:
            path = _geom_to_path(proj_geom)
    except Exception:
        path = _geom_to_path(proj_geom)

    n = len(hex_flat)
    chunk = 512 * 512
    mask = np.empty(n, dtype=bool)
    for i in range(math.ceil(n / chunk)):
        s, e = i * chunk, min((i + 1) * chunk, n)
        mask[s:e] = path.contains_points(hex_flat[s:e])
    cells = mask.reshape(rows, cols)

    if bridge_kernel >= 3:
        struct   = np.ones((bridge_kernel, bridge_kernel), dtype=bool)
        s3       = np.ones((3, 3), dtype=bool)
        eroded_c = ndimage.binary_erosion(cells, structure=struct)
        _, n_e   = ndimage.label(eroded_c, structure=s3)
        _, n_o   = ndimage.label(cells,    structure=s3)
        if n_e > n_o:
            cells = ndimage.binary_dilation(eroded_c, structure=struct) & cells

    return cells


# ------------------------------------------------------------------ #

def _compute_mountainous(
    elevation: np.ndarray,
    stride: int,
    full_h: int,
    full_w: int,
    cells: np.ndarray,
    river_mask: np.ndarray | None = None,
    percentile: int = 65,
    prom_floor: float = 220.0,
    scatter_prom: float = 80.0,
    scatter_max: int = 8,
    scatter_blob: int = 5,
) -> np.ndarray:
    """
    Mark hexes as mountain ridges/peaks, leaving valley floors flat.

    Uses topographic prominence: how much above the local valley floor is each
    hex?  A ridge hex scores high; a valley floor scores near zero (it IS the
    local minimum); a flat plateau also scores near zero despite being elevated.
    This naturally carves valleys through mountainous regions — important for
    train-game route planning, as valleys are the cheap paths.

    Steps:
      1. Fill NaN values via nearest-valid propagation.
      2. Compute prominence = elevation − minimum_filter(5×5).
         Non-land cells keep their nearest-land value so coastlines don't pull
         the local minimum to sea level.
      3. Threshold at the median (p50) of land-cell prominence, floored at 80 m.
         Flat regions (p50 < 15 m) are skipped entirely.
      4. Component filter: drop blobs < 0.2 % of land hexes.
    """
    from scipy import ndimage

    elev = elevation.copy().astype(np.float32)
    nan_mask = np.isnan(elev)

    n_valid = int((~nan_mask).sum())
    n_land  = int(cells.sum())
    print(f"[mountains] elevation: {n_valid}/{elev.size} valid, land={n_land}")

    if n_land == 0:
        return np.zeros((full_h, full_w), dtype=bool)

    # 1. NaN fill via nearest-valid propagation
    if nan_mask.all():
        print("[mountains] all elevation NaN — elevation API may have failed")
        return np.zeros((full_h, full_w), dtype=bool)
    elev_fill = elev.copy()
    if nan_mask.any():
        _, idx = ndimage.distance_transform_edt(nan_mask, return_indices=True)
        elev_fill = elev_fill[tuple(idx)]

    # 2. Topographic prominence in a 5×5 hex window (~85 km for 17km/hex grids).
    # The window is large enough to capture the valley floor even for ranges
    # separated by 2-3 hex wide valleys.
    local_min = ndimage.minimum_filter(elev_fill, 5)
    prominence = (elev_fill - local_min).clip(min=0.0)
    prominence[~cells] = 0.0

    # 3. Threshold — driven by the slider parameters:
    #    percentile  : p-tile of land prominence used as threshold (lower → more mountains)
    #    prom_floor  : hard minimum prominence so flat plains are excluded
    #
    # Secondary criterion: a hex can also qualify via high absolute elevation, but ONLY
    # when it also has meaningful local relief (prominence >= _PROM_SECONDARY).
    # This correctly excludes elevated but flat plateaus (e.g. Spain's Meseta Central,
    # ~700 m elevation but near-zero prominence) while still catching alpine foothills
    # (high elevation AND significant relief above their immediate surroundings).
    _ELEV_MIN = 400   # m — minimum elevation for secondary qualification

    land_scores = prominence[cells]
    p_val = float(np.nanpercentile(land_scores, percentile))
    if p_val < 15.0:
        print(f"[mountains] flat region (p{percentile}={p_val:.0f} m) — skipping")
        return np.zeros((full_h, full_w), dtype=bool)
    threshold = max(p_val, prom_floor)

    # Secondary prominence floor scales with the primary threshold so that
    # reducing the coverage slider also reduces secondary coverage.
    # Factor 0.5 lets pre-Alpine foothills qualify while excluding flat plateaus.
    _PROM_SECONDARY = max(threshold * 0.5, 60.0)

    _no_mountain = ~cells
    if river_mask is not None:
        _no_mountain |= river_mask
    # Primary: sufficient local relief.
    # Secondary: elevated AND meaningful local relief relative to primary threshold.
    _high_elev = (elev_fill >= _ELEV_MIN) & (prominence >= _PROM_SECONDARY)
    candidate = ((prominence >= threshold) | _high_elev) & ~_no_mountain

    # 4. Component filter
    s3 = np.ones((3, 3), dtype=bool)
    labeled, n_comp = ndimage.label(candidate, structure=s3)
    min_size = max(2, int(n_land * 0.002))
    sizes = np.bincount(labeled.ravel())
    result = np.zeros((full_h, full_w), dtype=bool)
    kept = 0
    for cid in range(1, n_comp + 1):
        if sizes[cid] >= min_size:
            result[labeled == cid] = True
            kept += 1
    result &= cells

    # 5. Scatter pass: secondary lower-threshold tier for isolated lowland blobs.
    # Any land hex with prominence >= scatter_prom that is not adjacent to an
    # existing mountain cluster (3-hex exclusion zone) can form a small blob.
    mtn_zone = ndimage.binary_dilation(result, np.ones((7, 7), dtype=bool))
    _excl = ~cells | mtn_zone
    if river_mask is not None:
        _excl |= river_mask
    scatter_cand = (prominence >= scatter_prom) & ~_excl
    s_labeled, s_ncomp = ndimage.label(scatter_cand, structure=s3)
    s_sizes = np.bincount(s_labeled.ravel())
    scatter_blobs_list = []
    for cid in range(1, s_ncomp + 1):
        if 1 <= s_sizes[cid] <= scatter_blob:
            mean_p = float(prominence[s_labeled == cid].mean())
            scatter_blobs_list.append((mean_p, cid))
    scatter_blobs_list.sort(reverse=True)
    n_scatter = 0
    for _, cid in scatter_blobs_list[:scatter_max]:
        result[s_labeled == cid] = True
        n_scatter += 1
    result &= cells

    _n_river = int(river_mask.sum()) if river_mask is not None else 0
    print(f"[mountains] p{percentile}={p_val:.0f} m  threshold={threshold:.0f} m  "
          f"prom_secondary={_PROM_SECONDARY:.0f} m  elev_min={_ELEV_MIN} m  "
          f"river_masked={_n_river}  candidates={int(candidate.sum())}  "
          f"components={n_comp}  kept={kept}  scatter={n_scatter}  "
          f"mountain_cells={int(result.sum())}")
    return result


# City numbers: 6 groups × 6 = 36, matching one die-pair outcome each
_CITY_NUMBERS = [10 * g + n for g in range(1, 7) for n in range(1, 7)]


def _place_cities(
    candidates: list[dict],
    grid,
    min_distance: int = 6,
    max_count: int = 36,
) -> list[dict]:
    """
    Spread-first placement with a hard minimum gap derived from the region.

    hard_min = floor(sqrt(land_hexes / max_count)) — the natural spacing if
    cities were packed uniformly.  No phase ever goes below this, so a region
    whose real cities are geographically clustered (e.g. Swiss Mittelland)
    produces fewer but well-spread cities instead of a wall of dots.

    Scoring is quadratic in gap so "find the emptiest area" wins decisively
    over population or border proximity.
    """
    import math as _math

    n_land = int(grid.cells.sum())
    max_pop = max((c["population"] for c in candidates), default=1) or 1

    # Minimum spacing enforced in every phase — never pack cities closer than
    # sqrt(land_per_city) hexes apart.
    hard_min = max(2, int(_math.sqrt(n_land / max_count)))

    # Hexes that touch the region boundary (immediate non-land neighbour)
    border_hexes: set[tuple] = set()
    for c in candidates:
        r, ci = c["row"], c["col"]
        nbrs = _NBRS_ODD if r % 2 else _NBRS_EVEN
        if any(not grid.is_land(r + dr, ci + dc) for dr, dc in nbrs):
            border_hexes.add((r, ci))

    # Expand one hop so cities slightly inward from the edge still get the bonus
    near_border: set[tuple] = set(border_hexes)
    for r, ci in list(border_hexes):
        nbrs = _NBRS_ODD if r % 2 else _NBRS_EVEN
        for dr, dc in nbrs:
            if grid.is_land(r + dr, ci + dc):
                near_border.add((r + dr, ci + dc))

    accepted: list[dict] = []
    placed: set[tuple] = set()

    def _gap(city):
        if not accepted:
            return 999
        r, ci = city["row"], city["col"]
        return min(HexGrid.hex_distance(r, ci, a["row"], a["col"]) for a in accepted)

    def _score(city):
        g = _gap(city)
        b = 1 if (city["row"], city["col"]) in near_border else 0
        p = _math.log1p(city["population"]) / _math.log1p(max_pop)
        # Quadratic gap: gap=8 scores 4× higher than gap=4 (vs 2× with linear),
        # so the algorithm strongly seeks the most isolated available spot.
        return g * g * 2 + b * 3 + p * 0.5

    # Phases: generous → natural → hard minimum → one-step fallback.
    # hard_min is never crossed except in the final fallback phase (hard_min-1),
    # which lets country-wide datasets (e.g. Germany) fill to max_count while
    # a regionally-clustered dataset (e.g. Swiss Mittelland) simply stops early.
    p1 = max(min_distance, hard_min * 2)
    p2 = hard_min + 1
    p3 = hard_min
    p4 = max(2, hard_min - 1)
    for phase_min in sorted({p1, p2, p3, p4}, reverse=True):
        pool = [c for c in candidates if (c["row"], c["col"]) not in placed]
        while len(accepted) < max_count:
            eligible = [c for c in pool if _gap(c) >= phase_min]
            if not eligible:
                break
            best = max(eligible, key=_score)
            city = dict(best)
            accepted.append(city)
            placed.add((city["row"], city["col"]))
            pool.remove(best)

    print(f"[cities] hard_min={hard_min}  placed={len(accepted)}/{max_count}")
    return accepted[:max_count]


def _compute_ferries(
    cells: np.ndarray,
    cities: list[dict],
    grid_h: int,
    grid_w: int,
) -> list[dict]:
    """
    Find island land components and return ferry dicts:
        {"from_row", "from_col"}  — mainland endpoint (coastal city preferred)
        {"to_row",   "to_col"}    — island endpoint   (coastal city > coastal hex)
        {"path"}                  — [(row,col)…] sea-hex route; empty if unreachable
    """
    from scipy import ndimage
    from collections import deque

    s3 = np.ones((3, 3), dtype=bool)
    labeled, n_comp = ndimage.label(cells, structure=s3)
    if n_comp <= 1:
        return []

    sizes = np.bincount(labeled.ravel())
    sizes[0] = 0
    main_id = int(np.argmax(sizes))

    # All coastal hexes (land adjacent to sea)
    sea = ~cells
    coast_mask = ndimage.binary_dilation(sea, s3) & cells

    # Group placed cities by component
    city_by_comp: dict[int, list] = {}
    for city in cities:
        comp = int(labeled[city["row"], city["col"]])
        if comp > 0:
            city_by_comp.setdefault(comp, []).append(city)

    # Mainland coastal hexes and coastal cities
    main_coast_mask = coast_mask & (labeled == main_id)
    mrows, mcols = np.where(main_coast_mask)
    main_coast = list(zip(mrows.tolist(), mcols.tolist()))
    main_city_pos = {(c["row"], c["col"]) for c in city_by_comp.get(main_id, [])}
    main_coastal_cities = [(r, c) for r, c in main_coast if (r, c) in main_city_pos]

    def _nearest(pr, pc, candidates):
        return min(candidates, key=lambda rc: (pr - rc[0]) ** 2 + (pc - rc[1]) ** 2)

    def _find_sea_path(start_rc, end_rc):
        """BFS through sea hexes from a land hex to another land hex."""
        queue = deque([(start_rc, [start_rc])])
        visited = {start_rc}
        while queue:
            (r, c), path = queue.popleft()
            if (r, c) == end_rc:
                return path
            nbrs = _NBRS_ODD if r % 2 else _NBRS_EVEN
            for dr, dc in nbrs:
                nr, nc = r + dr, c + dc
                if (0 <= nr < grid_h and 0 <= nc < grid_w
                        and (nr, nc) not in visited
                        and (not cells[nr, nc] or (nr, nc) == end_rc)):
                    visited.add((nr, nc))
                    queue.append(((nr, nc), path + [(nr, nc)]))
        return []

    ferries: list[dict] = []
    for comp_id, island_cities in city_by_comp.items():
        if comp_id == main_id:
            continue

        # Island endpoint: prefer coastal city, then nearest coastal hex, then
        # any city as last resort — ferry must arrive on the shore.
        island_coast_mask = coast_mask & (labeled == comp_id)
        irows, icols = np.where(island_coast_mask)
        island_coast = list(zip(irows.tolist(), icols.tolist()))
        island_city_pos = {(c["row"], c["col"]) for c in island_cities}
        island_coastal_cities = [(r, c) for r, c in island_coast
                                  if (r, c) in island_city_pos]

        ref = main_coast or [(grid_h // 2, grid_w // 2)]
        if island_coastal_cities:
            ir, ic = min(island_coastal_cities,
                         key=lambda rc: min((rc[0]-r)**2+(rc[1]-c)**2
                                            for r, c in ref))
        elif island_coast:
            ir, ic = min(island_coast,
                         key=lambda rc: min((rc[0]-r)**2+(rc[1]-c)**2
                                            for r, c in ref))
        else:
            best = min(island_cities,
                       key=lambda city: min((city["row"]-r)**2+(city["col"]-c)**2
                                            for r, c in ref))
            ir, ic = best["row"], best["col"]

        # Mainland endpoint
        if main_coastal_cities:
            mr, mc = _nearest(ir, ic, main_coastal_cities)
        elif main_coast:
            mr, mc = _nearest(ir, ic, main_coast)
        elif main_id in city_by_comp:
            best = min(city_by_comp[main_id],
                       key=lambda city: (ir-city["row"])**2+(ic-city["col"])**2)
            mr, mc = best["row"], best["col"]
        else:
            continue

        sea_path = _find_sea_path((mr, mc), (ir, ic))

        ferries.append({"from_row": mr,  "from_col": mc,
                        "to_row":   ir,  "to_col":   ic,
                        "path":     sea_path})
    return ferries


def _geom_to_path(geom: BaseGeometry) -> MplPath:
    if geom.geom_type == "MultiPolygon":
        return MplPath.make_compound_path(*[_poly_to_path(p) for p in geom.geoms])
    return _poly_to_path(geom)


def _poly_to_path(poly) -> MplPath:
    verts, codes = [], []
    for ring in [poly.exterior, *poly.interiors]:
        coords = list(ring.coords)
        verts.extend(coords)
        codes += [MplPath.MOVETO] + [MplPath.LINETO] * (len(coords) - 2) + [MplPath.CLOSEPOLY]
    return MplPath(verts, codes)

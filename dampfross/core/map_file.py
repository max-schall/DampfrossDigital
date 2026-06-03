"""
Save / load .dmpfmap files.

Format: ZIP archive containing
  meta.json       – scalar metadata
  cities.json     – city list
  ferries.json    – ferry routes (waypoints as [row, col, corner_idx])
  arrays/*.npy    – numpy arrays  (cells, is_mountainous, other_land,
                                   elevation, river_mask, hex_flat)
  rivers/*.npy    – one file per river-segment array
  proj_geom.wkt   – Shapely projected geometry (optional)
"""
import io
import json
import zipfile
from pathlib import Path

import numpy as np

FORMAT_VERSION = 1


def save_map(grid, path: str | Path) -> None:
    path = Path(path)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:

        # ── scalar metadata ──────────────────────────────────────────── #
        meta = {
            "format_version": FORMAT_VERSION,
            "rows":        grid.rows,
            "cols":        grid.cols,
            "region_name": grid.region_name,
            "hex_size_m":  grid.hex_size_m,
            "x_origin":    grid.x_origin,
            "y_origin":    grid.y_origin,
            "laea_proj":   grid.laea_proj,
            "bbox_wgs84":  list(grid.bbox_wgs84),
            "river_count":           grid.river_count,
            "elev_stride":           grid.elev_stride,
            "max_ferries_per_player": getattr(grid, "max_ferries_per_player", 1),
        }
        zf.writestr("meta.json", json.dumps(meta, indent=2))

        # ── cities and ferries ───────────────────────────────────────── #
        zf.writestr("cities.json", json.dumps(grid.cities))
        t_over = getattr(grid, "terrain_overrides", {})
        if t_over:
            zf.writestr("terrain_overrides.json",
                        json.dumps({f"{r},{c}": v for (r, c), v in t_over.items()}))
        ferries_ser = [
            {"waypoints": [list(wp) for wp in f.get("waypoints", [])]}
            for f in grid.ferries
        ]
        zf.writestr("ferries.json", json.dumps(ferries_ser))

        # ── numpy arrays ─────────────────────────────────────────────── #
        def _npy(name, arr):
            if arr is None:
                return
            buf = io.BytesIO()
            np.save(buf, arr)
            zf.writestr(f"arrays/{name}.npy", buf.getvalue())

        _npy("cells",          grid.cells)
        _npy("is_mountainous", grid.is_mountainous)
        _npy("other_land",     grid.other_land)
        _npy("elevation",      grid.elevation)
        _npy("river_mask",     grid.river_mask)
        _npy("hex_flat",       grid.hex_flat)

        # ── river segments ───────────────────────────────────────────── #
        for i, seg in enumerate(grid.river_segs):
            buf = io.BytesIO()
            np.save(buf, seg)
            zf.writestr(f"rivers/{i}.npy", buf.getvalue())
        river_names = getattr(grid, "river_names", [])
        if river_names:
            zf.writestr("river_names.json", json.dumps(river_names))

        # ── projected geometry ───────────────────────────────────────── #
        if grid.proj_geom is not None:
            try:
                zf.writestr("proj_geom.wkt", grid.proj_geom.wkt)
            except Exception:
                pass


def load_map_bytes(data: bytes):
    """Load a HexGrid from raw .dmpfmap bytes (no file path needed)."""
    with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
        return _load_from_zip(zf)


def load_map(path: str | Path):
    with zipfile.ZipFile(Path(path), "r") as zf:
        return _load_from_zip(zf)


def _load_from_zip(zf):
    from ..core.hex_grid import HexGrid

    names = set(zf.namelist())

    meta        = json.loads(zf.read("meta.json"))
    cities      = json.loads(zf.read("cities.json"))
    ferries_ser = json.loads(zf.read("ferries.json"))

    def _npy(name):
        key = f"arrays/{name}.npy"
        if key not in names:
            return None
        return np.load(io.BytesIO(zf.read(key)))

    cells = _npy("cells")
    if cells is None:
        raise ValueError("cells array missing — corrupt or incompatible file")

    grid = HexGrid(cells.astype(bool), meta.get("region_name", ""))

    mtn = _npy("is_mountainous")
    grid.is_mountainous = mtn.astype(bool) if mtn is not None else None

    ol = _npy("other_land")
    grid.other_land = ol.astype(bool) if ol is not None else \
        np.zeros_like(cells, dtype=bool)

    grid.elevation  = _npy("elevation")

    rm = _npy("river_mask")
    grid.river_mask = rm.astype(bool) if rm is not None else None

    grid.hex_flat   = _npy("hex_flat")

    # River segments
    river_segs, i = [], 0
    while f"rivers/{i}.npy" in names:
        river_segs.append(np.load(io.BytesIO(zf.read(f"rivers/{i}.npy"))))
        i += 1
    grid.river_segs  = river_segs
    grid.river_names = (json.loads(zf.read("river_names.json"))
                        if "river_names.json" in names else [])
    grid.river_count            = meta.get("river_count", 0)
    grid.elev_stride            = meta.get("elev_stride", 1)
    grid.max_ferries_per_player = meta.get("max_ferries_per_player", 1)

    grid.hex_size_m  = meta.get("hex_size_m", 1.0)
    grid.x_origin    = meta.get("x_origin",   0.0)
    grid.y_origin    = meta.get("y_origin",   0.0)
    grid.laea_proj   = meta.get("laea_proj",  "")
    grid.bbox_wgs84  = tuple(meta.get("bbox_wgs84", (0.0, 0.0, 0.0, 0.0)))

    grid.cities  = cities
    if "terrain_overrides.json" in names:
        raw = json.loads(zf.read("terrain_overrides.json"))
        grid.terrain_overrides = {
            tuple(int(x) for x in k.split(",")): v
            for k, v in raw.items()
        }
    grid.ferries = [
        {"waypoints": [tuple(wp) for wp in f.get("waypoints", [])]}
        for f in ferries_ser
    ]

    if "proj_geom.wkt" in names:
        try:
            from shapely import wkt as _wkt
            grid.proj_geom = _wkt.loads(zf.read("proj_geom.wkt").decode("utf-8"))
        except Exception:
            pass

    grid.compute_border_segs()
    return grid

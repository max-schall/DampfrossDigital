import json
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import platformdirs
import requests

_CACHE = Path(platformdirs.user_cache_dir("dampfross"))
_UA = {"User-Agent": "DampfrossDigital/0.1 (max.f.schall@gmail.com)"}

_NE_BASE = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector"
    "/master/geojson/"
)
_LAND_URL    = _NE_BASE + "ne_110m_land.geojson"
_BORDERS_URL = _NE_BASE + "ne_110m_admin_0_boundary_lines_land.geojson"
_RIVERS_URL  = _NE_BASE + "ne_10m_rivers_lake_centerlines.geojson"
_CITIES_URL  = _NE_BASE + "ne_10m_populated_places.geojson"



def _load_ne(filename: str, download_url: str) -> dict:
    """Download a Natural Earth GeoJSON once, cache in ~/.cache/dampfross/."""
    cache = _CACHE / filename
    _CACHE.mkdir(parents=True, exist_ok=True)
    if not cache.exists():
        r = requests.get(download_url, timeout=120, headers=_UA)
        r.raise_for_status()
        cache.write_bytes(r.content)
    with cache.open(encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------ #
# World land polygon                                                   #
# ------------------------------------------------------------------ #

def fetch_country_borders_ne(lat_min, lon_min, lat_max, lon_max):
    """
    Return list of [(lon,lat),...] polylines for country borders overlapping bbox.
    Data: Natural Earth 110m admin-0 boundary lines (cached).
    """
    fc = _load_ne("ne_110m_admin_0_boundary_lines_land.geojson", _BORDERS_URL)
    b_lat0, b_lat1 = lat_min - 1.0, lat_max + 1.0
    b_lon0, b_lon1 = lon_min - 1.0, lon_max + 1.0
    lines = []
    for feat in fc["features"]:
        geom = feat.get("geometry")
        if not geom:
            continue
        gtype = geom["type"]
        if gtype == "LineString":
            raw_lines = [geom["coordinates"]]
        elif gtype == "MultiLineString":
            raw_lines = geom["coordinates"]
        else:
            continue
        for raw in raw_lines:
            coords = [(float(p[0]), float(p[1])) for p in raw]
            if len(coords) < 2:
                continue
            if not any(b_lon0 <= c[0] <= b_lon1 and b_lat0 <= c[1] <= b_lat1
                       for c in coords):
                continue
            lines.append(coords)
    return lines


def fetch_world_land():
    """Return a shapely geometry of all world land (cached on disk)."""
    from shapely.geometry import shape
    from shapely.ops import unary_union

    fc = _load_ne("ne_110m_land.geojson", _LAND_URL)
    geoms = [shape(feat["geometry"]) for feat in fc["features"] if feat.get("geometry")]
    return unary_union(geoms)


# ------------------------------------------------------------------ #
# Rivers (Natural Earth 10 m)                                         #
# ------------------------------------------------------------------ #

def fetch_rivers_ne(lat_min, lon_min, lat_max, lon_max):
    """
    Return list of (name, [(lon, lat), …]) for rivers overlapping bbox.
    Sorted longest-first.  Data: Natural Earth 10m river centerlines (cached).
    """
    fc = _load_ne("ne_10m_rivers.geojson", _RIVERS_URL)

    # Expand bbox slightly so rivers entering from outside are included
    b_lat0, b_lat1 = lat_min - 0.5, lat_max + 0.5
    b_lon0, b_lon1 = lon_min - 0.5, lon_max + 0.5

    rivers = []
    for feat in fc["features"]:
        geom = feat.get("geometry")
        if not geom:
            continue
        props = feat.get("properties", {})
        # Skip lake centerlines
        if "lake" in (props.get("featurecla") or "").lower():
            continue
        name = props.get("name_en") or props.get("name") or ""

        gtype = geom["type"]
        lines = (geom["coordinates"] if gtype == "LineString"
                 else geom["coordinates"] if gtype == "MultiLineString"
                 else None)
        if lines is None:
            continue
        # Normalise: LineString gives a flat list of points
        if gtype == "LineString":
            lines = [lines]

        for raw in lines:
            coords = [(float(pt[0]), float(pt[1])) for pt in raw]
            if len(coords) < 2:
                continue
            # Keep only if the line passes through or near the bbox
            if not any(b_lon0 <= c[0] <= b_lon1 and b_lat0 <= c[1] <= b_lat1
                       for c in coords):
                continue
            length = sum(
                math.hypot(coords[i+1][0] - coords[i][0],
                           coords[i+1][1] - coords[i][1])
                for i in range(len(coords) - 1)
            )
            rivers.append((name, coords, length))

    rivers.sort(key=lambda x: x[2], reverse=True)
    return [(name, coords) for name, coords, _ in rivers]


# ------------------------------------------------------------------ #
# Elevation (Open-Meteo elevation API — no key, parallel batches)      #
# ------------------------------------------------------------------ #

_METEO_ELEV_URL = "https://api.open-meteo.com/v1/elevation"
_BATCH_SIZE     = 100   # open-meteo supports up to 100 per GET request
_ELEV_WORKERS   = 8     # parallel HTTP workers


def _fetch_one_batch(start: int, lats_slice, lons_slice) -> tuple[int, list]:
    """Fetch one batch; return (start_index, list_of_elevations_or_nan)."""
    lat_str = ",".join(f"{v:.5f}" for v in lats_slice)
    lon_str = ",".join(f"{v:.5f}" for v in lons_slice)
    for attempt in range(3):
        try:
            resp = requests.get(
                _METEO_ELEV_URL,
                params={"latitude": lat_str, "longitude": lon_str},
                timeout=20,
                headers=_UA,
            )
            resp.raise_for_status()
            vals = resp.json().get("elevation", [])
            return start, [float(v) if v is not None else float("nan") for v in vals]
        except Exception as exc:
            if attempt == 2:
                n = len(lats_slice)
                print(f"[elevation] batch {start}–{start+n} failed: {exc}")
                return start, [float("nan")] * n


def fetch_elevation_batch(
    lats: np.ndarray,
    lons: np.ndarray,
    progress=None,
) -> np.ndarray:
    """
    Fetch elevation via Open-Meteo (SRTM data, no API key, free tier).
    Batches are fetched in parallel.  Returns float32 array in metres.
    """
    n = len(lats)
    result = np.full(n, np.nan, dtype=np.float32)

    batches = [
        (start, lats[start:start + _BATCH_SIZE], lons[start:start + _BATCH_SIZE])
        for start in range(0, n, _BATCH_SIZE)
    ]

    completed = 0
    with ThreadPoolExecutor(max_workers=_ELEV_WORKERS) as pool:
        futures = {
            pool.submit(_fetch_one_batch, start, ls, lo): start
            for start, ls, lo in batches
        }
        for fut in as_completed(futures):
            start, vals = fut.result()
            for i, v in enumerate(vals):
                result[start + i] = v
            completed += len(vals)
            if progress:
                progress(completed, n)

    if progress:
        progress(n, n)
    return result


# ------------------------------------------------------------------ #
# Cities (Natural Earth 10 m populated places)                        #
# ------------------------------------------------------------------ #

def fetch_cities_ne(lat_min, lon_min, lat_max, lon_max):
    """
    Return list of {'name', 'lon', 'lat', 'population'} inside bbox.
    Sorted by population descending.
    Data: Natural Earth 10m populated places (cached).
    """
    fc = _load_ne("ne_10m_populated_places.geojson", _CITIES_URL)

    cities = []
    for feat in fc["features"]:
        geom = feat.get("geometry")
        if not geom or geom["type"] != "Point":
            continue
        lon, lat = float(geom["coordinates"][0]), float(geom["coordinates"][1])
        if not (lat_min <= lat <= lat_max and lon_min <= lon <= lon_max):
            continue
        props = feat.get("properties", {})
        name = props.get("NAME_EN") or props.get("NAME") or ""
        if not name:
            continue
        pop = props.get("POP_MAX") or props.get("POP_MIN") or 0
        try:
            population = int(pop) if pop is not None else 0
        except (ValueError, TypeError):
            population = 0
        cities.append({
            "name":       name,
            "lon":        lon,
            "lat":        lat,
            "population": population,
        })

    cities.sort(key=lambda c: c["population"], reverse=True)
    return cities

import math
import requests
from shapely.geometry import MultiPolygon, shape
from shapely.geometry.base import BaseGeometry


def _strip_distant_parts(geom: BaseGeometry, max_km: float = 1000.0) -> BaseGeometry:
    """
    Remove sub-polygons whose centroid is farther than max_km from the largest
    sub-polygon's centroid.  Handles overseas territories (Canary Islands,
    French Guiana, etc.) that would otherwise distort the hex grid.
    No-op for single-Polygon geometries.
    """
    if geom.geom_type != "MultiPolygon":
        return geom
    polys = list(geom.geoms)
    if len(polys) <= 1:
        return geom

    main = max(polys, key=lambda p: p.area)
    mlat, mlon = main.centroid.y, main.centroid.x

    def _km(lat2, lon2):
        dlat = math.radians(lat2 - mlat)
        dlon = math.radians(lon2 - mlon)
        a = (math.sin(dlat / 2) ** 2
             + math.cos(math.radians(mlat)) * math.cos(math.radians(lat2))
             * math.sin(dlon / 2) ** 2)
        return 2.0 * 6371.0 * math.asin(math.sqrt(min(a, 1.0)))

    kept, dropped = [], []
    for p in polys:
        (kept if _km(p.centroid.y, p.centroid.x) <= max_km else dropped).append(p)

    if dropped:
        print(f"[region] stripped {len(dropped)} distant part(s) "
              f"(>{max_km:.0f} km from main territory)")

    if not kept:
        return geom
    return kept[0] if len(kept) == 1 else MultiPolygon(kept)


class RegionFetcher:
    _URL = "https://nominatim.openstreetmap.org/search"
    _HEADERS = {"User-Agent": "DampfrossDigital/0.1 (max.f.schall@gmail.com)"}

    def fetch(self, query: str) -> tuple[BaseGeometry, str]:
        """Return (geometry, display_name) for the best polygon match."""
        params = {
            "q": query,
            "format": "json",
            "polygon_geojson": 1,
            "limit": 5,
        }
        r = requests.get(self._URL, params=params, headers=self._HEADERS, timeout=30)
        r.raise_for_status()

        results = r.json()
        if not results:
            raise ValueError(f"No results found for '{query}'")

        for result in results:
            geojson = result.get("geojson", {})
            if geojson.get("type") in ("Polygon", "MultiPolygon"):
                geom = _strip_distant_parts(shape(geojson))
                return geom, result["display_name"]

        raise ValueError(
            f"No polygon boundary found for '{query}'. "
            "Try a country, state, or large city name."
        )

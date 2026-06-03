# Slider Reference

## Terrain panel

**Coverage: top N%**
Controls what percentage of land hexes become mountains. The slider value is a percentile — the algorithm ranks all land hexes by their *topographic prominence* (how much they stick up above their local valley floor) and marks the top `(100 - value)%` as mountain candidates. At the default of 65, the top 35% by prominence are candidates. Lower the slider → more mountains; raise it → fewer.

**Min prom: N m**
A hard floor on the prominence threshold. Even if the percentile calculation gives a low number (e.g. on a generally flat map), a hex must still have at least this many metres of local relief above its surroundings to qualify. This prevents gentle rolling lowlands from getting flagged as mountain. At 220 m, only genuine ridgelines pass; at 0 m, even slight bumps can qualify.

**Scatter: N m**
A secondary, lower threshold for *isolated* hills — blobs that sit far from any existing mountain cluster. These catch things like the Harz or Teutoburger Wald, which have real prominence but lose out in the main percentile pass because Germany's Alps dominate the ranking. Blobs found via this pass are capped in size (see next slider) so they don't flood the map.

**Blobs: N**
How many of those isolated scatter blobs to actually add. The candidates are sorted by average prominence (strongest first), and only the top N are kept. Set to 0 to disable scatter entirely; higher values add more outlying hill groups.

---

## Coastline panel

**Erosion: N%**
Before testing which hex centres fall inside the region polygon, the polygon is shrunk inward by `N% × hex_size`. This makes hexes near thin coastal spurs, narrow peninsulas, or shallow fjords reclassify as sea — producing bays, inlets, and irregular coastlines instead of a perfectly solid blob. The default 28% gives roughly one hex of coastal "bite". 0% = raw polygon boundary (fat coastline); 50% = aggressive erosion (many coastal hexes lost).

**Bridges: None / 3×3 / 5×5**
After the erosion test, a morphological opening (erode then dilate with the chosen kernel) is applied. This breaks 1-hex-wide land connections — most famously the Strait of Messina between Sicily and the Italian mainland, which at coarse resolution has no hex centre in the water. `None` skips this step entirely. `3×3` breaks single-hex-wide bridges; `5×5` is more aggressive and can cut through 2-hex-wide isthmuses too. Only fires if the erosion step actually increases the number of land components, so it never inadvertently splits a mainland.

#!/usr/bin/env python3
"""Makes the outline of Denmark for the network page (data/map/denmark.json) from Natural Earth
(public domain, ne_10m_admin_0_countries.geojson, https://github.com/nvkelso/natural-earth-vector).
Usage: python scripts/make_dk_map.py path/to/ne_10m_admin_0_countries.geojson
The outline is projected to a 1000-wide SVG (equirectangular, x scaled by cos 56°) and simplified;
small islands are dropped. PROJ in the output lets the page place cities with the same projection."""
import json, math, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LON0, LAT0, K = 7.9, 57.85, 222.0
CX = math.cos(math.radians(56))
def proj(lon, lat): return ((lon - LON0) * CX * K + 20, (LAT0 - lat) * K + 20)

def dp(pts, eps):
    if len(pts) < 3: return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1; L = math.hypot(dx, dy) or 1e-9
    i, dmax = 0, 0
    for k in range(1, len(pts) - 1):
        d = abs(dy * pts[k][0] - dx * pts[k][1] + x2 * y1 - y2 * x1) / L
        if d > dmax: i, dmax = k, d
    if dmax <= eps: return [pts[0], pts[-1]]
    return dp(pts[:i + 1], eps)[:-1] + dp(pts[i:], eps)

def area(p): return abs(sum(p[i][0] * p[i - 1][1] - p[i - 1][0] * p[i][1] for i in range(len(p)))) / 2

def main(src):
    gj = json.load(open(src, encoding="utf-8"))
    f = next(x for x in gj["features"] if x["properties"].get("ADM0_A3") == "DNK")
    polys = f["geometry"]["coordinates"] if f["geometry"]["type"] == "MultiPolygon" else [f["geometry"]["coordinates"]]
    paths = []
    for poly in polys:
        ring = [proj(lon, lat) for lon, lat in poly[0]]
        if area(ring) < 25: continue          # drop islets (about 0.5 km²... a few px²)
        m = len(ring) // 2
        s = dp(ring[:m + 1], 0.6)[:-1] + dp(ring[m:], 0.6)  # a closed ring is split in two before simplifying
        if len(s) < 4: continue
        paths.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in s) + "Z")
    w, h = proj(15.3, 54.5)
    out = {"source": "Natural Earth 1:10m admin-0 countries (public domain)", "viewBox": f"0 0 {w + 20:.0f} {h + 20:.0f}",
           "proj": {"lon0": LON0, "lat0": LAT0, "k": K, "cx": CX, "pad": 20}, "d": "".join(paths)}
    (ROOT / "data/map/denmark.json").write_text(json.dumps(out), encoding="utf-8")
    print(len(paths), "shapes,", len(out["d"]), "characters, viewBox", out["viewBox"])

if __name__ == "__main__":
    main(sys.argv[1])

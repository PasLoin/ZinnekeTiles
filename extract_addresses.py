#!/usr/bin/env python3
import argparse, json, math, re, sys
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.strtree import STRtree

HN = "addr:housenumber"
STREET = "addr:street"
DIR = "label_dir"
AREA_TYPES = ("Polygon", "MultiPolygon")
LINE_TYPES = ("LineString", "MultiLineString")
ICON_KEYS = ("entrance", "shop", "disused:shop", "amenity", "craft", "office", "tourism",
             "healthcare", "leisure", "emergency", "historic", "barrier", "vending")
NEAR = 1e-5
STEP_M = 2.0
DIRECTIONS = {"n": (0, 1), "s": (0, -1), "e": (1, 0), "w": (-1, 0)}
FALLBACK_DIR = "x"


def label(value):
    parts = [p.strip() for p in str(value).split(";") if p.strip()]
    return ", ".join(parts)


def norm(value):
    return re.sub(r"\s+", "", str(value or "")).lower()


def osm_key(feat):
    props = feat.get("properties") or {}
    return props.get("@type"), props.get("@id")


def as_area(geom):
    g = shape(geom)
    if g.is_empty or g.geom_type not in AREA_TYPES:
        return None
    if not g.is_valid:
        g = g.buffer(0)
    return None if g.is_empty else g


def anchor(geom):
    g = shape(geom)
    if g.is_empty:
        return None, None
    if g.geom_type == "Point":
        return g, None
    if g.geom_type in AREA_TYPES:
        g = as_area(geom)
        if g is None:
            return None, None
        c = g.centroid
        return (c if g.contains(c) else g.representative_point()), g
    if g.geom_type in LINE_TYPES:
        return g.interpolate(0.5, normalized=True), None
    return g.representative_point(), None


def rank(feat):
    gt = (feat.get("geometry") or {}).get("type")
    return 0 if gt in AREA_TYPES else 1


def unique_by_osm_id(features):
    best = {}
    order = []
    for feat in features:
        key = osm_key(feat)
        if key == (None, None):
            key = ("anon", len(order))
        if key not in best:
            order.append(key)
            best[key] = feat
        elif rank(feat) < rank(best[key]):
            best[key] = feat
    return [best[k] for k in order]


def has_icon(props):
    return any(props.get(k) not in (None, "", "no") for k in ICON_KEYS)


def same_address(a, b):
    if norm(a["hn"]) != norm(b["hn"]):
        return False
    return not a["street"] or not b["street"] or norm(a["street"]) == norm(b["street"])


def inward_dir(pt, area):
    dy = STEP_M / 111320.0
    dx = STEP_M / (111320.0 * max(math.cos(math.radians(pt.y)), 1e-6))
    inner = area.representative_point()
    vx, vy = inner.x - pt.x, (inner.y - pt.y) * dx / dy
    best, best_score = None, None
    for name, (ux, uy) in DIRECTIONS.items():
        inside = area.contains(Point(pt.x + ux * dx, pt.y + uy * dy))
        score = (1 if inside else 0, ux * vx + uy * vy)
        if best_score is None or score > best_score:
            best, best_score = name, score
    return best


def nearest_area(pt, tree, geoms):
    idx = tree.query(pt, predicate="dwithin", distance=NEAR)
    if len(idx) == 0:
        return None
    return min((geoms[i] for i in idx), key=lambda g: g.distance(pt))


def load_buildings(path):
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        print(f"⚠  {p} introuvable : pas d'orientation des étiquettes", file=sys.stderr)
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    out = []
    for feat in data.get("features") or []:
        if feat.get("geometry"):
            g = as_area(feat["geometry"])
            if g is not None:
                out.append(g)
    return out


def extract(features, buildings=None):
    stats = {"in": len(features), "nodes": 0, "areas": 0, "other": 0, "skipped": 0,
             "dup_in_area": 0, "icon_to_area": 0, "oriented": 0, "dup_same_spot": 0}
    candidates = [f for f in features if (f.get("properties") or {}).get(HN)]
    candidates = unique_by_osm_id(candidates)

    nodes, areas, others = [], [], []
    for feat in candidates:
        geom = feat.get("geometry")
        if not geom:
            stats["skipped"] += 1
            continue
        pt, area = anchor(geom)
        if pt is None:
            stats["skipped"] += 1
            continue
        props = feat["properties"]
        rec = {"pt": pt, "area": area, "hn": label(props[HN]), "street": props.get(STREET),
               "icon": geom.get("type") == "Point" and has_icon(props)}
        if not rec["hn"]:
            stats["skipped"] += 1
            continue
        if area is not None:
            areas.append(rec)
        elif geom.get("type") == "Point":
            nodes.append(rec)
        else:
            others.append(rec)

    dropped_areas = set()
    kept_nodes = []
    if areas:
        area_tree = STRtree([a["area"] for a in areas])
    for rec in nodes:
        matches = []
        if areas:
            idx = area_tree.query(rec["pt"], predicate="dwithin", distance=NEAR)
            matches = [int(i) for i in idx if same_address(rec, areas[int(i)])]
        if matches and rec["icon"]:
            stats["icon_to_area"] += 1
            continue
        dropped_areas.update(matches)
        kept_nodes.append(rec)
    stats["dup_in_area"] = len(dropped_areas)

    icon_nodes = [n for n in kept_nodes if n["icon"]]
    if icon_nodes:
        geoms = list(buildings or []) + [a["area"] for a in areas]
        tree = STRtree(geoms) if geoms else None
        for rec in icon_nodes:
            area = nearest_area(rec["pt"], tree, geoms) if tree is not None else None
            rec["dir"] = inward_dir(rec["pt"], area) if area is not None else FALLBACK_DIR
            if area is not None:
                stats["oriented"] += 1

    kept = kept_nodes + [a for i, a in enumerate(areas) if i not in dropped_areas] + others

    seen = set()
    out = []
    for rec in kept:
        x, y = round(rec["pt"].x, 7), round(rec["pt"].y, 7)
        key = (norm(rec["hn"]), norm(rec["street"]), x, y)
        if key in seen:
            stats["dup_same_spot"] += 1
            continue
        seen.add(key)
        props = {HN: rec["hn"]}
        if rec["street"]:
            props[STREET] = rec["street"]
        if rec.get("dir"):
            props[DIR] = rec["dir"]
        out.append({"type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [x, y]},
                    "properties": props})

    stats["nodes"] = len(nodes)
    stats["areas"] = len(areas)
    stats["other"] = len(others)
    stats["out"] = len(out)
    return out, stats


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", default="addresses.json")
    p.add_argument("--buildings", default=None)
    args = p.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f"✗  {src} introuvable", file=sys.stderr)
        sys.exit(1)

    data = json.loads(src.read_text(encoding="utf-8"))
    features, stats = extract(data.get("features") or [], load_buildings(args.buildings))
    Path(args.output).write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False),
        encoding="utf-8")
    print(f"  {stats['out']} adresses ({stats['nodes']} nodes, {stats['areas']} surfaces, "
          f"{stats['other']} autres, {stats['dup_in_area']} surfaces doublées par un node, "
          f"{stats['icon_to_area']} entrées/POI remplacés par leur bâtiment, "
          f"{stats['oriented']} étiquettes orientées vers l'intérieur, "
          f"{stats['dup_same_spot']} doublons même point, {stats['skipped']} ignorées)")


if __name__ == "__main__":
    main()

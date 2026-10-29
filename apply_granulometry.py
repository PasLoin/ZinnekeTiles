#!/usr/bin/env python3
import argparse, json, math, sys
from pathlib import Path

ZOOM_BLOCKS = [(z, z) for z in range(10, 19)]


def match_rule(rule, props):
    spec = rule.get("match")
    if not spec:
        return True
    for tag, allowed in spec.items():
        v = props.get(tag)
        if v is None:
            return False
        if allowed != ["*"] and str(v) not in [str(a) for a in allowed]:
            return False
    return True


def apply(rule, props):
    action = rule.get("action", "keep")
    kp     = rule.get("keep_properties", "ALL")
    if kp == "ALL":
        return action, None
    return action, list(kp)


def filter_props(props, keep):
    if keep is None: return dict(props)
    return {k: v for k, v in props.items() if k in keep}


def existing_range(feat):
    hint = feat.get("tippecanoe") or {}
    lo = hint.get("minzoom")
    hi = hint.get("maxzoom")
    return (lo if isinstance(lo, (int, float)) else float("-inf"),
            hi if isinstance(hi, (int, float)) else float("inf"))


def process(feat, rules):
    props = feat.get("properties") or {}
    lo, hi = existing_range(feat)
    segments = []

    for zmin, zmax in ZOOM_BLOCKS:
        if zmax < lo or zmin > hi:
            continue
        zmin, zmax = int(max(zmin, lo)), int(min(zmax, hi))
        for rule in rules:
            rmin = rule.get("zoom_min", 10)
            rmax = rule.get("zoom_max", 18)
            if rmax < zmin or rmin > zmax:
                continue
            if not match_rule(rule, props):
                continue
            action, keep = apply(rule, props)
            if action != "drop":
                segments.append((zmin, zmax, keep))
            break

    if not segments:
        return []

    merged = []
    a_zmin, a_zmax, a_keep = segments[0]
    for zmin, zmax, keep in segments[1:]:
        if keep == a_keep and zmin == a_zmax + 1:
            a_zmax = zmax
        else:
            merged.append((a_zmin, a_zmax, a_keep))
            a_zmin, a_zmax, a_keep = zmin, zmax, keep
    merged.append((a_zmin, a_zmax, a_keep))

    base_hint = dict(feat.get("tippecanoe") or {})
    out = []
    for zmin, zmax, keep in merged:
        hint = dict(base_hint)
        hint["minzoom"] = zmin
        hint["maxzoom"] = zmax
        f = {"type": "Feature", "geometry": feat.get("geometry"),
             "properties": filter_props(props, keep),
             "tippecanoe": hint}
        if feat.get("id") is not None:
            f["id"] = feat["id"]
        out.append(f)
    return out


def load_geojson(path):
    text = path.read_text()
    try:
        data = json.loads(text)
        if isinstance(data, dict) and data.get("type") == "Feature":
            return {"type": "FeatureCollection", "features": [data]}, True
        return data, False
    except json.JSONDecodeError:
        pass
    feats = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            feats.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return {"type": "FeatureCollection", "features": feats}, True


def tier_of(props, tiers):
    for i, tier in enumerate(tiers, 1):
        for tag, values in tier.items():
            v = props.get(tag)
            if v is None:
                continue
            if "*" in values or str(v) in values:
                return i
    return len(tiers) + 1


def point_of(geom):
    if not geom:
        return None
    coords = geom.get("coordinates")
    while isinstance(coords, list) and coords and isinstance(coords[0], list):
        coords = coords[0]
    if isinstance(coords, list) and len(coords) >= 2:
        return float(coords[0]), float(coords[1])
    return None


def grid_cell(lon, lat, zoom, size):
    world = 512 * 2 ** zoom
    lat = max(min(lat, 85.0511), -85.0511)
    s = math.sin(math.radians(lat))
    x = (lon + 180.0) / 360.0 * world
    y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * world
    return int(x // size), int(y // size)


def assign_ranks(features, cfg):
    tiers = cfg.get("tiers") or []
    zoom = cfg.get("zoom", 15)
    size = cfg.get("grid", 128)
    rank_field = cfg.get("rank_field", "poi_rank")
    tier_field = cfg.get("tier_field", "poi_tier")
    cells = {}
    keys = {}
    for idx, f in enumerate(features):
        props = f.get("properties")
        if props is None:
            props = f["properties"] = {}
        tier = tier_of(props, tiers)
        props[tier_field] = tier
        pt = point_of(f.get("geometry"))
        if pt is None:
            continue
        fid = f.get("id", ("idx", idx))
        late = 1 if (f.get("tippecanoe") or {}).get("minzoom", zoom) > zoom else 0
        key = (late, 0 if props.get("name") else 1, tier, str(fid))
        known = keys.get(fid)
        if known is None or key < known[0]:
            keys[fid] = (key, grid_cell(pt[0], pt[1], zoom, size))
    for fid, (key, cell) in keys.items():
        cells.setdefault(cell, []).append((key, fid))
    ranks = {}
    for members in cells.values():
        for pos, (_, fid) in enumerate(sorted(members), 1):
            ranks[fid] = pos
    for idx, f in enumerate(features):
        fid = f.get("id", ("idx", idx))
        if fid in ranks:
            f["properties"][rank_field] = ranks[fid]
    return len(cells)


def process_layer(name, rules, dry_run, rank=None):
    return process_file(Path(f"{name}.json"), rules, dry_run, rank)


def layer_jobs(name, cfg):
    files = cfg.get("files")
    if files:
        return [(f"{name} ({fname})", Path(fname), rules, None) for fname, rules in files.items()]
    return [(name, Path(f"{name}.json"), cfg.get("rules", []), cfg.get("rank"))]


def process_file(path, rules, dry_run, rank=None):
    if not path.exists():
        return {"error": f"{path} introuvable"}

    data, was_ndjson = load_geojson(path)
    feats = data.get("features", [])
    out, dropped, expanded = [], 0, 0

    for f in feats:
        r = process(f, rules)
        if not r:
            dropped += 1
        else:
            expanded += max(0, len(r) - 1)
            out.extend(r)

    cells = assign_ranks(out, rank) if rank else 0

    if not dry_run:
        data["features"] = out
        if was_ndjson:
            path.write_text("".join(json.dumps(f, ensure_ascii=False) + "\n" for f in out))
        else:
            path.write_text(json.dumps(data, ensure_ascii=False))

    return {"in": len(feats), "out": len(out),
            "dropped": dropped, "expanded": expanded, "cells": cells}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--gran",    default="granulometry.json")
    p.add_argument("--layers",  default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--report",  default="granulometry_report.md")
    args = p.parse_args()

    gran_path = Path(args.gran)
    if not gran_path.exists():
        print(f"✗  {gran_path} introuvable — lance d'abord build_map.py", file=sys.stderr)
        sys.exit(1)

    gran = json.loads(gran_path.read_text())
    layer_cfgs = gran.get("layers", {})

    targets = ([l.strip() for l in args.layers.split(",")]
               if args.layers else list(layer_cfgs.keys()))

    if args.dry_run:
        print("  (dry-run — aucun fichier modifié)")

    rows = []
    total_in = total_out = total_drop = 0

    for name in targets:
        cfg = layer_cfgs.get(name)
        if not cfg:
            print(f"  ⚠  {name} absent de {gran_path}")
            continue

        for label, path, rules, rank in layer_jobs(name, cfg):
            print(f"→ {label}  ({len(rules)} règles)", end="  ")
            stats = process_file(path, rules, args.dry_run, rank)

            if "error" in stats:
                print(f"✗  {stats['error']}")
                rows.append(f"| {label} | — | — | — | ✗ |")
                continue

            pct = round(100 * stats["out"] / stats["in"]) if stats["in"] else 0
            exp = f" +{stats['expanded']} splits" if stats["expanded"] else ""
            mark = "○" if args.dry_run else "✓"
            rk = f", rang sur {stats['cells']} cellules" if stats.get("cells") else ""
            print(f"{mark}  {stats['in']} → {stats['out']}  "
                  f"({stats['dropped']} drop{exp}{rk})")

            total_in   += stats["in"]
            total_out  += stats["out"]
            total_drop += stats["dropped"]
            rows.append(f"| {label} | {stats['in']} | {stats['out']} "
                        f"| {stats['dropped']} | {pct}% |")

    pct_total = round(100 * total_out / total_in) if total_in else 0
    report = ["# Granulometry report", "",
              f"Config: `{args.gran}`",
              f"Dry-run: {'oui' if args.dry_run else 'non'}", "",
              "| Layer | In | Out | Drop | % kept |",
              "| :--- | ---: | ---: | ---: | ---: |"] + rows + [
              f"| **Total** | **{total_in}** | **{total_out}** "
              f"| **{total_drop}** | **{pct_total}%** |"]
    Path(args.report).write_text("\n".join(report) + "\n")
    print(f"\n✓  rapport → {args.report}")
    print(f"✓  {total_in} → {total_out} features  "
          f"({pct_total}% conservés, {total_drop} supprimés)")

if __name__ == "__main__":
    main()

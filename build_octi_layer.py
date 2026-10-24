#!/usr/bin/env python3
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


def color(value):
    v = (value or "").strip().lstrip("#")
    return f"#{v.lower()}" if v else "#777777"


def text_colour(hex_colour):
    v = hex_colour.lstrip("#")
    try:
        r, g, b = (int(v[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return "#ffffff"
    return "#000000" if 0.299 * r + 0.587 * g + 0.114 * b > 0.6 else "#ffffff"


def route_of(line):
    lid = str(line.get("id") or "")
    return lid.split("-", 1)[0] if "-" in lid else ""


def convert(graph):
    features = graph.get("features") or []
    points = {}
    station_lines = defaultdict(set)
    station_routes = defaultdict(set)
    out = []

    for f in features:
        geom = f.get("geometry") or {}
        props = f.get("properties") or {}
        if geom.get("type") == "Point":
            points[str(props.get("id"))] = f

    for f in features:
        geom = f.get("geometry") or {}
        if geom.get("type") != "LineString":
            continue
        coords = geom.get("coordinates") or []
        if len(coords) < 2:
            continue
        props = f.get("properties") or {}
        lines = props.get("lines") or []
        n = len(lines)
        for i, line in enumerate(lines):
            col = color(line.get("color"))
            out.append({
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": {
                    "kind": "line",
                    "ref": str(line.get("label") or ""),
                    "route": route_of(line),
                    "colour": col,
                    "text_colour": text_colour(col),
                    "slot": i - (n - 1) / 2,
                    "lines": n,
                },
            })
            for end in ("from", "to"):
                nid = str(props.get(end))
                station_lines[nid].add(str(line.get("id")))
                station_routes[nid].add(route_of(line))

    best = {}
    for nid, f in points.items():
        name = (f.get("properties") or {}).get("station_label")
        if not name:
            continue
        score = len(station_lines[nid])
        if name not in best or score > best[name][1]:
            best[name] = (nid, score)
    primary = {nid for nid, _ in best.values()}

    for nid, f in points.items():
        props = f.get("properties") or {}
        name = props.get("station_label")
        if not name:
            continue
        out.append({
            "type": "Feature",
            "geometry": f["geometry"],
            "properties": {
                "kind": "station",
                "name": name,
                "lines": len(station_lines[nid]),
                "subway": 1 if "subway" in station_routes[nid] else 0,
                "primary": 1 if nid in primary else 0,
            },
        })
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="_tmp_stib_octi.json")
    p.add_argument("--output", default="public_transport_octi.json")
    args = p.parse_args()

    text = Path(args.input).read_text() if Path(args.input).exists() else ""
    if not text.strip():
        print(f"  ⚠  {args.input} vide ou absent", file=sys.stderr)
        sys.exit(1)
    features = convert(json.loads(text))
    with open(args.output, "w", encoding="utf-8") as f:
        for feat in features:
            f.write(json.dumps(feat, ensure_ascii=False) + "\n")
    n_lines = sum(1 for x in features if x["properties"]["kind"] == "line")
    print(f"  {n_lines} tracés, {len(features) - n_lines} stations -> {args.output}")


if __name__ == "__main__":
    main()

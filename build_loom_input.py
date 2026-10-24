#!/usr/bin/env python3
import argparse
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

OPERATOR = "STIB/MIVB"
DEFAULT_ROUTES = ["subway", "tram"]
DEFAULT_COLORS = {"subway": "1f4e9d", "tram": "c8102e", "bus": "f39200"}


def config_routes(config_path):
    if yaml is None or not Path(config_path).exists():
        return None
    config = yaml.safe_load(Path(config_path).read_text()) or {}
    layer = ((config.get("layers") or {}).get("public_transport") or {})
    routes = (layer.get("octilinear") or {}).get("routes")
    return [str(r) for r in routes] if routes else None


def clean_color(value, route):
    v = (value or "").strip().lstrip("#").lower()
    if len(v) == 3 and all(ch in "0123456789abcdef" for ch in v):
        v = "".join(ch * 2 for ch in v)
    if len(v) == 6 and all(ch in "0123456789abcdef" for ch in v):
        return v
    return DEFAULT_COLORS.get(route, "777777")


def ref_key(ref):
    digits = "".join(ch for ch in ref if ch.isdigit())
    return (int(digits) if digits else 10**6, ref)


def parse(osm_file, routes):
    nodes = {}
    names = {}
    ways = {}
    rels = []
    for _, elem in ET.iterparse(osm_file, events=("end",)):
        if elem.tag == "node":
            nid = int(elem.get("id"))
            lon, lat = elem.get("lon"), elem.get("lat")
            if lon and lat:
                nodes[nid] = (round(float(lon), 7), round(float(lat), 7))
            for t in elem.findall("tag"):
                if t.get("k") == "name":
                    names[nid] = t.get("v")
            elem.clear()
        elif elem.tag == "way":
            ways[int(elem.get("id"))] = [int(nd.get("ref")) for nd in elem.findall("nd")]
            elem.clear()
        elif elem.tag == "relation":
            tags = {t.get("k"): t.get("v") for t in elem.findall("tag")}
            if (tags.get("type") == "route"
                    and tags.get("operator") == OPERATOR
                    and tags.get("access") != "no"
                    and tags.get("route") in routes
                    and tags.get("ref")):
                way_ids, stop_ids = [], []
                for m in elem.findall("member"):
                    role = m.get("role") or ""
                    if m.get("type") == "way" and not role.startswith("platform"):
                        way_ids.append(int(m.get("ref")))
                    elif m.get("type") == "node" and role.startswith("stop"):
                        stop_ids.append(int(m.get("ref")))
                rels.append({"tags": tags, "ways": way_ids, "stops": stop_ids})
            elem.clear()
    return nodes, names, ways, rels


def build_lines(rels):
    colours = defaultdict(Counter)
    for rel in rels:
        t = rel["tags"]
        key = (t["route"], t["ref"])
        colours[key][clean_color(t.get("colour"), t["route"])] += 1
    lines = {}
    for (route, ref), counter in colours.items():
        lines[(route, ref)] = {"id": f"{route}-{ref}", "label": ref,
                               "color": counter.most_common(1)[0][0]}
    return lines


def build_graph(nodes, names, ways, rels, lines):
    way_lines = defaultdict(set)
    stops = {}
    for rel in rels:
        t = rel["tags"]
        line_id = lines[(t["route"], t["ref"])]["id"]
        for wid in rel["ways"]:
            if wid in ways:
                way_lines[wid].add(line_id)
        for nid in rel["stops"]:
            name = names.get(nid)
            if name and nid in nodes:
                stops[nid] = name

    usage = Counter()
    for wid in way_lines:
        refs = [n for n in ways[wid] if n in nodes]
        usage.update(set(refs))
        if refs:
            usage[refs[0]] += 1
            usage[refs[-1]] += 1

    line_info = {l["id"]: l for l in lines.values()}
    order = {l["id"]: i for i, l in enumerate(
        sorted(lines.values(), key=lambda l: (l["id"].split("-")[0], ref_key(l["label"]))))}

    edges = []
    graph_nodes = set()
    seen = set()
    for wid in sorted(way_lines):
        refs = [n for n in ways[wid] if n in nodes]
        if len(refs) < 2:
            continue
        props_lines = [line_info[i] for i in sorted(way_lines[wid], key=order.get)]
        start = 0
        for i in range(1, len(refs)):
            last = i == len(refs) - 1
            if not (last or usage[refs[i]] > 1 or refs[i] in stops):
                continue
            seg = refs[start:i + 1]
            start = i
            if seg[0] == seg[-1]:
                continue
            key = (min(seg[0], seg[-1]), max(seg[0], seg[-1]), wid, len(seg))
            if key in seen:
                continue
            seen.add(key)
            graph_nodes.update((seg[0], seg[-1]))
            edges.append({
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [list(nodes[n]) for n in seg]},
                "properties": {"from": str(seg[0]), "to": str(seg[-1]), "lines": props_lines},
            })

    features = []
    for nid in sorted(graph_nodes):
        props = {"id": str(nid)}
        if nid in stops:
            props["station_id"] = stops[nid]
            props["station_label"] = stops[nid]
        features.append({"type": "Feature",
                         "geometry": {"type": "Point", "coordinates": list(nodes[nid])},
                         "properties": props})
    return features + edges


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="_tmp_pt.osm")
    p.add_argument("--output", default="stib_loom_input.json")
    p.add_argument("--config", default="map.config.yaml")
    p.add_argument("--routes", default=None)
    args = p.parse_args()

    routes = (args.routes.split(",") if args.routes
              else config_routes(args.config) or DEFAULT_ROUTES)
    nodes, names, ways, rels = parse(args.input, set(routes))
    if not rels:
        print(f"  ⚠  aucune relation {OPERATOR} pour {routes}", file=sys.stderr)
    lines = build_lines(rels)
    features = build_graph(nodes, names, ways, rels, lines)
    Path(args.output).write_text(json.dumps(
        {"type": "FeatureCollection", "features": features}, ensure_ascii=False))
    n_edges = sum(1 for f in features if f["geometry"]["type"] == "LineString")
    n_stations = sum(1 for f in features if "station_id" in f["properties"])
    print(f"  {len(lines)} lignes ({', '.join(routes)}), {n_edges} arêtes, "
          f"{n_stations} arrêts -> {args.output}")


if __name__ == "__main__":
    main()

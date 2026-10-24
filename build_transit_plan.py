#!/usr/bin/env python3
import argparse
import gzip
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

from pmtiles.tile import Compression, TileType, zxy_to_tileid
from pmtiles.writer import Writer

DEFAULTS = {
    "layout": "octilinear",
    "geo_pen": 0,
    "aggregation_distance": 50,
    "min_zoom": 10,
    "max_zoom": 17,
    "bands": [
        {"from": 10, "line_width": 12, "line_spacing": 4, "outline_width": 4},
        {"from": 12, "line_width": 20, "line_spacing": 6, "outline_width": 6},
        {"from": 14, "line_width": 30, "line_spacing": 8, "outline_width": 8},
    ],
}

LAYERS = {
    "inner-connections": {"class": "String", "color": "String", "line": "String",
                          "line-color": "String", "lineCap": "String", "width": "String"},
    "lines": {"class": "String", "color": "String", "line": "String",
              "line-color": "String", "lineCap": "String", "width": "String"},
    "stations": {"color": "String", "fillColor": "String", "stationId": "String",
                 "stationLabel": "String", "width": "String"},
}


def settings(config_path):
    s = dict(DEFAULTS)
    if yaml is not None and Path(config_path).exists():
        config = yaml.safe_load(Path(config_path).read_text()) or {}
        raw = (((config.get("layers") or {}).get("public_transport") or {}).get("octilinear"))
        if isinstance(raw, dict):
            s.update({k: v for k, v in raw.items() if k in DEFAULTS})
    return s


def tool(loom_bin, name):
    if loom_bin:
        path = Path(loom_bin) / name
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    found = shutil.which(name)
    if not found:
        raise FileNotFoundError(name)
    return found


def run(cmd, stdin, stdout=subprocess.PIPE):
    proc = subprocess.run(cmd, input=stdin, stdout=stdout, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        tail = proc.stderr.decode("utf-8", "replace").strip().splitlines()[-5:]
        raise RuntimeError(f"{Path(cmd[0]).name} a échoué :\n  " + "\n  ".join(tail))
    return proc.stdout


def build_graph(s, bins, graph):
    topo = run([bins["topo"], "-d", str(s["aggregation_distance"])], graph)
    ordered = run([bins["loom"]], topo)
    return run([bins["octi"], "-b", str(s["layout"]), "--geo-pen", str(s["geo_pen"]),
                "--retry-on-error"], ordered)


def render_tiles(s, bins, graph, out_dir):
    bands = sorted(s["bands"], key=lambda b: b["from"])
    for i, band in enumerate(bands):
        lo = max(int(band["from"]), int(s["min_zoom"]))
        hi = (int(bands[i + 1]["from"]) - 1) if i + 1 < len(bands) else int(s["max_zoom"])
        hi = min(hi, int(s["max_zoom"]))
        if lo > hi:
            continue
        run([bins["transitmap"], "--render-engine=mvt", "-z", f"{lo}-{hi}",
             "--line-width", str(band["line_width"]),
             "--line-spacing", str(band["line_spacing"]),
             "--outline-width", str(band["outline_width"]),
             "--mvt-path", str(out_dir)], graph, stdout=subprocess.DEVNULL)


def tile_lon(x, z):
    return x / (1 << z) * 360.0 - 180.0


def tile_lat(y, z):
    return math.degrees(math.atan(math.sinh(math.pi - 2.0 * math.pi * y / (1 << z))))


def pack(tile_dir, output, name):
    tiles = []
    for path in Path(tile_dir).glob("*/*/*.mvt"):
        data = path.read_bytes()
        if data:
            z, x, y = int(path.parts[-3]), int(path.parts[-2]), int(path.stem)
            tiles.append((zxy_to_tileid(z, x, y), z, x, y, data))
    if not tiles:
        raise RuntimeError(f"aucune tuile produite dans {tile_dir}")
    tiles.sort()
    zooms = sorted({t[1] for t in tiles})
    top = [t for t in tiles if t[1] == zooms[-1]]
    w = tile_lon(min(t[2] for t in top), zooms[-1])
    e = tile_lon(max(t[2] for t in top) + 1, zooms[-1])
    n = tile_lat(min(t[3] for t in top), zooms[-1])
    s = tile_lat(max(t[3] for t in top) + 1, zooms[-1])
    with open(output, "wb") as f:
        writer = Writer(f)
        for tile_id, _, _, _, data in tiles:
            writer.write_tile(tile_id, gzip.compress(data, mtime=0))
        writer.finalize(
            {"tile_type": TileType.MVT, "tile_compression": Compression.GZIP,
             "min_zoom": zooms[0], "max_zoom": zooms[-1],
             "min_lon_e7": int(w * 1e7), "min_lat_e7": int(s * 1e7),
             "max_lon_e7": int(e * 1e7), "max_lat_e7": int(n * 1e7),
             "center_zoom": zooms[0] + 3,
             "center_lon_e7": int((w + e) / 2 * 1e7), "center_lat_e7": int((s + n) / 2 * 1e7)},
            {"name": name, "format": "pbf",
             "attribution": "© OpenStreetMap contributors · LOOM (Universität Freiburg)",
             "vector_layers": [{"id": k, "fields": v, "minzoom": zooms[0], "maxzoom": zooms[-1]}
                               for k, v in LAYERS.items()]},
        )
    return len(tiles), zooms


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="_tmp_stib_loom.json")
    p.add_argument("--output", default="public_transport_octi.pmtiles.gz")
    p.add_argument("--config", default="map.config.yaml")
    p.add_argument("--loom-bin", default=os.environ.get("LOOM_BIN", ""))
    p.add_argument("--keep-graph", default=None)
    args = p.parse_args()

    s = settings(args.config)
    try:
        bins = {n: tool(args.loom_bin, n) for n in ("topo", "loom", "octi", "transitmap")}
    except FileNotFoundError as missing:
        print(f"  ⚠  {missing} introuvable (LOOM_BIN ou PATH), plan non régénéré", file=sys.stderr)
        sys.exit(2)

    graph = Path(args.input).read_bytes()
    try:
        octi = build_graph(s, bins, graph)
        if args.keep_graph:
            Path(args.keep_graph).write_bytes(octi)
        with tempfile.TemporaryDirectory(prefix="stib_mvt_") as tmp:
            render_tiles(s, bins, octi, tmp)
            count, zooms = pack(tmp, args.output, Path(args.output).name.split(".")[0])
    except RuntimeError as err:
        print(f"  ⚠  {err}", file=sys.stderr)
        sys.exit(1)
    size = Path(args.output).stat().st_size / 1024
    print(f"  {count} tuiles z{zooms[0]}-{zooms[-1]} ({s['layout']}, geo_pen={s['geo_pen']}) "
          f"-> {args.output} ({size:.0f} ko)")


if __name__ == "__main__":
    main()

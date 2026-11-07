import sys
from functools import partial

from .colors import c
from .config import config_hash, lc, with_default_subtypes
from .density import density_meta, poi_density
from .layers.addresses import addresses
from .layers.boundaries import boundaries
from .layers.buildings import buildings
from .layers.cycleway import cycleway
from .layers.green import green
from .layers.landuse import landuse
from .layers.lazy import lazy_layers
from .layers.leisure import leisure, pitch_markings
from .layers.ordering import order_layers
from .layers.pedestrian import pedestrian
from .layers.poi import poi
from .layers.public_transport import public_transport
from .layers.railway import railway
from .layers.roads import roads
from .layers.street_furniture import street_furniture
from .layers.trees import trees
from .layers.water import water
from .legend import build_legend
from .palette import palette, palette_errors
from .patterns import resolve_patterns
from .sources import SOURCES, vector_source
from .variants import apply_variant


def build_style(config, variant=None):
    source_hash = config_hash(config)
    for err in palette_errors(config.get("palette")):
        print(f"⚠  {err}", file=sys.stderr)
    excluded = set()
    name = (config.get("map") or {}).get("name", "Map")
    if variant:
        config = apply_variant(config, variant)
        excluded = set(variant["raw"].get("exclude") or [])
        name = (variant["raw"].get("map") or {}).get("name") or f"{name} · {variant['label']}"
    config = with_default_subtypes(config)
    L = config.get("layers", {})
    M = config.get("map", {})
    bgc = c(M.get("background", "#f2efe9"))
    gl = M.get(
        "glyphs", "https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf"
    )
    pal = partial(palette, config)

    layers = [{"id": "background", "type": "background", "paint": {"background-color": bgc}}]
    layers += landuse(lc(L, "landuse"))
    layers += green(lc(L, "green"))
    layers += water(lc(L, "water"), pal("water"))
    layers += leisure(lc(L, "leisure"), pal("leisure"))
    layers += buildings(lc(L, "buildings"), pal("buildings"))
    layers += addresses(lc(L, "addresses"), pal("addresses"))
    layers += trees(lc(L, "trees"), bgc)
    layers += railway(lc(L, "railway"), pal("railway"))
    layers += public_transport(lc(L, "public_transport"), pal("public_transport"))
    layers += roads(lc(L, "roads"), pal("roads"))
    layers += pedestrian(lc(L, "pedestrian"), pal("pedestrian"))
    layers += cycleway(lc(L, "cycleway"), pal("cycleway"))
    layers += boundaries(lc(L, "boundaries"))
    layers += pitch_markings(lc(L, "leisure")["sports"])
    layers += poi(lc(L, "poi"), pal("poi"))
    layers += street_furniture(lc(L, "street_furniture"))
    layers = [layer for layer in layers if layer.get("source") not in excluded]
    layers, first_label = order_layers(layers)

    sources = {n: vector_source(n) for n in SOURCES if n not in excluded}
    meta_map = {
        k: M[k]
        for k in ("name", "version", "center", "zoom", "background", "font", "glyphs")
        if k in M
    }
    meta_tiles = {n: dict(raw["tiles"]) for n, raw in L.items() if (raw or {}).get("tiles")}
    metadata = {
        "brussels:map": meta_map,
        "brussels:config_hash": source_hash,
        "brussels:patterns": resolve_patterns(config, layers),
        "brussels:legend": build_legend(config, layers),
    }
    if meta_tiles:
        metadata["brussels:tiles"] = meta_tiles
    density = poi_density(L.get("poi")) if "poi" not in excluded else None
    if density:
        metadata["brussels:poi_density"] = density_meta(density)
    lazy = lazy_layers(config, lc(L, "buildings"), first_label, excluded)
    if lazy:
        metadata["brussels:lazy"] = lazy
    if variant:
        metadata["brussels:variant"] = {
            "id": variant["id"],
            "label": variant["label"],
            "hash": config_hash(variant["raw"]),
        }
    return {
        "version": 8,
        "name": name,
        "metadata": metadata,
        "sources": sources,
        "glyphs": gl,
        "layers": layers,
    }

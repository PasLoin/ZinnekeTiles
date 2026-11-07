from .config import with_default_subtypes
from .density import POI_RANK_FIELD, POI_TIER_FIELD, poi_density
from .layers.roads import ROAD_ORDER, road_subtype
from .pmtiles import tile_inputs
from .sources import SOURCES

SUBTYPE_ONLY_LAYERS = {"landuse", "trees", "railway", "pedestrian"}


POI_PROPS = [
    "amenity",
    "shop",
    "disused:shop",
    "tourism",
    "craft",
    "office",
    "healthcare",
    "leisure",
    "historic",
    "emergency",
    "name",
    "name:fr",
    "name:nl",
    "cuisine",
    "opening_hours",
    "addr:street",
    "addr:housenumber",
    "website",
    "religion",
    "level",
    "level_min",
    "level_max",
    "level_approx",
    "level_hint",
]


def build_granulometry(config):
    config = with_default_subtypes(config)
    L = config.get("layers", {})
    out = {"_meta": {"generated_by": "build_map.py"}, "layers": {}}
    names = [n for n in L if n in SOURCES] + [n for n in SOURCES if n not in L]
    for name in names:
        raw = L.get(name) or {}
        ap = raw.get("appear_at", 10)
        st = raw.get("subtypes") or {}
        rules = []
        if name == "roads":
            LOW = ["highway", "name", "ref", "tunnel", "bridge", "layer", "oneway"]
            HIGH = LOW + ["maxspeed", "lanes", "access"]
            for hw in ROAD_ORDER:
                gap = road_subtype(raw, hw)["appear_at"]
                if gap > 10:
                    rules.append(
                        {
                            "match": {"highway": [hw]},
                            "zoom_min": 10,
                            "zoom_max": gap - 1,
                            "action": "drop",
                        }
                    )
                mid = min(gap + 4, 18)
                rules.append(
                    {
                        "match": {"highway": [hw]},
                        "zoom_min": gap,
                        "zoom_max": mid,
                        "keep_properties": LOW,
                    }
                )
                if mid < 18:
                    rules.append(
                        {
                            "match": {"highway": [hw]},
                            "zoom_min": mid + 1,
                            "zoom_max": 18,
                            "keep_properties": HIGH,
                        }
                    )
            rules.append(
                {
                    "match": {"man_made": ["bridge", "tunnel"]},
                    "zoom_min": 10,
                    "zoom_max": 18,
                    "keep_properties": ["man_made", "name", "layer", "bridge", "tunnel"],
                }
            )
        elif name == "poi":
            for pt, scfg in sorted(st.items()):
                scfg = scfg or {}
                pap = scfg.get("appear_at", ap)
                tag = scfg.get("tag", "amenity")
                if pap > 10:
                    rules.append(
                        {
                            "match": {tag: [pt]},
                            "zoom_min": 10,
                            "zoom_max": pap - 1,
                            "action": "drop",
                        }
                    )
                rules.append(
                    {
                        "match": {tag: [pt]},
                        "zoom_min": pap,
                        "zoom_max": 18,
                        "keep_properties": POI_PROPS,
                    }
                )
            if ap > 10:
                rules.append({"zoom_min": 10, "zoom_max": ap - 1, "action": "drop"})
            rules.append({"zoom_min": ap, "zoom_max": 18, "keep_properties": POI_PROPS})
        elif name in SUBTYPE_ONLY_LAYERS and st:
            for stk, scfg in sorted(st.items()):
                scfg = scfg or {}
                sap = scfg.get("appear_at", ap)
                tag = scfg.get("tag", name)
                if sap > 10:
                    rules.append(
                        {
                            "match": {tag: [stk]},
                            "zoom_min": 10,
                            "zoom_max": sap - 1,
                            "action": "drop",
                        }
                    )
                rules.append(
                    {
                        "match": {tag: [stk]},
                        "zoom_min": sap,
                        "zoom_max": 18,
                        "keep_properties": "ALL",
                    }
                )
            rules.append({"zoom_min": 10, "zoom_max": 18, "action": "drop"})
        else:
            if ap > 10:
                rules.append({"zoom_min": 10, "zoom_max": ap - 1, "action": "drop"})
            for stk, scfg in sorted(st.items()):
                scfg = scfg or {}
                sap = scfg.get("appear_at", ap)
                tag = scfg.get("tag", name)
                if sap > ap:
                    rules.append(
                        {
                            "match": {tag: [stk]},
                            "zoom_min": ap,
                            "zoom_max": sap - 1,
                            "action": "drop",
                        }
                    )
            rules.append({"zoom_min": ap, "zoom_max": 18, "keep_properties": "ALL"})
        if name == "buildings":
            out["layers"][name] = {
                "files": {
                    i["file"]: [
                        {
                            "zoom_min": i["min_zoom"],
                            "zoom_max": i["max_zoom"],
                            "keep_properties": "ALL",
                        }
                    ]
                    for i in tile_inputs(config, "buildings")
                }
            }
            continue
        out["layers"][name] = {"rules": rules}
        density = poi_density(raw) if name == "poi" else None
        if density:
            out["layers"][name]["rank"] = {
                "grid": density["grid"],
                "zoom": min(density["show"]) if density["show"] else ap,
                "tiers": density["tiers"],
                "rank_field": POI_RANK_FIELD,
                "tier_field": POI_TIER_FIELD,
            }
    return out

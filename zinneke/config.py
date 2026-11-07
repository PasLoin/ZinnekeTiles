import hashlib
import json

from .colors import c
from .density import poi_density


def lc(layers, name):
    r = layers.get(name) or {}
    ap = r.get("appear_at", 10)
    return {
        "label": r.get("label", name.capitalize()),
        "color": c(r.get("color")),
        "border_color": c(r.get("border_color")),
        "visible": r.get("visible", True),
        "appear_at": ap,
        "labels_at": r.get("labels_at", ap + 3),
        "opacity": r.get("opacity", 1.0),
        "subtypes": r.get("subtypes") or {},
        "extrusion_3d": r.get("extrusion_3d", False),
        "sports": r.get("sports"),
        "materials": {str(k): c(v) for k, v in (r.get("materials") or {}).items()},
        "osm_colour": r.get("osm_colour", True),
        "density": poi_density(r),
    }


def sc(cfg, key):
    s = cfg["subtypes"].get(key) or {}
    return {
        "tag": s.get("tag"),
        "color": c(s.get("color", cfg["color"])),
        "color_private": c(s.get("color_private")),
        "pattern": s.get("pattern"),
        "pattern_private": s.get("pattern_private"),
        "outline_color": c(s.get("outline_color")),
        "appear_at": s.get("appear_at", cfg["appear_at"]),
        "opacity": s.get("opacity", cfg["opacity"]),
        "by": s.get("by"),
        "by_color": {k: c(v) for k, v in (s.get("by_color") or {}).items()},
        "by_pattern": dict(s.get("by_pattern") or {}),
        "pattern_at": s.get("pattern_at"),
        "tunnel_color": c(s.get("tunnel_color")),
    }


DEFAULT_SUBTYPES = {
    "water": {
        "river": {"tag": "waterway", "appear_at": 10},
        "canal": {"tag": "waterway", "appear_at": 10},
        "stream": {"tag": "waterway", "appear_at": 13},
        "ditch": {"tag": "waterway", "appear_at": 14},
    },
    "trees": {
        "hedge": {"tag": "barrier", "appear_at": 14, "opacity": 0.85},
        "tree_row": {"tag": "natural", "appear_at": 15, "opacity": 0.55},
        "tree": {"tag": "natural", "appear_at": 17},
    },
    "pedestrian": {
        "pedestrian": {"tag": "highway", "appear_at": 13},
        "footway": {"tag": "highway", "appear_at": 14},
        "path": {"tag": "highway", "appear_at": 14},
        "steps": {"tag": "highway", "appear_at": 14},
    },
    "green": {
        "wood": {"tag": "natural", "color": "#add19e"},
        "grassland": {"tag": "natural", "color": "#cdebb0"},
    },
    "railway": {
        "rail": {"tag": "railway", "appear_at": 10},
        "subway": {"tag": "railway", "appear_at": 12},
        "tram": {"tag": "railway", "appear_at": 13},
        "miniature": {"tag": "railway", "appear_at": 14},
    },
}


def with_default_subtypes(config):
    layers = dict(config.get("layers") or {})
    for name, defaults in DEFAULT_SUBTYPES.items():
        raw = dict(layers.get(name) or {})
        st = {k: dict(v or {}) for k, v in (raw.get("subtypes") or {}).items()}
        for key, dflt in defaults.items():
            if key == "pedestrian" and "pedestrian_street" in st and "pedestrian" not in st:
                st["pedestrian"] = dict(st["pedestrian_street"])
            st[key] = {**dflt, **(st.get(key) or {})}
        raw["subtypes"] = st
        layers[name] = raw
    return {**config, "layers": layers}


def config_hash(config):
    canon = json.dumps(config, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:12]

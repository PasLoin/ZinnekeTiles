from ..colors import c

INDOOR_DEFAULTS = {
    "appear_at": 15,
    "level_height": 3.0,
    "slab": 0.3,
    "volume_ratio": 0.9,
    "floor_opacity": 0.9,
    "volume_opacity": 0.35,
    "colors": {
        "platform": "#b7a4e3",
        "footway": "#f2c38c",
        "corridor": "#f2c38c",
        "pedestrian": "#e9dcc2",
        "steps": "#d9822b",
        "room": "#c98f5a",
        "area": "#d8bf8f",
        "wall": "#5f5f5f",
        "elevator": "#3d7cc9",
        "escalator": "#b8542a",
        "arrow": "#fffaf0",
    },
}


INDOOR_VOLUME_KINDS = ["room", "wall", "elevator"]


INDOOR_FLOOR_KINDS = [
    "platform",
    "footway",
    "corridor",
    "pedestrian",
    "steps",
    "escalator",
    "room",
    "area",
]


INDOOR_ARROW_KINDS = ["arrow"]


INDOOR_ARROW_THICKNESS = 0.12


INDOOR_DEFAULT_WINDOW = {"lo": 0, "hi": 99, "offset": 0}


def indoor_settings(config):
    raw = (config.get("layers") or {}).get("indoor") or {}
    colors = dict(INDOOR_DEFAULTS["colors"])
    for kind, scfg in (raw.get("subtypes") or {}).items():
        if (scfg or {}).get("color"):
            colors[kind] = c(scfg["color"])
    out = {k: raw.get(k, v) for k, v in INDOOR_DEFAULTS.items() if k != "colors"}
    out["colors"] = colors
    return out


def indoor_value(field):
    if field == "top":
        return ["to-number", ["coalesce", ["get", "z_top"], ["get", "level_max"]], 0]
    return ["to-number", ["get", field], 0]


def indoor_level_expr(field, window, level_height):
    clamped = ["max", window["lo"], ["min", window["hi"], indoor_value(field)]]
    return ["*", ["-", clamped, window["offset"]], level_height]


def indoor_paint(extrusion, window, settings):
    h = settings["level_height"]
    base = indoor_level_expr("level_min", window, h)
    top = indoor_level_expr("top", window, h)
    if extrusion == "arrow":
        lifted = ["+", top, settings["slab"]]
        return {
            "fill-extrusion-base": lifted,
            "fill-extrusion-height": ["+", lifted, INDOOR_ARROW_THICKNESS],
        }
    extra = settings["slab"] if extrusion == "slab" else round(h * settings["volume_ratio"], 3)
    return {"fill-extrusion-base": base, "fill-extrusion-height": ["+", top, extra]}


def indoor_layers(settings):
    colors = settings["colors"]
    color_expr = ["match", ["get", "kind"]]
    for kind in sorted(colors):
        color_expr += [kind, colors[kind]]
    color_expr.append(colors["area"])
    out = []
    for lid, extrusion, kinds, opacity in (
        ("indoor-3d-floor", "slab", INDOOR_FLOOR_KINDS, settings["floor_opacity"]),
        ("indoor-3d-volume", "volume", INDOOR_VOLUME_KINDS, settings["volume_opacity"]),
        ("indoor-3d-arrows", "arrow", INDOOR_ARROW_KINDS, 1.0),
    ):
        paint = {"fill-extrusion-color": color_expr, "fill-extrusion-opacity": opacity}
        paint.update(indoor_paint(extrusion, INDOOR_DEFAULT_WINDOW, settings))
        out.append(
            {
                "id": lid,
                "type": "fill-extrusion",
                "source": "indoor",
                "source-layer": "indoor",
                "minzoom": settings["appear_at"],
                "metadata": {"brussels:group": "indoor", "brussels:extrusion": extrusion},
                "filter": ["in", ["get", "kind"], ["literal", kinds]],
                "layout": {"visibility": "none"},
                "paint": paint,
            }
        )
    return out

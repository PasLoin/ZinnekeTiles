from ..colors import c
from ..config import sc
from ..palette import palette


def leisure(cfg, pal=None):
    pal = pal or palette({}, "leisure")
    st = cfg["subtypes"]

    fill_expr = ["match", ["get","leisure"]]
    for k in sorted(st):
        s = sc(cfg, k)
        if s["color"]: fill_expr += [k, s["color"]]
    fill_expr.append(cfg["color"] or "#def3c0")
    if len(fill_expr) == 3:
        fill_expr = fill_expr[2]

    outline_expr = ["match", ["get","leisure"]]
    has_custom_outline = False
    for k in sorted(st):
        s = sc(cfg, k)
        if s["outline_color"]:
            outline_expr += [k, s["outline_color"]]
            has_custom_outline = True
    outline_expr.append(pal["outline"])

    out = [
        {"id":"leisure-fill","type":"fill",
         "source":"leisure","source-layer":"leisure",
         "filter":["==",["geometry-type"],"Polygon"],
         "paint":{"fill-color":fill_expr,"fill-opacity":1.0}},
        {"id":"leisure-outline","type":"line",
         "source":"leisure","source-layer":"leisure",
         "filter":["==",["geometry-type"],"Polygon"],
         "paint":{"line-color": outline_expr if has_custom_outline else pal["outline"],
                  "line-width":.5}},
    ]
    return out + pitch_surfaces(cfg.get("sports"))


SPORT_RENDER_KEY = "sport_render"


def _sport_values(sports, field, default):
    values = sports.get("values") or {}
    expr = ["match", ["get", SPORT_RENDER_KEY]]
    for k in sorted(values):
        v = (values[k] or {}).get(field)
        if v is not None:
            expr += [k, c(v) if isinstance(v, str) else v]
    if len(expr) == 2:
        return default
    expr.append(default)
    return expr


def _pitch_filter(geometry):
    return ["all", ["match", ["get", "leisure"], ["pitch"], True, False],
                   ["has", SPORT_RENDER_KEY],
                   ["==", ["geometry-type"], geometry]]


def pitch_surfaces(sports):
    if not sports:
        return []
    dflt = sports.get("default") or {}
    return [
        {"id": "pitch-sport-fill", "type": "fill",
         "source": "leisure", "source-layer": "leisure",
         "filter": _pitch_filter("Polygon"),
         "paint": {"fill-color": _sport_values(sports, "color", c(dflt.get("color", "#8ad3af"))),
                   "fill-opacity": 1.0}},
        {"id": "pitch-sport-outline", "type": "line",
         "source": "leisure", "source-layer": "leisure",
         "filter": _pitch_filter("Polygon"),
         "paint": {"line-color": _sport_values(sports, "outline_color",
                                               c(dflt.get("outline_color", "#6fb792"))),
                   "line-width": 0.8}},
    ]


def pitch_markings(sports):
    if not sports:
        return []
    dflt = sports.get("default") or {}
    length = ["case", ["has", "pitch_length"], ["get", "pitch_length"],
              _sport_values(sports, "length", dflt.get("length", 50))]
    z0 = sports.get("markings_at", 17)
    return [{
        "id": "pitch-markings", "type": "symbol",
        "source": "leisure", "source-layer": "leisure", "minzoom": z0,
        "filter": _pitch_filter("Point"),
        "layout": {
            "icon-image": ["case",
                ["all", ["==", ["get", SPORT_RENDER_KEY], "basketball"],
                        ["==", ["get", "hoops"], "1"]],
                "sport-markings-basketball-1hoop",
                ["concat", "sport-markings-", ["get", SPORT_RENDER_KEY]]],
            "icon-rotation-alignment": "map",
            "icon-pitch-alignment": "map",
            "icon-rotate": ["coalesce", ["get", "bearing"], 0],
            "icon-size": ["interpolate", ["exponential", 2], ["zoom"],
                          z0, ["*", length, round(0.01220 * 2 ** (z0 - 17), 6)],
                          z0 + 1, ["*", length, round(0.02442 * 2 ** (z0 - 17), 6)]],
            "icon-allow-overlap": True,
            "icon-ignore-placement": True,
            "symbol-placement": "point"},
        "paint": {"icon-opacity": ["interpolate", ["linear"], ["zoom"], z0, 0.7, z0 + 1, 0.95]},
    }]

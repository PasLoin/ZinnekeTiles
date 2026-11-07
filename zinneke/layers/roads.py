from ..colors import c, lighten
from ..expressions import curve_from, zoom
from ..palette import palette

ROAD_ORDER = [
    "track",
    "service",
    "busway",
    "living_street",
    "unclassified",
    "residential",
    "tertiary_link",
    "secondary_link",
    "primary_link",
    "trunk_link",
    "motorway_link",
    "tertiary",
    "secondary",
    "primary",
    "trunk",
    "motorway",
]


ROAD_LEGACY_GROUP = {
    "motorway": "motorway",
    "motorway_link": "motorway",
    "trunk": "trunk",
    "trunk_link": "trunk",
    "primary": "primary",
    "primary_link": "primary",
    "secondary": "secondary",
    "secondary_link": "secondary",
    "tertiary": "tertiary",
    "tertiary_link": "tertiary",
    "residential": "local",
    "unclassified": "local",
    "service": "local",
    "living_street": "local",
    "track": "track",
    "busway": "busway",
}


_W_MAJOR = [(10, 1.5), (13, 3.0), (15, 8.0), (18, 22.0)]


_W_PRIM = [(10, 1.2), (13, 2.5), (15, 7.0), (18, 20.0)]


_W_SEC = [(10, 1.0), (13, 2.5), (15, 7.0), (18, 18.0)]


_W_TERT = [(11, 0.8), (13, 2.0), (15, 6.0), (18, 16.0)]


_W_LOCAL = [(12, 0.6), (13, 1.2), (15, 4.5), (18, 14.0)]


_W_LIVING = [(13, 1.0), (15, 4.0), (18, 12.0)]


_W_LINK = [(12, 0.8), (15, 4.0), (18, 12.0)]


_W_SERV = [(14, 0.8), (16, 3.0), (18, 7.0)]


_W_BUS = [(12, 0.8), (15, 3.0), (18, 9.0)]


_W_TRACK = [(13, 0.6), (16, 1.5), (18, 2.5)]


ROAD_DEFAULTS = {
    "motorway": ("#e892a2", "#dc2a67", 10, _W_MAJOR),
    "motorway_link": ("#e892a2", "#dc2a67", 12, _W_LINK),
    "trunk": ("#f9b29c", "#c84e2f", 10, _W_MAJOR),
    "trunk_link": ("#f9b29c", "#c84e2f", 12, _W_LINK),
    "primary": ("#fcd6a4", "#a06b00", 10, _W_PRIM),
    "primary_link": ("#fcd6a4", "#a06b00", 12, _W_LINK),
    "secondary": ("#f7fabf", "#707d05", 10, _W_SEC),
    "secondary_link": ("#f7fabf", "#707d05", 13, _W_LINK),
    "tertiary": ("#ffffff", "#8f8f8f", 11, _W_TERT),
    "tertiary_link": ("#ffffff", "#8f8f8f", 13, _W_LINK),
    "residential": ("#ffffff", "#bbbbbb", 12, _W_LOCAL),
    "unclassified": ("#ffffff", "#bbbbbb", 12, _W_LOCAL),
    "living_street": ("#ededed", "#c6c6c6", 13, _W_LIVING),
    "service": ("#ffffff", "#bbbbbb", 14, _W_SERV),
    "busway": ("#ffffff", "#bbbbbb", 13, _W_BUS),
    "track": ("#996600", None, 13, _W_TRACK),
}


ROAD_TUNNEL_VALUES = ["yes", "building_passage"]


ROAD_LABEL_VALUES = [
    "motorway",
    "trunk",
    "primary",
    "secondary",
    "tertiary",
    "residential",
    "unclassified",
    "living_street",
]


def road_subtype(cfg_or_layer, value):
    raw_st = cfg_or_layer.get("subtypes") or {}
    layer_ap = cfg_or_layer.get("appear_at", 10) or 10
    fill, casing, ap, widths = ROAD_DEFAULTS[value]
    legacy = raw_st.get(ROAD_LEGACY_GROUP.get(value)) or {}
    own = raw_st.get(value) or {}
    merged = {**legacy, **own}
    return {
        "color": c(merged.get("color", fill)),
        "casing": c(merged.get("outline_color", casing))
        if casing or "outline_color" in merged
        else None,
        "appear_at": int(merged.get("appear_at", max(ap, layer_ap))),
        "opacity": merged.get("opacity"),
        "tunnel_color": c(merged.get("tunnel_color")),
        "widths": widths,
    }


def _road_border(z):
    return 0.5 if z <= 13 else (1.0 if z <= 16 else 1.5)


def _casing_curve(fill_curve, factor=1.0):
    return [(z, round(w + 2 * _road_border(z) * factor, 2)) for z, w in fill_curve]


def roads(cfg, pal=None):
    pal = pal or palette({}, "roads")
    out = []
    sort_key = ["coalesce", ["to-number", ["get", "layer"]], 0]

    for mm in ["tunnel", "bridge"]:
        fc = pal["tunnel_area"] if mm == "tunnel" else pal["bridge_area"]
        op = 0.1 if mm == "tunnel" else 0.5
        out.append(
            {
                "id": f"man_made-{mm}-fill",
                "type": "fill",
                "source": "roads",
                "source-layer": "roads",
                "filter": [
                    "all",
                    ["==", ["get", "man_made"], mm],
                    ["==", ["geometry-type"], "Polygon"],
                ],
                "layout": {"fill-sort-key": sort_key},
                "paint": {"fill-color": fc, "fill-opacity": op},
            }
        )
        dashed = {"line-dasharray": [2, 2]} if mm == "tunnel" else {}
        out.append(
            {
                "id": f"man_made-{mm}-outline",
                "type": "line",
                "source": "roads",
                "source-layer": "roads",
                "filter": ["==", ["get", "man_made"], mm],
                "layout": {"line-join": "round", "line-cap": "round", "line-sort-key": sort_key},
                "paint": {
                    "line-color": pal["tunnel_area_outline"]
                    if mm == "tunnel"
                    else pal["bridge_area_outline"],
                    "line-width": 2,
                    **dashed,
                },
            }
        )
        if mm == "tunnel":
            out.append(
                {
                    "id": "man_made-tunnel-line-fill",
                    "type": "line",
                    "source": "roads",
                    "source-layer": "roads",
                    "filter": [
                        "all",
                        ["==", ["get", "man_made"], "tunnel"],
                        ["==", ["geometry-type"], "LineString"],
                    ],
                    "layout": {
                        "line-join": "round",
                        "line-cap": "round",
                        "line-sort-key": sort_key,
                    },
                    "paint": {
                        "line-color": pal["tunnel_area"],
                        "line-opacity": 0.3,
                        "line-width": zoom([(14, 2), (16, 10), (18, 20)]),
                    },
                }
            )

    is_tunnel = ["in", ["get", "tunnel"], ["literal", ROAD_TUNNEL_VALUES]]
    is_bridge = ["all", ["has", "bridge"], ["!=", ["get", "bridge"], "no"]]
    variants = {
        "tunnel": is_tunnel,
        "surface": ["all", ["!", is_tunnel], ["!", is_bridge]],
        "bridge": ["all", ["!", is_tunnel], is_bridge],
    }
    resolved = {v: road_subtype(cfg, v) for v in ROAD_ORDER}

    def layer(lid, hw, variant, paint, cap="round"):
        s = resolved[hw]
        return {
            "id": lid,
            "type": "line",
            "source": "roads",
            "source-layer": "roads",
            "minzoom": s["appear_at"],
            "filter": ["all", ["==", ["get", "highway"], hw], variants[variant]],
            "layout": {"line-cap": cap, "line-join": "round", "line-sort-key": sort_key},
            "paint": paint,
        }

    def casing_pass(variant):
        for hw in ROAD_ORDER:
            s = resolved[hw]
            if not s["casing"]:
                continue
            fill_w = curve_from(s["widths"], s["appear_at"])
            if variant == "bridge":
                col, w, extra = pal["bridge_casing"], _casing_curve(fill_w, 1.6), {}
            elif variant == "tunnel":
                col, w, extra = s["casing"], _casing_curve(fill_w), {"line-dasharray": [2, 1]}
            else:
                col, w, extra = s["casing"], _casing_curve(fill_w), {}
            out.append(
                layer(
                    f"roads-{variant}-casing-{hw}",
                    hw,
                    variant,
                    {"line-color": col, "line-width": zoom(w), **extra},
                    cap="butt" if variant != "surface" else "round",
                )
            )

    def fill_pass(variant):
        for hw in ROAD_ORDER:
            s = resolved[hw]
            w = curve_from(s["widths"], s["appear_at"])
            tunnel_col = s["tunnel_color"] or lighten(s["color"])
            paint = {
                "line-color": tunnel_col if variant == "tunnel" else s["color"],
                "line-width": zoom(w),
            }
            if hw == "track":
                paint["line-dasharray"] = [3, 2]
            if (
                variant != "tunnel"
                and s["opacity"] is not None
                and abs(float(s["opacity"]) - 1.0) > 0.01
            ):
                paint["line-opacity"] = float(s["opacity"])
            out.append(
                layer(
                    f"roads-{variant}-fill-{hw}",
                    hw,
                    variant,
                    paint,
                    cap="butt" if hw == "track" else "round",
                )
            )

    casing_pass("tunnel")
    fill_pass("tunnel")
    casing_pass("surface")
    fill_pass("surface")

    bap = resolved["busway"]["appear_at"]
    out.append(
        {
            "id": "roads-center-busway",
            "type": "line",
            "source": "roads",
            "source-layer": "roads",
            "minzoom": bap,
            "filter": ["match", ["get", "highway"], ["busway"], True, False],
            "layout": {"line-cap": "butt", "line-join": "round", "line-sort-key": sort_key},
            "paint": {
                "line-color": pal["busway_center"],
                "line-width": zoom(curve_from([(12, 0.4), (18, 2)], bap)),
                "line-dasharray": [2, 2],
            },
        }
    )

    casing_pass("bridge")
    fill_pass("bridge")

    out.append(
        {
            "id": "road-labels",
            "type": "symbol",
            "source": "roads",
            "source-layer": "roads",
            "minzoom": cfg["labels_at"],
            "filter": ["match", ["get", "highway"], ROAD_LABEL_VALUES, True, False],
            "layout": {
                "text-field": ["get", "name"],
                "text-font": ["Noto Sans Regular"],
                "text-size": zoom([(cfg["labels_at"], 10), (18, 13)]),
                "symbol-placement": "line",
                "text-max-angle": 30,
            },
            "paint": {
                "text-color": pal["label"],
                "text-halo-color": pal["label_halo"],
                "text-halo-width": 1.5,
            },
        }
    )

    out.append(
        {
            "id": "road-oneway-arrows",
            "type": "symbol",
            "source": "roads",
            "source-layer": "roads",
            "minzoom": 16,
            "filter": ["==", ["get", "oneway"], "yes"],
            "layout": {
                "symbol-placement": "line",
                "symbol-spacing": zoom([(16, 150), (18, 80)]),
                "text-field": "→",
                "text-font": ["Noto Sans Regular"],
                "text-size": zoom([(16, 10), (18, 14)]),
                "text-rotation-alignment": "map",
                "text-pitch-alignment": "map",
                "text-keep-upright": False,
                "text-allow-overlap": True,
                "text-ignore-placement": True,
            },
            "paint": {
                "text-color": pal["oneway"],
                "text-opacity": 0.7,
                "text-halo-color": pal["oneway_halo"],
                "text-halo-width": 1,
            },
        }
    )

    return out

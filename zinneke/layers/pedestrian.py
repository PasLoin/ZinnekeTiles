from ..colors import c
from ..expressions import curve_from, interp, zoom
from ..palette import palette

FOOTWAY_WIDTHS = [(14, 0.7), (15, 1.0), (16, 1.3), (18, 1.3), (19, 1.6)]


FOOTWAY_BACKGROUND = 2.0


FOOTWAY_DASH_Z14 = (1, 3)


FOOTWAY_DASHES = {
    "paved": {15: (2, 3.5), 16: (3, 3.5), 17: (3, 3)},
    "unpaved": {15: (1, 4)},
    "unknown": {15: (1, 3, 2, 4), 16: (1, 4, 2, 3)},
}


SURFACE_PAVED = [
    "paved",
    "asphalt",
    "cobblestone",
    "cobblestone:flattened",
    "sett",
    "unhewn_cobblestone",
    "concrete",
    "concrete:lanes",
    "concrete:plates",
    "paving_stones",
    "metal",
    "wood",
]


SURFACE_UNPAVED = [
    "unpaved",
    "compacted",
    "dirt",
    "earth",
    "fine_gravel",
    "grass",
    "grass_paver",
    "gravel",
    "ground",
    "mud",
    "pebblestone",
    "salt",
    "sand",
    "woodchips",
    "clay",
    "ice",
    "snow",
    "rock",
]


def _footway_surface_filter(kind):
    paved = ["in", ["get", "surface"], ["literal", SURFACE_PAVED]]
    unpaved = ["in", ["get", "surface"], ["literal", SURFACE_UNPAVED]]
    if kind == "paved":
        return paved
    if kind == "unpaved":
        return unpaved
    return ["all", ["!", paved], ["!", unpaved]]


def _footway_noaccess():
    return [
        "any",
        ["in", ["get", "foot"], ["literal", ["no", "private"]]],
        [
            "all",
            ["in", ["get", "access"], ["literal", ["no", "private"]]],
            [
                "!",
                [
                    "in",
                    ["get", "foot"],
                    ["literal", ["yes", "designated", "permissive", "destination"]],
                ],
            ],
        ],
    ]


def _footway_width_at(z):
    return interp(FOOTWAY_WIDTHS, z)


def _footway_dasharray(kind):
    w14 = _footway_width_at(14)
    expr = ["step", ["zoom"], ["literal", [round(v / w14, 2) for v in FOOTWAY_DASH_Z14]]]
    for z, dash in sorted(FOOTWAY_DASHES[kind].items()):
        w = _footway_width_at(z)
        expr += [z, ["literal", [round(v / w, 2) for v in dash]]]
    return expr


def _footway_layers(key, s, ap, no_access):
    col = c(s.get("color", "#fa8072"))
    background = c(s.get("outline_color", "#ffffff"))
    hw = ["==", ["get", "highway"], key]
    visible = ["any", [">=", ["zoom"], 15], ["!", _footway_noaccess()]]
    bz = max(ap, 15)
    out = [
        {
            "id": f"pedestrian-{key}-casing",
            "type": "line",
            "source": "pedestrian",
            "source-layer": "pedestrian",
            "minzoom": bz,
            "filter": hw,
            "layout": {"line-cap": "round", "line-join": "round"},
            "paint": {
                "line-color": background,
                "line-opacity": 0.4,
                "line-width": zoom(
                    [
                        (z, round(w + FOOTWAY_BACKGROUND, 2))
                        for z, w in curve_from(FOOTWAY_WIDTHS, bz)
                    ]
                ),
            },
        }
    ]
    for kind in ("paved", "unpaved", "unknown"):
        out.append(
            {
                "id": f"pedestrian-{key}-{kind}",
                "type": "line",
                "source": "pedestrian",
                "source-layer": "pedestrian",
                "minzoom": ap,
                "filter": ["all", hw, _footway_surface_filter(kind), visible],
                "layout": {"line-cap": "round", "line-join": "round"},
                "paint": {
                    "line-color": ["case", _footway_noaccess(), no_access, col],
                    "line-width": zoom(curve_from(FOOTWAY_WIDTHS, ap)),
                    "line-dasharray": _footway_dasharray(kind),
                },
            }
        )
    return out


def pedestrian(cfg, pal=None):
    pal = pal or palette({}, "pedestrian")
    col = cfg["color"] or "#97644c"
    st = cfg["subtypes"]
    ped = {**(st.get("pedestrian_street") or {}), **(st.get("pedestrian") or {})}
    ap_ped = ped.get("appear_at", 13)
    ped_fill = c(ped.get("color", "#ededed"))
    ped_casing = c(ped.get("outline_color", "#999"))
    out = []
    out.append(
        {
            "id": "pedestrian-street-casing",
            "type": "line",
            "source": "pedestrian",
            "source-layer": "pedestrian",
            "minzoom": ap_ped,
            "filter": ["==", ["get", "highway"], "pedestrian"],
            "layout": {"line-cap": "round", "line-join": "round"},
            "paint": {"line-color": ped_casing, "line-width": zoom([(ap_ped, 1.2), (18, 6)])},
        }
    )
    out.append(
        {
            "id": "pedestrian-street-fill",
            "type": "line",
            "source": "pedestrian",
            "source-layer": "pedestrian",
            "minzoom": ap_ped,
            "filter": ["==", ["get", "highway"], "pedestrian"],
            "layout": {"line-cap": "round", "line-join": "round"},
            "paint": {"line-color": ped_fill, "line-width": zoom([(ap_ped, 0.8), (18, 4)])},
        }
    )
    for key in ("footway", "path"):
        s = st.get(key) or {}
        out += _footway_layers(key, s, s.get("appear_at", 14), pal["no_access"])
    s = st.get("steps") or {}
    ap = s.get("appear_at", 14)
    out.append(
        {
            "id": "pedestrian-steps",
            "type": "line",
            "source": "pedestrian",
            "source-layer": "pedestrian",
            "minzoom": ap,
            "filter": ["==", ["get", "highway"], "steps"],
            "paint": {
                "line-color": c(s.get("color", col)),
                "line-width": zoom([(14, 1.5), (18, 4)]),
                "line-dasharray": [0.2, 0.5],
            },
        }
    )
    return out

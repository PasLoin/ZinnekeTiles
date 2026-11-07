from ..colors import lighten
from ..config import sc
from ..expressions import zoom
from ..palette import palette

RAILWAY_DEFS = {
    "rail": ([(10, 2), (18, 7)], [(10, 0.8), (18, 2)]),
    "subway": (None, [(12, 0.8), (18, 2)]),
    "tram": (None, [(13, 0.5), (18, 1.5)]),
    "miniature": (None, [(14, 0.3), (18, 1)]),
}


RAILWAY_TUNNEL_VALUES = ["yes", "building_passage"]


def railway(cfg, pal=None):
    pal = pal or palette({}, "railway")
    out = []
    resolved = {}
    for rw in RAILWAY_DEFS:
        s = sc(cfg, rw)
        if s["color"]:
            resolved[rw] = s

    def opacity(s, paint):
        if abs(float(s["opacity"]) - 1.0) > 0.01:
            paint["line-opacity"] = float(s["opacity"])
        return paint

    is_tunnel = ["in", ["get", "tunnel"], ["literal", RAILWAY_TUNNEL_VALUES]]
    for rw in ["rail", "subway", "tram"]:
        if rw not in resolved:
            continue
        s = resolved[rw]
        ap = s["appear_at"]
        tcol = s["tunnel_color"] or lighten(s["color"])
        filt_t = ["all", ["==", ["get", "railway"], rw], is_tunnel]
        if rw == "rail":
            out += [
                {
                    "id": f"railway-tunnel-{rw}-casing",
                    "type": "line",
                    "source": "railway",
                    "source-layer": "railway",
                    "minzoom": ap,
                    "filter": filt_t,
                    "layout": {"line-join": "round"},
                    "paint": {
                        "line-color": tcol,
                        "line-width": zoom([(ap, 3), (18, 7)]),
                        "line-dasharray": [0.2, 4],
                        "line-opacity": 0.4,
                    },
                },
                {
                    "id": f"railway-tunnel-{rw}-core",
                    "type": "line",
                    "source": "railway",
                    "source-layer": "railway",
                    "minzoom": ap,
                    "filter": filt_t,
                    "layout": {"line-join": "round"},
                    "paint": {
                        "line-color": tcol,
                        "line-width": zoom([(ap, 0.8), (18, 2)]),
                        "line-dasharray": [5, 3],
                        "line-opacity": 0.5,
                    },
                },
            ]
        else:
            out.append(
                {
                    "id": f"railway-tunnel-{rw}",
                    "type": "line",
                    "source": "railway",
                    "source-layer": "railway",
                    "minzoom": ap,
                    "filter": filt_t,
                    "layout": {"line-join": "round"},
                    "paint": {
                        "line-color": tcol,
                        "line-width": zoom(RAILWAY_DEFS[rw][1]),
                        "line-dasharray": [5, 3],
                        "line-opacity": 0.4 if rw == "tram" else 0.5,
                    },
                }
            )

    for rw, (ties_w, core_w) in RAILWAY_DEFS.items():
        if rw not in resolved:
            continue
        s = resolved[rw]
        col, ap = s["color"], s["appear_at"]
        filt_s = [
            "all",
            ["==", ["get", "railway"], rw],
            ["!", is_tunnel],
            ["!=", ["get", "bridge"], "yes"],
        ]
        filt_b = ["all", ["==", ["get", "railway"], rw], ["==", ["get", "bridge"], "yes"]]
        for suffix, filt in [("", filt_s), ("-bridge", filt_b)]:
            if ties_w:
                if suffix == "-bridge":
                    out.append(
                        {
                            "id": "railway-bridge-casing",
                            "type": "line",
                            "source": "railway",
                            "source-layer": "railway",
                            "minzoom": ap,
                            "filter": [
                                "all",
                                [
                                    "match",
                                    ["get", "railway"],
                                    ["rail", "subway", "tram"],
                                    True,
                                    False,
                                ],
                                ["==", ["get", "bridge"], "yes"],
                            ],
                            "layout": {"line-join": "round"},
                            "paint": {
                                "line-color": pal["bridge_casing"],
                                "line-width": zoom([(ap, 4), (18, 9)]),
                                "line-opacity": 0.15,
                            },
                        }
                    )
                out.append(
                    {
                        "id": f"railway-{rw}{suffix}-ties",
                        "type": "line",
                        "source": "railway",
                        "source-layer": "railway",
                        "minzoom": ap,
                        "filter": filt,
                        "layout": {"line-join": "round"},
                        "paint": opacity(
                            s,
                            {
                                "line-color": col,
                                "line-width": zoom(ties_w),
                                "line-dasharray": [0.2, 4],
                            },
                        ),
                    }
                )
                out.append(
                    {
                        "id": f"railway-{rw}{suffix}-core",
                        "type": "line",
                        "source": "railway",
                        "source-layer": "railway",
                        "minzoom": ap,
                        "filter": filt,
                        "layout": {"line-join": "round"},
                        "paint": opacity(s, {"line-color": col, "line-width": zoom(core_w)}),
                    }
                )
            else:
                out.append(
                    {
                        "id": f"railway-{rw}{suffix}",
                        "type": "line",
                        "source": "railway",
                        "source-layer": "railway",
                        "minzoom": ap,
                        "filter": filt,
                        "layout": {"line-join": "round"},
                        "paint": opacity(s, {"line-color": col, "line-width": zoom(core_w)}),
                    }
                )
    return out

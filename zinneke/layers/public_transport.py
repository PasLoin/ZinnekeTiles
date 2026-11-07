from ..config import sc
from ..expressions import zoom
from ..palette import palette


def public_transport(cfg, pal=None):
    pal = pal or palette({}, "public_transport")
    col = cfg["color"] or "#e3004f"
    ap = cfg["appear_at"]
    la = cfg["labels_at"]
    by_route = ["match", ["get", "route"]]
    for key in cfg["subtypes"]:
        s = sc(cfg, key)
        if (s["tag"] or "route") == "route" and s["color"]:
            by_route += [key, s["color"]]
    fallback = by_route + [col] if len(by_route) > 2 else col
    return [
        {
            "id": "public_transport-casing",
            "type": "line",
            "source": "public_transport",
            "source-layer": "public_transport",
            "minzoom": ap,
            "layout": {"line-join": "round", "line-cap": "round"},
            "paint": {
                "line-color": pal["casing"],
                "line-width": zoom([(ap, 3), (18, 9)]),
                "line-opacity": 0.6,
            },
        },
        {
            "id": "public_transport-line",
            "type": "line",
            "source": "public_transport",
            "source-layer": "public_transport",
            "minzoom": ap,
            "layout": {"line-join": "round", "line-cap": "round"},
            "paint": {
                "line-color": ["coalesce", ["get", "colour"], fallback],
                "line-width": zoom([(ap, 1.5), (18, 5)]),
                "line-opacity": 0.85,
            },
        },
        {
            "id": "public_transport-label",
            "type": "symbol",
            "source": "public_transport",
            "source-layer": "public_transport",
            "minzoom": la,
            "layout": {
                "text-field": ["get", "ref"],
                "text-font": ["Noto Sans Regular"],
                "text-size": 11,
                "symbol-placement": "line",
                "text-max-angle": 30,
            },
            "paint": {
                "text-color": ["coalesce", ["get", "colour:text"], pal["label"]],
                "text-halo-color": pal["label_halo"],
                "text-halo-width": 1.5,
            },
        },
    ]

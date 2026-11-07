from ..expressions import zoom
from ..palette import palette


def cycleway(cfg, pal=None):
    pal = pal or palette({}, "cycleway")
    col = cfg["color"] or "#0000ff"
    out = [
        {
            "id": "cycleway",
            "type": "line",
            "source": "cycleway",
            "source-layer": "cycleway",
            "minzoom": cfg["appear_at"],
            "paint": {
                "line-color": col,
                "line-width": zoom([(cfg["appear_at"], 0.8), (18, 2)]),
                "line-dasharray": [3, 3],
            },
        }
    ]

    out.append(
        {
            "id": "cycleway-oneway-arrows",
            "type": "symbol",
            "source": "cycleway",
            "source-layer": "cycleway",
            "minzoom": 16,
            "filter": ["==", ["get", "oneway"], "yes"],
            "layout": {
                "symbol-placement": "line",
                "symbol-spacing": zoom([(16, 100), (18, 60)]),
                "text-field": "→",
                "text-font": ["Noto Sans Regular"],
                "text-size": zoom([(16, 10), (18, 13)]),
                "text-rotation-alignment": "map",
                "text-pitch-alignment": "map",
                "text-keep-upright": False,
                "text-allow-overlap": True,
                "text-ignore-placement": True,
            },
            "paint": {
                "text-color": pal["oneway"],
                "text-opacity": 0.95,
                "text-halo-color": col,
                "text-halo-width": 1.5,
            },
        }
    )

    return out

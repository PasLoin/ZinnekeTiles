from ..expressions import zoom
from ..palette import palette

ADDRESS_LABEL_OFFSET = 1.5


ADDRESS_DIAGONAL_FACTOR = 0.8


ADDRESS_DIR_ANCHORS = {
    "n": [("bottom", 0, -1), ("bottom-left", 1, -1), ("bottom-right", -1, -1)],
    "s": [("top", 0, 1), ("top-left", 1, 1), ("top-right", -1, 1)],
    "e": [("left", 1, 0), ("bottom-left", 1, -1), ("top-left", 1, 1)],
    "w": [("right", -1, 0), ("bottom-right", -1, -1), ("top-right", -1, 1)],
    "x": [("top", 0, 1), ("bottom", 0, -1), ("left", 1, 0), ("right", -1, 0)],
}


def _anchor_offsets(anchors, r=ADDRESS_LABEL_OFFSET, k=ADDRESS_DIAGONAL_FACTOR):
    out = []
    for name, dx, dy in anchors:
        f = r * k if dx and dy else r
        out += [name, [round(dx * f, 2), round(dy * f, 2)]]
    return ["literal", out]


def address_anchor_expr():
    expr = ["match", ["get", "label_dir"]]
    for d, anchors in ADDRESS_DIR_ANCHORS.items():
        expr += [d, _anchor_offsets(anchors)]
    expr.append(_anchor_offsets([("center", 0, 0)]))
    return expr


def addresses(cfg, pal=None):
    pal = pal or palette({}, "addresses")
    ap = cfg["appear_at"]
    return [
        {
            "id": "address-labels",
            "type": "symbol",
            "source": "addresses",
            "source-layer": "addresses",
            "minzoom": ap,
            "layout": {
                "text-field": ["get", "addr:housenumber"],
                "text-font": ["Noto Sans Regular"],
                "text-size": zoom([(ap, 9), (18, 11)]),
                "text-variable-anchor-offset": address_anchor_expr(),
                "text-padding": 1,
                "text-allow-overlap": False,
            },
            "paint": {
                "text-color": cfg["color"] or "#6f5e50",
                "text-halo-color": pal["halo"],
                "text-halo-width": 1.2,
            },
        }
    ]

from ..config import sc
from ..expressions import by_expr, zoom

TREE_SYMBOLS = {"needleleaved": "▲"}


TREE_SYMBOL_DEFAULT = "●"


TREE_LEAF_TYPES = ["broadleaved", "needleleaved"]


def _tree_symbol_layout(z0, sizes):
    known = ["in", ["get", "leaf_type"], ["literal", TREE_LEAF_TYPES]]
    field = ["match", ["get", "leaf_type"]]
    for k in sorted(TREE_SYMBOLS):
        field += [k, TREE_SYMBOLS[k]]
    field.append(TREE_SYMBOL_DEFAULT)
    (a_known, a_other), (b_known, b_other) = sizes
    size = zoom([(z0, ["case", known, a_known, a_other]), (18, ["case", known, b_known, b_other])])
    return {
        "text-field": field,
        "text-font": ["Noto Sans Regular"],
        "text-size": size,
        "text-allow-overlap": False,
    }


TREE_DEFAULT_COLORS = {"hedge": "#6ba048", "tree_row": "#8fbc77", "tree": "#7eb36a"}


def trees(cfg, halo="#f2efe9"):
    def resolved(key):
        s = sc(cfg, key)
        s["color"] = s["color"] or TREE_DEFAULT_COLORS[key]
        return s

    hedge = resolved("hedge")
    row = resolved("tree_row")
    tree = resolved("tree")
    ha, ra, ta = hedge["appear_at"], row["appear_at"], tree["appear_at"]
    leaf_color = by_expr(tree, "by_color", tree["color"])

    def line(lid, value, tag, s, widths):
        paint = {"line-color": s["color"], "line-width": zoom(widths)}
        if abs(float(s["opacity"]) - 1.0) > 0.01:
            paint["line-opacity"] = float(s["opacity"])
        return {
            "id": lid,
            "type": "line",
            "source": "trees",
            "source-layer": "trees",
            "minzoom": s["appear_at"],
            "filter": ["all", ["==", ["geometry-type"], "LineString"], ["==", ["get", tag], value]],
            "layout": {"line-cap": "round", "line-join": "round"},
            "paint": paint,
        }

    row_symbols = {
        "id": "trees-row-symbols",
        "type": "symbol",
        "source": "trees",
        "source-layer": "trees",
        "minzoom": ra + 1,
        "filter": [
            "all",
            ["==", ["geometry-type"], "LineString"],
            ["match", ["get", "natural"], ["tree_row"], True, False],
        ],
        "layout": {
            "symbol-placement": "line",
            "symbol-spacing": zoom([(ra + 1, 48), (18, 32)]),
            "text-rotation-alignment": "map",
            **_tree_symbol_layout(ra + 1, ((9, 8), (13, 12))),
        },
        "paint": {"text-color": leaf_color, "text-halo-color": halo, "text-halo-width": 0.8},
    }

    tree_symbols = {
        "id": "trees-tree",
        "type": "symbol",
        "source": "trees",
        "source-layer": "trees",
        "minzoom": ta,
        "filter": ["all", ["==", ["geometry-type"], "Point"], ["==", ["get", "natural"], "tree"]],
        "layout": _tree_symbol_layout(ta, ((10, 9), (14, 13))),
        "paint": {"text-color": leaf_color, "text-halo-color": halo, "text-halo-width": 0.9},
    }

    return [
        line("trees-hedge", "hedge", hedge["tag"] or "barrier", hedge, [(ha, 0.8), (18, 3.5)]),
        line("trees-row-line", "tree_row", row["tag"] or "natural", row, [(ra, 0.5), (18, 1.5)]),
        row_symbols,
        tree_symbols,
    ]

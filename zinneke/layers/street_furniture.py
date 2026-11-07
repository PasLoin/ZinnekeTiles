from ..colors import c
from ..expressions import zoom


def street_furniture_point_filter(st):
    by_tag = {}
    for val, scfg in st.items():
        tag = (scfg or {}).get("tag") or "amenity"
        by_tag.setdefault(tag, []).append(val)
    clauses = []
    for tag in sorted(by_tag):
        vals = sorted(by_tag[tag])
        if vals == [tag]:
            clauses.append(["has", tag])
        else:
            clauses.append(["in", ["get", tag], ["literal", vals]])
    point = ["==", ["geometry-type"], "Point"]
    if not clauses:
        return point
    return ["all", point, ["any"] + clauses]


def street_furniture(cfg):
    st = cfg["subtypes"]
    ap = cfg["appear_at"]
    fence_color = c((st.get("fence") or {}).get("color") or cfg["color"] or "#9c9c9c")

    icon_expr = [
        "coalesce",
        ["image", ["concat", "poi-", ["get", "emergency"]]],
        [
            "case",
            ["has", "vending"],
            ["image", ["concat", "poi-vending-", ["get", "vending"]]],
            ["image", ""],
        ],
        [
            "case",
            ["has", "door"],
            ["image", ["concat", "poi-door-", ["get", "door"]]],
            ["image", ""],
        ],
        ["image", ["concat", "poi-", ["get", "amenity"]]],
        ["image", ["concat", "poi-", ["get", "barrier"]]],
        ["image", ["concat", "poi-", ["get", "tourism"]]],
        [
            "case",
            ["==", ["get", "highway"], "street_lamp"],
            ["image", "poi-street_lamp"],
            ["image", ""],
        ],
        ["case", ["has", "entrance"], ["image", "poi-entrance"], ["image", ""]],
    ]

    out = []
    if "fence" in st:
        out.append(
            {
                "id": "street-furniture-fence",
                "type": "line",
                "source": "street_furniture",
                "source-layer": "street_furniture",
                "minzoom": ap,
                "filter": [
                    "all",
                    ["==", ["get", "barrier"], "fence"],
                    ["==", ["geometry-type"], "LineString"],
                ],
                "paint": {
                    "line-color": fence_color,
                    "line-width": zoom([(ap, 0.5), (18, 1.5)]),
                    "line-opacity": 0.8,
                },
            }
        )
    out.append(
        {
            "id": "street-furniture-icon",
            "type": "symbol",
            "source": "street_furniture",
            "source-layer": "street_furniture",
            "minzoom": ap,
            "filter": street_furniture_point_filter(st),
            "layout": {
                "icon-image": icon_expr,
                "icon-size": zoom([(ap, 0.7), (18, 1.0)]),
                "icon-allow-overlap": False,
                "icon-padding": 2,
                "icon-anchor": "center",
            },
            "paint": {"icon-opacity": 0.9},
        }
    )
    return out

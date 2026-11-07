from ..config import sc
from ..expressions import color_or_case


GREEN_RENDER_ORDER = ["park", "garden", "forest", "wood", "scrub", "shrubbery",
                      "heath", "grass", "grassland", "meadow", "flowerbed"]


def green(cfg):
    out = []
    st = cfg["subtypes"]

    hatch_vals = []

    order = [v for v in GREEN_RENDER_ORDER if v in st]
    order += sorted(v for v in st if v not in order)
    for val in order:
        s = sc(cfg, val)
        if not s["color"]: continue
        filt = ["==", ["get", s["tag"] or "leisure"], val]

        col_expr = color_or_case(s["color"], s["color_private"])
        l = {"id": f"green-{val}", "type": "fill",
             "source": "green", "source-layer": "green",
             "filter": filt,
             "paint": {"fill-color": col_expr}}
        if s["appear_at"] > 10: l["minzoom"] = s["appear_at"]
        if abs(s["opacity"] - 1.0) > 0.01: l["paint"]["fill-opacity"] = s["opacity"]
        out.append(l)

        if s["pattern_private"]:
            hatch_vals.append((val, s["pattern_private"], s["appear_at"]))

    from collections import defaultdict
    by_pattern = defaultdict(list)
    for val, pat, _ap in hatch_vals:
        by_pattern[pat].append(val)

    for pat, vals in by_pattern.items():
        tag_val_filters = []
        for val in vals:
            tag = (st.get(val) or {}).get("tag", "leisure")
            tag_val_filters.append(["==", ["get", tag], val])
        out.append({
            "id": f"green-hatch-{pat.replace('-','_')}", "type": "fill",
            "source": "green", "source-layer": "green",
            "filter": ["all", ["any"] + tag_val_filters,
                              ["==", ["get", "access"], "private"]],
            "paint": {"fill-pattern": pat}
        })

    return out

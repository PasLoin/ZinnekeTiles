from ..config import sc
from ..expressions import by_expr


LANDUSE_RENDER_ORDER = [
    "residential", "industrial", "commercial", "retail",
    "railway", "education", "farmland", "farmyard",
    "brownfield", "greenfield", "construction", "landfill",
    "allotments", "cemetery", "garages", "depot", "quarry",
    "religious", "recreation_ground", "village_green", "military",
]


def landuse(cfg):
    out = []
    order = [v for v in LANDUSE_RENDER_ORDER if v in cfg["subtypes"]]
    order += [v for v in cfg["subtypes"] if v not in order]

    for val in order:
        s = sc(cfg, val)
        if not s["color"]: continue
        tag = s["tag"] or "landuse"
        l = {"id": f"landuse-{val}", "type": "fill",
             "source": "landuse", "source-layer": "landuse",
             "filter": ["==", ["get", tag], val],
             "paint": {"fill-color": by_expr(s, "by_color", s["color"])}}
        if s["appear_at"] > 10: l["minzoom"] = s["appear_at"]
        if abs(s["opacity"] - 1.0) > 0.01: l["paint"]["fill-opacity"] = s["opacity"]
        out.append(l)
        if s["pattern"]:
            out.append({
                "id": f"landuse-{val}-hatch", "type": "fill",
                "source": "landuse", "source-layer": "landuse",
                "minzoom": s["pattern_at"] or s["appear_at"],
                "filter": ["==", ["get", tag], val],
                "paint": {"fill-pattern": by_expr(s, "by_pattern", s["pattern"])}
            })
        if s["outline_color"]:
            ol = {"id": f"landuse-{val}-outline", "type": "line",
                  "source": "landuse", "source-layer": "landuse",
                  "filter": ["==", ["get", tag], val],
                  "paint": {"line-color": s["outline_color"], "line-width": 0.5}}
            if s["appear_at"] > 10: ol["minzoom"] = s["appear_at"]
            out.append(ol)
    return out

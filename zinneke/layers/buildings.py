from ..palette import palette


LEVEL_HEIGHT = 3


def extrusion_exprs(height_fallback, levels_fallback, no_info_height):
    base = ["case",
        ["has", "min_height"], ["to-number", ["get", "min_height"], 0],
        ["has", "building:min_level"], ["*", ["to-number", ["get", "building:min_level"], 0], LEVEL_HEIGHT],
        0]
    top = ["case",
        ["has", "height"], ["to-number", ["get", "height"], height_fallback],
        ["has", "building:levels"], ["*", ["to-number", ["get", "building:levels"], levels_fallback], LEVEL_HEIGHT],
        ["+", base, no_info_height]]
    return base, ["max", top, ["+", base, 1]]


def facade_color(cfg, fallback):
    materials = cfg.get("materials") or {}
    by_material = fallback
    if materials:
        by_material = ["match", ["get", "building:material"]]
        for value, color in sorted(materials.items()):
            by_material += [value, color]
        by_material.append(fallback)
    if not cfg.get("osm_colour", True):
        return by_material
    return ["to-color", ["get", "building:colour"], by_material, fallback]


def buildings(cfg, pal=None):
    pal = pal or palette({}, "buildings")
    col = cfg["color"] or "#fce1c5"
    bc  = cfg["border_color"] or "#d4a574"
    ap  = cfg["appear_at"]

    base_expr, normal_height_expr = extrusion_exprs(6, 2, 7.5)

    has_height_info = ["any",
        ["has", "height"], ["has", "min_height"],
        ["has", "building:levels"], ["has", "building:min_level"]]

    is_roof = ["==", ["get", "building"], "roof"]
    is_untagged_roof = ["all", is_roof, ["!", has_height_info]]
    roof_color = pal["roof"]

    out = [{"id":"buildings-fill","type":"fill",
             "source":"buildings","source-layer":"buildings","minzoom":ap,
             "paint":{"fill-color":col}}]
    if cfg["extrusion_3d"]:
        out.append({"id":"buildings-3d","type":"fill-extrusion",
            "source":"buildings","source-layer":"buildings","minzoom":ap,
            "layout":{"visibility":"none"},
            "filter": ["all",
                ["==", ["get", "lod"], "detail"],
                ["!=", ["get", "covered_by_parts"], "yes"]],
            "paint":{"fill-extrusion-color": ["case", is_roof, roof_color, facade_color(cfg, col)],
                     "fill-extrusion-base": ["case", is_untagged_roof, 7.2, base_expr],
                     "fill-extrusion-height": ["case", is_untagged_roof, 7.5, normal_height_expr],
                     "fill-extrusion-opacity": 0.75}})
    out.append({"id":"buildings-outline","type":"line",
        "source":"buildings","source-layer":"buildings","minzoom":ap,
        "paint":{"line-color":bc,"line-width":.5}})
    return out


def building_parts_layers(cfg):
    col = cfg["color"] or "#fce1c5"
    base, top = extrusion_exprs(9, 3, 9)
    return [{"id": "building-parts-3d", "type": "fill-extrusion",
             "source": "building_parts", "source-layer": "building_parts", "minzoom": 13,
             "metadata": {"brussels:group": "building_parts"},
             "layout": {"visibility": "none"},
             "paint": {"fill-extrusion-color": facade_color(cfg, col),
                       "fill-extrusion-base": base,
                       "fill-extrusion-height": top,
                       "fill-extrusion-opacity": 0.85}}]

PMTILES_DEFAULTS = {
    "landuse":          {"max_zoom": 18, "simplification": 2},
    "roads":            {"max_zoom": 18, "simplification": 2},
    "water":            {"max_zoom": 18, "simplification": 2},
    "green":            {"max_zoom": 18, "simplification": 2},
    "trees":            {"max_zoom": 18, "simplification": 2},
    "leisure":          {"max_zoom": 18, "simplification": 2},
    "boundaries":       {"max_zoom": 14, "simplification": 10},
    "poi":              {"max_zoom": 16, "simplification": 10},
    "pedestrian":       {"max_zoom": 18, "simplification": 10},
    "cycleway":         {"max_zoom": 18, "simplification": 10},
    "railway":          {"max_zoom": 18, "simplification": 10},
    "public_transport": {"max_zoom": 16, "simplification": 10},
    "street_furniture": {"max_zoom": 18, "simplification": 10},
    "buildings":        {"max_zoom": 18, "simplification": 2, "detail_from": 13},
    "building_parts":   {"min_zoom": 13, "max_zoom": 18, "simplification": 2},
    "indoor":           {"min_zoom": 15, "max_zoom": 18, "simplification": 2},
    "addresses":        {"min_zoom": 16, "max_zoom": 18, "simplification": 10},
}


def tile_settings(config, name):
    raw = ((config.get("layers") or {}).get(name) or {}).get("tiles") or {}
    return {"min_zoom": 10, **PMTILES_DEFAULTS.get(name, {"max_zoom": 18, "simplification": 10}), **raw}


def tile_inputs(config, name):
    t = tile_settings(config, name)
    if name != "buildings":
        return [{"file": f"{name}.json", "min_zoom": t["min_zoom"], "max_zoom": t["max_zoom"]}]
    ap = ((config.get("layers") or {}).get("buildings") or {}).get("appear_at", 10)
    start = max(t["min_zoom"], ap)
    detail_from = max(t["detail_from"], start)
    inputs = []
    if start < detail_from:
        inputs.append({"file": "buildings_merged.json", "min_zoom": start,
                       "max_zoom": detail_from - 1})
    inputs.append({"file": "buildings_detail.json", "min_zoom": detail_from,
                   "max_zoom": t["max_zoom"]})
    return inputs


def build_pmtiles_params(config):
    out = {"_meta": {"generated_by": "build_map.py"}, "layers": {}}
    for name in PMTILES_DEFAULTS:
        t = tile_settings(config, name)
        inputs = tile_inputs(config, name)
        out["layers"][name] = {
            "min_zoom": min(i["min_zoom"] for i in inputs),
            "max_zoom": max(i["max_zoom"] for i in inputs),
            "simplification": t["simplification"],
            "inputs": inputs,
        }
    return out

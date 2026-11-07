from .colors import c


PALETTE_DEFAULTS = {
    "water":            {"tunnel_core": "#e6faf9"},
    "buildings":        {"roof": "#6b4f3a"},
    "leisure":          {"outline": "#adadad"},
    "roads": {
        "bridge_casing": "#000000", "busway_center": "#6699ff",
        "tunnel_area": "#adadad", "tunnel_area_outline": "#ffc0cb",
        "bridge_area": "#ffebee", "bridge_area_outline": "#adadad",
        "label": "#222222", "label_halo": "rgba(255,255,255,0.8)",
        "oneway": "#666666", "oneway_halo": "rgba(255,255,255,0.6)",
    },
    "pedestrian":       {"no_access": "#bbbbbb"},
    "cycleway":         {"oneway": "#ffffff"},
    "railway":          {"bridge_casing": "#000000"},
    "public_transport": {"casing": "#ffffff", "label": "#000000",
                         "label_halo": "rgba(255,255,255,0.85)"},
    "addresses":        {"halo": "rgba(255,255,255,0.85)"},
    "poi":              {"stroke": "#fff", "label_halo": "rgba(255,255,255,0.8)"},
}


def palette(config, group):
    raw = ((config.get("palette") or {}).get(group) or {})
    return {k: c(raw.get(k, v)) for k, v in PALETTE_DEFAULTS[group].items()}


def palette_errors(raw):
    errors = []
    for group, values in (raw or {}).items():
        if group not in PALETTE_DEFAULTS:
            errors.append(f"palette.{group} : groupe inconnu ({', '.join(sorted(PALETTE_DEFAULTS))})")
            continue
        for key in (values or {}):
            if key not in PALETTE_DEFAULTS[group]:
                errors.append(f"palette.{group}.{key} : clé inconnue "
                              f"({', '.join(sorted(PALETTE_DEFAULTS[group]))})")
    return errors

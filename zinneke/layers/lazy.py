from .buildings import building_parts_layers
from .indoor import indoor_layers, indoor_settings


LAZY_GROUPS = ("building_parts", "indoor")


def lazy_layers(config, buildings_cfg, before, excluded=()):
    settings = indoor_settings(config)
    attribution = "© OpenStreetMap contributors"
    groups = [g for g in LAZY_GROUPS if g not in excluded and "buildings" not in excluded]
    if not groups:
        return None
    sources = {g: {"type": "vector", "url": f"./{g}.pmtiles", "attribution": attribution}
               for g in groups}
    layers = []
    if "building_parts" in groups:
        layers += building_parts_layers(buildings_cfg)
    if "indoor" in groups:
        layers += indoor_layers(settings)
    return {
        "before": before,
        "level_height": settings["level_height"],
        "slab": settings["slab"],
        "volume_ratio": settings["volume_ratio"],
        "sources": sources,
        "layers": layers,
    }

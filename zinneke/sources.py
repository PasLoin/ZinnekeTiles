OSM_ATTRIBUTION = "© OpenStreetMap contributors"

SOURCES = [
    "landuse",
    "roads",
    "buildings",
    "water",
    "green",
    "trees",
    "boundaries",
    "poi",
    "pedestrian",
    "cycleway",
    "railway",
    "public_transport",
    "leisure",
    "street_furniture",
    "addresses",
]


def vector_source(name):
    return {"type": "vector", "url": f"./{name}.pmtiles", "attribution": OSM_ATTRIBUTION}

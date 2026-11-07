from .colors import COLORS, c
from .config import DEFAULT_SUBTYPES, lc
from .sources import SOURCES


SUBTYPE_LABELS = {
    "landuse": {
        "allotments": "Jardins familiaux", "brownfield": "Friche", "cemetery": "Cimetière",
        "commercial": "Commercial", "construction": "Chantier", "depot": "Dépôt",
        "education": "Éducation", "farmland": "Terres agricoles", "farmyard": "Cour de ferme",
        "garages": "Garages", "greenfield": "Terrain non bâti", "industrial": "Industriel",
        "landfill": "Décharge", "military": "Militaire", "quarry": "Carrière",
        "railway": "Emprise ferroviaire", "recreation_ground": "Terrain de loisirs",
        "religious": "Religieux", "residential": "Résidentiel", "retail": "Commerces",
        "village_green": "Pelouse communale",
    },
    "water": {
        "canal": "Canal", "ditch": "Fossé", "river": "Rivière", "stream": "Ruisseau",
        "wetland": "Zone humide",
    },
    "green": {
        "flowerbed": "Parterres", "forest": "Forêt", "garden": "Jardins", "grass": "Pelouse",
        "grassland": "Prairie", "heath": "Lande", "meadow": "Pré", "park": "Parcs",
        "scrub": "Broussailles", "shrubbery": "Massifs arbustifs", "wood": "Bois",
    },
    "trees": {"hedge": "Haies", "tree": "Arbres", "tree_row": "Alignements d’arbres"},
    "leisure": {
        "dog_park": "Parc à chiens", "fitness_station": "Fitness extérieur",
        "outdoor_seating": "Terrasses", "pitch": "Terrains de sport", "playground": "Aires de jeux",
    },
    "roads": {
        "motorway": "Autoroute", "motorway_link": "Bretelle d’autoroute",
        "trunk": "Voie rapide", "trunk_link": "Bretelle de voie rapide",
        "primary": "Route principale", "primary_link": "Bretelle principale",
        "secondary": "Route secondaire", "secondary_link": "Bretelle secondaire",
        "tertiary": "Route tertiaire", "tertiary_link": "Bretelle tertiaire",
        "residential": "Rue résidentielle", "unclassified": "Route non classée",
        "living_street": "Zone de rencontre", "service": "Voie de service",
        "busway": "Site propre bus", "track": "Chemin agricole",
    },
    "pedestrian": {
        "footway": "Chemins piétons", "path": "Sentiers", "pedestrian": "Rues piétonnes",
        "steps": "Escaliers",
    },
    "railway": {"miniature": "Miniature", "rail": "Rail", "subway": "Métro", "tram": "Tram"},
    "public_transport": {"tram": "Tram", "subway": "Métro", "bus": "Bus"},
    "street_furniture": {
        "bench": "Bancs", "bollard": "Potelets", "bus_trap": "Sas Bus",
        "cycle_barrier": "Chicanes vélo", "entrance": "Entrées", "fence": "Clôtures",
        "gate": "Portails", "lift_gate": "Barrières levantes", "lounger": "Transats",
        "planter": "Bacs à plantes", "street_lamp": "Lampadaires",
        "vending_machine": "Distributeurs", "waste_basket": "Poubelles",
        "defibrillator": "Défibrillateurs", "fire_hydrant": "Bornes incendie",
        "fire_extinguisher": "Extincteurs", "fire_hose": "Dévidoirs incendie",
        "life_ring": "Bouées de sauvetage", "phone": "Téléphones d’urgence",
        "assembly_point": "Points de rassemblement",
        "atm": "Distributeurs de billets", "charging_station": "Bornes de recharge",
        "bicycle_rental": "Vélos partagés", "car_sharing": "Voitures partagées",
        "taxi": "Stations de taxi", "parcel_locker": "Consignes à colis",
        "toilets": "Toilettes", "drinking_water": "Eau potable", "fountain": "Fontaines",
        "public_bookcase": "Boîtes à livres", "bicycle_repair_station": "Réparation vélo",
        "dog_toilet": "Canisites", "post_box": "Boîtes aux lettres",
        "recycling": "Recyclage", "clock": "Horloges", "photo_booth": "Photomatons",
        "give_box": "Boîtes à dons", "artwork": "Œuvres d’art",
    },
}


LEGEND_TOKEN_ALIASES = {
    "pedestrian": {"street": "pedestrian"},
    "trees": {"row": "tree_row"},
}


LEGEND_FALLBACK_COLOR = "#cccccc"


PAINT_COLOR_KEYS = ("fill-color", "line-color", "circle-color",
                    "fill-extrusion-color", "icon-color", "text-color")


def default_subtype_label(group, key):
    return SUBTYPE_LABELS.get(group, {}).get(key) or key.replace("_", " ").capitalize()


def _expr_color(expr):
    if isinstance(expr, str):
        return expr if expr.startswith(("#", "rgb", "hsl")) or expr in COLORS else None
    if isinstance(expr, list):
        for item in reversed(expr[1:]):
            found = _expr_color(item)
            if found:
                return c(found)
    return None


def paint_color(layers):
    rank = lambda l: tuple(part in l["id"].split("-") for part in ("casing", "tunnel", "bridge"))
    for l in sorted(layers, key=rank):
        paint = l.get("paint") or {}
        for key in PAINT_COLOR_KEYS:
            found = _expr_color(paint.get(key))
            if found:
                return c(found)
    return None


SWATCH_OF_TYPE = {"fill": "fill", "fill-extrusion": "fill", "line": "line",
                  "circle": "dot", "symbol": "dot"}


SWATCH_TYPES = ("fill", "line", "dot")


def swatch_type(layers):
    counts = {k: 0 for k in SWATCH_TYPES}
    for l in layers:
        if l["type"] != "symbol":
            counts[SWATCH_OF_TYPE.get(l["type"], "dot")] += 1
    if not any(counts.values()):
        return "dot"
    return max(SWATCH_TYPES, key=lambda k: counts[k])


def legend_subtype(group, layer_id, keys):
    aliases = LEGEND_TOKEN_ALIASES.get(group, {})
    for token in reversed(layer_id.split("-")[1:]):
        key = aliases.get(token, token)
        if key in keys:
            return key
    head = layer_id.split("-")[0]
    return head if head in keys and head != group else None


LEGEND_GROUP_TAGS = {"landuse": "landuse", "leisure": "leisure", "roads": "highway",
                     "pedestrian": "highway", "railway": "railway", "public_transport": "route"}


LEGEND_SUBTYPE_TAGS = {"water": {"wetland": "natural"}}


def subtype_filter(group, key, raw):
    tag = ((raw or {}).get("tag")
           or (DEFAULT_SUBTYPES.get(group, {}).get(key) or {}).get("tag")
           or LEGEND_SUBTYPE_TAGS.get(group, {}).get(key)
           or LEGEND_GROUP_TAGS.get(group))
    if not tag:
        return None
    if key == tag:
        return ["has", tag]
    return ["==", ["get", tag], key]


def build_legend(config, layers):
    L = config.get("layers") or {}
    by_source = {}
    for l in layers:
        if l.get("source"):
            by_source.setdefault(l["source"], []).append(l)
    order = [n for n in L if n in by_source] + [n for n in SOURCES if n in by_source and n not in L]
    legend = []
    for name in order:
        cfg = lc(L, name)
        group_layers = by_source[name]
        known = list(cfg["subtypes"])
        known += [k for k in {**DEFAULT_SUBTYPES.get(name, {}), **SUBTYPE_LABELS.get(name, {})}
                  if k not in known]
        assigned = {}
        for l in group_layers:
            key = legend_subtype(name, l["id"], known)
            assigned.setdefault(key, []).append(l)
        own = assigned.get(None, [])
        keys = [k for k in cfg["subtypes"]
                if k in assigned or (own and subtype_filter(name, k, cfg["subtypes"].get(k)))]
        keys += [k for k in assigned if k is not None and k not in keys]
        items = []
        for key in keys:
            raw = cfg["subtypes"].get(key) or {}
            item_layers = assigned.get(key, [])
            color = (c(raw.get("color")) or paint_color(item_layers) or cfg["color"]
                     or paint_color(own) or LEGEND_FALLBACK_COLOR)
            item = {"id": key,
                    "label": raw.get("label") or default_subtype_label(name, key),
                    "color": color,
                    "swatch": swatch_type(item_layers or own),
                    "layers": [l["id"] for l in item_layers]}
            filt = subtype_filter(name, key, raw) if own else None
            if filt:
                item["filter"] = filt
                if not item_layers and raw.get("appear_at") not in (None, cfg["appear_at"]):
                    item["appear_at"] = raw["appear_at"]
            items.append(item)
        color = (cfg["color"] or (items[0]["color"] if items else None)
                 or paint_color(own) or LEGEND_FALLBACK_COLOR)
        swatch = (L.get(name) or {}).get("swatch")
        if swatch not in SWATCH_TYPES:
            swatch = swatch_type(group_layers)
        entry = {"id": name, "label": cfg["label"], "color": color,
                 "swatch": swatch, "visible": bool(cfg["visible"]),
                 "layers": [l["id"] for l in own], "items": items}
        colors = [c(v) for v in (L.get(name) or {}).get("swatch_colors") or [] if v]
        if len(colors) > 1:
            entry["colors"] = colors
        legend.append(entry)
    return legend

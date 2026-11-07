import copy
import re
from pathlib import Path

import yaml

from .config import with_default_subtypes
from .layers.indoor import INDOOR_DEFAULTS
from .layers.lazy import LAZY_GROUPS
from .layers.roads import ROAD_DEFAULTS, ROAD_LEGACY_GROUP, ROAD_ORDER, road_subtype
from .palette import palette_errors
from .patterns import DEFAULT_PATTERNS
from .sources import SOURCES


VARIANT_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


VARIANT_KEYS = ("variant", "exclude", "map", "palette", "patterns", "layers")


VARIANT_DATA_KEYS = ("tiles", "density", "tag")


DEFAULT_VARIANT = {"id": "default", "label": "Standard"}


class VariantError(ValueError):
    pass


def deep_merge(base, over):
    if not isinstance(base, dict) or not isinstance(over, dict):
        return copy.deepcopy(over)
    out = copy.deepcopy(base)
    for key, value in over.items():
        if value is None:
            out.pop(key, None)
        elif key in out:
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def variant_layer_names(base):
    return set((base.get("layers") or {})) | set(SOURCES) | {"indoor"}


def _base_layer(base, name):
    return (with_default_subtypes(base).get("layers") or {}).get(name) or {}


def known_subtypes(base, name):
    keys = set((_base_layer(base, name).get("subtypes") or {}))
    if name == "roads":
        keys |= set(ROAD_ORDER) | set(ROAD_LEGACY_GROUP.values())
    if name == "indoor":
        keys |= set(INDOOR_DEFAULTS["colors"])
    return keys


def base_appear_at(base, name, key=None):
    raw = _base_layer(base, name)
    ap = raw.get("appear_at", INDOOR_DEFAULTS["appear_at"] if name == "indoor" else 10)
    if key is None:
        return ap
    if name == "roads" and key in ROAD_DEFAULTS:
        return road_subtype(raw, key)["appear_at"]
    return ((raw.get("subtypes") or {}).get(key) or {}).get("appear_at", ap)


def _data_key_paths(node, path):
    if not isinstance(node, dict):
        return []
    found = []
    for key, value in node.items():
        here = f"{path}.{key}"
        if key in VARIANT_DATA_KEYS:
            found.append(here)
        found += _data_key_paths(value, here)
    return found


def variant_errors(base, raw, vid):
    errors = []
    if not VARIANT_ID_RE.match(vid) or vid == DEFAULT_VARIANT["id"]:
        errors.append(f"identifiant « {vid} » invalide : minuscules, chiffres et tirets, "
                      f"et différent de « {DEFAULT_VARIANT['id']} »")
    if not isinstance(raw, dict):
        return errors + ["le fichier doit contenir un objet YAML"]
    for key in raw:
        if key not in VARIANT_KEYS:
            errors.append(f"clé de premier niveau inconnue : {key} ({', '.join(VARIANT_KEYS)})")
    names = variant_layer_names(base)
    exclude = raw.get("exclude") or []
    if not isinstance(exclude, list):
        errors.append("exclude doit être une liste de couches")
        exclude = []
    for name in exclude:
        if name not in names | set(LAZY_GROUPS):
            errors.append(f"exclude : couche inconnue « {name} »")
    errors += palette_errors(raw.get("palette"))
    declared = {**DEFAULT_PATTERNS, **(base.get("patterns") or {})}
    for pname, pcfg in (raw.get("patterns") or {}).items():
        if pname not in declared and not (pcfg or {}).get("file"):
            errors.append(f"patterns.{pname} : nouveau motif sans « file »")
    for name, layer in (raw.get("layers") or {}).items():
        where = f"layers.{name}"
        if name not in names:
            errors.append(f"{where} : couche inconnue")
            continue
        if layer is None:
            errors.append(f"{where} : une couche ne se supprime pas avec null, utilisez exclude")
            continue
        if not isinstance(layer, dict):
            errors.append(f"{where} : objet YAML attendu")
            continue
        for path in _data_key_paths(layer, where):
            errors.append(f"{path} : clé de données interdite dans une variante "
                          f"(les tuiles sont communes à tous les styles)")
        if "appear_at" in layer and layer["appear_at"] < base_appear_at(base, name):
            errors.append(f"{where}.appear_at : {layer['appear_at']} < {base_appear_at(base, name)} "
                          f"(une variante ne peut pas afficher plus tôt que les tuiles)")
        known = known_subtypes(base, name)
        for key, scfg in (layer.get("subtypes") or {}).items():
            swhere = f"{where}.subtypes.{key}"
            if key not in known:
                errors.append(f"{swhere} : sous-type absent de la base")
                continue
            if isinstance(scfg, dict) and "appear_at" in scfg \
                    and scfg["appear_at"] < base_appear_at(base, name, key):
                errors.append(f"{swhere}.appear_at : {scfg['appear_at']} < "
                              f"{base_appear_at(base, name, key)} "
                              f"(une variante ne peut pas afficher plus tôt que les tuiles)")
    return errors


def load_variant(path):
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    meta = (raw.get("variant") or {}) if isinstance(raw, dict) else {}
    return {"id": path.stem, "label": str(meta.get("label") or path.stem),
            "path": str(path), "raw": raw}


def apply_variant(base, variant):
    raw = variant["raw"]
    errors = variant_errors(base, raw, variant["id"])
    if errors:
        raise VariantError("\n".join(f"  - {e}" for e in errors))
    merged = copy.deepcopy(base)
    for key in ("map", "palette", "layers"):
        if raw.get(key):
            merged[key] = deep_merge(base.get(key) or {}, raw[key])
    if raw.get("patterns"):
        merged["patterns"] = deep_merge({**DEFAULT_PATTERNS, **(base.get("patterns") or {})},
                                        raw["patterns"])
    return merged

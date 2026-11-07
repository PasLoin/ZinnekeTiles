import sys

DEFAULT_PATTERNS = {
    "military-hatch": {"file": "assets/military_hatch.svg", "size": 20},
    "green-hatch": {
        "file": "assets/military_hatch.svg",
        "size": 20,
        "replace": {"#bd4a72": "#a9ccac"},
    },
    "grave_yard_generic": {"file": "assets/patterns/grave_yard_generic.svg", "size": 32},
    "grave_yard_christian": {"file": "assets/patterns/grave_yard_christian.svg", "size": 32},
    "grave_yard_jewish": {"file": "assets/patterns/grave_yard_jewish.svg", "size": 32},
    "grave_yard_muslim": {"file": "assets/patterns/grave_yard_muslim.svg", "size": 32},
}


def _pattern_names(expr):
    if isinstance(expr, str):
        return {expr}
    if isinstance(expr, list) and expr and expr[0] == "match":
        names = set()
        for i, item in enumerate(expr[2:], start=2):
            if (i % 2 == 1 or i == len(expr) - 1) and isinstance(item, str):
                names.add(item)
        return names
    return set()


def resolve_patterns(config, layers):
    declared = {**DEFAULT_PATTERNS, **(config.get("patterns") or {})}
    used = set()
    for layer in layers:
        used |= _pattern_names((layer.get("paint") or {}).get("fill-pattern"))
    missing = sorted(used - set(declared))
    if missing:
        print(f"⚠  motifs utilisés mais non déclarés dans patterns: {missing}", file=sys.stderr)
    return {name: declared[name] for name in sorted(used) if name in declared}

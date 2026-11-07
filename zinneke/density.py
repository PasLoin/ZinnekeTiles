POI_RANK_FIELD = "poi_rank"


POI_TIER_FIELD = "poi_tier"


def poi_density(raw):
    d = (raw or {}).get("density")
    if not d:
        return None
    tiers = []
    for t in d.get("tiers") or []:
        tiers.append(
            {
                str(k): [str(x) for x in (v if isinstance(v, list) else [v])]
                for k, v in (t or {}).items()
            }
        )
    out = {
        "grid": int(d.get("grid", 128)),
        "show": {int(k): int(v) for k, v in (d.get("show") or {}).items()},
        "tiers": tiers,
    }
    for k in ("dots_at", "overlap_at"):
        if d.get(k) is not None:
            out[k] = int(d[k])
    return out


def density_meta(d):
    out = {k: v for k, v in d.items() if k != "show"}
    out["show"] = {str(z): n for z, n in sorted(d["show"].items())}
    return out


def poi_rank_filter(d):
    show = sorted(d["show"].items())
    if not show:
        return None
    step = ["step", ["zoom"], show[0][1]]
    for z, n in show[1:]:
        step += [z, n]
    return [
        "any",
        [">=", ["zoom"], show[-1][0] + 1],
        ["<=", ["coalesce", ["get", POI_RANK_FIELD], 0], step],
    ]


def poi_sort_key(d):
    return [
        "+",
        ["*", ["coalesce", ["get", POI_TIER_FIELD], len(d["tiers"]) + 1], 1000],
        ["coalesce", ["get", POI_RANK_FIELD], 0],
    ]

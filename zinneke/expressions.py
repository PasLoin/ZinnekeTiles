def by_expr(s, field, default):
    values = s.get(field) or {}
    if not s.get("by") or not values:
        return default
    expr = ["match", ["get", s["by"]]]
    for k in sorted(values):
        expr += [k, values[k]]
    expr.append(default)
    return expr


def zoom(pairs):
    stops = []
    for z, v in pairs:
        if stops and z <= stops[-1][0]:
            stops[-1] = (stops[-1][0], v)
        else:
            stops.append((z, v))
    if len(stops) == 1: return stops[0][1]
    e = ["interpolate",["linear"],["zoom"]]
    for z,v in stops: e += [z,v]
    return e


def color_or_case(col, col_private):
    if col_private:
        return ["case", ["==", ["get", "access"], "private"], col_private, col]
    return col


def interp(stops, z):
    if z <= stops[0][0]:  return stops[0][1]
    if z >= stops[-1][0]: return stops[-1][1]
    for (z0, v0), (z1, v1) in zip(stops, stops[1:]):
        if z0 <= z <= z1:
            return round(v0 + (v1 - v0) * (z - z0) / (z1 - z0), 2)


def curve_from(stops, ap):
    return [(ap, interp(stops, ap))] + [(z, w) for z, w in stops if z > ap]

#!/usr/bin/env python3
import argparse
import json
import math
import re
import struct
import sys
from collections import Counter
from pathlib import Path

try:
    import shapely
    from shapely.geometry import Polygon, MultiPolygon, GeometryCollection, Point, shape
    from shapely.geometry.polygon import orient
except ImportError:
    print("✗  pip install 'shapely>=2.1'", file=sys.stderr)
    sys.exit(1)

LEVEL_HEIGHT = 3.0
EARTH_RADIUS = 6371008.8
ORIGIN = (4.3517, 50.8503)
CHUNK_SIZE = 1000.0
MAX_VERTICES = 65535
MIN_AREA = 4.0
MIN_RECTANGULARITY = 0.7
MIN_CONVEXITY = 0.85
FLAT_OFFSET = 0.15
EPS = 1e-6

BUILDING_DEFAULTS = (6.0, 2.0, 7.5)
PART_DEFAULTS = (9.0, 3.0, 9.0)

DEFAULT_WALL = "#fce1c5"
DEFAULT_ROOF = "#8c5a46"

ROOF_MATERIALS = {
    "roof_tiles": "#a4553b", "tile": "#a4553b", "tiles": "#a4553b",
    "slate": "#4b5059", "metal": "#8b9096", "metal_sheet": "#8b9096",
    "zinc": "#8f969c", "copper": "#5f9c87", "lead": "#7d8288",
    "concrete": "#9b9a96", "glass": "#a9c4d1", "asphalt_shingle": "#5a5652",
    "tar_paper": "#4a4846", "eternit": "#8d8d88", "thatch": "#b39a62",
    "wood": "#8a6a48", "stone": "#9a958b", "gravel": "#a39f96",
    "plants": "#7c9a5a", "grass": "#7c9a5a", "plastic": "#c9c9c4",
}

ROOF_NAMED = {
    "red": "#b04a36", "darkred": "#7f2f24", "brown": "#7a4a32", "darkbrown": "#5a3524",
    "maroon": "#6e2a22", "orange": "#c9763f", "black": "#2e2e30", "grey": "#8a8a8a",
    "gray": "#8a8a8a", "darkgrey": "#5c5f63", "darkgray": "#5c5f63", "lightgrey": "#c4c4c4",
    "lightgray": "#c4c4c4", "white": "#efefea", "green": "#4f7a52", "darkgreen": "#3b5a3d",
    "blue": "#50627a", "darkblue": "#3a4760", "yellow": "#d4bd70", "beige": "#d8c9a8",
}

CSS_TABLE = """
aliceblue:f0f8ff antiquewhite:faebd7 aqua:00ffff aquamarine:7fffd4 azure:f0ffff beige:f5f5dc
bisque:ffe4c4 black:000000 blanchedalmond:ffebcd blue:0000ff blueviolet:8a2be2 brown:a52a2a
burlywood:deb887 cadetblue:5f9ea0 chartreuse:7fff00 chocolate:d2691e coral:ff7f50
cornflowerblue:6495ed cornsilk:fff8dc crimson:dc143c cyan:00ffff darkblue:00008b darkcyan:008b8b
darkgoldenrod:b8860b darkgray:a9a9a9 darkgreen:006400 darkgrey:a9a9a9 darkkhaki:bdb76b
darkmagenta:8b008b darkolivegreen:556b2f darkorange:ff8c00 darkorchid:9932cc darkred:8b0000
darksalmon:e9967a darkseagreen:8fbc8f darkslateblue:483d8b darkslategray:2f4f4f
darkslategrey:2f4f4f darkturquoise:00ced1 darkviolet:9400d3 deeppink:ff1493 deepskyblue:00bfff
dimgray:696969 dimgrey:696969 dodgerblue:1e90ff firebrick:b22222 floralwhite:fffaf0
forestgreen:228b22 fuchsia:ff00ff gainsboro:dcdcdc ghostwhite:f8f8ff gold:ffd700
goldenrod:daa520 gray:808080 green:008000 greenyellow:adff2f grey:808080 honeydew:f0fff0
hotpink:ff69b4 indianred:cd5c5c indigo:4b0082 ivory:fffff0 khaki:f0e68c lavender:e6e6fa
lavenderblush:fff0f5 lawngreen:7cfc00 lemonchiffon:fffacd lightblue:add8e6 lightcoral:f08080
lightcyan:e0ffff lightgoldenrodyellow:fafad2 lightgray:d3d3d3 lightgreen:90ee90 lightgrey:d3d3d3
lightpink:ffb6c1 lightsalmon:ffa07a lightseagreen:20b2aa lightskyblue:87cefa
lightslategray:778899 lightslategrey:778899 lightsteelblue:b0c4de lightyellow:ffffe0 lime:00ff00
limegreen:32cd32 linen:faf0e6 magenta:ff00ff maroon:800000 mediumaquamarine:66cdaa
mediumblue:0000cd mediumorchid:ba55d3 mediumpurple:9370db mediumseagreen:3cb371
mediumslateblue:7b68ee mediumspringgreen:00fa9a mediumturquoise:48d1cc mediumvioletred:c71585
midnightblue:191970 mintcream:f5fffa mistyrose:ffe4e1 moccasin:ffe4b5 navajowhite:ffdead
navy:000080 oldlace:fdf5e6 olive:808000 olivedrab:6b8e23 orange:ffa500 orangered:ff4500
orchid:da70d6 palegoldenrod:eee8aa palegreen:98fb98 paleturquoise:afeeee palevioletred:db7093
papayawhip:ffefd5 peachpuff:ffdab9 peru:cd853f pink:ffc0cb plum:dda0dd powderblue:b0e0e6
purple:800080 rebeccapurple:663399 red:ff0000 rosybrown:bc8f8f royalblue:4169e1
saddlebrown:8b4513 salmon:fa8072 sandybrown:f4a460 seagreen:2e8b57 seashell:fff5ee sienna:a0522d
silver:c0c0c0 skyblue:87ceeb slateblue:6a5acd slategray:708090 slategrey:708090 snow:fffafa
springgreen:00ff7f steelblue:4682b4 tan:d2b48c teal:008080 thistle:d8bfd8 tomato:ff6347
turquoise:40e0d0 violet:ee82ee wheat:f5deb3 white:ffffff whitesmoke:f5f5f5 yellow:ffff00
yellowgreen:9acd32
"""

CSS_NAMED = {k: "#" + v for k, v in (item.split(":") for item in CSS_TABLE.split())}

COMPASS = {
    "N": 0, "NNE": 22.5, "NE": 45, "ENE": 67.5, "E": 90, "ESE": 112.5, "SE": 135, "SSE": 157.5,
    "S": 180, "SSW": 202.5, "SW": 225, "WSW": 247.5, "W": 270, "WNW": 292.5, "NW": 315, "NNW": 337.5,
}

SHAPE_ALIASES = {
    "gabled": "gabled", "hipped": "hipped", "side_hipped": "side_hipped",
    "half-hipped": "half_hipped", "half_hipped": "half_hipped",
    "pyramidal": "pyramidal", "cone": "pyramidal", "skillion": "skillion",
    "round": "round", "gambrel": "gambrel", "mansard": "mansard", "saltbox": "saltbox",
    "dome": "dome", "domed": "dome", "onion": "dome",
}

_light = (-0.35, 0.45, 0.82)
_norm = math.sqrt(sum(c * c for c in _light))
LIGHT = tuple(c / _norm for c in _light)


def js_number(value, fallback):
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return fallback
    return number if math.isfinite(number) else fallback


def loose_number(value):
    if value is None:
        return None
    match = re.search(r"-?\d+(?:[.,]\d+)?", str(value))
    if not match:
        return None
    return float(match.group(0).replace(",", "."))


def parse_direction(value):
    if value is None:
        return None
    text = str(value).strip().upper()
    if text in COMPASS:
        return float(COMPASS[text])
    number = loose_number(text)
    return None if number is None else number % 360.0


def parse_color(value, named, strict=False):
    if value is None:
        return None
    text = str(value).strip().lower()
    if not strict:
        text = text.replace(" ", "").replace("_", "")
    if text in named:
        text = named[text]
    if re.fullmatch(r"#[0-9a-f]{6}" if strict else r"#?[0-9a-f]{6}", text):
        text = text.lstrip("#")
        return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))
    if re.fullmatch(r"#[0-9a-f]{3}", text):
        return tuple(int(c * 2, 16) for c in text[1:])
    return None


def material_key(value):
    return str(value or "").strip().lower()


def explicit_roof_color(props):
    colour = props.get("roof:colour")
    return (parse_color(colour, {**CSS_NAMED, **ROOF_NAMED})
            or parse_color(ROOF_MATERIALS.get(material_key(colour)), {})
            or parse_color(ROOF_MATERIALS.get(material_key(props.get("roof:material"))), {}))


def roof_color(props):
    return explicit_roof_color(props) or parse_color(DEFAULT_ROOF, {})


class Palette:
    def __init__(self, default=None, materials=None):
        self.default = default or parse_color(DEFAULT_WALL, {})
        self.materials = materials or {}


def wall_color(props, palette):
    return (parse_color(props.get("building:colour"), CSS_NAMED, strict=True)
            or palette.materials.get(material_key(props.get("building:material")))
            or palette.default)


def roof_kind(props):
    shape_value = str(props.get("roof:shape", "")).strip().lower()
    if shape_value in ("", "flat"):
        return "flat" if explicit_roof_color(props) else None
    return SHAPE_ALIASES.get(shape_value)


def wall_profile(props, defaults):
    height_fallback, levels_fallback, no_info = defaults
    if "min_height" in props:
        base = js_number(props["min_height"], 0.0)
    elif "building:min_level" in props:
        base = js_number(props["building:min_level"], 0.0) * LEVEL_HEIGHT
    else:
        base = 0.0
    if "height" in props:
        top, explicit = js_number(props["height"], height_fallback), True
    elif "building:levels" in props:
        top, explicit = js_number(props["building:levels"], levels_fallback) * LEVEL_HEIGHT, False
    else:
        top, explicit = base + no_info, False
    return base, max(top, base + 1.0), explicit


def default_roof_height(kind, half_width, half_length, props):
    explicit = loose_number(props.get("roof:height"))
    if explicit is not None and explicit > 0:
        return explicit, True
    levels = loose_number(props.get("roof:levels"))
    if levels is not None and levels > 0:
        return levels * LEVEL_HEIGHT, True
    angle = loose_number(props.get("roof:angle"))
    span = 2 * half_width if kind == "skillion" else half_width
    if angle is not None and 0 < angle < 89:
        return span * math.tan(math.radians(angle)), True
    if kind == "skillion":
        return min(span * math.tan(math.radians(15)), 4.0), False
    if kind == "dome":
        return min(half_width, half_length, 15.0), False
    if kind == "round":
        return min(half_width * 0.5, 6.0), False
    return min(half_width * math.tan(math.radians(40)), 8.0), False


def resolve_heights(base, top, explicit_height, roof_height, roof_explicit):
    if explicit_height:
        if not roof_explicit:
            roof_height = min(roof_height, 0.5 * (top - base))
        eaves = max(base + 0.5, top - roof_height)
        return eaves, top - eaves
    return top, roof_height


class Projector:
    def __init__(self, lon0, lat0):
        self.mx0, self.my0 = self.mercator(lon0, lat0)
        self.scale = 2 * math.pi * EARTH_RADIUS * math.cos(math.radians(lat0))

    @staticmethod
    def mercator(lon, lat):
        x = (180.0 + lon) / 360.0
        y = (180.0 - (180.0 / math.pi) * math.log(math.tan(math.pi / 4 + lat * math.pi / 360.0))) / 360.0
        return x, y

    def local(self, lon, lat):
        mx, my = self.mercator(lon, lat)
        return (mx - self.mx0) * self.scale, -(my - self.my0) * self.scale

    def polygon(self, geom):
        def ring(coords):
            return [self.local(c[0], c[1]) for c in coords]
        return Polygon(ring(geom.exterior.coords), [ring(r.coords) for r in geom.interiors])


class Frame:
    def __init__(self, poly, props, kind):
        direction = parse_direction(props.get("roof:direction"))
        if direction is not None:
            t = math.radians(direction)
            b = (math.sin(t), math.cos(t))
            a = (b[1], -b[0])
        else:
            rect = list(poly.minimum_rotated_rectangle.exterior.coords)
            e1 = (rect[1][0] - rect[0][0], rect[1][1] - rect[0][1])
            e2 = (rect[2][0] - rect[1][0], rect[2][1] - rect[1][1])
            longer, shorter = (e1, e2) if math.hypot(*e1) >= math.hypot(*e2) else (e2, e1)
            ridge = shorter if str(props.get("roof:orientation", "")).strip().lower() == "across" else longer
            n = math.hypot(*ridge)
            a = (ridge[0] / n, ridge[1] / n)
            b = (-a[1], a[0])
        us = [x * a[0] + y * a[1] for x, y in poly.exterior.coords]
        vs = [x * b[0] + y * b[1] for x, y in poly.exterior.coords]
        um, vm = (min(us) + max(us)) / 2, (min(vs) + max(vs)) / 2
        self.a, self.b = a, b
        self.center = (a[0] * um + b[0] * vm, a[1] * um + b[1] * vm)
        self.half_length = (max(us) - min(us)) / 2
        self.half_width = (max(vs) - min(vs)) / 2

    def plane(self, p, q, r):
        a, b, (cx, cy) = self.a, self.b, self.center
        A = p * a[0] + q * b[0]
        B = p * a[1] + q * b[1]
        return (A, B, r - A * cx - B * cy)


def profile_planes(frame, points, axis, sign, extent, scale):
    planes = []
    for (x0, h0), (x1, h1) in zip(points, points[1:]):
        m = (h1 - h0) / (x1 - x0)
        d = -m * sign / scale
        const = h0 + m * (extent / scale - x0)
        planes.append(frame.plane(d, 0.0, const) if axis == "u" else frame.plane(0.0, d, const))
    return planes


ROUND_PROFILE = [(e, math.sqrt(max(0.0, 1 - (1 - e) ** 2))) for e in (0.0, 0.1, 0.25, 0.45, 0.7, 1.0)]
GABLE_PROFILE = [(0.0, 0.0), (1.0, 1.0)]
GAMBREL_PROFILE = [(0.0, 0.0), (0.4, 0.75), (1.0, 1.0)]
MANSARD_PROFILE = [(0.0, 0.0), (0.2, 0.8), (1.0, 1.0)]


def frame_planes(kind, frame):
    l, w = frame.half_length, frame.half_width

    def sides(points):
        return (profile_planes(frame, points, "v", 1, w, w)
                + profile_planes(frame, points, "v", -1, w, w))

    def ends(points, signs=(1, -1)):
        out = []
        for s in signs:
            out += profile_planes(frame, points, "u", s, l, w)
        return out

    if kind == "gabled":
        return sides(GABLE_PROFILE)
    if kind == "round":
        return sides(ROUND_PROFILE)
    if kind == "gambrel":
        return sides(GAMBREL_PROFILE)
    if kind == "hipped":
        return sides(GABLE_PROFILE) + ends(GABLE_PROFILE)
    if kind == "side_hipped":
        return sides(GABLE_PROFILE) + ends(GABLE_PROFILE, (1,))
    if kind == "half_hipped":
        return sides(GABLE_PROFILE) + ends([(0.0, 0.5), (1.0, 1.5)])
    if kind == "mansard":
        return sides(MANSARD_PROFILE) + ends(MANSARD_PROFILE)
    if kind == "skillion":
        return [frame.plane(0.0, -1.0 / (2 * w), 0.5)]
    if kind == "saltbox":
        r = -0.3
        return [frame.plane(0.0, -1.0 / (w * (1 - r)), 1.0 / (1 - r)),
                frame.plane(0.0, 1.0 / (w * (1 + r)), 1.0 / (1 + r))]
    if kind == "dome":
        planes = [frame.plane(0.0, 0.0, 1.0)]
        for rho in (0.4, 0.65, 0.82, 0.93):
            for k in range(16):
                t = 2 * math.pi * k / 16
                u0, v0 = rho * l * math.cos(t), rho * w * math.sin(t)
                h0 = math.sqrt(1 - rho * rho)
                du, dv = -u0 / (l * l * h0), -v0 / (w * w * h0)
                planes.append(frame.plane(du, dv, h0 - du * u0 - dv * v0))
        return planes
    return []


def pyramid_planes(poly):
    hull = orient(poly.convex_hull, 1.0)
    cx, cy = hull.centroid.x, hull.centroid.y
    pts = list(hull.exterior.coords)
    planes = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        nx, ny = -(y1 - y0), x1 - x0
        dc = (cx - x0) * nx + (cy - y0) * ny
        if dc <= EPS:
            continue
        A, B = nx / dc, ny / dc
        planes.append((A, B, -(A * x0 + B * y0)))
    return planes


def evaluate(plane, x, y):
    return plane[0] * x + plane[1] * y + plane[2]


def clip(polygon, g):
    out = []
    n = len(polygon)
    for i in range(n):
        p, q = polygon[i], polygon[(i + 1) % n]
        gp, gq = g(p), g(q)
        if gp <= 0:
            out.append(p)
        if (gp < 0 < gq) or (gq < 0 < gp):
            t = gp / (gp - gq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def regions(planes, bounds):
    minx, miny, maxx, maxy = bounds
    pad = 1.0
    rect = [(minx - pad, miny - pad), (maxx + pad, miny - pad), (maxx + pad, maxy + pad), (minx - pad, maxy + pad)]
    for i, pi in enumerate(planes):
        poly = clip(rect, lambda p, pi=pi: -evaluate(pi, *p))
        for j, pj in enumerate(planes):
            if i == j or len(poly) < 3:
                continue
            dA, dB, dC = pi[0] - pj[0], pi[1] - pj[1], pi[2] - pj[2]
            if abs(dA) < 1e-12 and abs(dB) < 1e-12:
                if dC > 0 or (abs(dC) <= 1e-12 and j < i):
                    poly = []
                continue
            poly = clip(poly, lambda p, dA=dA, dB=dB, dC=dC: dA * p[0] + dB * p[1] + dC)
        if len(poly) >= 3:
            yield pi, Polygon(poly)


def polygons_of(geom):
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, (MultiPolygon, GeometryCollection)):
        return [p for g in geom.geoms for p in polygons_of(g)]
    return []


def shade(color, factor):
    return tuple(max(0, min(255, int(round(c * factor)))) for c in color)


def roof_shade(plane, height_scale):
    nx, ny, nz = -plane[0] * height_scale, -plane[1] * height_scale, 1.0
    n = math.sqrt(nx * nx + ny * ny + nz * nz)
    d = (nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2]) / n
    return 0.7 + 0.3 * d


def wall_shade(nx, ny):
    return 0.66 + 0.22 * (nx * LIGHT[0] + ny * LIGHT[1])


class Roof:
    def __init__(self):
        self.groups = []

    def add(self, vertices, triangles, color):
        self.groups.append((vertices, triangles, color))


def build_roof(poly, kind, frame, eaves, roof_height, roof_rgb, wall_rgb):
    planes = pyramid_planes(poly) if kind == "pyramidal" else frame_planes(kind, frame)
    if not planes:
        return None
    pieces = []
    for plane, region in regions(planes, poly.bounds):
        for piece in polygons_of(poly.intersection(region)):
            if piece.area > 1e-3:
                pieces.append((plane, piece))
    if not pieces:
        return None
    peak = max(evaluate(plane, x, y) for plane, piece in pieces for x, y in piece.exterior.coords)
    if peak <= 1e-3:
        return None
    scale = roof_height / peak
    boundary = poly.boundary
    roof = Roof()

    def z(plane, x, y):
        return eaves + max(0.0, evaluate(plane, x, y)) * scale

    for plane, piece in pieces:
        index, vertices, triangles = {}, [], []
        for tri in polygons_of(shapely.constrained_delaunay_triangles(piece)):
            pts = list(tri.exterior.coords)[:3]
            area2 = (pts[1][0] - pts[0][0]) * (pts[2][1] - pts[0][1]) - (pts[2][0] - pts[0][0]) * (pts[1][1] - pts[0][1])
            if abs(area2) < 1e-9:
                continue
            if area2 < 0:
                pts = [pts[0], pts[2], pts[1]]
            ids = []
            for x, y in pts:
                key = (round(x, 4), round(y, 4))
                if key not in index:
                    index[key] = len(vertices)
                    vertices.append((x, y, z(plane, x, y)))
                ids.append(index[key])
            if len(set(ids)) == 3:
                triangles.append(tuple(ids))
        if triangles:
            roof.add(vertices, triangles, shade(roof_rgb, roof_shade(plane, scale)))

        for ring in [piece.exterior, *piece.interiors]:
            pts = list(ring.coords)
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                length = math.hypot(x1 - x0, y1 - y0)
                if length < 1e-3:
                    continue
                mid = Point((x0 + x1) / 2, (y0 + y1) / 2)
                if mid.distance(boundary) > 1e-3 or Point(x0, y0).distance(boundary) > 1e-3 or Point(x1, y1).distance(boundary) > 1e-3:
                    continue
                h0, h1 = z(plane, x0, y0), z(plane, x1, y1)
                if h0 - eaves < 0.02 and h1 - eaves < 0.02:
                    continue
                nx, ny = (y1 - y0) / length, -(x1 - x0) / length
                if poly.contains(Point(mid.x + nx * 0.01, mid.y + ny * 0.01)):
                    nx, ny = -nx, -ny
                if nx * (y1 - y0) - ny * (x1 - x0) < 0:
                    x0, y0, x1, y1, h0, h1 = x1, y1, x0, y0, h1, h0
                vertices = [(x0, y0, eaves), (x1, y1, eaves), (x1, y1, h1), (x0, y0, h0)]
                faces = [f for f, h in (((0, 1, 2), h1), ((0, 2, 3), h0)) if h - eaves >= 0.02]
                roof.add(vertices, faces, shade(wall_rgb, wall_shade(nx, ny)))
    return roof


def build_flat(poly, height, roof_rgb):
    roof = Roof()
    index, vertices, triangles = {}, [], []
    for tri in polygons_of(shapely.constrained_delaunay_triangles(poly)):
        pts = list(tri.exterior.coords)[:3]
        area2 = (pts[1][0] - pts[0][0]) * (pts[2][1] - pts[0][1]) - (pts[2][0] - pts[0][0]) * (pts[1][1] - pts[0][1])
        if abs(area2) < 1e-9:
            continue
        if area2 < 0:
            pts = [pts[0], pts[2], pts[1]]
        ids = []
        for x, y in pts:
            key = (round(x, 4), round(y, 4))
            if key not in index:
                index[key] = len(vertices)
                vertices.append((x, y, height))
            ids.append(index[key])
        if len(set(ids)) == 3:
            triangles.append(tuple(ids))
    if not triangles:
        return None
    roof.add(vertices, triangles, shade(roof_rgb, roof_shade((0.0, 0.0, 0.0), 1.0)))
    return roof


def plan(props, defaults, poly, kind):
    if poly.area < MIN_AREA:
        return None, "too_small"
    if kind == "flat":
        _, top, _ = wall_profile(props, defaults)
        return (None, top + FLAT_OFFSET, 0.0), None
    if kind == "pyramidal":
        if poly.area / poly.convex_hull.area < MIN_CONVEXITY:
            return None, "irregular"
        frame = None
        hull = poly.minimum_rotated_rectangle
        rect = list(hull.exterior.coords)
        half_width = min(math.dist(rect[0], rect[1]), math.dist(rect[1], rect[2])) / 2
        half_length = max(math.dist(rect[0], rect[1]), math.dist(rect[1], rect[2])) / 2
    else:
        frame = Frame(poly, props, kind)
        if frame.half_width < 0.5 or frame.half_length < 0.5:
            return None, "too_small"
        if poly.area / (4 * frame.half_width * frame.half_length) < MIN_RECTANGULARITY:
            return None, "irregular"
        half_width, half_length = frame.half_width, frame.half_length
    base, top, explicit = wall_profile(props, defaults)
    roof_height, roof_explicit = default_roof_height(kind, half_width, half_length, props)
    eaves, roof_height = resolve_heights(base, top, explicit, roof_height, roof_explicit)
    if roof_height < 0.3:
        return None, "too_low"
    return (frame, eaves, roof_height), None


def eligible(props, is_part):
    if not is_part:
        if props.get("covered_by_parts") == "yes":
            return False
        if props.get("lod", "detail") != "detail":
            return False
        has_info = any(k in props for k in ("height", "min_height", "building:levels", "building:min_level"))
        if props.get("building") == "roof" and not has_info:
            return False
    return True


class Mesh:
    def __init__(self, origin):
        self.origin = origin
        self.positions = []
        self.colors = []
        self.indices = []

    def count(self):
        return len(self.positions)

    def add(self, vertices, triangles, color):
        start = len(self.positions)
        ox, oy = self.origin
        for x, y, h in vertices:
            self.positions.append((x - ox, h, -(y - oy)))
            self.colors.append(color)
        for a, b, c in triangles:
            self.indices.append((start + a, start + b, start + c))


class Chunks:
    def __init__(self, size):
        self.size = size
        self.meshes = {}

    def add(self, anchor, roof):
        key = (math.floor(anchor[0] / self.size), math.floor(anchor[1] / self.size))
        origin = ((key[0] + 0.5) * self.size, (key[1] + 0.5) * self.size)
        meshes = self.meshes.setdefault(key, [Mesh(origin)])
        needed = sum(len(v) for v, _, _ in roof.groups)
        if meshes[-1].count() + needed > MAX_VERTICES:
            meshes.append(Mesh(origin))
        for vertices, triangles, color in roof.groups:
            meshes[-1].add(vertices, triangles, color)

    def all(self):
        return [m for key in sorted(self.meshes) for m in self.meshes[key] if m.indices]


def write_glb(path, meshes, projector, lon0, lat0):
    binary = bytearray()
    views, accessors, gl_meshes, nodes = [], [], [], []

    def view(data, target):
        while len(binary) % 4:
            binary.append(0)
        views.append({"buffer": 0, "byteOffset": len(binary), "byteLength": len(data), "target": target})
        binary.extend(data)
        return len(views) - 1

    for mesh in meshes:
        pos = struct.pack(f"<{3 * mesh.count()}f", *[c for p in mesh.positions for c in p])
        col = bytes(c for rgb in mesh.colors for c in (*rgb, 255))
        idx = struct.pack(f"<{3 * len(mesh.indices)}H", *[i for t in mesh.indices for i in t])
        xs, ys, zs = zip(*mesh.positions)
        accessors.append({"bufferView": view(pos, 34962), "componentType": 5126, "count": mesh.count(),
                          "type": "VEC3", "min": [min(xs), min(ys), min(zs)], "max": [max(xs), max(ys), max(zs)]})
        accessors.append({"bufferView": view(col, 34962), "componentType": 5121, "normalized": True,
                          "count": mesh.count(), "type": "VEC4"})
        accessors.append({"bufferView": view(idx, 34963), "componentType": 5123,
                          "count": 3 * len(mesh.indices), "type": "SCALAR"})
        n = len(accessors)
        gl_meshes.append({"primitives": [{"attributes": {"POSITION": n - 3, "COLOR_0": n - 2},
                                          "indices": n - 1, "material": 0, "mode": 4}]})
        nodes.append({"mesh": len(gl_meshes) - 1, "translation": [mesh.origin[0], 0.0, -mesh.origin[1]]})

    while len(binary) % 4:
        binary.append(0)
    doc = {
        "asset": {"version": "2.0", "generator": "ZinnekeTiles generate_roofs.py",
                  "extras": {"origin": [lon0, lat0], "mercator": [projector.mx0, projector.my0],
                             "metersPerUnit": projector.scale, "axes": "x=east y=up z=south"}},
        "extensionsUsed": ["KHR_materials_unlit"],
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": gl_meshes,
        "materials": [{"pbrMetallicRoughness": {"baseColorFactor": [1, 1, 1, 1], "metallicFactor": 0,
                                                "roughnessFactor": 1},
                       "doubleSided": True, "extensions": {"KHR_materials_unlit": {}}}],
        "accessors": accessors,
        "bufferViews": views,
        "buffers": [{"byteLength": len(binary)}],
    }
    json_bytes = json.dumps(doc, separators=(",", ":")).encode()
    json_bytes += b" " * ((4 - len(json_bytes) % 4) % 4)
    total = 12 + 8 + len(json_bytes) + 8 + len(binary)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(json_bytes), 0x4E4F534A))
        f.write(json_bytes)
        f.write(struct.pack("<II", len(binary), 0x004E4942))
        f.write(binary)
    return total


def process(features, defaults, is_part, projector, chunks, palette, stats):
    for feat in features:
        props = feat.setdefault("properties", {})
        props.pop("roof_eaves", None)
        kind = roof_kind(props)
        if not kind or not eligible(props, is_part):
            continue
        try:
            geom = shape(feat["geometry"])
        except Exception:
            stats["invalid"] += 1
            continue
        polys = []
        for part in polygons_of(geom):
            local = projector.polygon(part)
            if not local.is_valid:
                local = local.buffer(0)
            polys += [orient(p, 1.0) for p in polygons_of(local)]
        if not polys:
            stats["invalid"] += 1
            continue
        roofs, eaves_values = [], []
        for poly in polys:
            params, reason = plan(props, defaults, poly, kind)
            if reason:
                stats[reason] += 1
                roofs = []
                break
            frame, eaves, roof_height = params
            if kind == "flat":
                roof = build_flat(poly, eaves, roof_color(props))
            else:
                roof = build_roof(poly, kind, frame, eaves, roof_height, roof_color(props), wall_color(props, palette))
            if roof is None:
                stats["empty"] += 1
                roofs = []
                break
            roofs.append((poly, roof))
            eaves_values.append(eaves)
        if not roofs:
            continue
        for poly, roof in roofs:
            p = poly.representative_point()
            chunks.add((p.x, p.y), roof)
        if kind != "flat":
            props["roof_eaves"] = round(min(eaves_values), 2)
        stats[f"ok:{kind}"] += 1


def load_palette(config_path):
    try:
        import yaml
        cfg = yaml.safe_load(Path(config_path).read_text()) or {}
        layer = (cfg.get("layers") or {}).get("buildings") or {}
    except Exception:
        layer = {}
    default = parse_color(layer.get("color") or DEFAULT_WALL, CSS_NAMED) or parse_color(DEFAULT_WALL, {})
    materials = {}
    for key, value in (layer.get("materials") or {}).items():
        rgb = parse_color(value, CSS_NAMED)
        if rgb:
            materials[material_key(key)] = rgb
    return Palette(default, materials)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--buildings", default="buildings_detail.json")
    p.add_argument("--parts", default="building_parts.json")
    p.add_argument("--config", default="map.config.yaml")
    p.add_argument("--out", default="www/roofs.glb")
    p.add_argument("--chunk", type=float, default=CHUNK_SIZE)
    args = p.parse_args(argv)

    projector = Projector(*ORIGIN)
    chunks = Chunks(args.chunk)
    stats = Counter()
    palette = load_palette(args.config)

    for path, defaults, is_part in ((args.buildings, BUILDING_DEFAULTS, False), (args.parts, PART_DEFAULTS, True)):
        if not Path(path).exists():
            print(f"⚠  {path} absent", file=sys.stderr)
            continue
        with open(path) as f:
            data = json.load(f)
        process(data.get("features", []), defaults, is_part, projector, chunks, palette, stats)
        with open(path, "w") as f:
            json.dump(data, f, ensure_ascii=False)

    meshes = chunks.all()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    size = write_glb(args.out, meshes, projector, *ORIGIN)
    ok = {k[3:]: v for k, v in stats.items() if k.startswith("ok:")}
    skipped = {k: v for k, v in stats.items() if not k.startswith("ok:")}
    triangles = sum(len(m.indices) for m in meshes)
    print(f"✓  {args.out} : {sum(ok.values())} toits, {len(meshes)} maillages, "
          f"{triangles} triangles, {size / 1024:.0f} Ko")
    print(f"   formes : {dict(sorted(ok.items(), key=lambda kv: -kv[1]))}")
    print(f"   ignorés : {dict(skipped)}")


if __name__ == "__main__":
    main()

import json
import struct
import sys
from pathlib import Path

import pytest
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import generate_roofs as gr


def rect(w, h):
    return orient(Polygon([(0, 0), (w, 0), (w, h), (0, h)]), 1.0)


def roof_vertices(roof):
    return [v for vertices, _, _ in roof.groups for v in vertices]


def walls(roof):
    return [g for g in roof.groups
            if len(g[0]) == 4 and g[0][0][:2] == g[0][3][:2] and g[0][1][:2] == g[0][2][:2]]


def build(kind, poly, props=None, defaults=gr.BUILDING_DEFAULTS):
    params, reason = gr.plan(props or {"roof:shape": kind}, defaults, poly, kind)
    assert reason is None
    frame, eaves, height = params
    roof = gr.build_roof(poly, kind, frame, eaves, height, (150, 80, 60), (240, 220, 200))
    assert roof is not None
    return roof, eaves, height


def test_wall_profile_matches_style_expressions():
    assert gr.wall_profile({}, gr.BUILDING_DEFAULTS) == (0.0, 7.5, False)
    assert gr.wall_profile({"height": "12"}, gr.BUILDING_DEFAULTS) == (0.0, 12.0, True)
    assert gr.wall_profile({"height": "12 m"}, gr.BUILDING_DEFAULTS) == (0.0, 6.0, True)
    assert gr.wall_profile({"building:levels": "4"}, gr.BUILDING_DEFAULTS) == (0.0, 12.0, False)
    assert gr.wall_profile({"min_height": "5", "height": "5.5"}, gr.BUILDING_DEFAULTS) == (5.0, 6.0, True)
    assert gr.wall_profile({}, gr.PART_DEFAULTS) == (0.0, 9.0, False)


def test_roof_included_in_explicit_height():
    eaves, height = gr.resolve_heights(0.0, 15.0, True, 5.0, True)
    assert (eaves, height) == (10.0, 5.0)


def test_roof_added_above_levels():
    eaves, height = gr.resolve_heights(0.0, 9.0, False, 4.0, False)
    assert (eaves, height) == (9.0, 4.0)


def test_default_roof_capped_by_half_wall_height():
    eaves, height = gr.resolve_heights(0.0, 8.0, True, 6.0, False)
    assert height == pytest.approx(4.0)
    assert eaves == pytest.approx(4.0)


def test_roof_height_sources():
    assert gr.default_roof_height("gabled", 5, 10, {"roof:height": "3,5"}) == (3.5, True)
    assert gr.default_roof_height("gabled", 5, 10, {"roof:levels": "1"}) == (3.0, True)
    height, explicit = gr.default_roof_height("gabled", 5, 10, {"roof:angle": "45"})
    assert height == pytest.approx(5.0) and explicit


def test_parsers():
    assert gr.parse_direction("NE") == 45.0
    assert gr.parse_direction("270") == 270.0
    assert gr.parse_direction(None) is None
    assert gr.parse_color("#abc", {}) == (170, 187, 204)
    assert gr.parse_color("darkgrey", gr.CSS_NAMED) == (169, 169, 169)
    assert gr.roof_color({"roof:colour": "darkgrey"}) == gr.parse_color(gr.ROOF_NAMED["darkgrey"], {})
    assert gr.roof_color({"roof:material": "slate"}) == gr.parse_color(gr.ROOF_MATERIALS["slate"], {})


def test_shape_aliases():
    assert gr.roof_kind({"roof:shape": "Domed"}) == "dome"
    assert gr.roof_kind({"roof:shape": "half-hipped"}) == "half_hipped"
    assert gr.roof_kind({"roof:shape": "many"}) is None


def test_flat_roofs_only_when_coloured():
    assert gr.roof_kind({"roof:shape": "flat"}) is None
    assert gr.roof_kind({}) is None
    assert gr.roof_kind({"roof:shape": "flat", "roof:colour": "grey"}) == "flat"
    assert gr.roof_kind({"roof:material": "gravel"}) == "flat"
    assert gr.roof_kind({"roof:colour": "nimportequoi"}) is None


def test_roof_colour_falls_back_to_material_name():
    assert gr.explicit_roof_color({"roof:colour": "zinc"}) == gr.parse_color(gr.ROOF_MATERIALS["zinc"], {})
    assert gr.explicit_roof_color({"roof:colour": "light_grey"}) == gr.parse_color(gr.ROOF_NAMED["lightgrey"], {})
    assert gr.explicit_roof_color({}) is None


def test_wall_colour_follows_style_priority():
    palette = gr.Palette((1, 2, 3), {"brick": (200, 100, 50)})
    assert gr.wall_color({"building:colour": "Bisque", "building:material": "brick"}, palette) == (255, 228, 196)
    assert gr.wall_color({"building:colour": "#C0c0c0"}, palette) == (192, 192, 192)
    assert gr.wall_color({"building:colour": "light grey", "building:material": "Brick"}, palette) == (200, 100, 50)
    assert gr.wall_color({"building:colour": "c0c0c0"}, palette) == (1, 2, 3)
    assert gr.wall_color({}, palette) == (1, 2, 3)


def test_css_table_is_complete():
    assert len(gr.CSS_NAMED) == 148
    for name in ("blanchedalmond", "lightgoldenrodyellow", "gainsboro", "firebrick", "darkgrey"):
        assert name in gr.CSS_NAMED


def test_palette_reads_config(tmp_path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text('layers:\n  buildings:\n    color: "#101010"\n    materials: { Brick: "#200000", glass: lightblue }\n')
    palette = gr.load_palette(cfg)
    assert palette.default == (16, 16, 16)
    assert palette.materials == {"brick": (32, 0, 0), "glass": (173, 216, 230)}
    assert gr.load_palette(tmp_path / "absent.yaml").default == gr.parse_color(gr.DEFAULT_WALL, {})


def test_project_config_materials_match_style():
    import yaml
    cfg = yaml.safe_load((ROOT / "map.config.yaml").read_text())
    materials = cfg["layers"]["buildings"].get("materials") or {}
    palette = gr.load_palette(ROOT / "map.config.yaml")
    assert set(palette.materials) == {k.lower() for k in materials}


def test_flat_roof_sits_on_top_without_cut():
    poly = rect(10, 10)
    params, reason = gr.plan({"roof:colour": "grey", "height": "12"}, gr.BUILDING_DEFAULTS, poly, "flat")
    assert reason is None
    _, z, _ = params
    assert z == pytest.approx(12.0 + gr.FLAT_OFFSET)
    roof = gr.build_flat(poly, z, (10, 20, 30))
    vertices = roof_vertices(roof)
    assert {round(v[2], 6) for v in vertices} == {round(z, 6)}
    assert sum(len(t) for _, t, _ in roof.groups) == 2


def test_frame_follows_long_side_and_orientation():
    frame = gr.Frame(rect(20, 8), {}, "gabled")
    assert frame.half_length == pytest.approx(10)
    assert frame.half_width == pytest.approx(4)
    across = gr.Frame(rect(20, 8), {"roof:orientation": "across"}, "gabled")
    assert across.half_length == pytest.approx(4)
    assert across.half_width == pytest.approx(10)


def test_gabled_roof_peak_and_gables():
    roof, eaves, height = build("gabled", rect(20, 8), {"roof:shape": "gabled", "height": "12", "roof:height": "4"})
    zs = [z for _, _, z in roof_vertices(roof)]
    assert eaves == pytest.approx(8.0)
    assert max(zs) == pytest.approx(12.0)
    assert min(zs) == pytest.approx(8.0)
    ridge = [(x, y) for x, y, z in roof_vertices(roof) if z == pytest.approx(12.0)]
    assert all(y == pytest.approx(4.0) for _, y in ridge)
    gables = [g for g in walls(roof) if g[1]]
    assert len(gables) >= 2
    assert all(max(v[2] for v in g[0]) == pytest.approx(12.0) for g in gables)


@pytest.mark.parametrize("kind", ["hipped", "side_hipped", "half_hipped", "gambrel", "mansard",
                                  "round", "saltbox", "skillion", "dome", "pyramidal"])
def test_every_shape_reaches_full_height(kind):
    roof, eaves, height = build(kind, rect(16, 10))
    zs = [z for _, _, z in roof_vertices(roof)]
    assert max(zs) == pytest.approx(eaves + height, abs=1e-6)
    assert min(zs) >= eaves - 1e-6


def test_hipped_has_no_gable_walls():
    roof, eaves, _ = build("hipped", rect(16, 10))
    assert not [g for g in walls(roof) if g[1]]


def test_irregular_footprint_is_skipped():
    l_shape = orient(Polygon([(0, 0), (20, 0), (20, 4), (4, 4), (4, 20), (0, 20)]), 1.0)
    params, reason = gr.plan({"roof:shape": "gabled"}, gr.BUILDING_DEFAULTS, l_shape, "gabled")
    assert params is None and reason == "irregular"


def test_eligibility():
    assert not gr.eligible({"covered_by_parts": "yes"}, False)
    assert not gr.eligible({"building": "roof"}, False)
    assert gr.eligible({"building": "roof", "height": "4"}, False)
    assert gr.eligible({"covered_by_parts": "yes"}, True)


def lonlat_rect(lon, lat, d=0.0002):
    return [[[lon, lat], [lon + 2 * d, lat], [lon + 2 * d, lat + d], [lon, lat + d], [lon, lat]]]


def write_fc(path, features):
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))


def test_main_writes_eaves_and_valid_glb(tmp_path):
    buildings = tmp_path / "buildings_detail.json"
    parts = tmp_path / "building_parts.json"
    write_fc(buildings, [
        {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": lonlat_rect(4.35, 50.85)},
         "properties": {"building": "yes", "lod": "detail", "roof:shape": "gabled", "height": "12", "roof:height": "4"}},
        {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": lonlat_rect(4.36, 50.85)},
         "properties": {"building": "yes", "lod": "detail", "roof:shape": "flat"}},
        {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": lonlat_rect(4.37, 50.85)},
         "properties": {"building": "yes", "lod": "detail", "roof:shape": "hipped", "covered_by_parts": "yes"}},
        {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": lonlat_rect(4.39, 50.85)},
         "properties": {"building": "yes", "lod": "detail", "roof:colour": "black"}},
    ])
    write_fc(parts, [
        {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": lonlat_rect(4.38, 50.85)},
         "properties": {"building:part": "yes", "roof:shape": "dome", "roof_eaves": 99}},
    ])
    out = tmp_path / "roofs.glb"
    gr.main(["--buildings", str(buildings), "--parts", str(parts), "--out", str(out),
             "--config", str(tmp_path / "missing.yaml")])

    props = [f["properties"] for f in json.loads(buildings.read_text())["features"]]
    assert props[0]["roof_eaves"] == 8.0
    assert "roof_eaves" not in props[1]
    assert "roof_eaves" not in props[2]
    assert "roof_eaves" not in props[3]
    part = json.loads(parts.read_text())["features"][0]["properties"]
    assert part["roof_eaves"] == 9.0

    data = out.read_bytes()
    magic, version, total = struct.unpack_from("<III", data, 0)
    assert (magic, version, total) == (0x46546C67, 2, len(data))
    json_len, json_type = struct.unpack_from("<II", data, 12)
    assert json_type == 0x4E4F534A
    doc = json.loads(data[20:20 + json_len])
    assert doc["asset"]["extras"]["origin"] == list(gr.ORIGIN)
    assert len(doc["nodes"]) == len(doc["meshes"]) >= 1
    vertices = sum(acc["count"] for acc in doc["accessors"] if acc["type"] == "VEC3")
    assert vertices > 4
    bin_len, bin_type = struct.unpack_from("<II", data, 20 + json_len)
    assert bin_type == 0x004E4942 and bin_len == doc["buffers"][0]["byteLength"]


def test_main_is_idempotent(tmp_path):
    buildings = tmp_path / "b.json"
    write_fc(buildings, [{"type": "Feature", "geometry": {"type": "Polygon", "coordinates": lonlat_rect(4.35, 50.85)},
                          "properties": {"building": "yes", "roof:shape": "gabled"}}])
    args = ["--buildings", str(buildings), "--parts", str(tmp_path / "none.json"),
            "--out", str(tmp_path / "r.glb"), "--config", str(tmp_path / "none.yaml")]
    gr.main(args)
    first = (tmp_path / "r.glb").read_bytes()
    gr.main(args)
    assert (tmp_path / "r.glb").read_bytes() == first

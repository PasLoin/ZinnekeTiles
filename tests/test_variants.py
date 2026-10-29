import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from build_map import (
    PALETTE_DEFAULTS, VariantError, apply_variant, build_manifest, build_pmtiles_params,
    build_style, build_variants, deep_merge, load_variant, variant_errors, variant_style_path,
)

CONFIG = yaml.safe_load((ROOT / "map.config.yaml").read_text())
VARIANT_FILES = sorted((ROOT / "styles").glob("*.y*ml"))
HEX = re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")


def variant(raw, vid="essai"):
    return {"id": vid, "label": vid.capitalize(), "path": f"{vid}.yaml", "raw": raw}


def layer_ids(style):
    return [l["id"] for l in style["layers"]]


def by_id(style):
    return {l["id"]: l for l in style["layers"]}


def is_gray(color):
    h = color[1:]
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return h[0:2] == h[2:4] == h[4:6]


def test_deep_merge_overrides_nested_and_null_deletes():
    base = {"a": {"b": 1, "c": {"d": 2}}, "e": [1, 2], "f": {"g": 1}}
    out = deep_merge(base, {"a": {"c": {"d": 3}}, "e": [9], "f": None})
    assert out == {"a": {"b": 1, "c": {"d": 3}}, "e": [9]}
    assert base["a"]["c"]["d"] == 2


def test_default_style_has_no_variant_metadata():
    style = build_style(CONFIG)
    assert "brussels:variant" not in style["metadata"]
    assert style["name"] == CONFIG["map"]["name"]


def test_empty_variant_keeps_every_layer():
    base = build_style(CONFIG)
    style = build_style(CONFIG, variant({}))
    assert layer_ids(style) == layer_ids(base)
    assert style["sources"] == base["sources"]
    assert style["metadata"]["brussels:variant"]["id"] == "essai"


def test_variant_keeps_base_config_hash():
    base = build_style(CONFIG)
    style = build_style(CONFIG, variant({"map": {"background": "#000000"}}))
    assert style["metadata"]["brussels:config_hash"] == base["metadata"]["brussels:config_hash"]


def test_variant_name_defaults_to_base_and_label():
    style = build_style(CONFIG, variant({}, "sombre"))
    assert style["name"] == f"{CONFIG['map']['name']} · Sombre"
    style = build_style(CONFIG, variant({"map": {"name": "Autre"}}))
    assert style["name"] == "Autre"


def test_variant_does_not_mutate_base_config():
    before = copy.deepcopy(CONFIG)
    build_style(CONFIG, variant({"layers": {"water": {"color": "#000000"}}, "exclude": ["poi"]}))
    assert CONFIG == before


def test_layer_color_override():
    style = build_style(CONFIG, variant({"layers": {"water": {"color": "#123456"}}}))
    assert by_id(style)["water-fill"]["paint"]["fill-color"] == "#123456"


def test_road_subtype_override():
    raw = {"layers": {"roads": {"subtypes": {"primary": {"outline_color": "#010101"}}}}}
    style = build_style(CONFIG, variant(raw))
    assert by_id(style)["roads-surface-casing-primary"]["paint"]["line-color"] == "#010101"
    assert by_id(style)["roads-surface-fill-primary"]["paint"]["line-color"] \
        == CONFIG["layers"]["roads"]["subtypes"]["primary"]["color"]


@pytest.mark.parametrize("group,key", [(g, k) for g, keys in PALETTE_DEFAULTS.items() for k in keys])
def test_every_palette_key_reaches_the_style(group, key):
    probe = "#123456"
    style = build_style(CONFIG, variant({"palette": {group: {key: probe}}}))
    lazy = style["metadata"].get("brussels:lazy") or {}
    assert probe in json.dumps(style["layers"]) + json.dumps(lazy.get("layers", []))


def test_palette_in_base_config_is_honored():
    cfg = copy.deepcopy(CONFIG)
    cfg["palette"] = {"roads": {"label": "#123456"}}
    assert by_id(build_style(cfg))["road-labels"]["paint"]["text-color"] == "#123456"


def test_exclude_removes_layers_sources_and_legend():
    style = build_style(CONFIG, variant({"exclude": ["poi", "trees"]}))
    assert not any(l.get("source") in ("poi", "trees") for l in style["layers"])
    assert "poi" not in style["sources"] and "trees" not in style["sources"]
    assert {g["id"] for g in style["metadata"]["brussels:legend"]}.isdisjoint({"poi", "trees"})
    assert "brussels:poi_density" not in style["metadata"]


def test_exclude_leisure_drops_its_icon_and_pitch_markings():
    ids = layer_ids(build_style(CONFIG, variant({"exclude": ["leisure"]})))
    assert "leisure-icon" not in ids and "pitch-markings" not in ids
    assert "poi-icon" in ids


def test_exclude_prunes_unused_patterns():
    style = build_style(CONFIG, variant({"exclude": ["landuse"]}))
    assert not any(p.startswith(("grave_yard", "military")) for p in style["metadata"]["brussels:patterns"])
    assert "green-hatch" in style["metadata"]["brussels:patterns"]


def test_exclude_lazy_groups():
    lazy = build_style(CONFIG, variant({"exclude": ["indoor"]}))["metadata"]["brussels:lazy"]
    assert list(lazy["sources"]) == ["building_parts"]
    assert all(l["source"] == "building_parts" for l in lazy["layers"])
    style = build_style(CONFIG, variant({"exclude": ["buildings"]}))
    assert "brussels:lazy" not in style["metadata"]


def test_lazy_before_points_to_an_existing_layer():
    style = build_style(CONFIG, variant({"exclude": ["addresses", "poi", "leisure"]}))
    assert style["metadata"]["brussels:lazy"]["before"] in layer_ids(style)


def test_patterns_replace_is_merged():
    raw = {"patterns": {"green-hatch": {"replace": {"#bd4a72": "#111111"}}}}
    pat = build_style(CONFIG, variant(raw))["metadata"]["brussels:patterns"]["green-hatch"]
    assert pat["replace"] == {"#bd4a72": "#111111"}
    assert pat["file"] == CONFIG["patterns"]["green-hatch"]["file"]


def test_null_clears_materials_and_osm_colour_off():
    raw = {"layers": {"buildings": {"materials": None, "osm_colour": False, "color": "#cccccc"}}}
    style = build_style(CONFIG, variant(raw))
    assert by_id(style)["buildings-3d"]["paint"]["fill-extrusion-color"][3] == "#cccccc"
    parts = style["metadata"]["brussels:lazy"]["layers"][0]
    assert parts["paint"]["fill-extrusion-color"] == "#cccccc"


def test_raising_appear_at_is_allowed():
    raw = {"layers": {"roads": {"subtypes": {"service": {"appear_at": 16}}}}}
    assert by_id(build_style(CONFIG, variant(raw)))["roads-surface-fill-service"]["minzoom"] == 16


@pytest.mark.parametrize("raw,needle", [
    ({"layers": {"roads": {"tiles": {"max_zoom": 16}}}}, "layers.roads.tiles"),
    ({"layers": {"poi": {"density": {"grid": 64}}}}, "layers.poi.density"),
    ({"layers": {"landuse": {"subtypes": {"retail": {"tag": "shop"}}}}}, "subtypes.retail.tag"),
    ({"layers": {"roads": {"subtypes": {"service": {"appear_at": 12}}}}}, "service.appear_at"),
    ({"layers": {"buildings": {"appear_at": 10}}}, "layers.buildings.appear_at"),
    ({"layers": {"landuse": {"subtypes": {"vineyard": {"color": "#000"}}}}}, "vineyard"),
    ({"layers": {"unicorns": {"color": "#000"}}}, "layers.unicorns"),
    ({"layers": {"water": None}}, "exclude"),
    ({"exclude": ["nope"]}, "nope"),
    ({"palette": {"roads": {"nope": "#000"}}}, "palette.roads.nope"),
    ({"palette": {"sky": {"a": "#000"}}}, "palette.sky"),
    ({"patterns": {"new-hatch": {"size": 4}}}, "patterns.new-hatch"),
    ({"exclud": ["poi"]}, "exclud"),
])
def test_invalid_variants_are_rejected(raw, needle):
    with pytest.raises(VariantError) as e:
        build_style(CONFIG, variant(raw))
    assert needle in str(e.value)


@pytest.mark.parametrize("vid", ["Noir", "noir_blanc", "default", "-nb", "nb-", ""])
def test_invalid_ids_are_rejected(vid):
    assert any("identifiant" in e for e in variant_errors(CONFIG, {}, vid))


@pytest.mark.parametrize("vid", ["nb", "toner", "noir-et-blanc", "v2"])
def test_valid_ids(vid):
    assert variant_errors(CONFIG, {}, vid) == []


def test_variant_never_changes_tile_inputs():
    raw = {"layers": {"roads": {"appear_at": 12, "subtypes": {"service": {"appear_at": 17}}}}}
    merged = apply_variant(CONFIG, variant(raw))
    assert build_pmtiles_params(merged) == build_pmtiles_params(CONFIG)


def test_variant_style_path_and_manifest():
    assert variant_style_path("www/style.json", "nb") == Path("www/style.nb.json")
    manifest = build_manifest("www/style.json", [variant({}, "nb")])
    assert manifest == {"default": "default", "styles": [
        {"id": "default", "label": "Standard", "url": "style.json"},
        {"id": "nb", "label": "Nb", "url": "style.nb.json"},
    ]}


def test_load_variant_uses_file_stem_and_label(tmp_path):
    f = tmp_path / "sombre.yaml"
    f.write_text("variant:\n  label: Sombre\nmap:\n  background: '#000000'\n")
    v = load_variant(f)
    assert (v["id"], v["label"]) == ("sombre", "Sombre")


def test_cli_builds_variants_and_manifest(tmp_path):
    vdir = tmp_path / "styles"
    vdir.mkdir()
    (vdir / "sombre.yaml").write_text("variant: { label: Sombre }\nexclude: [poi]\n")
    out = tmp_path / "www" / "style.json"
    subprocess.run([sys.executable, str(ROOT / "build_map.py"), "--config", str(ROOT / "map.config.yaml"),
                    "--style-out", str(out), "--only", "style", "--variants", str(vdir)],
                   check=True, capture_output=True)
    manifest = json.loads((out.parent / "styles.json").read_text())
    assert [s["id"] for s in manifest["styles"]] == ["default", "sombre"]
    style = json.loads((out.parent / "style.sombre.json").read_text())
    assert "poi" not in style["sources"]


def test_cli_fails_on_invalid_variant(tmp_path):
    vdir = tmp_path / "styles"
    vdir.mkdir()
    (vdir / "casse.yaml").write_text("layers: { roads: { tiles: { max_zoom: 12 } } }\n")
    r = subprocess.run([sys.executable, str(ROOT / "build_map.py"), "--config", str(ROOT / "map.config.yaml"),
                        "--style-out", str(tmp_path / "style.json"), "--only", "style",
                        "--variants", str(vdir)], capture_output=True, text=True)
    assert r.returncode == 1
    assert "layers.roads.tiles" in r.stderr


def test_cli_rejects_duplicate_ids(tmp_path):
    vdir = tmp_path / "styles"
    vdir.mkdir()
    (vdir / "nb.yaml").write_text("{}\n")
    (vdir / "nb.yml").write_text("{}\n")
    r = subprocess.run([sys.executable, str(ROOT / "build_map.py"), "--config", str(ROOT / "map.config.yaml"),
                        "--style-out", str(tmp_path / "style.json"), "--only", "style",
                        "--variants", str(vdir)], capture_output=True, text=True)
    assert r.returncode == 1 and "double" in r.stderr


@pytest.mark.parametrize("path", VARIANT_FILES, ids=lambda p: p.name)
def test_repository_variants_build(path):
    v = load_variant(path)
    style = build_style(CONFIG, v)
    assert style["metadata"]["brussels:variant"]["id"] == path.stem
    used = {l["source"] for l in style["layers"] if l.get("source")}
    assert used == set(style["sources"])


def test_nb_variant_is_grayscale():
    path = ROOT / "styles" / "nb.yaml"
    if not path.exists():
        pytest.skip("styles/nb.yaml absent")
    style = build_style(CONFIG, load_variant(path))
    lazy = style["metadata"].get("brussels:lazy") or {}
    text = json.dumps(style["layers"]) + json.dumps(lazy.get("layers", [])) \
        + json.dumps(style["metadata"]["brussels:patterns"])
    colors = set(HEX.findall(text)) - {"#bd4a72", "#88b78e"}
    assert sorted(c for c in colors if not is_gray(c)) == []


def test_removed_variants_are_cleaned_up(tmp_path):
    vdir = tmp_path / "styles"
    vdir.mkdir()
    (vdir / "garde.yaml").write_text("{}\n")
    (vdir / "vieux.yaml").write_text("{}\n")
    out = tmp_path / "www" / "style.json"
    out.parent.mkdir()
    build_variants(CONFIG, vdir, out)
    assert (out.parent / "style.vieux.json").exists()
    (vdir / "vieux.yaml").unlink()
    (out.parent / "style.manuel.json").write_text('{"metadata": {}}')
    build_variants(CONFIG, vdir, out)
    assert not (out.parent / "style.vieux.json").exists()
    assert (out.parent / "style.garde.json").exists()
    assert (out.parent / "style.manuel.json").exists()
    manifest = json.loads((out.parent / "styles.json").read_text())
    assert [s["id"] for s in manifest["styles"]] == ["default", "garde"]

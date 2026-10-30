import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build_map as bm

BASE = yaml.safe_load((ROOT / "map.config.yaml").read_text())

CASES = {
    "couleur de couche": (["layers", "water", "color"], "#123456"),
    "visible false": (["layers", "trees", "visible"], False),
    "opacité de couche": (["layers", "landuse", "opacity"], 0.5),
    "libellé de couche": (["layers", "green", "label"], "Verdure"),
    "libellé de sous-type": (["layers", "landuse", "subtypes", "retail", "label"], "Magasins"),
    "appear_at de sous-type": (["layers", "roads", "subtypes", "service", "appear_at"], 16),
    "tunnel_color": (["layers", "roads", "subtypes", "primary", "tunnel_color"], "#123456"),
    "color_private": (["layers", "green", "subtypes", "park", "color_private"], "#123456"),
    "by_color": (["layers", "trees", "subtypes", "tree", "by_color", "broadleaved"], "#123456"),
    "materials": (["layers", "buildings", "materials", "brick"], "#123456"),
    "extrusion_3d false": (["layers", "buildings", "extrusion_3d"], False),
    "border_color": (["layers", "buildings", "border_color"], "#123456"),
    "labels_at": (["layers", "poi", "labels_at"], 18),
    "swatch": (["layers", "addresses", "swatch"], "line"),
    "swatch_colors": (["layers", "public_transport", "swatch_colors"], ["#123456", "#654321"]),
    "sports.default": (["layers", "leisure", "sports", "default", "color"], "#123456"),
    "sports.markings_at": (["layers", "leisure", "sports", "markings_at"], 18),
    "tiles": (["layers", "roads", "tiles", "max_zoom"], 17),
    "density": (["layers", "poi", "density", "grid"], 96),
    "patterns.replace": (["patterns", "green-hatch", "replace"], {"#bd4a72": "#123456"}),
    "map.background": (["map", "background"], "#123456"),
    "map.center": (["map", "center"], [4.4, 50.85]),
    "indoor couleur": (["layers", "indoor", "subtypes", "room", "color"], "#123456"),
    "indoor level_height": (["layers", "indoor", "level_height"], 3.5),
    "indoor slab": (["layers", "indoor", "slab"], 0.5),
    "indoor volume_ratio": (["layers", "indoor", "volume_ratio"], 0.7),
    "indoor opacités": (["layers", "indoor", "floor_opacity"], 0.6),
    "indoor appear_at": (["layers", "indoor", "appear_at"], 16),
}


def signature(style):
    meta = style["metadata"]
    keys = ("brussels:lazy", "brussels:patterns", "brussels:legend", "brussels:tiles",
            "brussels:poi_density", "brussels:map")
    return json.dumps([style["layers"]] + [meta.get(k) for k in keys], sort_keys=True)


def retro(style):
    with tempfile.TemporaryDirectory() as tmp:
        src, out = Path(tmp) / "style.json", Path(tmp) / "config.yaml"
        src.write_text(json.dumps(style))
        subprocess.run([sys.executable, str(ROOT / "retro_style.py"), "--style", str(src), "--out", str(out)],
                       cwd=ROOT, check=True, capture_output=True)
        return yaml.safe_load(out.read_text())


def with_value(path, value):
    cfg = copy.deepcopy(BASE)
    node = cfg
    for key in path[:-1]:
        node = node.setdefault(key, {})
    node[path[-1]] = value
    return cfg


@pytest.mark.parametrize("name", list(CASES))
def test_retro_recovers_each_capability(name):
    path, value = CASES[name]
    style = bm.build_style(with_value(path, value))
    assert signature(style) != signature(bm.build_style(BASE)), "le cas de test n'a pas d'effet"
    assert signature(bm.build_style(retro(style))) == signature(style)


def test_indoor_section_is_style_only():
    cfg = with_value(["layers", "indoor"], {"level_height": 3.5, "subtypes": {"room": {"color": "#123456"}}})
    assert bm.build_granulometry(cfg) == bm.build_granulometry(BASE)
    assert bm.build_pmtiles_params(cfg) == bm.build_pmtiles_params(BASE)


def test_default_indoor_is_not_written():
    out = retro(bm.build_style(BASE))
    assert "indoor" not in out["layers"]

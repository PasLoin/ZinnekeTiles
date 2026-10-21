import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import generate_poi_icons as gpi


def write(tmp_path, props_list):
    path = tmp_path / "street_furniture.json"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [0, 0]}, "properties": p}
        for p in props_list
    ]}))
    return path


@pytest.mark.parametrize("props, expected", [
    ({"amenity": "toilets", "toilets:position": "urinal"}, "toilets-urinal"),
    ({"amenity": "toilets", "toilets:position": "urinal", "male": "yes", "female": "no"}, "toilets-urinal"),
    ({"amenity": "toilets", "female": "yes", "male": "no"}, "toilets-female"),
    ({"amenity": "toilets", "male": "yes", "female": "no"}, "toilets-male"),
    ({"amenity": "toilets", "male": "yes", "female": "yes"}, "toilets-unisex"),
])
def test_composite_case_selected(tmp_path, props, expected):
    counts = gpi.extract_composite_cases(write(tmp_path, [props]))
    assert counts == {expected: 1}


@pytest.mark.parametrize("props", [
    {"amenity": "toilets"},
    {"amenity": "toilets", "male": "yes"},
    {"amenity": "toilets", "toilets:position": "seated;urinal"},
    {"amenity": "toilets", "unisex": "yes"},
    {"amenity": "cafe", "male": "yes", "female": "yes"},
])
def test_composite_case_not_selected(tmp_path, props):
    assert gpi.extract_composite_cases(write(tmp_path, [props])) == {}


def test_composite_icons_exist_locally():
    for case in gpi.COMPOSITE_CASES:
        assert gpi.check_local(case["icon_key"]) == case["icon_key"]

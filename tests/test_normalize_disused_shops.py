import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import normalize_disused_shops as nds
from filter_geojson import matches_filters, parse_filter


@pytest.mark.parametrize("value", ["yes", "clothes", "convenience", "hairdresser"])
def test_disused_shop_becomes_vacant(value):
    props = {"disused:shop": value, "name": "Ancien magasin"}
    assert nds.normalize_properties(props) is True
    assert props["shop"] == "vacant"
    assert props["disused:shop"] == value


@pytest.mark.parametrize("active", [
    {"shop": "bakery"},
    {"shop": "vacant"},
    {"amenity": "restaurant"},
    {"craft": "tailor"},
    {"office": "company"},
    {"leisure": "hackerspace"},
])
def test_active_poi_wins_over_disused_shop(active):
    props = {"disused:shop": "clothes", **active}
    before = dict(props)
    assert nds.normalize_properties(props) is False
    assert props == before


def test_without_disused_shop_nothing_changes():
    props = {"amenity": "casino", "name": "Casino"}
    assert nds.normalize_properties(props) is False
    assert "shop" not in props


def test_normalize_file_roundtrip(tmp_path):
    path = tmp_path / "poi.json"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": None, "properties": {"disused:shop": "yes"}},
        {"type": "Feature", "geometry": None, "properties": {"disused:shop": "books", "shop": "books"}},
        {"type": "Feature", "geometry": None, "properties": {"shop": "vacant"}},
        {"type": "Feature", "geometry": None, "properties": None},
    ]}))
    assert nds.normalize_file(path) == 1
    shops = [(f["properties"] or {}).get("shop") for f in json.loads(path.read_text())["features"]]
    assert shops == ["vacant", "books", "vacant", None]


def test_cli(tmp_path, capsys):
    path = tmp_path / "poi.json"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": None, "properties": {"disused:shop": "clothes"}},
    ]}))
    assert nds.main([str(path)]) == 0
    assert "1 disused:shop=*" in capsys.readouterr().out


def test_poi_filters_keep_disused_shops_casino_hackerspace():
    script = (ROOT / "generate_json.bash").read_text()
    block = script.split("POI_FILTERS=(", 1)[1].split(")", 1)[0]
    filters = [parse_filter(line.strip()) for line in block.splitlines() if line.strip()]
    for props in ({"disused:shop": "clothes"}, {"amenity": "casino"},
                  {"leisure": "hackerspace"}, {"emergency": "ambulance_station"}):
        assert matches_filters({**props, "@type": "node"}, filters), props
    assert not matches_filters({"leisure": "pitch", "@type": "node"}, filters)


def test_pipeline_runs_normalizer_on_poi():
    script = (ROOT / "generate_json.bash").read_text()
    assert "python3 normalize_disused_shops.py poi.json" in script

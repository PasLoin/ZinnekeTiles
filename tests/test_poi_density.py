import copy
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from apply_granulometry import assign_ranks, grid_cell, tier_of
from build_map import build_granulometry, build_style, zoom

CONFIG = yaml.safe_load((ROOT / "map.config.yaml").read_text())


def layer(style, lid):
    return next(l for l in style["layers"] if l["id"] == lid)


def without_density(cfg):
    cfg = copy.deepcopy(cfg)
    cfg["layers"]["poi"].pop("density", None)
    return cfg


def point(fid, lon, lat, **props):
    return {"type": "Feature", "id": fid,
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": props, "tippecanoe": {"minzoom": 15, "maxzoom": 18}}


RANK_CFG = {"grid": 128, "zoom": 15, "rank_field": "poi_rank", "tier_field": "poi_tier",
            "tiers": [{"amenity": ["hospital"]}, {"amenity": ["pharmacy"]}]}


def test_poi_zooms_follow_config():
    style = build_style(CONFIG)
    assert layer(style, "poi-icon")["minzoom"] == 15
    assert layer(style, "poi-circle")["minzoom"] == 17
    text = layer(style, "poi-icon")["layout"]["text-field"]
    assert text[:4] == ["step", ["zoom"], "", 16]


def test_street_furniture_from_18():
    style = build_style(CONFIG)
    assert layer(style, "street-furniture-icon")["minzoom"] == 18
    assert layer(style, "street-furniture-fence")["minzoom"] == 18


def test_collision_until_overlap_at():
    icon = layer(build_style(CONFIG), "poi-icon")
    assert icon["layout"]["icon-allow-overlap"] == ["step", ["zoom"], False, 18, True]
    assert icon["layout"]["symbol-sort-key"][0] == "+"


def test_rank_filter_per_zoom():
    icon = layer(build_style(CONFIG), "poi-icon")
    assert icon["filter"] == ["any", [">=", ["zoom"], 17],
                              ["<=", ["coalesce", ["get", "poi_rank"], 0],
                               ["step", ["zoom"], 1, 16, 3]]]


def test_without_density_keeps_previous_behaviour():
    style = build_style(without_density(CONFIG))
    icon = layer(style, "poi-icon")
    assert icon["layout"]["icon-allow-overlap"] is True
    assert "filter" not in icon
    assert "symbol-sort-key" not in icon["layout"]
    assert "brussels:poi_density" not in style["metadata"]
    assert "rank" not in build_granulometry(without_density(CONFIG))["layers"]["poi"]


def test_density_published_in_metadata_and_granulometry():
    style = build_style(CONFIG)
    meta = style["metadata"]["brussels:poi_density"]
    assert meta["show"] == {"15": 1, "16": 3}
    rank = build_granulometry(CONFIG)["layers"]["poi"]["rank"]
    assert rank["zoom"] == 15 and rank["grid"] == 128
    assert rank["tiers"] == meta["tiers"]


def test_zoom_collapses_duplicate_stops():
    assert zoom([(18, .5), (18, 1.5)]) == 1.5
    assert zoom([(15, 2), (18, 4)]) == ["interpolate", ["linear"], ["zoom"], 15, 2, 18, 4]


def test_tier_of():
    tiers = RANK_CFG["tiers"]
    assert tier_of({"amenity": "hospital"}, tiers) == 1
    assert tier_of({"amenity": "pharmacy"}, tiers) == 2
    assert tier_of({"shop": "vacant"}, tiers) == 3


def test_rank_orders_by_tier_inside_a_cell():
    feats = [point("a", 4.35, 50.85, amenity="pharmacy", name="P"),
             point("b", 4.35001, 50.85001, amenity="hospital", name="H"),
             point("c", 4.35002, 50.85002, shop="vacant", name="V")]
    assert grid_cell(4.35, 50.85, 15, 128) == grid_cell(4.35002, 50.85002, 15, 128)
    assign_ranks(feats, RANK_CFG)
    ranks = {f["id"]: f["properties"]["poi_rank"] for f in feats}
    assert ranks == {"b": 1, "a": 2, "c": 3}
    assert feats[1]["properties"]["poi_tier"] == 1


def test_unnamed_and_late_features_rank_last():
    feats = [point("a", 4.35, 50.85, amenity="hospital"),
             point("b", 4.35001, 50.85001, amenity="pharmacy", name="P"),
             point("c", 4.35002, 50.85002, amenity="hospital", name="H")]
    feats[2]["tippecanoe"]["minzoom"] = 16
    assign_ranks(feats, RANK_CFG)
    ranks = {f["id"]: f["properties"]["poi_rank"] for f in feats}
    assert ranks == {"b": 1, "a": 2, "c": 3}


def test_each_cell_has_its_own_rank_one():
    feats = [point("a", 4.35, 50.85, amenity="pharmacy", name="P"),
             point("b", 4.40, 50.80, shop="vacant", name="V")]
    assert assign_ranks(feats, RANK_CFG) == 2
    assert [f["properties"]["poi_rank"] for f in feats] == [1, 1]


def test_split_segments_share_rank():
    a1 = point("a", 4.35, 50.85, amenity="pharmacy", name="P")
    a2 = copy.deepcopy(a1)
    a2["tippecanoe"] = {"minzoom": 17, "maxzoom": 18}
    b = point("b", 4.35001, 50.85001, amenity="pharmacy", name="Q")
    feats = [a1, a2, b]
    assign_ranks(feats, RANK_CFG)
    assert a1["properties"]["poi_rank"] == a2["properties"]["poi_rank"] == 1
    assert b["properties"]["poi_rank"] == 2

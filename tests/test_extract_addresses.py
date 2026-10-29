import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from extract_addresses import extract


def node(i, x, y, **tags):
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [x, y]},
            "properties": {"@type": "node", "@id": i, **tags}}


def area(i, ring, kind="way", **tags):
    return {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring]},
            "properties": {"@type": kind, "@id": i, **tags}}


SQUARE = [[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]
L_SHAPE = [[0, 0], [0, 3], [1, 3], [1, 1], [3, 1], [3, 0], [0, 0]]


def numbers(out):
    return sorted(f["properties"]["addr:housenumber"] for f in out)


def test_nodes_and_buildings_become_points():
    out, stats = extract([
        node(1, 5, 5, **{"addr:housenumber": "3"}),
        area(2, SQUARE, building="yes", **{"addr:housenumber": "7", "addr:street": "Rue X"}),
    ])
    assert numbers(out) == ["3", "7"]
    assert all(f["geometry"]["type"] == "Point" for f in out)
    assert stats["nodes"] == 1 and stats["areas"] == 1


def test_features_without_housenumber_are_ignored():
    out, _ = extract([node(1, 0, 0, entrance="yes"), area(2, SQUARE, building="yes")])
    assert out == []


def test_node_inside_building_with_same_number_wins():
    out, stats = extract([
        node(1, 0.5, 0.5, **{"addr:housenumber": "12 A"}),
        area(2, SQUARE, building="yes", **{"addr:housenumber": "12a"}),
    ])
    assert numbers(out) == ["12 A"]
    assert stats["dup_in_area"] == 1


def test_different_numbers_are_kept():
    out, _ = extract([
        node(1, 0.5, 0.5, **{"addr:housenumber": "12"}),
        area(2, SQUARE, building="yes", **{"addr:housenumber": "14"}),
    ])
    assert numbers(out) == ["12", "14"]


def test_different_streets_are_kept():
    out, _ = extract([
        node(1, 0.5, 0.5, **{"addr:housenumber": "1", "addr:street": "Rue A"}),
        area(2, SQUARE, building="yes", **{"addr:housenumber": "1", "addr:street": "Rue B"}),
    ])
    assert len(out) == 2


def test_point_lies_inside_concave_building():
    from shapely.geometry import Point, Polygon
    out, _ = extract([area(1, L_SHAPE, building="yes", **{"addr:housenumber": "9"})])
    x, y = out[0]["geometry"]["coordinates"]
    assert Polygon(L_SHAPE).contains(Point(x, y))


def test_multiple_values_are_joined():
    out, _ = extract([node(1, 0, 0, **{"addr:housenumber": "17;19"})])
    assert numbers(out) == ["17, 19"]


def test_same_osm_object_exported_twice_keeps_polygon():
    line = {"type": "Feature", "geometry": {"type": "LineString", "coordinates": SQUARE},
            "properties": {"@type": "way", "@id": 5, "addr:housenumber": "2"}}
    poly = area(5, SQUARE, **{"addr:housenumber": "2"})
    out, stats = extract([line, poly])
    assert len(out) == 1 and stats["areas"] == 1


def test_only_minimal_properties_are_kept():
    out, _ = extract([node(1, 0, 0, name="X", note="Z",
                           **{"addr:housenumber": "4", "addr:street": "Rue Y"})])
    assert out[0]["properties"] == {"addr:housenumber": "4", "addr:street": "Rue Y"}
    shop, _ = extract([node(2, 0, 0, shop="bakery", name="X", **{"addr:housenumber": "4"})])
    assert shop[0]["properties"] == {"addr:housenumber": "4", "label_dir": "x"}


BUILDING = [[0, 0], [0, 0.0001], [0.0001, 0.0001], [0.0001, 0], [0, 0]]


def test_entrance_with_same_number_as_building_yields_to_building():
    out, stats = extract([
        node(1, 0.00005, 0, entrance="yes", **{"addr:housenumber": "31"}),
        area(2, BUILDING, building="yes", **{"addr:housenumber": "31"}),
    ])
    assert len(out) == 1
    assert "label_dir" not in out[0]["properties"]
    assert stats["icon_to_area"] == 1


def test_plain_node_on_outline_still_wins_over_building():
    out, stats = extract([
        node(1, 0.00005, 0, **{"addr:housenumber": "31"}),
        area(2, BUILDING, building="yes", **{"addr:housenumber": "31"}),
    ])
    assert len(out) == 1 and out[0]["geometry"]["coordinates"] == [0.00005, 0]
    assert stats["dup_in_area"] == 1


def test_entrance_label_points_into_building():
    from shapely.geometry import Polygon
    building = Polygon(BUILDING)
    cases = {(0.00005, 0): "n", (0.00005, 0.0001): "s", (0, 0.00005): "e", (0.0001, 0.00005): "w"}
    for i, ((x, y), expected) in enumerate(cases.items()):
        out, _ = extract([node(i, x, y, entrance="main", **{"addr:housenumber": "5"})], [building])
        assert out[0]["properties"]["label_dir"] == expected


def test_entrance_far_from_buildings_gets_fallback_dir():
    out, _ = extract([node(1, 5, 5, entrance="yes", **{"addr:housenumber": "5"})], [])
    assert out[0]["properties"]["label_dir"] == "x"


def test_plain_nodes_have_no_label_dir():
    from shapely.geometry import Polygon
    out, _ = extract([node(1, 0.00005, 0, **{"addr:housenumber": "5"})], [Polygon(BUILDING)])
    assert "label_dir" not in out[0]["properties"]


def test_entrance_no_is_not_an_icon():
    from shapely.geometry import Polygon
    out, _ = extract([node(1, 0.00005, 0, entrance="no", **{"addr:housenumber": "5"})],
                     [Polygon(BUILDING)])
    assert "label_dir" not in out[0]["properties"]

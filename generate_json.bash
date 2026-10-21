#!/usr/bin/env bash
set -euo pipefail

SRC="brussels_capital_region-latest.osm.pbf"

if [ ! -f "$SRC" ]; then
  echo "✗ Fichier $SRC introuvable" >&2; exit 1
fi

FILESIZE=$(stat -c%s "$SRC" 2>/dev/null || stat -f%z "$SRC")
if [ "$FILESIZE" -lt 1000000 ]; then
  echo "✗ $SRC trop petit (${FILESIZE} octets) — téléchargement probablement échoué" >&2; exit 1
fi

FILETYPE=$(file -b "$SRC")
if [[ "$FILETYPE" != *"OpenStreetMap"* ]]; then
  echo "✗ $SRC n'est pas un fichier PBF valide" >&2
  echo "  Détecté : $FILETYPE" >&2
  exit 1
fi

echo "✓ Source valide : $SRC ($(numfmt --to=iec "$FILESIZE"))"

echo "→ data-info"
osmium fileinfo -e -j "$SRC" > _tmp_fileinfo.json
python3 - "$SRC" _tmp_fileinfo.json www/data-info.json << 'DATA_INFO'
import hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
src, info_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
info = json.loads(Path(info_path).read_text())
header = (info.get("header") or {}).get("option") or {}
h = hashlib.sha256()
with open(src, "rb") as f:
    for chunk in iter(lambda: f.read(1 << 20), b""):
        h.update(chunk)
data = {
    "source": Path(src).name,
    "timestamp": ((info.get("data") or {}).get("timestamp") or {}).get("last") or None,
    "replication_timestamp": header.get("osmosis_replication_timestamp"),
    "replication_sequence": header.get("osmosis_replication_sequence_number"),
    "sha256": h.hexdigest()[:12],
    "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
}
Path(out_path).parent.mkdir(parents=True, exist_ok=True)
Path(out_path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
print(f"  {out_path} : {data['timestamp']} ({data['sha256']})")
DATA_INFO
rm -f _tmp_fileinfo.json

extract() {
  local name="$1"; shift
  echo "→ $name"
  osmium tags-filter "$SRC" "$@" -o "_tmp_${name}.osm.pbf" --overwrite
  osmium export "_tmp_${name}.osm.pbf" -o "${name}.json" --overwrite --attributes=id,type
  rm -f "_tmp_${name}.osm.pbf"
  python3 filter_geojson.py "${name}.json" --layer "$name" --filters "$@"
}

config_filters() {
  python3 - "$1" "$2" << 'CONFIG_FILTERS'
import sys
import yaml
layer, fallback = sys.argv[1], sys.argv[2].split()
with open("map.config.yaml") as f:
    cfg = yaml.safe_load(f) or {}
st = ((cfg.get("layers") or {}).get(layer) or {}).get("subtypes") or {}
if not st:
    print(" ".join(fallback))
    sys.exit(0)
by_tag = {}
for value, scfg in st.items():
    tag = (scfg or {}).get("tag") or "amenity"
    by_tag.setdefault(tag, []).append(value)
out = []
for tag in sorted(by_tag):
    values = sorted(by_tag[tag])
    if values == [tag]:
        out.append(f"n/{tag}=*")
    else:
        out.append(f"nwr/{tag}=" + ",".join(values))
print(" ".join(out))
CONFIG_FILTERS
}

extract roads \
  nwr/highway=motorway,motorway_link,trunk,trunk_link,primary,primary_link,secondary,secondary_link,tertiary,tertiary_link,residential,living_street,unclassified,service,track,busway nwr/man_made=bridge,tunnel

echo "→ buildings"
osmium tags-filter "$SRC" nwr/building=* -o "_tmp_buildings.osm.pbf" --overwrite
osmium export "_tmp_buildings.osm.pbf" -o "buildings.json" --overwrite \
  --attributes=id,type --geometry-types=polygon
rm -f "_tmp_buildings.osm.pbf"
echo "  $(wc -l < "buildings.json") lignes"
echo "  → copie buildings.json → buildings_detail.json (avant merge)"
cp buildings.json buildings_detail.json

python3 << 'TAG_DETAIL'
import json
with open('buildings_detail.json') as f:
    data = json.load(f)
for feat in data.get('features', []):
    feat.setdefault('properties', {})['lod'] = 'detail'
with open('buildings_detail.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False)
print(f"  {len(data.get('features', []))} features taguées lod=detail")
TAG_DETAIL

echo "→ building_parts"
osmium tags-filter "$SRC" wr/building:part -o "_tmp_building_parts.osm.pbf" --overwrite
osmium export "_tmp_building_parts.osm.pbf" -o "building_parts.json" --overwrite \
  --attributes=id,type --geometry-types=polygon
rm -f "_tmp_building_parts.osm.pbf"
python3 << 'PARTS_CLEAN'
import json
with open('building_parts.json') as f:
    data = json.load(f)
before = len(data.get('features', []))
kept = []
for feat in data.get('features', []):
    props = feat.get('properties') or {}
    if props.get('building:part') == 'no':
        continue
    props.pop('@id', None)
    props.pop('@type', None)
    kept.append(feat)
data['features'] = kept
with open('building_parts.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False)
print(f"  {before} → {len(kept)} building:part (toutes valeurs sauf no)")
PARTS_CLEAN

echo "→ relations type=building (cas complexes)"
osmium tags-filter "$SRC" r/type=building -o "_tmp_building_rel.osm.pbf" --overwrite
osmium cat "_tmp_building_rel.osm.pbf" -o "_tmp_building_rel.osm" --overwrite
REL_COUNT=$(grep -c "<relation" "_tmp_building_rel.osm" 2>/dev/null || true)
echo "  ${REL_COUNT} relations type=building trouvées"

python3 compute_building_coverage.py \
  --buildings buildings_detail.json \
  --parts     building_parts.json \
  --relations _tmp_building_rel.osm \
  --threshold 0.90 \
  || echo "⚠  compute_building_coverage.py en échec (non bloquant — buildings-3d affichera tout)"
rm -f _tmp_building_rel.osm.pbf _tmp_building_rel.osm

python3 << 'STRIP_BUILD_PROPS'
import json
with open('buildings_detail.json') as f:
    data = json.load(f)
removed = 0
for feat in data.get('features', []):
    props = feat.get('properties', {})
    for k in ('@id', '@type', 'covered_by_parts_source'):
        if k in props:
            del props[k]
            removed += 1
with open('buildings_detail.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False)
print(f"  {removed} propriétés de build retirées (@id/@type/covered_by_parts_source)")
STRIP_BUILD_PROPS

extract water \
  nwr/natural=water nwr/waterway=river,canal,stream,ditch nwr/landuse=basin nwr/natural=wetland

extract green \
  nwr/landuse=flowerbed nwr/natural=shrubbery nwr/natural=scrub \
  nwr/leisure=park,garden nwr/landuse=forest,meadow,grass nwr/natural=wood \
  nwr/natural=grassland,heath

extract trees \
  nwr/natural=tree nwr/natural=tree_row nwr/barrier=hedge  

extract landuse \
  nwr/landuse=residential,industrial,commercial,retail,railway,education,construction,brownfield,greenfield,landfill,military,cemetery,allotments,farmland,farmyard,garages,religious,recreation_ground,village_green,quarry,depot

echo "→ landuse coverage check (vs wiki + map.config.yaml)"
osmium tags-filter "$SRC" nwr/landuse=* -o "_tmp_landuse_all.osm.pbf" --overwrite
osmium export "_tmp_landuse_all.osm.pbf" -o "_tmp_landuse_all.json" --overwrite
python3 check_landuse_coverage.py \
  --all-json _tmp_landuse_all.json \
  --config   map.config.yaml \
  --report   landuse_report.md \
  || echo "⚠  landuse coverage check en échec (non bloquant)"
rm -f _tmp_landuse_all.osm.pbf _tmp_landuse_all.json

extract boundaries \
  nwr/boundary=administrative

SF_FILTERS=$(config_filters street_furniture \
  "nwr/amenity=bench,lounger,waste_basket,vending_machine,atm,charging_station,bicycle_rental,car_sharing,taxi,parcel_locker,toilets,drinking_water,fountain,public_bookcase,bicycle_repair_station,dog_toilet,post_box,recycling,clock,photo_booth,give_box nwr/barrier=bollard,gate,bus_trap,cycle_barrier,lift_gate,planter,fence nwr/highway=street_lamp n/entrance=* nwr/emergency=assembly_point,defibrillator,fire_extinguisher,fire_hose,fire_hydrant,life_ring,phone nwr/tourism=artwork")
echo "  filtres street_furniture (map.config.yaml) : ${SF_FILTERS}"
read -r -a SF_FILTER_ARGS <<< "$SF_FILTERS"
extract street_furniture "${SF_FILTER_ARGS[@]}"

echo "→ street_furniture coverage check (vs wiki + map.config.yaml)"
osmium tags-filter "$SRC" \
  nwr/amenity=bench,lounger,waste_basket,vending_machine,drinking_water,clock,bicycle_parking,shelter,give_box,atm,charging_station,bicycle_rental,car_sharing,taxi,parcel_locker,toilets,fountain,public_bookcase,bicycle_repair_station,dog_toilet,post_box,recycling,photo_booth,kick-scooter_parking,motorcycle_parking,waste_disposal \
  nwr/tourism=artwork \
  nwr/barrier=bollard,gate,bus_trap,cycle_barrier,lift_gate,planter,fence,kissing_gate,block,full-height_turnstile,swing_gate,stile \
  nwr/highway=street_lamp \
  n/entrance=* \
  nwr/emergency=assembly_point,defibrillator,fire_extinguisher,fire_hose,fire_hydrant,life_ring,phone,siren,water_tank,suction_point,fire_alarm_box,first_aid_kit,emergency_ward_entrance \
  -o "_tmp_street_furniture_all.osm.pbf" --overwrite
osmium export "_tmp_street_furniture_all.osm.pbf" -o "_tmp_street_furniture_all.json" --overwrite
python3 check_street_furniture_coverage.py \
  --all-json _tmp_street_furniture_all.json \
  --config   map.config.yaml \
  --report   street_furniture_report.md \
  || echo "⚠  street_furniture coverage check en échec (non bloquant)"
rm -f _tmp_street_furniture_all.osm.pbf _tmp_street_furniture_all.json

echo "→ poi"
POI_FILTERS=(
  nwr/shop=*
  nwr/disused:shop=*
  nwr/amenity=restaurant,cafe,bar,pub,fast_food,ice_cream,biergarten,food_court,bank,bureau_de_change,money_transfer,pharmacy,hospital,clinic,doctors,dentist,veterinary,social_facility,school,college,university,kindergarten,childcare,library,driving_school,music_school,language_school,dancing_school,research_institute,theatre,cinema,arts_centre,nightclub,events_venue,conference_centre,exhibition_centre,social_centre,community_centre,studio,music_venue,planetarium,casino,gambling,brothel,stripclub,love_hotel,swingerclub,hookah_lounge,internet_cafe,post_office,police,fire_station,townhall,courthouse,prison,crematorium,place_of_worship,marketplace,fuel,car_wash,car_rental,ferry_terminal
  nwr/emergency=ambulance_station
  nwr/healthcare=physiotherapist,psychotherapist,laboratory,alternative,blood_donation,optometrist,audiologist,podiatrist,speech_therapist,rehabilitation,midwife,nurse,counselling
  nwr/office=*
  nwr/tourism=hotel,hostel,guest_house,apartment,museum,gallery,attraction,information,viewpoint,zoo,theme_park
  nwr/leisure=playground,hackerspace,sports_centre,fitness_centre,dance,escape_game,stadium,sauna,amusement_arcade,bowling_alley,indoor_play,trampoline_park,tanning_salon,miniature_golf,horse_riding
  nwr/historic=castle,monument,memorial,manor,ruins,wayside_shrine,wayside_cross,archaeological_site,city_gate
  nwr/craft=*
)
osmium tags-filter "$SRC" "${POI_FILTERS[@]}" -o "_tmp_poi.osm.pbf" --overwrite
osmium export "_tmp_poi.osm.pbf" -o "poi.json" --overwrite --add-unique-id=type_id --attributes=id,type
rm -f "_tmp_poi.osm.pbf"
python3 filter_geojson.py poi.json --layer poi --filters "${POI_FILTERS[@]}"

echo "  → normalisation POI en points + dédoublonnage"
python3 << 'POI_POINTS'
import json

def ring_area_and_centroid(ring):
    if len(ring) < 3:
        return 0.0, None
    area2, cx, cy = 0.0, 0.0, 0.0
    x0, y0 = ring[0][0], ring[0][1]
    pts = ring if ring[0] == ring[-1] else ring + [ring[0]]
    for (x1, y1, *_), (x2, y2, *_) in zip(pts, pts[1:]):
        x1, y1, x2, y2 = x1 - x0, y1 - y0, x2 - x0, y2 - y0
        cross = x1 * y2 - x2 * y1
        area2 += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    if area2 == 0:
        return 0.0, None
    return area2 / 2.0, [x0 + cx / (3.0 * area2), y0 + cy / (3.0 * area2)]

def avg_point(coords):
    pts = []
    def collect(v):
        if isinstance(v, list) and len(v) >= 2 and isinstance(v[0], (int, float)):
            pts.append(v[:2]); return
        if isinstance(v, list):
            for i in v: collect(i)
    collect(coords)
    if not pts:
        return None
    return [sum(p[0] for p in pts) / len(pts),
            sum(p[1] for p in pts) / len(pts)]

def to_point(geom):
    gt, coords = geom.get('type'), geom.get('coordinates')
    if gt == 'Point':
        return coords
    if gt == 'Polygon' and coords:
        _, c = ring_area_and_centroid(coords[0])
        return c or avg_point(coords)
    if gt == 'MultiPolygon' and coords:
        best, best_a = None, -1.0
        for poly in coords:
            if not poly: continue
            a, c = ring_area_and_centroid(poly[0])
            if c and abs(a) > best_a:
                best, best_a = c, abs(a)
        return best or avg_point(coords)
    return None

with open('poi.json') as f:
    collection = json.load(f)

features = collection.get('features', [])
before = len(features)
seen_ids = set()
kept = []
stats = {'pt': 0, 'conv': 0, 'dup': 0, 'skip': 0}
for feat in features:
    geom = feat.get('geometry') or {}
    pt = to_point(geom)
    if pt is None:
        stats['skip'] += 1
        continue

    fid = feat.get('id')
    if fid is not None and fid in seen_ids:
        stats['dup'] += 1
        continue
    if fid is not None:
        seen_ids.add(fid)

    was_point = geom.get('type') == 'Point'
    feat['geometry'] = {'type': 'Point', 'coordinates': pt}

    kept.append(feat)
    stats['pt' if was_point else 'conv'] += 1

collection['features'] = kept

with open('poi.json', 'w') as out:
    json.dump(collection, out, ensure_ascii=False)

print(f"  {before} → {len(kept)} POI "
      f"({stats['pt']} points, {stats['conv']} surfaces→centroïde, "
      f"{stats['dup']} doublons, {stats['skip']} ignorés)")
POI_POINTS

echo "  → disused:shop=* → shop=vacant"
python3 normalize_disused_shops.py poi.json

echo "  → valeurs multiples cuisine/religion/vending/door"
python3 normalize_multi_values.py poi.json street_furniture.json


echo "  → niveaux POI / mobilier urbain (level, repeat_on, location)"
python3 assign_levels.py poi.json street_furniture.json

extract leisure \
  nwr/leisure=playground,pitch,fitness_station,dog_park,outdoor_seating

echo "  → calcul orientation des terrains de sport"
python3 compute_pitch_bearing.py

extract pedestrian \
  nwr/highway=pedestrian,footway,path,steps

extract cycleway \
  nwr/highway=cycleway

extract railway \
  nwr/railway=rail,tram,subway,miniature

echo "→ public_transport (relations STIB/MIVB)"
osmium tags-filter "$SRC" r/route=bus,tram,subway,trolleybus -o "_tmp_pt.osm.pbf" --overwrite
osmium cat "_tmp_pt.osm.pbf" -o "_tmp_pt.osm" --overwrite
python3 extract_stib_routes.py
rm -f _tmp_pt.osm.pbf _tmp_pt.osm
echo "  $(wc -l < "public_transport.json") lignes"

echo "→ indoor (intérieur + souterrain)"
osmium tags-filter "$SRC" \
  nwr/indoor=room,area,corridor,wall \
  nwr/highway=footway,steps,corridor,path,pedestrian,elevator \
  nwr/railway=platform \
  nwr/public_transport=platform \
  -o "_tmp_indoor.osm.pbf" --overwrite
osmium export "_tmp_indoor.osm.pbf" -o "_tmp_indoor.json" --overwrite --attributes=id,type
python3 extract_indoor.py --input _tmp_indoor.json --output indoor.json --levels-out www/indoor-levels.json
rm -f "_tmp_indoor.osm.pbf" "_tmp_indoor.json"

echo "✓ couches extraites (+ buildings_detail.json, building_parts.json, indoor.json pour la 3D)"

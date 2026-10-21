# Street furniture coverage report

Comparaison entre les tags `amenity=*` / `barrier=*` / `highway=street_lamp` / `emergency=*` présents dans l'extrait Bruxelles et ceux rendus par `map.config.yaml` (cf. issue #51 — "Streets furnitures, small object (micromapping)").

- ✓ rendus : 37
- ⚠ manquants (présents mais sans style) : 11
- · sans donnée dans le pbf Bxl : 4
- `entrance=*` (toutes valeurs confondues) : 12496 features — rendu (rendu uniforme par clé, pas par valeur)

## ⚠ Présents dans Bxl mais non rendus

Ces valeurs existent dans le pbf mais n'ont pas de sous-type dans `layers.street_furniture.subtypes` → ajouter un rendu dans `map.config.yaml` (et au besoin une icône, voir `missing-icons.txt` après `generate_poi_icons.py`).

| tag | valeur | features |
| :--- | :--- | ---: |
| `amenity` | `bicycle_parking` | 7666 |
| `amenity` | `shelter` | 3676 |
| `barrier` | `block` | 298 |
| `barrier` | `swing_gate` | 65 |
| `amenity` | `waste_disposal` | 54 |
| `amenity` | `motorcycle_parking` | 45 |
| `barrier` | `full-height_turnstile` | 27 |
| `barrier` | `stile` | 20 |
| `amenity` | `kick-scooter_parking` | 6 |
| `barrier` | `kissing_gate` | 5 |
| `emergency` | `water_tank` | 2 |

## ✓ Rendus

| tag | valeur | features |
| :--- | :--- | ---: |
| `highway` | `street_lamp` | 10240 |
| `amenity` | `bench` | 7839 |
| `barrier` | `bollard` | 7348 |
| `amenity` | `waste_basket` | 6876 |
| `barrier` | `fence` | 4617 |
| `barrier` | `gate` | 3507 |
| `amenity` | `vending_machine` | 1811 |
| `tourism` | `artwork` | 1213 |
| `amenity` | `recycling` | 946 |
| `barrier` | `lift_gate` | 844 |
| `amenity` | `charging_station` | 769 |
| `emergency` | `fire_hydrant` | 647 |
| `amenity` | `fountain` | 496 |
| `amenity` | `post_box` | 414 |
| `amenity` | `dog_toilet` | 384 |
| `amenity` | `bicycle_rental` | 367 |
| `emergency` | `defibrillator` | 272 |
| `amenity` | `car_sharing` | 217 |
| `amenity` | `toilets` | 211 |
| `amenity` | `taxi` | 193 |
| `amenity` | `drinking_water` | 182 |
| `barrier` | `cycle_barrier` | 132 |
| `amenity` | `bicycle_repair_station` | 131 |
| `amenity` | `atm` | 111 |
| `amenity` | `public_bookcase` | 108 |
| `barrier` | `planter` | 73 |
| `amenity` | `clock` | 51 |
| `amenity` | `lounger` | 48 |
| `emergency` | `life_ring` | 39 |
| `amenity` | `parcel_locker` | 36 |
| `amenity` | `photo_booth` | 24 |
| `emergency` | `assembly_point` | 22 |
| `barrier` | `bus_trap` | 15 |
| `emergency` | `fire_extinguisher` | 6 |
| `amenity` | `give_box` | 4 |
| `emergency` | `phone` | 4 |
| `emergency` | `fire_hose` | 2 |

## · Sans donnée dans le pbf Bxl

Configurés et/ou listés comme candidats (wiki OSM), mais absents de l'extrait actuel — aucun rendu généré pour eux (conforme : on ne rend pas ce qui n'existe pas dans les données).

| tag | valeur | configuré dans map.config.yaml ? |
| :--- | :--- | :---: |
| `emergency` | `fire_alarm_box` | non |
| `emergency` | `first_aid_kit` | non |
| `emergency` | `siren` | non |
| `emergency` | `suction_point` | non |

## Sous-types `vending=*` (raffinement d'icône)

`amenity=vending_machine` est déjà rendu ci-dessus ; ces valeurs ne créent pas de couche supplémentaire, seulement une icône plus précise si elle existe (même principe que `cuisine=*` / `religion=*` pour les POI — cf. `generate_poi_icons.py` et `missing-icons.txt`).

| vending | features |
| :--- | ---: |
| `parking_tickets` | 1448 |
| `public_transport_tickets` | 232 |
| `excrement_bags` | 63 |
| `newspapers` | 18 |
| `coffee` | 15 |
| `condoms` | 6 |
| `admission_tickets` | 3 |
| `drinks` | 2 |
| `sweets` | 1 |
| `candles` | 1 |
| `snacks` | 1 |
| `umbrella` | 1 |
| `sweets;drinks;condoms` | 1 |
| `potatoes;eggs` | 1 |
| `milk` | 1 |
| `chemist` | 1 |
| `souvenirs` | 1 |
| `sun_cream` | 1 |
| `food` | 1 |
| `drinks;food` | 1 |
| `meat` | 1 |
| `chemist;condoms` | 1 |
| `elongated_coin` | 1 |
| `condoms;menstrual_products` | 1 |


# ZinnekeTiles

Is it possible to run Brussels on a mini maximal vector tile on github page ?

*Anciennement « Brussels minimal vector tile ».*

Carte MapLibre de la Région de Bruxelles-Capitale, générée à partir d'un extrait OpenStreetMap et publiée sur GitHub Pages sous forme de fichiers PMTiles statiques, sans serveur de tuiles : [pasloin.github.io/ZinnekeTiles](https://pasloin.github.io/ZinnekeTiles/).

Chaque thème a son propre fichier PMTiles dans `www/`, et le style MapLibre est compilé depuis un seul fichier de configuration, `map.config.yaml`. La carte est régénérée chaque mois à partir des données OSM du jour.

## Ce que fait la carte

La carte affiche quinze couches : occupation du sol, espaces verts, loisirs et terrains de sport, eau, bâtiments, numéros de rue, arbres et haies, rail, lignes STIB, routes, chemins piétons, pistes cyclables, limites administratives, POI et mobilier urbain. La légende est générée depuis la configuration et permet d'afficher ou de masquer chaque couche et chaque sous-type.

Le bouton MODE 3D extrude les bâtiments selon leur hauteur. La couleur suit `building:colour`, puis `building:material`, puis la couleur de la couche. Les parties de bâtiments (`building:part`) ne sont téléchargées qu'au passage en 3D, et l'intérieur des bâtiments qu'au choix d'un mode dans le panneau Niveaux. Le bouton TOITS ajoute les toits modélisés à partir des tags `roof:*` (forme, hauteur, orientation, couleur), et le panneau Niveaux affiche l'intérieur cartographié : tout ce qui est au-dessus du sol, uniquement le souterrain, ou un niveau choisi.

Le bouton DATA affiche les attributs OSM de l'objet sous le curseur. À partir du zoom 16, le lien « éditer dans OpenStreetMap » ouvre l'éditeur au même endroit. Les terrains de sport sont colorés par sport et reçoivent leurs lignes de marquage à partir du zoom 17. Les icônes de POI viennent de fichiers locaux ou des jeux Temaki, Maki et OSM Liberty, et un système de grille limite leur nombre aux zooms moyens en gardant les plus importants. L'attribution indique la date des données OSM et celle de la dernière mise à jour.

L'interface est utilisable sur téléphone : les panneaux se réorganisent sous 600 px de large ou 500 px de haut.

## Prérequis système

Installez les outils suivants avant de régénérer les données :

| Outil | Usage dans ce dépôt | Vérification rapide |
| :--- | :--- | :--- |
| `osmium` / `osmium-tool` | Filtrer le PBF OSM et exporter les GeoJSON intermédiaires. | `osmium --version` |
| `tippecanoe` | Convertir les GeoJSON en archives PMTiles. | `tippecanoe --version` |
| `python3` | Exécuter les scripts d'extraction, d'enrichissement et de compilation. | `python3 --version` |
| Node.js + npm | Installer et lancer Vitest, Playwright et les validateurs JS. | `node --version && npm --version` |
| Navigateurs Playwright | Exécuter les tests E2E Chromium desktop/mobile. | `npx playwright install chromium` |

Dépendances Python utilisées par les scripts :

```bash
pip install -r requirements.txt
```

Dépendances Node :

```bash
npm install
npx playwright install chromium
```

## Vue d'ensemble du dépôt

La configuration et le style :

- `map.config.yaml` est la source du style. On modifie ce fichier, jamais `www/style.json`.
- `build_map.py` compile `map.config.yaml` en trois fichiers : `www/style.json`, `granulometry.json` (quels objets et quels attributs garder à chaque zoom) et `pmtiles_params.json` (zooms et simplification de chaque PMTiles).
- `retro_style.py` reconstruit un `map.config.yaml` à partir d'un `style.json` (voir [Reconstruire la configuration depuis un style](#reconstruire-la-configuration-depuis-un-style)).
- `poi-icons.config.yaml` déclare les icônes qui dépendent de plusieurs tags à la fois (toilettes hommes/femmes, types d'œuvres d'art…).

L'extraction depuis le PBF, lancée par `generate_json.bash` :

- `filter_geojson.py` nettoie chaque export osmium : objets référencés hors filtre, doublons ligne/surface des ways fermées, mobilier urbain cartographié en ligne ou en surface ramené à un point.
- `compute_building_coverage.py` repère les bâtiments entièrement couverts par leurs `building:part`, pour ne pas les dessiner deux fois en 3D.
- `extract_addresses.py` construit la couche des numéros de rue, `extract_indoor.py` celle de l'intérieur des bâtiments (avec la liste des niveaux, `www/indoor-levels.json`), et `extract_stib_routes.py` les lignes STIB à partir des relations de transport.
- `normalize_disused_shops.py`, `normalize_multi_values.py` et `assign_levels.py` (avec `osm_levels.py`) harmonisent les POI : commerces fermés, valeurs multiples comme `cuisine=pita;durum`, niveau de chaque objet.
- `compute_pitch_bearing.py` calcule l'orientation des terrains de sport pour leurs marquages.
- `check_landuse_coverage.py` et `check_street_furniture_coverage.py` comparent les valeurs présentes dans l'extrait à celles que la configuration dessine, et écrivent `landuse_report.md` et `street_furniture_report.md`.
- Le script écrit aussi `www/data-info.json` avec la date de l'extrait.

Les étapes suivantes :

- `generate_roofs.py` modélise les toits en 3D et écrit `www/roofs.glb`.
- `generate_poi_icons.py` cherche une icône pour chaque type de POI et de mobilier présent, écrit `www/poi-icons.json` et liste les manques dans `missing-icons.txt`.
- `merge_buildings.py` fusionne les bâtiments mitoyens pour les zooms bas.
- `apply_granulometry.py` applique `granulometry.json` aux GeoJSON et écrit `granulometry_report.md`.
- `generate_pmtiles.bash` produit un PMTiles par couche avec les paramètres de `pmtiles_params.json` et met à jour `sizepmtiles.md`.

Le reste :

- `www/` contient l'application statique, le style, les icônes, les motifs et les PMTiles publiés.
- `tests/` contient les tests Python, les tests unitaires Vitest, les tests E2E Playwright et le validateur de style.
- `design-icons-specs.md` décrit les contraintes de dessin des icônes locales, et `how-to.md` reprend les cas d'édition courants.

## Modifier le style de la carte

`www/style.json` est généré par `build_map.py` : toute modification faite à la main dans ce fichier disparaît au build suivant.

```
map.config.yaml  →  build_map.py  →  www/style.json
```

1. Éditez `map.config.yaml` (couleurs, zooms, opacités, sous-types…).
2. Régénérez le style :

```bash
python3 build_map.py
```

3. Vérifiez visuellement (voir [Tests unitaires et E2E](#7-tests-unitaires-et-e2e) pour `npm run serve`).
4. Commitez `map.config.yaml` et `www/style.json`.

### Ce que la configuration pilote en dehors du style

`map.config.yaml` décide aussi de ce qui part dans les tuiles. Changer un `appear_at` modifie la granulométrie : sous ce zoom, les objets sont retirés des PMTiles. La section `tiles` d'une couche fixe ses zooms et sa simplification dans Tippecanoe, et les sous-types de `street_furniture` servent de filtres d'extraction à osmium. Ces changements ne prennent effet qu'après une régénération des tuiles, alors qu'un changement de couleur ne demande qu'un `python3 build_map.py`.

### Section `map`

| Champ | Description |
| :--- | :--- |
| `name`, `version` | Nom et version du style |
| `center`, `zoom` | Position initiale de la carte |
| `background` | Couleur du fond |
| `font` | Couleur par défaut des étiquettes |
| `glyphs` | URL des polices |

### Champs d'une couche

| Champ | Description |
| :--- | :--- |
| `label` | Nom lisible de la couche (titre du groupe dans la légende) |
| `color` | Couleur principale (fill ou line) |
| `border_color` | Couleur du contour (ex : buildings) |
| `appear_at` | Zoom minimum d'apparition |
| `labels_at` | Zoom minimum des étiquettes (défaut : `appear_at + 3`) |
| `opacity` | Opacité globale, de 0 à 1 |
| `visible` | `false` pour masquer la couche au chargement (décochée dans la légende) |
| `swatch` | Pastille de légende : `fill`, `line` ou `dot` (défaut : type de layer majoritaire) |
| `swatch_colors` | Pastille multicolore, par exemple `["#007cc2", "#ef3e42"]` pour les lignes STIB |
| `extrusion_3d` | `true` pour le rendu 3D des bâtiments |
| `materials` | Bâtiments : couleur 3D par valeur de `building:material` (`building:colour` reste prioritaire) |
| `tiles` | Paramètres du PMTiles : `min_zoom`, `max_zoom`, `simplification`, et `detail_from` pour les bâtiments |
| `sports` | Loisirs uniquement : couleur, contour et longueur des terrains par sport (`default`, `values`), zoom des marquages (`markings_at`) |
| `density` | POI uniquement : désencombrement, voir plus bas |

La section `density` des POI contient `grid` (taille de cellule en pixels), `show` (nombre maximal de POI par cellule à chaque zoom), `tiers` (paliers d'importance par tag, du plus important au moins important), `dots_at` (zoom à partir duquel les POI sans icône deviennent des points) et `overlap_at` (zoom à partir duquel les icônes peuvent se chevaucher).

### Champs d'un sous-type (`subtypes`)

| Champ | Description |
| :--- | :--- |
| `tag` | Tag OSM du filtre (`landuse`, `leisure`, `highway`…) |
| `label` | Nom affiché dans la légende (défaut : libellé intégré à `build_map.py`) |
| `color` | Couleur principale du sous-type |
| `color_private` | Couleur si `access=private` |
| `pattern` | `fill-pattern` (ex : `military-hatch`) |
| `pattern_private` | `fill-pattern` uniquement si `access=private` (ex : `green-hatch`) |
| `pattern_at` | Zoom d'apparition du motif (défaut : `appear_at`) |
| `outline_color` | Couleur du contour, ou de la bordure pour les routes |
| `appear_at` | Zoom minimum pour ce sous-type |
| `opacity` | Opacité du remplissage, de 0 à 1 |
| `by` | Clé OSM secondaire qui fait varier le rendu (ex : `religion` pour les cimetières, `leaf_type` pour les arbres) |
| `by_color`, `by_pattern` | Couleur ou motif par valeur de la clé `by` |
| `tunnel_color` | Couleur des tronçons en tunnel (défaut : `color` éclaircie) |

Pour les routes, les sous-types sont les classes `highway` : `motorway`, `trunk`, `primary`, `secondary`, `tertiary` et leurs bretelles `_link`, puis `residential`, `unclassified`, `living_street`, `service`, `busway` et `track`. Les épaisseurs de trait sont fixées dans `build_map.py` et ne se règlent pas depuis la configuration.

### Section `patterns`

Chaque motif SVG utilisé par `pattern` ou `by_pattern` y est déclaré avec `file` (chemin dans `www/`), `size` (en pixels) et `replace`, une table de substitution de couleurs appliquée au SVG au chargement. Le même fichier peut ainsi servir avec plusieurs couleurs.

### Section `layers.indoor`

Cette section est facultative et ne concerne que le rendu 3D de l'intérieur. Elle accepte `appear_at`, `level_height` (hauteur d'un niveau en mètres), `slab` (épaisseur des planchers), `volume_ratio` (hauteur des volumes rapportée à celle du niveau), `floor_opacity`, `volume_opacity`, et une couleur par type d'espace dans `subtypes` : `room`, `corridor`, `footway`, `pedestrian`, `platform`, `steps`, `escalator`, `elevator`, `wall`, `area` et `arrow`. Sans cette section, les valeurs par défaut de `build_map.py` s'appliquent.

### Légende

`build_map.py` écrit la légende dans `style.json` (`metadata["brussels:legend"]`) et `www/legend.js` la construit au chargement.

Il y a un groupe par couche de `map.config.yaml`, dans l'ordre du fichier, et une sous-entrée par sous-type qui a ses propres layers, dans l'ordre des `subtypes`. Chaque layer du style est rattaché à un groupe, si bien qu'une couche ajoutée plus tard apparaît d'elle-même dans la légende. Les layers sans sous-type (étiquettes, flèches, ouvrages d'art…) suivent leur groupe et restent visibles tant qu'au moins une sous-entrée est cochée.

La couleur d'une entrée est la `color` de la configuration. À défaut, c'est la couleur lue dans la peinture des layers (hors bordures, tunnels et ponts), et en dernier recours `#cccccc`. Les groupes se replient, un groupe partiellement coché s'affiche dans un état mixte, et deux boutons permettent de tout afficher ou de tout masquer.

### Reconstruire la configuration depuis un style

`retro_style.py` fait le chemin inverse de `build_map.py` : il lit un `style.json` et écrit un `map.config.yaml`. C'est utile pour reprendre un style modifié dans Maputnik.

```bash
python3 retro_style.py --style www/style.json --out map.config.new.yaml
```

Sans `--out`, le script écrit dans `map.config.yaml` et écrase le fichier existant. Mieux vaut écrire à côté puis comparer.

Le script relit tous les champs décrits plus haut : couleurs, contours, zooms, opacités, visibilité, libellés, motifs, couleurs privées, clés `by`, couleurs de tunnel, pastilles de légende, matériaux, paramètres `tiles`, `sports`, `density`, section `patterns`, section `map` et réglages de l'intérieur 3D. Il s'appuie sur les métadonnées que `build_map.py` range dans le style (légende, motifs, tuiles, désencombrement, couches 3D chargées à la demande) et sur les identifiants de layers de ZinnekeTiles.

Il a trois limites :

- Une modification que la configuration ne sait pas exprimer, comme une épaisseur de trait ou un layer ajouté à la main, n'est pas reprise et disparaît au build suivant.
- Un style construit pour d'autres tuiles (OpenMapTiles, Shortbread…) n'utilise ni nos couches ni nos identifiants, et le script n'en tire rien d'utilisable.
- Les commentaires et la mise en forme du `map.config.yaml` d'origine ne sont pas conservés.

Le workflow GitHub `retro.yml` lance le script depuis l'onglet Actions, sous *Retro-engineer config from style*. Il prend le chemin du style source (`style_path`), le fichier de sortie (`config_out`) et `overwrite`, à mettre sur `true` pour écraser un fichier existant. Le YAML produit est commité automatiquement.

Deux suites de tests surveillent cet aller-retour. `tests/test_roundtrip.py` vérifie sur la configuration réelle que l'aller-retour garde le nombre et l'ordre des layers, les sources et les principales couleurs et zooms. `tests/test_retro_capabilities.py` modifie un champ de la configuration à la fois et vérifie que le style reconstruit est identique à l'original.

## Workflow de développement complet

L'ordre est le même que dans le déploiement : configuration, extraction, enrichissement, granulométrie, PMTiles, validation, tests.

### 1. Compiler la configuration

```bash
python3 build_map.py
```

### 2. Extraire les couches GeoJSON

```bash
./generate_json.bash
```

La commande vérifie que `brussels_capital_region-latest.osm.pbf` est bien un PBF OSM, puis produit les couches `roads`, `buildings`, `water`, `green`, `trees`, `landuse`, `boundaries`, `street_furniture`, `addresses`, `poi`, `leisure`, `pedestrian`, `cycleway`, `railway`, `public_transport`, `building_parts` et `indoor`. Elle écrit aussi `www/data-info.json`, `www/indoor-levels.json` et les rapports de couverture `landuse_report.md` et `street_furniture_report.md`.

Les POI surfaciques sont convertis en points et dédoublonnés, les lignes STIB sont reconstruites depuis les relations, et l'orientation des terrains de sport est calculée au passage. Relancez `python3 compute_pitch_bearing.py` seul uniquement si vous modifiez `leisure.json` sans refaire l'extraction.

### 3. Enrichir

```bash
python3 generate_roofs.py --buildings buildings_detail.json --parts building_parts.json --out www/roofs.glb
python3 generate_poi_icons.py --poi-json poi.json street_furniture.json
python3 merge_buildings.py
```

`merge_buildings.py` produit `buildings_merged.json` pour les zooms bas et garde `buildings_detail.json` pour les zooms hauts. Il ne sert que si `buildings.appear_at` est inférieur à `buildings.tiles.detail_from` (13 par défaut) ; sinon `pmtiles_params.json` ne référence pas le fichier fusionné.

### 4. Appliquer la granulométrie

```bash
python3 apply_granulometry.py
```

Les objets sont retirés sous leur zoom d'apparition, et leurs attributs sont allégés aux zooms bas pour réduire la taille des tuiles. Le résumé est écrit dans `granulometry_report.md`.

```bash
# Simuler sans écrire (dry-run) :
python3 apply_granulometry.py --dry-run

# Appliquer uniquement certaines couches :
python3 apply_granulometry.py --layers roads,poi
```

### 5. Générer les PMTiles

```bash
./generate_pmtiles.bash
mv *.pmtiles www/
```

Le script produit un `.pmtiles` par couche à la racine, avec les zooms et la simplification de `pmtiles_params.json`, et met à jour `sizepmtiles.md`. Une couche sans données est sautée avec un avertissement et l'ancienne version reste dans `www/`.

### 6. Valider le style et les PMTiles

Validation rapide :

```bash
npm run test:validate
```

Validation stricte, qui lit les métadonnées des PMTiles et vérifie que chaque layer vectoriel de `www/style.json` référence une source et un `source-layer` réellement présents :

```bash
mkdir -p tmp/pmtiles-metadata
python3 scripts/extract_pmtiles_metadata.py www/*.pmtiles --out-dir tmp/pmtiles-metadata
python3 scripts/validate_style_pmtiles.py --style www/style.json --metadata-dir tmp/pmtiles-metadata
```

### 7. Tests unitaires et E2E

Les tests Python couvrent la compilation, l'aller-retour avec `retro_style.py` et les scripts d'extraction (toits, adresses, intérieur, niveaux…) :

```bash
python3 -m pytest tests
```

Les tests unitaires Vitest se lancent une fois, en mode watch ou avec la couverture :

```bash
npm test
npm run test:watch
npm run test:coverage
```

Les tests E2E Playwright démarrent eux-mêmes un serveur statique sur le port 8080 via `playwright.config.js` :

```bash
npm run test:e2e
```

Pour regarder la carte en local, sur http://localhost:8080 :

```bash
npm run serve
```

`npm run test:all` enchaîne Vitest, la validation du style et Playwright.

#### Mise en page mobile

`tests/e2e/map-layout.spec.js` vérifie qu'aucun élément de l'interface (titre, niveaux, légende, boutons, contrôles MapLibre, attribution) ne se chevauche ni ne sort de l'écran, du petit téléphone (360×640) à l'écran d'ordinateur, en 2D comme en 3D et avec chaque panneau ouvert. Il tourne aussi dans le projet `mobile-chrome`. Une modification de `www/index.html` qui touche aux panneaux ou aux contrôles doit le garder vert.

En mode compact (largeur ≤ 600 px ou hauteur ≤ 500 px), le panneau Niveaux passe sous le titre et les boutons s'empilent à droite. Un seul panneau est ouvert à la fois et la légende démarre repliée. Elle se place au-dessus de l'attribution, dont la hauteur est suivie en continu (`--attrib-h`, `--controls-h`).

## Déploiement automatique

Le workflow `deploy.yml` reconstruit et publie la carte. Il se lance à chaque push sur `main` qui ne touche pas seulement des fichiers générés, à la main depuis l'onglet Actions, et le 1er de chaque mois à 3 h UTC.

Il compile la configuration, télécharge l'extrait OSM du jour, puis enchaîne l'extraction, les toits, les icônes, la fusion des bâtiments, la granulométrie et les PMTiles. Il commite ensuite les fichiers générés (PMTiles, `style.json`, `poi-icons.json`, `data-info.json`, `roofs.glb`, rapports) et publie `www/` sur GitHub Pages avec les rapports. Si `map.config.yaml` est absent, il garde `www/style.json` tel quel.

Sur chaque pull request, `tests.yml` lance les tests unitaires, la validation du style, les tests Python de compilation et d'aller-retour, et les tests E2E, et `validate-pmtiles-metadata.yml` confronte le style à la spécification MapLibre et aux métadonnées des PMTiles.

## Mettre à jour le PBF

Le pipeline attend un fichier nommé exactement `brussels_capital_region-latest.osm.pbf` à la racine du dépôt.

Le workflow `deploy.yml` télécharge l'extrait quotidien `Brussels-daily.pbf` publié par le dépôt [PasLoin/Osm-python-analyse_Belgium](https://github.com/PasLoin/Osm-python-analyse_Belgium), puis le copie sous ce nom. Pour reproduire la même source en local :

```bash
curl -L \
  -o brussels_capital_region-latest.osm.pbf \
  https://raw.githubusercontent.com/PasLoin/Osm-python-analyse_Belgium/main/pbf_analyse/history/Brussels-daily.pbf
file brussels_capital_region-latest.osm.pbf
osmium fileinfo brussels_capital_region-latest.osm.pbf
```

Après remplacement du PBF, relancez toute la chaîne :

```bash
python3 build_map.py
./generate_json.bash
python3 generate_roofs.py --buildings buildings_detail.json --parts building_parts.json --out www/roofs.glb
python3 generate_poi_icons.py --poi-json poi.json street_furniture.json
python3 merge_buildings.py
python3 apply_granulometry.py
./generate_pmtiles.bash
mv *.pmtiles www/
npm run test:validate
python3 -m pytest tests
npm test
npm run test:e2e
```

Pour une autre source OSM, gardez le même nom de fichier ou modifiez la variable `SRC` dans `generate_json.bash`.

## Ajouter une couche

Une nouvelle couche touche l'extraction, la compilation du style et la reconstruction inverse.

1. Extrayez les objets OSM dans `generate_json.bash`, avec un appel `extract nouvelle_couche ...` pour un filtrage simple, ou un script Python dédié sur le modèle de `extract_stib_routes.py` pour une extraction plus complexe.
2. Dans `build_map.py`, ajoutez le nom à `SOURCES` et à `PMTILES_DEFAULTS`, écrivez la fonction qui produit les layers de la couche et appelez-la dans `build_style()`. La source MapLibre, la légende, la granulométrie et les paramètres PMTiles en découlent. Si seuls les sous-types déclarés doivent rester dans les tuiles, ajoutez aussi la couche à `SUBTYPE_ONLY_LAYERS`.
3. Déclarez la couche dans `map.config.yaml` avec ses couleurs, zooms et, au besoin, une section `tiles`, puis lancez `python3 build_map.py`.
4. Ajoutez les préfixes d'identifiants de ses layers à `GROUPS` dans `retro_style.py`, pour que l'aller-retour la retrouve.
5. Régénérez les données (granulométrie et PMTiles) et déplacez `nouvelle_couche.pmtiles` dans `www/`.
6. Lancez `npm run test:validate` et `python3 -m pytest tests`, puis ajoutez ou adaptez des tests dans `tests/unit/` ou `tests/e2e/` si l'interface, la légende ou les layers visibles changent.

## Ajouter une icône POI

`www/poi_icons.js` charge les icônes listées dans `www/poi-icons.json`, que génère `generate_poi_icons.py`. Pour chaque type présent dans `poi.json` et `street_furniture.json`, le script cherche un fichier local dans `www/assets/icons/`, puis une icône Temaki, Maki ou OSM Liberty. Les règles de nommage et de dessin sont dans [design-icons-specs.md](design-icons-specs.md).

1. Identifiez la clé OSM qui doit produire l'icône. `shop=butcher` donne le type `butcher`, `cuisine=friture` donne `cuisine-friture`.
2. Si aucune icône CDN ne convient, ajoutez un SVG dans `www/assets/icons/`, par exemple `www/assets/icons/butcher.svg`. Il doit être sous licence CC0 (voir [Licences](#licences)) : dessin original ou reprise d'un jeu CC0 comme openstreetmap-carto.
3. Si le nom du fichier ou de l'icône CDN ne correspond pas au type, ajoutez une entrée dans `CDN_NAME_OVERRIDES` de `generate_poi_icons.py`. Elle peut pointer vers un fichier local (`local`) ou vers une icône Temaki, Maki ou Liberty.
4. Si l'icône dépend de plusieurs tags à la fois (par exemple `amenity=toilets` avec `male=yes` et `female=no`), déclarez le cas dans `composite_cases` de `poi-icons.config.yaml`.
5. Régénérez le manifeste et vérifiez les manques :

```bash
python3 generate_poi_icons.py --poi-json poi.json street_furniture.json
cat missing-icons.txt
npm test -- tests/unit/poi_icons.test.js
```

6. Lancez les tests E2E si l'icône change le rendu visible de la carte ou de la légende.

## Commandes utiles

| Commande | Description |
| :--- | :--- |
| `pip install -r requirements.txt` | Installe les dépendances Python (pyyaml, shapely, pytest). |
| `python3 build_map.py` | Compile `map.config.yaml` en `www/style.json`, granulométrie et paramètres PMTiles. |
| `python3 retro_style.py --out map.config.new.yaml` | Reconstruit une configuration depuis `www/style.json`. |
| `python3 apply_granulometry.py` | Applique les règles de granulométrie aux GeoJSON. |
| `python3 -m pytest tests` | Lance tous les tests Python. |
| `npm run serve` | Sert `www/` sur le port 8080. |
| `npm test` | Lance les tests unitaires Vitest. |
| `npm run test:watch` | Lance Vitest en mode interactif. |
| `npm run test:coverage` | Produit la couverture des tests unitaires. |
| `npm run test:validate` | Vérifie la cohérence de `www/style.json`, des PMTiles et des assets. |
| `npm run test:e2e` | Lance les tests Playwright desktop et mobile. |
| `npm run test:e2e:ui` | Ouvre l'interface Playwright. |
| `npm run test:e2e:report` | Affiche le dernier rapport Playwright. |
| `npm run test:all` | Lance Vitest, la validation du style et Playwright. |

## Limitations connues

`www/index.html` contient du CSS inline et des handlers `onclick` inline. Ça fonctionne, mais ça complique une future politique CSP stricte. Une refactorisation vers `www/style.css` et `addEventListener` est prévue.

## Dépannage

- `brussels_capital_region-latest.osm.pbf n'est pas un fichier PBF valide` : le téléchargement a sans doute renvoyé une page HTML ou un fichier incomplet. Relancez-le et vérifiez avec `file ...`.
- `tippecanoe: command not found` : installez Tippecanoe et vérifiez qu'il est dans le `PATH`.
- Icônes POI manquantes : consultez `missing-icons.txt`, ajoutez un SVG local ou un override, puis relancez `generate_poi_icons.py`.
- Playwright ne trouve pas Chromium : lancez `npx playwright install chromium`.
- Le style référence une couche absente : comparez `www/style.json`, les noms des fichiers `www/*.pmtiles` et les `vector_layers` extraits par `scripts/extract_pmtiles_metadata.py`.
- `map.config.yaml` et `www/style.json` divergent : lancez `python3 build_map.py` pour régénérer le style depuis la configuration, ou `retro_style.py` pour reconstruire la configuration depuis le style.
- Les tests d'aller-retour échouent : `tests/test_retro_capabilities.py` indique quel champ `retro_style.py` ne retrouve plus. Sinon, comparez le YAML produit par `retro_style.py` avec `map.config.yaml`. Une différence signale soit un champ que `retro_style.py` ne lit pas, soit un rendu de `build_map.py` qui n'a pas d'équivalent dans la configuration.

## Licences

ZinnekeTiles assemble des éléments sous plusieurs licences :

| Élément | Licence | Détail |
| :--- | :--- | :--- |
| Code du projet (scripts, `www/*.js`, `www/index.html`, configuration, tests) | [MIT](LICENSE) | © 2026 PasLoin |
| Données cartographiques (PMTiles, GeoJSON, `roofs.glb`, `data-info.json`) | [ODbL 1.0](https://opendatacommons.org/licenses/odbl/) | © [contributeurs OpenStreetMap](https://www.openstreetmap.org/copyright) |
| Rendu : [MapLibre GL JS](https://github.com/maplibre/maplibre-gl-js) et [PMTiles](https://github.com/protomaps/PMTiles) | [BSD-3-Clause](https://github.com/maplibre/maplibre-gl-js/blob/main/LICENSE.txt) / [BSD-3-Clause](https://github.com/protomaps/PMTiles/blob/main/LICENSE) | Chargés depuis unpkg, non redistribués dans ce dépôt |
| Icônes [Temaki](https://github.com/rapideditor/temaki), [Maki](https://github.com/mapbox/maki) et [OSM Liberty](https://github.com/maputnik/osm-liberty) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) | Chargées depuis leur CDN par `www/poi_icons.js` |
| Icônes additionnelles reprises d'[openstreetmap-carto](https://github.com/gravitystorm/openstreetmap-carto) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) | Dans `www/assets/` |
| Icônes et motifs originaux ZinnekeTiles (non dérivés) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) | Dans `www/assets/` |

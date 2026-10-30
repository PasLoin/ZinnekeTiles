# ZinnekeTiles

Is it possible to run Brussels on a mini maximal vector tile on github page ?

*Anciennement « Brussels minimal vector tile ».*

Prototype de carte MapLibre pour la Région de Bruxelles-Capitale, générée à partir d'un extrait OpenStreetMap PBF local et publiée comme fichiers PMTiles statiques dans `www/`.

L'objectif est de garder un jeu de tuiles vectorielles minimal, lisible et versionnable pour GitHub Pages : une couche PMTiles par thème, un style MapLibre unique, et une suite de tests qui vérifie à la fois le style, l'interface et le rendu dans un navigateur.

## Prérequis système

Installez les outils suivants avant de régénérer les données :

| Outil | Usage dans ce dépôt | Vérification rapide |
| :--- | :--- | :--- |
| `osmium` / `osmium-tool` | Filtrer le PBF OSM et exporter les GeoJSON intermédiaires. | `osmium --version` |
| `tippecanoe` | Convertir les GeoJSON en archives PMTiles. | `tippecanoe --version` |
| `python3` | Exécuter les scripts d'enrichissement des couches. | `python3 --version` |
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

- `brussels_capital_region-latest.osm.pbf` : extrait source OpenStreetMap attendu par le pipeline.
- `requirements.txt` : dépendances Python versionnées (`pyyaml`, `shapely`, `pytest`).
- `map.config.yaml` : **source de vérité du style**. Modifier ce fichier, pas `www/style.json` directement.
- `build_map.py` : compile `map.config.yaml` → `www/style.json` + `granulometry.json` + `pmtiles_params.json`.
- `styles/*.yaml` : variantes de style (surcharges de `map.config.yaml`), compilées en `www/style.<id>.json` — voir [Variantes de style](#variantes-de-style).
- `retro_style.py` : ingénierie inverse d'un `style.json` existant → `map.config.yaml` (bootstrap ou import).
- `generate_json.bash` : extrait les couches thématiques depuis le PBF et produit les GeoJSON intermédiaires (`roads.json`, `poi.json`, etc.).
- `apply_granulometry.py` : filtre les GeoJSON selon les règles LOD générées par `build_map.py`.
- `filter_geojson.py` : nettoie chaque GeoJSON exporté par osmium (objets référencés hors filtre, doublons ligne/surface des ways fermées, mobilier urbain cartographié en ligne ou surface ramené à un point).
- `compute_pitch_bearing.py`, `extract_stib_routes.py`, `merge_buildings.py` : enrichissements appliqués aux GeoJSON. Le rendu des terrains de sport (section `leisure.sports` du YAML), les motifs (`patterns`) et les paramètres PMTiles (`tiles`) sont générés par `build_map.py` depuis `map.config.yaml`.
- `generate_poi_icons.py` : génère `www/poi-icons.json` et `missing-icons.txt` à partir des types POI réellement présents.
- `generate_pmtiles.bash` : convertit les GeoJSON en PMTiles et met à jour `sizepmtiles.md`.
- `www/` : application statique, style MapLibre, icônes et PMTiles publiables.
- `tests/` : tests unitaires Vitest, tests E2E Playwright, validation du style et tests Python de non-régression.

---

## Modifier le style de la carte

> **Règle principale : ne jamais éditer `www/style.json` directement.**
> Ce fichier est généré automatiquement par `build_map.py` à partir de `map.config.yaml`.

### Cycle de travail normal

```
map.config.yaml  →  build_map.py  →  www/style.json
```

1. Éditez `map.config.yaml` (couleurs, zooms, opacités, sous-types…).
2. Régénérez le style :

```bash
python3 build_map.py
```

3. Vérifiez visuellement (voir [Serveur local](#serveur-local)).
4. Commitez `map.config.yaml` **et** `www/style.json`.

### Champs disponibles dans `map.config.yaml`

**Niveau couche :**

| Champ | Description |
| :--- | :--- |
| `label` | Nom lisible de la couche (titre du groupe dans la légende) |
| `color` | Couleur principale (fill ou line) |
| `border_color` | Couleur du contour (ex : buildings) |
| `appear_at` | Zoom minimum d'apparition |
| `labels_at` | Zoom minimum des étiquettes (défaut : `appear_at + 3`) |
| `opacity` | Opacité globale (0.0–1.0) |
| `visible` | `false` pour masquer la couche au chargement (décochée dans la légende) |
| `swatch` | Pastille de légende : `fill`, `line` ou `dot` (défaut : type de layer majoritaire) |
| `extrusion_3d` | `true` pour activer le rendu 3D des bâtiments |

**Niveau sous-type (`subtypes`) :**

| Champ | Description |
| :--- | :--- |
| `tag` | Tag OSM du filtre (`landuse`, `leisure`, `highway`…) |
| `label` | Nom affiché dans la légende (défaut : libellé intégré à `build_map.py`) |
| `color` | Couleur principale du sous-type |
| `color_private` | Couleur si `access=private` |
| `pattern` | `fill-pattern` (ex : `military-hatch`) |
| `pattern_private` | `fill-pattern` uniquement si `access=private` (ex : `green-hatch`) |
| `outline_color` | Couleur du contour |
| `appear_at` | Zoom minimum pour ce sous-type |
| `opacity` | Opacité fill (0.0–1.0) |

### Légende

La légende n'est plus écrite à la main dans `index.html` : `build_map.py` la génère dans `style.json` (`metadata["brussels:legend"]`) et `www/legend.js` la construit au chargement.

- Un groupe par couche de `map.config.yaml`, dans l'ordre du fichier ; une sous-entrée par sous-type qui possède ses propres layers, dans l'ordre des `subtypes`.
- Chaque layer sourcé du style est rattaché à un groupe : une couche ajoutée plus tard apparaît donc automatiquement dans la légende.
- Les layers sans sous-type (étiquettes, flèches, ouvrages d'art…) suivent le groupe : ils restent visibles tant qu'au moins une sous-entrée est cochée.
- Couleur : `color` de la config, sinon couleur lue dans la peinture des layers (hors casing, tunnel et pont), sinon `#cccccc`.
- Boutons « Tout afficher » / « Tout masquer », groupes repliables, état mixte quand seule une partie des sous-entrées est cochée.

### Couleurs annexes (`palette`)

Les couleurs secondaires qui ne dépendent pas d'un sous-type sont regroupées dans une section `palette` facultative. Sans cette section, les valeurs par défaut de `build_map.py` s'appliquent.

| Groupe | Clés |
| :--- | :--- |
| `water` | `tunnel_core` |
| `buildings` | `roof` |
| `leisure` | `outline` |
| `roads` | `bridge_casing`, `busway_center`, `tunnel_area`, `tunnel_area_outline`, `bridge_area`, `bridge_area_outline`, `label`, `label_halo`, `oneway`, `oneway_halo` |
| `pedestrian` | `no_access` |
| `cycleway` | `oneway` |
| `railway` | `bridge_casing` |
| `public_transport` | `casing`, `label`, `label_halo` |
| `addresses` | `halo` |
| `poi` | `stroke`, `label_halo` |

```yaml
palette:
  roads: { label: "#222222", bridge_casing: "#000000" }
```

Sur `buildings`, `osm_colour: false` ignore le tag `building:colour` en 3D (utile pour un rendu monochrome). Combinez-le avec `materials: null` dans une variante pour retirer aussi les couleurs par matériau.

### Importer un style externe (bootstrap `retro_style.py`)

Si vous disposez d'un `style.json` MapLibre existant (Maputnik, import externe…) et souhaitez en faire la source de vérité, utilisez `retro_style.py` pour en extraire automatiquement un `map.config.yaml` :

```bash
python3 retro_style.py --style www/style.json --out map.config.yaml
```

Ce script extrait couleurs, `border_color`, `appear_at`, `labels_at`, `extrusion_3d`, opacités, `color_private`, patterns et sous-types pour toutes les couches reconnues.

> **Attention :** si `map.config.yaml` existe déjà, ajoutez `--out map.config.new.yaml` pour ne pas l'écraser, puis comparez.

Le workflow GitHub `retro.yml` fait la même chose en un clic depuis l'onglet **Actions** :

1. Actions → *Retro-engineer config from style* → **Run workflow**
2. Choisissez `overwrite: true` pour écraser l'existant, ou laissez `false` pour créer un fichier parallèle.
3. Le fichier YAML généré est commité automatiquement.

### Garantie bidirectionnelle

La chaîne est conçue pour être réversible sans perte :

```
map.config.yaml  →  build_map.py   →  www/style.json
www/style.json   →  retro_style.py →  map.config.yaml  →  build_map.py  →  www/style.json (≃ identique)
```

Les tests de non-régression Python (`tests/test_roundtrip.py`) vérifient automatiquement cette propriété à chaque PR.

---

## Variantes de style

Plusieurs styles peuvent coexister sur les **mêmes PMTiles**. `map.config.yaml` reste la base et produit `www/style.json`. Chaque fichier `styles/<id>.yaml` est une surcharge partielle de la base, compilée en `www/style.<id>.json`. Le manifeste `www/styles.json` liste tous les styles.

```bash
python3 build_map.py --only style --variants styles
```

```
map.config.yaml                    →  www/style.json
map.config.yaml + styles/nb.yaml   →  www/style.nb.json
                                   →  www/styles.json
```

### Format d'une variante

```yaml
variant:
  label: Noir et blanc
exclude: [poi, trees]
map:
  background: "#ffffff"
palette:
  roads: { label: "#000000" }
patterns:
  green-hatch: { replace: { "#bd4a72": "#9a9a9a" } }
layers:
  water: { color: "#c4c4c4" }
  roads:
    subtypes:
      primary: { color: "#ffffff", outline_color: "#2b2b2b" }
```

| Clé | Rôle |
| :--- | :--- |
| `variant.label` | Nom affiché dans le sélecteur (défaut : l'identifiant) |
| `exclude` | Couches retirées du style, de ses sources et de la légende (rien n'est téléchargé). Accepte aussi `indoor` et `building_parts` |
| `map`, `palette`, `patterns`, `layers` | Fusionnés récursivement sur la base. `null` supprime une clé (ex : `materials: null`) |

- **Identifiant** : nom du fichier, en minuscules, chiffres et tirets (`nb`, `noir-et-blanc`). `default` est réservé.
- **Masquer sans retirer** : `visible: false` garde la couche dans le style, décochée dans la légende ; `exclude` la supprime.
- **Hachage** : `metadata["brussels:config_hash"]` reste celui de la base (il identifie les tuiles) ; `metadata["brussels:variant"]` porte l'identifiant, le libellé et le hash de la variante.
- **Fichiers obsolètes** : supprimer `styles/x.yaml` supprime `www/style.x.json` au build suivant.

### Ce qu'une variante ne peut pas faire

Les tuiles sont communes à tous les styles : une variante ne modifie que la présentation. `build_map.py` refuse donc une variante qui :

- contient `tiles`, `density` ou `tag` ;
- abaisse un `appear_at` sous celui de la base (les objets n'existent pas dans les tuiles à ce zoom) — le relever est permis ;
- déclare une couche, un sous-type, une clé de palette ou une clé de premier niveau inconnus ;
- ajoute un motif sans `file`.

Le build échoue avec la liste complète des erreurs.

### Dans la carte

`www/index.html` lit `www/styles.json` et affiche un sélecteur dans le panneau titre dès qu'il y a au moins deux styles. Le style choisi passe par le paramètre `?style=<id>`, qui conserve la position (`#zoom/lat/lon`) :

```
https://pasloin.github.io/ZinnekeTiles/?style=nb#16/50.8466/4.3528
```

Un identifiant inconnu ou un manifeste absent ramène au style par défaut.

Une autre page peut aussi charger directement `https://pasloin.github.io/ZinnekeTiles/style.nb.json`. Les URL des sources (`./roads.pmtiles`) et des motifs (`assets/…`) y sont relatives : résolvez-les par rapport à l'URL du style avant de créer la carte, et préfixez les sources par `pmtiles://`.

---

## Workflow de développement complet

L'ordre recommandé est : **config → extraction → LOD → PMTiles → validation → tests**.

### 1. Modifier le style (si besoin)

```bash
# Éditer map.config.yaml, puis :
python3 build_map.py
```

### 2. Extraction des couches GeoJSON

```bash
./generate_json.bash
```

Cette commande lit `brussels_capital_region-latest.osm.pbf`, vérifie que le fichier est bien un PBF OSM, puis produit les couches GeoJSON suivantes : `roads`, `buildings`, `water`, `green`, `trees`, `landuse`, `boundaries`, `poi`, `leisure`, `pedestrian`, `cycleway`, `railway` et `public_transport`.

À cette étape, les POI surfaciques sont convertis en points représentatifs et dédoublonnés. La couche `public_transport` est reconstruite depuis les relations STIB/MIVB.

### 3. Enrichissement des données et du style

```bash
python3 merge_buildings.py
python3 generate_poi_icons.py
```

- `merge_buildings.py` produit `buildings_merged.json` pour les zooms bas, tout en conservant `buildings_detail.json` pour les zooms hauts. Il n'est utile que si `buildings.appear_at` est inférieur à `buildings.tiles.detail_from` (13 par défaut) : sinon `pmtiles_params.json` ne référence pas le fichier fusionné.
- `generate_poi_icons.py` inspecte `poi.json`, résout les icônes locales/CDN disponibles, écrit `www/poi-icons.json`, puis liste les manques dans `missing-icons.txt`.

> `generate_json.bash` lance déjà `compute_pitch_bearing.py` après l'extraction de `leisure.json`. Relancez `compute_pitch_bearing.py` manuellement uniquement si vous modifiez `leisure.json` sans refaire toute l'extraction.

### 4. Application de la granulométrie (LOD)

```bash
python3 apply_granulometry.py
```

Filtre les GeoJSON selon les règles LOD définies dans `granulometry.json` (généré par `build_map.py`). Les features hors zoom d'apparition sont supprimées ; les propriétés sont allégées aux zooms bas pour réduire la taille des tuiles.

```bash
# Simuler sans écrire (dry-run) :
python3 apply_granulometry.py --dry-run

# Appliquer uniquement certaines couches :
python3 apply_granulometry.py --layers roads,poi
```

### 5. Génération des PMTiles

```bash
./generate_pmtiles.bash
```

Le script produit un fichier `.pmtiles` par source vectorielle et met à jour le rapport `sizepmtiles.md`. Les fichiers générés à la racine doivent ensuite remplacer ceux de `www/` :

```bash
mv *.pmtiles www/
```

Les sources déclarées dans `www/style.json` doivent correspondre aux noms des PMTiles publiés dans `www/`.

### 6. Validation du style et des PMTiles

Validation rapide utilisée par npm :

```bash
npm run test:validate
```

Validation stricte avec lecture des métadonnées PMTiles :

```bash
mkdir -p tmp/pmtiles-metadata
python3 scripts/extract_pmtiles_metadata.py www/*.pmtiles --out-dir tmp/pmtiles-metadata
python3 scripts/validate_style_pmtiles.py --style www/style.json --metadata-dir tmp/pmtiles-metadata
```

La première commande extrait les métadonnées PMTiles. La seconde vérifie que chaque layer vectoriel de `www/style.json` référence une source existante et un `source-layer` réellement présent dans le PMTiles.

### 7. Tests unitaires et E2E

Tests unitaires :

```bash
npm test
```

Tests unitaires en mode watch :

```bash
npm run test:watch
```

Couverture Vitest :

```bash
npm run test:coverage
```

Tests Python de non-régression (round-trip `retro_style` ↔ `build_map`) :

```bash
python3 -m pytest tests/test_roundtrip.py -v
```

Tests E2E Playwright :

```bash
npm run test:e2e
```

Playwright démarre automatiquement un serveur statique sur `http://localhost:8080` via `playwright.config.js`. Pour tester manuellement l'application :

```bash
npm run serve
```

Suite complète :

```bash
npm run test:all
```

#### Mise en page mobile

`tests/e2e/map-layout.spec.js` vérifie qu'aucun élément de l'interface (titre, niveaux, légende, boutons, contrôles MapLibre, attribution) ne se chevauche ni ne sort de l'écran, du petit téléphone (360×640) à l'écran d'ordinateur, en 2D comme en 3D et avec chaque panneau ouvert. Il tourne aussi dans le projet `mobile-chrome`. Toute modification de `www/index.html` qui touche aux panneaux ou aux contrôles doit le garder vert.

En mode compact (largeur ≤ 600 px ou hauteur ≤ 500 px) :

- le panneau Niveaux passe sous le titre et les boutons s'empilent à droite ;
- un seul panneau est ouvert à la fois, la légende démarre repliée ;
- la légende se place au-dessus de l'attribution, dont la hauteur est suivie en continu (`--attrib-h`, `--controls-h`).

---

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

Après remplacement du PBF, relancez le workflow complet :

```bash
python3 build_map.py
./generate_json.bash
python3 merge_buildings.py
python3 apply_granulometry.py
python3 generate_poi_icons.py
./generate_pmtiles.bash
mv *.pmtiles www/
npm run test:validate
python3 -m pytest tests/test_roundtrip.py -v
npm test
npm run test:e2e
```

Si vous préférez une source OSM différente, conservez le même nom de fichier ou modifiez la variable `SRC` dans `generate_json.bash`.

---

## Ajouter une couche

Ajouter une couche implique de modifier les trois parties du pipeline : extraction, tuilage, style.

1. **Extraire les objets OSM** dans `generate_json.bash`.
   - Ajoutez un appel `extract nouvelle_couche ...` pour un filtrage simple.
   - Pour une extraction relationnelle ou une transformation avancée, suivez le modèle de `public_transport` ou ajoutez un script Python dédié.
2. **Déclarer la couche dans `map.config.yaml`** avec ses couleurs et zooms, puis régénérez :
```bash
   python3 build_map.py
```
3. **Appliquer la granulométrie** (optionnel) : les règles LOD sont auto-générées par `build_map.py`. Vérifiez `granulometry.json` puis relancez `apply_granulometry.py`.
4. **Générer le PMTiles** dans `generate_pmtiles.bash`.
   - Ajoutez la couche aux tableaux `MAX_ZOOM` et `SIMPLIFICATION`.
   - Ajoutez son nom dans la boucle des couches standard, sauf si elle nécessite une commande Tippecanoe spéciale comme `buildings`.
5. **Publier le fichier** dans `www/`.
   - Après génération, déplacez `nouvelle_couche.pmtiles` vers `www/`.
6. **Déclarer la source MapLibre** dans `www/style.json`.
   - La source est ajoutée automatiquement par `build_map.py` si la couche est déclarée dans `map.config.yaml`.
7. **Valider**.
   - Lancez `npm run test:validate`, puis `python3 -m pytest tests/test_roundtrip.py -v`.
   - Ajoutez ou adaptez des tests dans `tests/unit/` ou `tests/e2e/` si l'interface, la légende ou les layers visibles changent.

---

## Ajouter une icône POI

Les icônes POI sont résolues par `www/poi_icons.js` à partir du manifeste `www/poi-icons.json`. Ce manifeste est généré par `generate_poi_icons.py`.

1. Identifiez la clé OSM qui doit produire l'icône.
   - Exemple simple : `shop=butcher` produit le type `butcher`.
   - Exemple sous-type : `cuisine=friture` produit la clé `cuisine-friture`.
2. Ajoutez un SVG local dans `www/assets/icons/` si aucune icône CDN ne convient.
   - Utilisez un nom explicite et stable, par exemple `www/assets/icons/butcher.svg`.
   - L'icône doit être sous licence CC0 (voir [Licences](#licences)) : dessin original ou reprise d'un jeu CC0 comme openstreetmap-carto.
3. Si le nom local/CDN ne correspond pas à la clé POI, ajoutez ou ajustez l'entrée dans `CDN_NAME_OVERRIDES` dans `generate_poi_icons.py`.
   - Les overrides peuvent pointer vers un fichier local (`local`) ou vers un nom d'icône Temaki, Maki ou Liberty.
4. Regénérez le manifeste :

```bash
python3 generate_poi_icons.py
```

5. Vérifiez les manques restants :

```bash
cat missing-icons.txt
npm test -- tests/unit/poi_icons.test.js
```

6. Lancez les tests E2E si l'icône modifie le rendu visible de la carte ou de la légende.

---

## Commandes utiles

| Commande | Description |
| :--- | :--- |
| `pip install -r requirements.txt` | Installe toutes les dépendances Python (pyyaml, shapely, pytest). |
| `python3 build_map.py` | Compile `map.config.yaml` → `www/style.json` + granulométrie + params PMTiles. |
| `python3 retro_style.py` | Ingénierie inverse `www/style.json` → `map.config.yaml`. |
| `python3 apply_granulometry.py` | Applique les règles LOD aux GeoJSON. |
| `npm run serve` | Sert `www/` sur le port 8080 pour inspection locale. |
| `npm test` | Lance les tests unitaires Vitest. |
| `npm run test:watch` | Lance Vitest en mode interactif. |
| `npm run test:coverage` | Produit la couverture des tests unitaires. |
| `npm run test:validate` | Valide la cohérence de `www/style.json` et des assets attendus. |
| `npm run test:e2e` | Lance les tests Playwright desktop et mobile. |
| `npm run test:e2e:ui` | Ouvre l'interface Playwright. |
| `npm run test:e2e:report` | Affiche le dernier rapport Playwright. |
| `npm run test:all` | Lance unitaires, validation de style et E2E. |
| `python3 -m pytest tests/test_roundtrip.py -v` | Tests de non-régression Python (round-trip style ↔ config). |

---

## Connus et limitations

### CSS inline et handlers inline

La page `www/index.html` contient actuellement du CSS inline et des handlers `onclick` inline. Cela fonctionne mais complexifie une future politique CSP stricte. Une refactorisation vers `www/style.css` + `addEventListener` est planifiée.

---

## Dépannage

- **`brussels_capital_region-latest.osm.pbf n'est pas un fichier PBF valide`** : le téléchargement a probablement renvoyé une page HTML ou un fichier incomplet. Relancez le téléchargement et vérifiez `file ...`.
- **`tippecanoe: command not found`** : installez Tippecanoe et vérifiez qu'il est dans le `PATH`.
- **Icônes POI manquantes** : consultez `missing-icons.txt`, ajoutez un SVG local ou un override, puis relancez `python3 generate_poi_icons.py`.
- **Playwright ne trouve pas Chromium** : lancez `npx playwright install chromium`.
- **Le style référence une couche absente** : comparez `www/style.json`, les noms de fichiers `www/*.pmtiles` et les `vector_layers` extraits par `scripts/extract_pmtiles_metadata.py`.
- **`map.config.yaml` et `www/style.json` divergent** : lancez `python3 build_map.py` pour régénérer le style depuis la config, ou `python3 retro_style.py` pour reconstruire la config depuis le style.
- **Les tests round-trip échouent** : comparez le YAML généré par `retro_style.py` avec `map.config.yaml` de référence. Les divergences indiquent un champ non capturé par `retro_style.py` ou un comportement de `build_map.py` qui n'a pas d'équivalent dans la config.

---

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

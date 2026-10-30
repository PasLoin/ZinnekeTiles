# How-to : éditer le style de la carte

## Principe général

Le style MapLibre (`www/style.json`) est généré par `build_map.py` : ne l'éditez pas à la main, vos modifications disparaîtraient au build suivant.

Toute modification de couleur, de zoom ou de sous-type passe par `map.config.yaml`, puis par `build_map.py`.

```
map.config.yaml  ──►  build_map.py  ──►  www/style.json
```

## Cas 1 : modifier une couleur ou un zoom

1. Ouvrez `map.config.yaml`.
2. Trouvez la couche concernée et ajustez le champ voulu (`color`, `appear_at`, `opacity`…).
3. Régénérez :

```bash
python3 build_map.py
```

4. Vérifiez dans le navigateur :

```bash
npm run serve
# ouvrir http://localhost:8080
```

5. Commitez les deux fichiers modifiés :

```bash
git add map.config.yaml www/style.json
git commit -m "style: ..."
```

Un changement de couleur suffit tel quel. Un changement d'`appear_at` ou de section `tiles` modifie aussi ce qui part dans les tuiles : il ne sera visible qu'après une régénération des PMTiles, faite par le déploiement automatique.

## Cas 2 : travailler depuis Maputnik

Maputnik permet d'éditer le style visuellement, mais il produit un `style.json` modifié, pas un `map.config.yaml`.

Pour réintégrer un style édité dans Maputnik :

1. Exportez le style depuis Maputnik (bouton Export) et enregistrez-le, par exemple sous `maputnik.json`.
2. Reconstruisez une configuration depuis ce style :

```bash
python3 retro_style.py --style maputnik.json --out map.config.new.yaml
```

3. Comparez avec la configuration actuelle, remplacez-la, puis régénérez le style :

```bash
diff map.config.yaml map.config.new.yaml
mv map.config.new.yaml map.config.yaml
python3 build_map.py
```

4. Lancez les tests d'aller-retour :

```bash
python3 -m pytest tests/test_roundtrip.py tests/test_retro_capabilities.py -v
```

`retro_style.py` retrouve tout ce que la configuration sait exprimer. Ce que Maputnik permet en plus, comme une épaisseur de trait ou un layer ajouté à la main, n'est pas repris : vérifiez le rendu après l'étape 3.

> Maputnik en ligne avec le style de ce dépôt :
> [maputnik.github.io/editor](https://maputnik.github.io/editor/#15.4/50.832973/4.318494/-1.9/39)
> (charger depuis l'URL `https://pmtiles.duckdns.org/brussels_ultimate_style.json`)

## Cas 3 : importer un style externe

La procédure est la même que pour Maputnik, à condition que le style ait été construit pour les tuiles et les identifiants de layers de ZinnekeTiles. Un style écrit pour d'autres tuiles (OpenMapTiles, Shortbread…) ne donne rien d'utilisable.

```bash
python3 retro_style.py --style mon-style.json --out map.config.new.yaml
```

Le workflow GitHub `retro.yml` fait la même chose sans ligne de commande. Dans l'onglet Actions, choisissez *Retro-engineer config from style* puis Run workflow, avec ces paramètres :

- `style_path` : chemin du style source (défaut : `www/style.json`)
- `config_out` : chemin de sortie (défaut : `map.config.yaml`)
- `overwrite` : `true` pour écraser l'existant

Le YAML généré est commité automatiquement dans le dépôt.

## Référence rapide des champs de `map.config.yaml`

La liste complète, avec les sections `map`, `patterns` et `layers.indoor`, est dans le [README](README.md#modifier-le-style-de-la-carte). Les champs les plus courants :

### Niveau couche

```yaml
layers:
  buildings:
    label: Bâtiments          # nom lisible
    color: "#fce1c5"          # couleur principale (fill ou line)
    border_color: "#d4a574"   # couleur du contour
    appear_at: 13             # zoom minimum d'apparition
    labels_at: 16             # zoom minimum des étiquettes (défaut : appear_at + 3)
    opacity: 0.9              # opacité globale (0.0–1.0)
    visible: true             # false pour masquer
    extrusion_3d: true        # rendu 3D (buildings uniquement)
```

### Niveau sous-type

```yaml
    subtypes:
      forest:
        tag: natural               # tag OSM du filtre
        color: "#add19e"           # couleur du sous-type
        color_private: "#d9ecd2"   # couleur si access=private
        pattern: "military-hatch"  # fill-pattern
        pattern_private: "green-hatch"  # fill-pattern si access=private
        outline_color: "#6fb792"   # couleur du contour
        appear_at: 12              # zoom minimum pour ce sous-type
        opacity: 0.8               # opacité
```

## Tests de non-régression

Après toute modification du style ou de la configuration, lancez :

```bash
python3 -m pytest tests/test_roundtrip.py tests/test_retro_capabilities.py -v
npm run test:validate
```

La première commande vérifie l'aller-retour entre `retro_style.py` et `build_map.py`, la seconde la cohérence entre `style.json`, les PMTiles et les assets.

Le workflow `.github/workflows/tests.yml` les lance aussi sur chaque pull request.

## Installation de l'environnement Python

Les dépendances Python sont listées dans `requirements.txt` :

```bash
pip install -r requirements.txt
```

Cela installe `pyyaml` (lecture de la configuration), `shapely` (calculs géométriques des scripts d'extraction) et `pytest` (tests). Le CI installe le même fichier.

# Spécifications techniques des icônes POI

Ce document décrit les contraintes à respecter pour dessiner une icône locale dans `www/assets/icons/`. Il complète la procédure « Ajouter une icône POI » du README.

## Chaîne de rendu

Comprendre le trajet d'une icône évite la plupart des erreurs :

1. `generate_poi_icons.py` lit `poi.json` et `street_furniture.json`, détecte les types présents et cherche une icône pour chacun, dans l'ordre : fichier local, Temaki, Maki, OSM Liberty. Il écrit le résultat dans `www/poi-icons.json`.
2. Dans le navigateur, `www/poi_icons.js` télécharge le SVG, le passe dans `recolorSvg()`, le dessine sur un canvas de **20 × 20 px** (`ICON_SIZE`), puis l'enregistre dans MapLibre sous le nom `poi-<type>`.
3. MapLibre affiche l'icône entre 70 % et 100 % de cette taille selon le zoom, soit **14 à 20 px** à l'écran.

Une icône locale est donc toujours rastérisée à 20 px, quelle que soit sa taille d'origine. C'est cette taille qu'il faut viser pour la lisibilité.

## Nom du fichier

| Cas | Type généré | Nom de fichier |
| :--- | :--- | :--- |
| Tag principal : `shop`, `amenity`, `tourism`, `craft`, `leisure`, `emergency`, `barrier`… | la **valeur** du tag, ex. `shop=cheese` → `cheese` | `cheese.svg` |
| Sous-type : `cuisine`, `religion`, `vending`, `door` | `<clé>-<valeur>`, ex. `cuisine=pizza` → `cuisine-pizza` | `cuisine-pizza.svg` ou `cuisine_pizza.svg` |
| Clé de présence : `entrance` | la **clé**, quelle que soit la valeur | `entrance.svg` |
| Cas combiné : plusieurs tags à la fois, déclaré dans `COMPOSITE_CASES` de `generate_poi_icons.py` | l'`icon_key` du cas, ex. `amenity=toilets` + `male=yes` + `female=no` → `toilets-male` | `toilets-male.svg` |

Points à connaître :

- Le nom avec tiret est cherché en premier. Si les deux variantes existent, celle avec underscore est ignorée : n'en gardez qu'une.
- Le type est la valeur seule, sans la clé. Deux clés qui partagent une valeur partagent donc la même icône (par exemple `emergency=phone` et un éventuel `amenity=phone`).
- Seule la **première** valeur d'un tag multiple est retenue (`cuisine=pita;durum` donne `cuisine-pita`), à cause de `normalize_multi_values.py`.
- Si le nom du fichier ne peut pas suivre ces règles, ajoutez une entrée dans `CDN_NAME_OVERRIDES` de `generate_poi_icons.py` avec la clé `local`.

## Ordre de priorité à l'affichage

Quand un objet porte plusieurs tags, la première icône disponible l'emporte, dans cet ordre :

1. les cas combinés (`COMPOSITE_CASES`), dans l'ordre de leur déclaration : le premier cas dont toutes les conditions sont remplies l'emporte ;
2. les sous-types (`cuisine`, `religion`, `vending`, `door`) ;
3. les tags principaux, par **ordre alphabétique** de clé (`amenity` avant `emergency` avant `leisure` avant `shop`…) ;
4. les clés de présence (`entrance`) ;
5. l'icône générique `shop` pour tout commerce sans icône propre.

Exemple : une fromagerie avec `cuisine=sandwich` affiche le sandwich, pas le fromage.

Les toilettes utilisent les cas combinés, testés dans cet ordre :

| Conditions (en plus de `amenity=toilets`) | Icône |
| :--- | :--- |
| `toilets:position=urinal` | `toilets-urinal.svg` |
| `female=yes` et `male=no` | `toilets-female.svg` |
| `male=yes` et `female=no` | `toilets-male.svg` |
| `male=yes` et `female=yes` | `toilets-unisex.svg` |

Les valeurs doivent être exactes : `toilets:position=seated;urinal` ou `male=yes` sans `female` ne correspondent à aucun cas et gardent l'icône `toilets`.

## Format du SVG

- **viewBox :** `0 0 14 14` (format des icônes locales existantes) ou `0 0 15 15` (format Maki et Temaki). Indiquez aussi `width` et `height` égaux au viewBox.
- **Marge :** gardez environ 0,5 unité de vide sur chaque bord. Un tracé qui touche le bord est coupé au rendu.
- **Centrage :** centrez visuellement, pas seulement géométriquement. Une forme lourde en bas doit remonter un peu.
- **Fichier épuré :** pas de métadonnées d'éditeur (Inkscape, `sodipodi`, `rdf`), pas d'`id` inutiles, pas de `transform` hérités d'un calque. Un `transform` volontaire (rotation, mise à l'échelle) est accepté.
- **Autonome :** pas d'image intégrée, pas de lien externe, pas de police. Le texte (chiffres, lettres) doit être dessiné en tracés.
- **Identifiants :** un `id` de dégradé n'a besoin d'être unique que dans le fichier. Chaque icône est chargée séparément.

## Couleur

`recolorSvg()` impose la couleur des POI (`ICON_COLOR`, actuellement `#734a08`). La couleur choisie dans le SVG n'a donc aucune importance. Le comportement exact :

| Dans le SVG | Résultat |
| :--- | :--- |
| `currentColor` (n'importe où, y compris `stop-color`) | remplacé par la couleur des POI |
| `fill="…"`, `stroke="…"` | remplacés par la couleur des POI |
| `style="fill:…"`, `style="stroke:…"` | remplacés par la couleur des POI |
| `fill="none"`, `fill="transparent"`, `stroke="none"` | conservés |
| `fill="url(#id)"`, `stroke="url(#id)"` | conservés (dégradés) |
| `opacity`, `fill-opacity`, `stroke-opacity`, `stop-opacity` | conservés |
| aucun `fill` sur la balise `<svg>` | `fill` ajouté avec la couleur des POI |

Conséquences pratiques :

- **Une seule teinte.** Pour hiérarchiser deux éléments, jouez sur l'opacité (par exemple `opacity=".5"`), pas sur la couleur. Exemples : `cuisine_friture.svg`, le fromage de `cuisine-sandwich.svg`.
- **Pas de halo ni de contour blanc.** Un `stroke="#fff"` devient brun et produit une tache épaisse autour de l'icône. Supprimez-le en reprenant une icône externe (cas de `kindergarten.svg`).
- **Les vides sont transparents.** Pour un détail clair sur une forme pleine (trous du fromage, ligne des lèvres), découpez-le avec `fill-rule="evenodd"`. Ne le dessinez pas en blanc.

## Dégradés

Un dégradé est possible en ne faisant varier que l'opacité de la couleur des POI :

```svg
<defs>
  <radialGradient id="g" gradientUnits="userSpaceOnUse" cx="7" cy="9.6" r="8.6">
    <stop offset=".15" stop-color="currentColor"/>
    <stop offset="1" stop-color="currentColor" stop-opacity=".55"/>
  </radialGradient>
</defs>
<path fill="url(#g)" d="…"/>
```

- Utilisez toujours `stop-color="currentColor"`. Une couleur fixe resterait telle quelle et sortirait de la palette de la carte.
- Gardez une opacité minimale d'environ 0,5 : en dessous, la forme se perd sur le fond `#f2efe9`.
- Préférez `gradientUnits="userSpaceOnUse"` pour que plusieurs tracés partagent le même dégradé.
- Exemple complet : `cannabis.svg`.

## Lisibilité à 20 px

À 20 px, une unité d'un viewBox 14 vaut environ 1,4 px.

- **Épaisseur minimale :** 1 unité pour un trait, 0,6 unité pour une découpe en `evenodd`. En dessous, le détail disparaît ou devient flou.
- **Peu de détails :** visez 2 ou 3 éléments lisibles au maximum. La mayo du sandwich a été retirée pour cette raison.
- **Silhouette d'abord :** l'icône doit être reconnaissable en ombre pleine. Testez-la sans ses détails intérieurs.
- **Éviter les confusions :** comparez avec les icônes voisines. Une part de pizza symétrique avec une croûte détachée ressemblait au symbole Wi-Fi ; l'inclinaison a réglé le problème.
- **Traits :** `stroke-linecap="round"` et `stroke-linejoin="round"` rendent mieux que les angles vifs à cette taille.

## Pièges de tracé

- **Sens de tracé et `nonzero` :** deux sous-tracés qui se chevauchent dans le même `<path>`, tracés en sens opposés, laissent un trou à l'intersection. Placez-les dans deux `<path>` distincts, ou utilisez `evenodd` volontairement.
- **`evenodd` et superpositions :** avec `evenodd`, une zone recouverte deux fois devient vide. Réservez-le aux découpes.
- **Rotation :** une forme tournée dépasse souvent du viewBox. Ajoutez une mise à l'échelle (`scale(.9)` autour du centre) et vérifiez les extrémités.

## Licence

Les icônes locales doivent être sous licence **CC0** (voir la section Licences du README) :

- dessin original, ou reprise d'un jeu CC0 (openstreetmap-carto, Temaki, Maki) ;
- pas de reprise ni d'adaptation d'un jeu sous licence avec attribution (Font Awesome Free est en CC BY 4.0) ou sous licence non libre.

## Vérifications avant commit

1. Aperçu du SVG en grand et à **20 × 20 px**, sur le fond `#f2efe9` et dans la couleur `#734a08`.
2. Résolution par le script :

   ```bash
   python3 -c "import generate_poi_icons as g; print(g.check_local('cuisine-pizza'))"
   ```

3. Tests :

   ```bash
   npm test -- tests/unit/poi_icons.test.js
   python3 -m pytest -q
   ```

4. Après le build en CI : le type ne doit plus figurer dans `missing-icons.txt`.

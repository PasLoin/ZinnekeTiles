import argparse
import json
import sys
from pathlib import Path

import yaml

from .catalog import build_variants
from .granulometry import build_granulometry
from .pmtiles import build_pmtiles_params
from .style import build_style
from .variants import VariantError


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--config",      default="map.config.yaml")
    p.add_argument("--style-out",   default="www/style.json")
    p.add_argument("--gran-out",    default="granulometry.json")
    p.add_argument("--pmtiles-out", default="pmtiles_params.json")
    p.add_argument("--only", choices=["style","granulometry","pmtiles"], default=None)
    p.add_argument("--variants",    default=None,
                   help="dossier de variantes (*.yaml) → style.<id>.json + styles.json")
    args = p.parse_args(argv)
    cfg_path = Path(args.config)
    if not cfg_path.exists():
        print(f"✗  {cfg_path} introuvable", file=sys.stderr); sys.exit(1)
    with open(cfg_path) as f:
        config = yaml.safe_load(f)
    print(f"→ {cfg_path}  ({len(config.get('layers',{}))} couches)")
    only = args.only
    if only in (None,"style"):
        s = build_style(config)
        Path(args.style_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.style_out).write_text(json.dumps(s,indent=2,ensure_ascii=False))
        print(f"✓  {args.style_out}  ({len(s['layers'])} layers MapLibre)")
        if args.variants:
            try:
                outputs, manifest = build_variants(config, args.variants, args.style_out)
            except VariantError as e:
                print(f"✗  variante invalide — {e}", file=sys.stderr); sys.exit(1)
            for out, n in outputs:
                print(f"✓  {out}  ({n} layers MapLibre)")
            print(f"✓  {manifest}  ({len(outputs) + 1} styles)")
    if only in (None,"granulometry"):
        g = build_granulometry(config)
        Path(args.gran_out).write_text(json.dumps(g,indent=2,ensure_ascii=False))
        n_rules = sum(len(v.get("rules", [])) + sum(len(r) for r in v.get("files", {}).values())
                      for v in g["layers"].values())
        print(f"✓  {args.gran_out}  ({n_rules} règles)")
    if only in (None,"pmtiles"):
        pm = build_pmtiles_params(config)
        Path(args.pmtiles_out).write_text(json.dumps(pm,indent=2,ensure_ascii=False))
        print(f"✓  {args.pmtiles_out}")
    if only is None:
        print("\nSuite :")
        for s in ["bash generate_json.bash","python3 apply_granulometry.py","bash generate_pmtiles.bash"]:
            print(f"   {s}")

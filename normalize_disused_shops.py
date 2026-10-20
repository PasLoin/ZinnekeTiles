import argparse
import json
import sys

DISUSED_KEY = 'disused:shop'
VACANT = 'vacant'
ACTIVE_KEYS = ('shop', 'amenity', 'tourism', 'craft', 'office', 'healthcare', 'leisure', 'emergency')


def normalize_properties(props):
    if not props.get(DISUSED_KEY):
        return False
    if any(props.get(key) for key in ACTIVE_KEYS):
        return False
    props['shop'] = VACANT
    return True


def normalize_collection(collection):
    changed = 0
    for feat in collection.get('features', []):
        props = feat.get('properties')
        if isinstance(props, dict) and normalize_properties(props):
            changed += 1
    return changed


def normalize_file(path):
    with open(path) as f:
        collection = json.load(f)
    changed = normalize_collection(collection)
    if changed:
        with open(path, 'w') as out:
            json.dump(collection, out, ensure_ascii=False)
    return changed


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('paths', nargs='+')
    args = parser.parse_args(argv)
    for path in args.paths:
        changed = normalize_file(path)
        print(f"  {path} : {changed} {DISUSED_KEY}=* affichés comme shop={VACANT}")
    return 0


if __name__ == '__main__':
    sys.exit(main())

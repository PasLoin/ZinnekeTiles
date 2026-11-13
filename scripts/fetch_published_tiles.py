#!/usr/bin/env python3
import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_BASE = "https://pasloin.github.io/ZinnekeTiles/"


def names_from_params(path):
    data = json.loads(Path(path).read_text())
    return [f"{layer}.pmtiles" for layer in (data.get("layers") or {})]


def names_from_style(path):
    data = json.loads(Path(path).read_text())
    names = []
    for source in (data.get("sources") or {}).values():
        url = source.get("url") or ""
        if url.startswith("pmtiles://"):
            url = url[len("pmtiles://") :]
        name = url.rsplit("/", 1)[-1]
        if name.endswith(".pmtiles"):
            names.append(name)
    return names


def fetch(base, name, dest, timeout):
    target = dest / name
    tmp = target.with_suffix(target.suffix + ".part")
    try:
        with urllib.request.urlopen(base + name, timeout=timeout) as resp, open(tmp, "wb") as out:
            while chunk := resp.read(1 << 20):
                out.write(chunk)
    except (urllib.error.URLError, OSError) as exc:
        tmp.unlink(missing_ok=True)
        return False, str(exc)
    tmp.replace(target)
    return True, f"{target.stat().st_size / 1e6:.1f} Mo"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*")
    ap.add_argument("--params", action="append", default=[])
    ap.add_argument("--style", action="append", default=[])
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--out", default="www")
    ap.add_argument("--timeout", type=float, default=120)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    names = list(args.names)
    for path in args.params:
        names += names_from_params(path)
    for path in args.style:
        names += names_from_style(path)
    names = sorted(set(names))
    if not names:
        print("Aucun fichier à récupérer", file=sys.stderr)
        return 1

    base = args.base if args.base.endswith("/") else args.base + "/"
    dest = Path(args.out)
    dest.mkdir(parents=True, exist_ok=True)

    failed = []
    for name in names:
        ok, info = fetch(base, name, dest, args.timeout)
        print(f"{'✓' if ok else '✗'} {name} ({info})")
        if not ok:
            failed.append(name)

    if failed:
        print(f"{len(failed)}/{len(names)} fichier(s) non récupéré(s) : {', '.join(failed)}")
        return 1 if args.strict else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())

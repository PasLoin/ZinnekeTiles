import json
from pathlib import Path

from .style import build_style
from .variants import DEFAULT_VARIANT, VariantError, load_variant


def variant_files(directory):
    directory = Path(directory)
    if not directory.is_dir():
        return []
    files = sorted(list(directory.glob("*.yaml")) + list(directory.glob("*.yml")))
    stems = [f.stem for f in files]
    duplicates = sorted({s for s in stems if stems.count(s) > 1})
    if duplicates:
        raise VariantError(f"  - identifiants en double dans {directory} : {', '.join(duplicates)}")
    return files


def variant_style_path(style_out, vid):
    style_out = Path(style_out)
    return style_out.with_name(f"{style_out.stem}.{vid}{style_out.suffix}")


def build_manifest(style_out, variants):
    entries = [{**DEFAULT_VARIANT, "url": Path(style_out).name}]
    for v in variants:
        entries.append(
            {"id": v["id"], "label": v["label"], "url": variant_style_path(style_out, v["id"]).name}
        )
    return {"default": DEFAULT_VARIANT["id"], "styles": entries}


def build_variants(config, directory, style_out):
    variants = [load_variant(f) for f in variant_files(directory)]
    outputs = []
    for v in variants:
        try:
            style = build_style(config, v)
        except VariantError as e:
            raise VariantError(f"{v['path']} :\n{e}") from None
        out = variant_style_path(style_out, v["id"])
        out.write_text(json.dumps(style, indent=2, ensure_ascii=False))
        outputs.append((out, len(style["layers"])))
    remove_stale_variants(style_out, {v["id"] for v in variants})
    manifest = Path(style_out).with_name("styles.json")
    manifest.write_text(
        json.dumps(build_manifest(style_out, variants), indent=2, ensure_ascii=False)
    )
    return outputs, manifest


def remove_stale_variants(style_out, keep):
    style_out = Path(style_out)
    removed = []
    for f in style_out.parent.glob(f"{style_out.stem}.*{style_out.suffix}"):
        vid = f.name[len(style_out.stem) + 1 : -len(style_out.suffix)]
        if vid in keep:
            continue
        try:
            meta = json.loads(f.read_text(encoding="utf-8")).get("metadata") or {}
        except (ValueError, OSError):
            continue
        if (meta.get("brussels:variant") or {}).get("id") == vid:
            f.unlink()
            removed.append(f)
    return removed

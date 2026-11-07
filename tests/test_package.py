import json
import pkgutil
import subprocess
import sys
from pathlib import Path

import pytest

import zinneke

ROOT = Path(__file__).resolve().parent.parent

MODULES = sorted(m.name for m in pkgutil.walk_packages(zinneke.__path__, "zinneke."))


@pytest.mark.parametrize("name", MODULES)
def test_module_importable_alone(name):
    code = f"import importlib; importlib.import_module({name!r})"
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_public_api():
    for name in zinneke.__all__:
        assert hasattr(zinneke, name)


def test_cli_entry_points_agree(tmp_path):
    outs = []
    for cmd in ([str(ROOT / "build_map.py")], ["-m", "zinneke"]):
        out = tmp_path / f"{len(outs)}.json"
        subprocess.run(
            [
                sys.executable,
                *cmd,
                "--config",
                str(ROOT / "map.config.yaml"),
                "--only",
                "pmtiles",
                "--pmtiles-out",
                str(out),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        outs.append(json.loads(out.read_text()))
    assert outs[0] == outs[1]

#!/usr/bin/env python3
import importlib.util
import sys

if importlib.util.find_spec("yaml") is None:
    print("✗  pip install pyyaml", file=sys.stderr)
    sys.exit(1)

from zinneke.cli import main

if __name__ == "__main__":
    main()

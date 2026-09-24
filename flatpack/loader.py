"""Run a model file and return the chips it stamps."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

from . import turtle


def load(path) -> turtle.Model:
    path = Path(path).resolve()
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    b = turtle.begin(path.stem)
    try:
        runpy.run_path(str(path), run_name="__flatpack_model__")
    finally:
        turtle.end(b)
    return b.finish()

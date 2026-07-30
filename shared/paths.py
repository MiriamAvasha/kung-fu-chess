"""Bootstrap sys.path for flat repo layout (root + engine domain)."""

from __future__ import annotations

import sys
from pathlib import Path


def add_project_paths(start: Path | None = None) -> Path:
    """
    Ensure both the repo root and engine/ domain root are importable.

    - root: client, server, services, shared, assets, tests
    - engine/: constants, model, rules, GameEngine package, etc.
    """
    if start is None:
        start = Path(__file__).resolve().parent
    else:
        start = start.resolve()

    root = start
    # Walk up until we find the flat layout markers.
    for candidate in [start, *start.parents]:
        if (candidate / 'engine').is_dir() and (candidate / 'server').is_dir():
            root = candidate
            break

    engine_root = root / 'engine'
    for path in (engine_root, root):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)
    return root

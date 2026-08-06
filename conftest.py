"""Make `src/` importable for pytest without requiring an editable install.

Mirrors the sys.path convention already used by the entrypoints in `script/`.
"""
from __future__ import annotations

from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

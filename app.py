"""Streamlit entry at repo root.

Use **Main file path** = `app.py` in Streamlit Community Cloud, or keep
`webmaster-pipeline-dashboard/app.py` — both work.
"""

from __future__ import annotations

import runpy
from pathlib import Path

_TARGET = Path(__file__).resolve().parent / "webmaster-pipeline-dashboard" / "app.py"
if not _TARGET.is_file():
    raise FileNotFoundError(f"Dashboard not found: {_TARGET}")
runpy.run_path(str(_TARGET), run_name="__main__")

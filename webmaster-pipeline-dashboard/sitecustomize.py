"""Прокси для раннего bootstrap: если cwd = эта папка, корневой sitecustomize не в sys.path.

См. ../sitecustomize.py — единственная копия логики.
"""

from __future__ import annotations

import runpy
from pathlib import Path

_root_sc = Path(__file__).resolve().parent.parent / "sitecustomize.py"
if _root_sc.is_file():
    runpy.run_path(str(_root_sc), run_name="_linkbuilding_early_env")

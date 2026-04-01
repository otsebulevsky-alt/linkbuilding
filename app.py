"""Streamlit entry at repo root (Community Cloud: опционально Main file path = `app.py`).

Предпочтительно в Cloud: **Main file path** = `webmaster-pipeline-dashboard/app.py` (без этого шима).
Зависимости — только корневой `requirements.txt` (один манифест, без `-r` на второй файл).
"""

from __future__ import annotations

import os
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_DASH = _ROOT / "webmaster-pipeline-dashboard"
_APP = _DASH / "app.py"

if not _APP.is_file():
    raise FileNotFoundError(f"Dashboard not found: {_APP}")

try:
    os.chdir(_DASH)
except OSError:
    pass

dash_s = str(_DASH)
if dash_s not in sys.path:
    sys.path.insert(0, dash_s)

_spec = spec_from_file_location("streamlit_webmaster_dashboard", _APP)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Cannot load {_APP}")
_mod = module_from_spec(_spec)
# Перезаписываем модуль на каждом прогоне скрипта (как у обычного streamlit run).
sys.modules["streamlit_webmaster_dashboard"] = _mod
_spec.loader.exec_module(_mod)

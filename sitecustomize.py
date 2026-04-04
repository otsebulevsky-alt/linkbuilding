"""Ранний bootstrap для Streamlit Community Cloud (uv + Linux).

Переменные из app.py приходят слишком поздно: при `streamlit run ...` пакет streamlit
и pyarrow/protobuf грузятся раньше пользовательского скрипта → heap abort
(`free(): corrupted unsorted chunks`) до первой строки app.py.

Python автоматически импортирует `sitecustomize`, если модуль найден на sys.path
(обычно cwd = корень клона репозитория на Cloud).

Только os.environ.setdefault — безопасно для unittest/CI из корня репо.
"""

from __future__ import annotations

import os


def _apply() -> None:
    os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
    os.environ.setdefault("MALLOC_ARENA_MAX", "2")
    os.environ.setdefault("PYTHONMALLOC", "malloc")
    for k in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        os.environ.setdefault(k, "1")


_apply()

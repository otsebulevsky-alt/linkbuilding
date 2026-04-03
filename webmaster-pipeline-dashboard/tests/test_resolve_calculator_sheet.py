"""resolve_calculator_sheet_title: граничные случаи без реального API."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lib.sheets_service import get_sheet_title_by_gid, resolve_calculator_sheet_title


class TestResolveCalculatorSheet(unittest.TestCase):
    def test_resolve_none_service(self) -> None:
        title, err = resolve_calculator_sheet_title(None, "1xrjeVD0Q94JI08v2gFvtv1NbiTAbq0fSjv-A-g5pPSs", 0)
        self.assertIsNone(title)
        self.assertIn("не инициализирован", err)

    def test_get_title_none_service(self) -> None:
        self.assertIsNone(get_sheet_title_by_gid(None, "any_id", 0))


if __name__ == "__main__":
    unittest.main()

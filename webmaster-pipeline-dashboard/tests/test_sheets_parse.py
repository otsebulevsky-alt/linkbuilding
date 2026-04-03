"""Парсинг ответа Sheets values.append."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lib.sheets_service import parse_append_updated_range_start_row_0based


class TestParseUpdatedRange(unittest.TestCase):
    def test_range_with_sheet_name(self) -> None:
        self.assertEqual(
            parse_append_updated_range_start_row_0based("'Сбор'!A64:F64"),
            63,
        )

    def test_single_cell(self) -> None:
        self.assertEqual(
            parse_append_updated_range_start_row_0based("Sheet1!Z10"),
            9,
        )


if __name__ == "__main__":
    unittest.main()

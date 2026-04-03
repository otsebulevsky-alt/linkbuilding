"""Дедуп и подсветка цен по домену (логика без Google API)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lib.inbox_sheet_dedupe import exact_duplicate_sheet_rows_to_delete, _price_highlight_for_sheet_rows


class TestExactDuplicateRemoval(unittest.TestCase):
    def test_removes_second_identical_row(self) -> None:
        df = pd.DataFrame(
            [
                ["a.com", "2026-01-01", "$10", "", "x@a.com", "hi"],
                ["a.com", "2026-01-01", "$10", "", "x@a.com", "hi"],
            ],
            columns=["Домен", "дата", "цена", "Цена после торг", "Почта", "F"],
        )
        to_del = exact_duplicate_sheet_rows_to_delete(df)
        self.assertEqual(to_del, [2])

    def test_keeps_one_when_three_identical(self) -> None:
        df = pd.DataFrame(
            [["x.io", "d", "$1", "", "e@x.io", "t"]] * 3,
            columns=["Домен", "дата", "цена", "x", "Почта", "F"],
        )
        to_del = exact_duplicate_sheet_rows_to_delete(df)
        self.assertEqual(sorted(to_del), [2, 3])


class TestPriceHighlight(unittest.TestCase):
    def test_lower_green_higher_red(self) -> None:
        df = pd.DataFrame(
            [
                ["med.com", "$1200", "a@x.com"],
                ["med.com", "$800", "b@x.com"],
            ],
            columns=["Домен", "цена", "Почта"],
        )
        h = _price_highlight_for_sheet_rows(df, "Домен", "цена")
        self.assertEqual(h.get(1), "red")
        self.assertEqual(h.get(2), "green")

    def test_single_row_per_domain_clear(self) -> None:
        df = pd.DataFrame(
            [["only.com", "$50", "a@x.com"]],
            columns=["Домен", "цена", "Почта"],
        )
        h = _price_highlight_for_sheet_rows(df, "Домен", "цена")
        self.assertEqual(h.get(1), "clear")


if __name__ == "__main__":
    unittest.main()

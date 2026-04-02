"""Unit tests for trade_bargain helpers."""

from __future__ import annotations

import unittest

from lib.trade_bargain import (
    cell_matches_responsible,
    collect_responsible_needles,
    normalize_domain_cell,
    parse_price_number,
)


class FakeCfg:
    trade_responsible_name = "Oleg Tsebulevskiy"
    linkbuilder_filter = "Олег"
    linkbuilder_aliases = ["Oleg", "oleg"]


class TestTradeBargain(unittest.TestCase):
    def test_normalize_domain(self) -> None:
        self.assertEqual(normalize_domain_cell("HTTPS://Example.COM/path"), "example.com")
        self.assertEqual(normalize_domain_cell("www.foo.io"), "foo.io")

    def test_parse_price(self) -> None:
        self.assertEqual(parse_price_number("100"), 100.0)
        self.assertEqual(parse_price_number("$250"), 250.0)
        self.assertEqual(parse_price_number("1,234.50"), 1234.5)
        self.assertIsNone(parse_price_number(""))

    def test_needles_and_match(self) -> None:
        cfg = FakeCfg()
        needles = collect_responsible_needles(cfg)
        self.assertTrue(any("Tsebulevskiy" in n for n in needles))
        self.assertTrue(cell_matches_responsible("Oleg Tsebulevskiy", needles))
        self.assertFalse(cell_matches_responsible("Someone Else", needles))


if __name__ == "__main__":
    unittest.main()

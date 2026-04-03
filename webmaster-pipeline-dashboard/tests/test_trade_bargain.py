"""Unit tests for trade_bargain helpers."""

from __future__ import annotations

import unittest

import pandas as pd

from lib.trade_bargain import (
    cell_matches_responsible,
    collect_responsible_needles,
    find_webmaster_email_in_inbox_log,
    normalize_domain_cell,
    parse_calc_trade_date_to_ymd,
    parse_price_number,
    resolve_calc_trade_date_col,
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

    def test_find_email_sorts_by_ymd_from_mail_sync(self) -> None:
        """Колонка «дата» в «Сбор с ответов» — ГГГГ-ММ-ДД (дата синка); берём самую свежую почту по домену."""
        df = pd.DataFrame(
            [
                {"Домен": "a.com", "дата": "2026-04-01", "Почта": "old@x.com"},
                {"Домен": "a.com", "дата": "2026-04-03", "Почта": "new@x.com"},
            ]
        )
        self.assertEqual(find_webmaster_email_in_inbox_log(df, "a.com"), "new@x.com")

    def test_find_email_ddm_yyyy(self) -> None:
        df = pd.DataFrame(
            [
                {"Домен": "b.io", "дата": "01.03.2026", "Почта": "first@y.com"},
                {"Домен": "b.io", "дата": "15.03.2026", "Почта": "last@y.com"},
            ]
        )
        self.assertEqual(find_webmaster_email_in_inbox_log(df, "b.io"), "last@y.com")

    def test_find_email_english_date_header(self) -> None:
        df = pd.DataFrame(
            [
                {"Домен": "c.org", "Date": "2026-02-01", "Почта": "a@c.org"},
                {"Домен": "c.org", "Date": "2026-02-10", "Почта": "b@c.org"},
            ]
        )
        self.assertEqual(find_webmaster_email_in_inbox_log(df, "c.org"), "b@c.org")

    def test_resolve_trade_date_explicit_comment_column(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Domain": "x.com",
                    "Цена, $": 10,
                    "Ответственный": "Oleg",
                    "Комментарий (Денис)": "2026-04-03",
                    "Дата проверки": "",
                }
            ]
        )
        col = resolve_calc_trade_date_col(df, "Комментарий (Денис)")
        self.assertEqual(col, "Комментарий (Денис)")

    def test_parse_calc_trade_date_flexible(self) -> None:
        self.assertEqual(parse_calc_trade_date_to_ymd("30.03.2026"), (2026, 3, 30))
        self.assertEqual(parse_calc_trade_date_to_ymd("2026-03-30"), (2026, 3, 30))
        self.assertEqual(parse_calc_trade_date_to_ymd("2026 03 30"), (2026, 3, 30))
        self.assertEqual(parse_calc_trade_date_to_ymd("2024 04 03"), (2024, 4, 3))
        self.assertIsNone(parse_calc_trade_date_to_ymd(""))
        self.assertIsNone(parse_calc_trade_date_to_ymd("not a date"))


if __name__ == "__main__":
    unittest.main()

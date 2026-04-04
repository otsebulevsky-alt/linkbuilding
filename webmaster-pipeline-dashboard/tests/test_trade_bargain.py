"""Unit tests for trade_bargain helpers."""

from __future__ import annotations

import unittest

import pandas as pd

from lib.trade_bargain import (
    calc_trade_date_is_in_window,
    cell_matches_responsible,
    collect_responsible_needles,
    discover_calculator_dataframe_from_rows,
    extract_first_email_from_inbox_cell,
    find_webmaster_email_in_inbox_log,
    normalize_domain_cell,
    parse_calc_trade_date_to_ymd,
    parse_price_number,
    resolve_calc_domain_col,
    resolve_calc_price_col,
    resolve_calc_responsible_col,
    resolve_calc_trade_date_col,
    _pad_rows_to_max_width,
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

    def test_extract_email_when_cell_has_reply_text_after_address(self) -> None:
        cell = (
            "camilanascimento98@gmail.com Could you please let us know if payment "
            "via cryptocurrency (e.g. USDT) or PayPal would be possible?"
        )
        self.assertEqual(extract_first_email_from_inbox_cell(cell), "camilanascimento98@gmail.com")

    def test_find_email_strips_trailing_reply_text(self) -> None:
        """Как в «Сбор с ответов»: в одной ячейке email + текст вебмастера — в IMAP уходит только email."""
        df = pd.DataFrame(
            [
                {
                    "Домен": "panafricafootball.com",
                    "дата": "2026-04-03",
                    "Почта": "camilanascimento98@gmail.com Could you please let us know if payment via PayPal would be possible?",
                },
            ]
        )
        self.assertEqual(
            find_webmaster_email_in_inbox_log(df, "panafricafootball.com"),
            "camilanascimento98@gmail.com",
        )

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

    def test_resolve_empty_prefers_comment_denys_over_dата_проверки(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Domain": "x.com",
                    "Дата проверки": "2020-01-01",
                    "Комментарий (Денис)": "2026-04-03",
                }
            ]
        )
        self.assertEqual(resolve_calc_trade_date_col(df, ""), "Комментарий (Денис)")

    def test_resolve_explicit_wrong_falls_back_to_heuristic(self) -> None:
        df = pd.DataFrame([{"Дата проверки": "2026-01-01", "Комментарий (Денис)": "2026-04-03"}])
        self.assertEqual(
            resolve_calc_trade_date_col(df, "Такого столбца нет"),
            "Комментарий (Денис)",
        )

    def test_resolve_trade_date_english_date_column(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Domain": "x.com",
                    "Price": 80,
                    "Responsible": "Oleg",
                    "Date": "2026 04 03",
                }
            ]
        )
        self.assertEqual(resolve_calc_trade_date_col(df, ""), "Date")

    def test_resolve_trade_date_truncated_comment_header(self) -> None:
        """Как в узкой колонке Sheets: «Комментарий (Де)» без «нис»."""
        df = pd.DataFrame(
            columns=["Domain", "Цена, $", "Ответственный", "Комментарий (Де)"],
        )
        col = resolve_calc_trade_date_col(df, "Комментарий (Денис)")
        self.assertEqual(col, "Комментарий (Де)")

    def test_discover_header_after_preamble_rows(self) -> None:
        rows = [
            ["[ВНУТРЕННИЙ] Калькулятор доноров"],
            [],
            ["Domain", "Цена, $", "Ответственный", "Комментарий (Денис)"],
            ["x.com", 80, "Oleg", "2026-04-03"],
        ]
        df, hi = discover_calculator_dataframe_from_rows(rows, "Комментарий (Денис)")
        self.assertEqual(hi, 2)
        self.assertEqual(resolve_calc_price_col(df), "Цена, $")
        self.assertEqual(resolve_calc_trade_date_col(df, "Комментарий (Денис)"), "Комментарий (Денис)")

    def test_discover_header_after_row_index_80(self) -> None:
        """Шапка ниже «старого» лимита 80 строк — раньше такие листы не распознавались."""
        rows: list[list] = [["noise"]] * 90
        rows.append(
            ["Domain", "Цена, $", "Ответственный", "Комментарий (Денис)"],
        )
        rows.append(["x.com", 80, "Oleg Tsebulevskiy", "2026-04-03"])
        df, hi = discover_calculator_dataframe_from_rows(rows, "Комментарий (Денис)")
        self.assertEqual(hi, 90)
        self.assertEqual(resolve_calc_responsible_col(df), "Ответственный")

    def test_resolve_calc_responsible_explicit_header(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Domain": "a.org",
                    "Цена, $": 10,
                    "RB": "Oleg",
                    "Комментарий (Денис)": "2026-04-03",
                }
            ]
        )
        self.assertIsNone(resolve_calc_responsible_col(df))
        self.assertEqual(resolve_calc_responsible_col(df, "RB"), "RB")

    def test_resolve_responsible_zwsp_in_header(self) -> None:
        """ZWSP в заголовке ломал подстроку «ответствен»."""
        dirty = "Ответ\u200bственный"
        df = pd.DataFrame(columns=["Domain", "Цена, $", dirty, "Комментарий (Денис)"])
        self.assertEqual(resolve_calc_responsible_col(df), dirty)

    def test_resolve_responsible_fallback_column_m_placeholder(self) -> None:
        """Как у Sheets API: 13-й столбец без текста → _c12; типичный Telecomasia layout."""
        cols = [
            "Domain",
            "DR",
            "Traffic",
            "RD",
            "LD",
            "RD/LD",
            "Стагнация",
            "Цена, $",
            "Ссылки",
            "Балл",
            "Вывод",
            "Гео",
            "_c12",
            "Комментарий (Денис)",
        ]
        df = pd.DataFrame(columns=cols)
        self.assertEqual(resolve_calc_responsible_col(df), "_c12")

    def test_pad_rows_header_extends_to_data_width(self) -> None:
        header = ["Domain", "Цена, $", "Ответственный", "Комментарий (Денис)"]
        data = ["x.com", 10, "Oleg", "2026-04-03", "extra"]
        rows = _pad_rows_to_max_width([header, data])
        self.assertEqual(len(rows[0]), 5)
        self.assertEqual(len(rows[1]), 5)

    def test_price_column_not_blocked_by_sold_like_header(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Domain": "a.com",
                    "sold": 0,
                    "Цена, $": 50,
                    "Ответственный": "Oleg",
                    "Комментарий (Денис)": "2026-04-03",
                }
            ]
        )
        self.assertEqual(resolve_calc_price_col(df), "Цена, $")

    def test_resolve_calc_columns_telecomasia_like(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Domain": "a.org",
                    "DR": 50,
                    "Traffic": 1000,
                    "Цена, $": 80,
                    "Ответственный": "Oleg Tsebulovskiy",
                    "Комментарий (Денис)": "2026 04 03",
                }
            ]
        )
        self.assertEqual(resolve_calc_domain_col(df), "Domain")
        self.assertEqual(resolve_calc_price_col(df), "Цена, $")
        self.assertEqual(resolve_calc_responsible_col(df), "Ответственный")
        self.assertEqual(resolve_calc_trade_date_col(df, "Комментарий (Денис)"), "Комментарий (Денис)")

    def test_calc_trade_date_window(self) -> None:
        self.assertTrue(calc_trade_date_is_in_window((2026, 4, 3), (2026, 4, 3), 0))
        self.assertFalse(calc_trade_date_is_in_window((2026, 4, 2), (2026, 4, 3), 0))
        self.assertTrue(calc_trade_date_is_in_window((2026, 4, 2), (2026, 4, 3), 7))
        self.assertFalse(calc_trade_date_is_in_window((2026, 3, 1), (2026, 4, 3), 30))
        self.assertFalse(calc_trade_date_is_in_window((2026, 4, 10), (2026, 4, 3), 30))

    def test_parse_calc_trade_date_flexible(self) -> None:
        self.assertEqual(parse_calc_trade_date_to_ymd("30.03.2026"), (2026, 3, 30))
        self.assertEqual(parse_calc_trade_date_to_ymd("2026-03-30"), (2026, 3, 30))
        self.assertEqual(parse_calc_trade_date_to_ymd("2026 03 30"), (2026, 3, 30))
        self.assertEqual(parse_calc_trade_date_to_ymd("2026 04 03"), (2026, 4, 3))
        self.assertEqual(parse_calc_trade_date_to_ymd("2024 04 03"), (2024, 4, 3))
        self.assertIsNone(parse_calc_trade_date_to_ymd(""))
        self.assertIsNone(parse_calc_trade_date_to_ymd("not a date"))


if __name__ == "__main__":
    unittest.main()

"""Tests for EEAT HTML checks (weekly-outreach parity)."""

from __future__ import annotations

import unittest

from lib.eeat_page_check import (
    exact_target_url_on_page,
    has_author_link_in_html,
    normalize_anchor_text,
    normalize_url_for_match,
    run_eeat_html_checks,
    verify_outgoing_link_and_anchor_pair,
)


class TestEeatPageCheck(unittest.TestCase):
    def test_normalize_url_trailing_slash(self) -> None:
        a = normalize_url_for_match("https://WWW.Example.COM/post/")
        b = normalize_url_for_match("https://example.com/post")
        self.assertEqual(a, b)

    def test_exact_target_on_page(self) -> None:
        html = '<a href="https://telecomasia.net/go">click</a>'
        self.assertTrue(
            exact_target_url_on_page(html, "https://www.telecomasia.net/go/")
        )

    def test_author_link_marker_in_anchor_text(self) -> None:
        html = '<p>By <a href="https://x.com/y">Alisa Author</a></p>'
        self.assertTrue(has_author_link_in_html(html, ["alisa"]))

    def test_run_eeat_mention_in_plain(self) -> None:
        html = "<p>Text by алиса here</p>"
        r = run_eeat_html_checks(html, ["алиса"])
        self.assertTrue(r["eeat_mention"])
        self.assertFalse(r["eeat_author_link"])

    def test_run_eeat_empty_html_with_markers(self) -> None:
        """Публикации: при пустом body проверка EEAT даёт False/False, а не «пропуск»."""
        r = run_eeat_html_checks("", ["алиса"])
        self.assertFalse(r["eeat_mention"])
        self.assertFalse(r["eeat_author_link"])

    def test_normalize_anchor_nbsp(self) -> None:
        self.assertEqual(normalize_anchor_text("a\u00a0b"), "a b")

    def test_placement_pair_href_and_anchor_ok(self) -> None:
        html = '<p><a href="https://www.example.com/page/">betway app download</a></p>'
        r = verify_outgoing_link_and_anchor_pair(
            html,
            outgoing_url="https://example.com/page",
            anchor_text="betway app download",
            anchor_case_insensitive=False,
        )
        self.assertTrue(r["placement_pair_ok"])
        self.assertTrue(r["href_found"])

    def test_placement_pair_wrong_anchor(self) -> None:
        html = '<a href="https://x.com/y">other text</a>'
        r = verify_outgoing_link_and_anchor_pair(
            html,
            outgoing_url="https://x.com/y",
            anchor_text="wanted anchor",
            anchor_case_insensitive=False,
        )
        self.assertFalse(r["placement_pair_ok"])
        self.assertTrue(r["href_found"])
        self.assertEqual(r["detail"], "anchor_mismatch")

    def test_placement_pair_case_insensitive_anchor(self) -> None:
        html = '<a href="https://x.com/">BetWay</a>'
        r = verify_outgoing_link_and_anchor_pair(
            html,
            outgoing_url="https://x.com/",
            anchor_text="betway",
            anchor_case_insensitive=True,
        )
        self.assertTrue(r["placement_pair_ok"])


if __name__ == "__main__":
    unittest.main()

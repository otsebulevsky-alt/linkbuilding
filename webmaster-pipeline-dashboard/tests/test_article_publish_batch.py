"""Tests for article publish email HTML builder."""

from __future__ import annotations

import unittest

from lib.article_publish_batch import build_article_publish_email_html


class TestArticlePublishBatch(unittest.TestCase):
    def test_bilingual_body_contains_link(self) -> None:
        html = build_article_publish_email_html("https://example.com/post", "100")
        self.assertIn("Hello", html)
        self.assertIn("Здравствуйте", html)
        self.assertIn("https://example.com/post", html)
        self.assertIn("100", html)

    def test_plain_article_text(self) -> None:
        html = build_article_publish_email_html("Draft title only", "")
        self.assertIn("Draft title only", html)
        self.assertIn("as discussed", html.lower())
        self.assertIn("по согласованию", html)


if __name__ == "__main__":
    unittest.main()

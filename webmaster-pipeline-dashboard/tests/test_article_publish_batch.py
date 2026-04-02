"""Tests for article publish email HTML builder."""

from __future__ import annotations

import unittest

from lib.article_publish_batch import build_article_publish_email_html, is_google_docs_or_drive_url


class TestArticlePublishBatch(unittest.TestCase):
    def test_bilingual_body_contains_link(self) -> None:
        doc = "https://docs.google.com/document/d/abc/edit"
        html = build_article_publish_email_html(doc, "100")
        self.assertIn("Hello", html)
        self.assertIn("Здравствуйте", html)
        self.assertIn("docs.google.com", html)
        self.assertIn("Пожалуйста, разместите нашу статью", html)
        self.assertIn("100", html)

    def test_plain_article_text(self) -> None:
        html = build_article_publish_email_html("Draft title only", "")
        self.assertIn("Draft title only", html)
        self.assertIn("as discussed", html.lower())
        self.assertIn("по согласованию", html)

    def test_is_google_doc_url(self) -> None:
        self.assertTrue(
            is_google_docs_or_drive_url("https://docs.google.com/document/d/1EBNiXXXX/edit")
        )
        self.assertTrue(is_google_docs_or_drive_url("https://drive.google.com/file/d/xxx/view"))
        self.assertFalse(is_google_docs_or_drive_url("https://published-site.com/post"))
        self.assertFalse(is_google_docs_or_drive_url(""))


if __name__ == "__main__":
    unittest.main()

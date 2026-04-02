"""Unit tests for Gmail thread reply header helpers."""

from __future__ import annotations

import email
import unittest

from lib.mail_thread_lookup import _build_references, _normalize_msg_id


class TestMailThreadLookup(unittest.TestCase):
    def test_normalize_msg_id_adds_brackets(self) -> None:
        self.assertEqual(_normalize_msg_id("abc@mail.gmail.com"), "<abc@mail.gmail.com>")
        self.assertEqual(_normalize_msg_id("<x@y>"), "<x@y>")

    def test_build_references_appends_current_mid(self) -> None:
        raw = (
            b"Message-ID: <last@example.com>\r\n"
            b"References: <a@b> <c@d>\r\n"
            b"\r\n"
        )
        msg = email.message_from_bytes(raw)
        refs = _build_references(msg)
        self.assertIn("<a@b>", refs)
        self.assertIn("<c@d>", refs)
        self.assertIn("<last@example.com>", refs)
        self.assertTrue(refs.endswith("<last@example.com>"))

    def test_build_references_no_dup_if_mid_already_in_chain(self) -> None:
        raw = (
            b"Message-ID: <same@example.com>\r\n"
            b"References: <a@b> <same@example.com>\r\n"
            b"\r\n"
        )
        msg = email.message_from_bytes(raw)
        refs = _build_references(msg)
        self.assertEqual(refs.count("<same@example.com>"), 1)


if __name__ == "__main__":
    unittest.main()

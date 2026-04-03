"""Unit tests for Gmail thread reply header helpers."""

from __future__ import annotations

import email
import unittest

from lib.mail_thread_lookup import (
    _build_references,
    _extract_last_quoted_mailbox_from_list_row,
    _headers_mention_domain,
    _mailbox_arg_for_imap,
    _mailboxes_for_thread_search,
    _normalize_msg_id,
)


class _FakeImapList:
    """Минимальная заглушка: только list() для _mailboxes_for_thread_search."""

    def __init__(self, rows: list[bytes]) -> None:
        self._rows = rows

    def list(self) -> tuple[str, list[bytes]]:
        return "OK", self._rows


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

    def test_headers_mention_domain_in_subject(self) -> None:
        raw = (
            b"Subject: Content collaboration idea for panafricafootball.com\r\n"
            b"From: x@y.com\r\n"
            b"\r\n"
        )
        msg = email.message_from_bytes(raw)
        self.assertTrue(_headers_mention_domain(msg, "panafricafootball.com"))
        self.assertFalse(_headers_mention_domain(msg, "other.org"))

    def test_headers_mention_domain_www_variant(self) -> None:
        raw = b"Subject: Re: offer for www.example.com\r\nMessage-ID: <a@b>\r\n\r\n"
        msg = email.message_from_bytes(raw)
        self.assertTrue(_headers_mention_domain(msg, "example.com"))

    def test_mailboxes_without_imap_only_primary(self) -> None:
        """Без сессии IMAP нет LIST — только основной ящик (нет хардкода [Gmail]/All Mail)."""
        m = _mailboxes_for_thread_search("INBOX", None)
        self.assertEqual(m, ["INBOX"])

    def test_mailboxes_with_imap_sent_then_all(self) -> None:
        """После INBOX идут папки \\Sent, затем \\All (исходящие с доменом в теме — в Sent)."""
        fake = _FakeImapList(
            [
                rb'(\HasNoChildren \All) "/" "[Gmail]/All Mail"',
                rb'(\HasNoChildren \Sent) "/" "[Gmail]/Sent Mail"',
            ]
        )
        m = _mailboxes_for_thread_search("INBOX", fake)
        self.assertEqual(m, ["INBOX", "[Gmail]/Sent Mail", "[Gmail]/All Mail"])

    def test_extract_quoted_mailbox_from_list_row_ascii(self) -> None:
        row = rb'(\HasNoChildren \All) "/" "[Gmail]/All Mail"'
        self.assertEqual(_extract_last_quoted_mailbox_from_list_row(row), "[Gmail]/All Mail")

    def test_extract_quoted_mailbox_preserves_modified_utf7(self) -> None:
        row = rb'(\All) "/" "[Gmail]/&BBIQSQZAAEEQQQBDgGo-"'
        name = _extract_last_quoted_mailbox_from_list_row(row)
        self.assertIsNotNone(name)
        self.assertTrue(name.startswith("[Gmail]/"))

    def test_mailbox_arg_inbox_atom(self) -> None:
        self.assertEqual(_mailbox_arg_for_imap("INBOX"), "INBOX")
        self.assertEqual(_mailbox_arg_for_imap("inbox"), "inbox")

    def test_mailbox_arg_gmail_sent_quoted(self) -> None:
        w = _mailbox_arg_for_imap("[Gmail]/Sent Mail")
        self.assertTrue(w.startswith('"'))
        self.assertTrue(w.endswith('"'))
        self.assertIn("[Gmail]/Sent Mail", w)


if __name__ == "__main__":
    unittest.main()

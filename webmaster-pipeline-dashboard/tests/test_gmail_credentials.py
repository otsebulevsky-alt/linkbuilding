"""Пароли Gmail из Secrets: заглушки и fallback IMAP/SMTP."""

from __future__ import annotations

import unittest

from lib.gmail_credentials import (
    is_placeholder_gmail_app_password,
    resolve_imap_user_password,
    resolve_smtp_host_port_user_password,
)


class GmailCredentialsTest(unittest.TestCase):
    def test_placeholder_x_only(self) -> None:
        self.assertTrue(is_placeholder_gmail_app_password(""))
        self.assertTrue(is_placeholder_gmail_app_password("xxxx"))
        self.assertTrue(is_placeholder_gmail_app_password("xxxx xxxx xxxx xxxx"))
        self.assertTrue(is_placeholder_gmail_app_password("  XXxx  "))
        self.assertFalse(is_placeholder_gmail_app_password("abcdabcdabcdabcd"))
        self.assertFalse(is_placeholder_gmail_app_password("xxxx1234"))

    def test_imap_falls_back_when_imap_is_placeholder(self) -> None:
        sec = {
            "GMAIL_SMTP_USER": "a@b.c",
            "GMAIL_SMTP_APP_PASSWORD": "realpass",
            "GMAIL_IMAP_APP_PASSWORD": "xxxx xxxx xxxx xxxx",
        }
        u, p = resolve_imap_user_password(sec)
        self.assertEqual(u, "a@b.c")
        self.assertEqual(p, "realpass")

    def test_imap_prefers_real_imap_password(self) -> None:
        sec = {
            "GMAIL_SMTP_USER": "a@b.c",
            "GMAIL_SMTP_APP_PASSWORD": "smtp",
            "GMAIL_IMAP_APP_PASSWORD": "imapreal",
        }
        u, p = resolve_imap_user_password(sec)
        self.assertEqual(p, "imapreal")

    def test_smtp_falls_back_when_smtp_is_placeholder(self) -> None:
        sec = {
            "GMAIL_SMTP_USER": "a@b.c",
            "GMAIL_SMTP_APP_PASSWORD": "xxxx xxxx xxxx xxxx",
            "GMAIL_IMAP_APP_PASSWORD": "onlyimap",
        }
        h, port, u, p = resolve_smtp_host_port_user_password(sec)
        self.assertEqual(p, "onlyimap")
        self.assertEqual(u, "a@b.c")
        self.assertEqual(port, 587)


if __name__ == "__main__":
    unittest.main()

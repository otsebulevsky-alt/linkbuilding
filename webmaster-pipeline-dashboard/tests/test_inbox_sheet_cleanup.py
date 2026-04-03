"""Строки «Сбор с ответов»: шум = bounce / только наш шаблон оплаты (не «только email» — см. IMAP-синк)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pandas as pd

from lib.inbox_sheet_cleanup import inbox_log_row_is_removable_noise, mail_cell_is_inbox_noise


_BOUNCE_SNIPPET = (
    "Address not found. Your message wasn't delivered to notification@slack.com "
    "because the address couldn't be found or is unable to receive email."
)


class TestMailCellNoise(unittest.TestCase):
    def test_template_en_with_email_prefix(self) -> None:
        cell = (
            "james@mail.hur Could you please let us know if payment via cryptocurrency "
            "(e.g. USDT) or PayPal would be possible?"
        )
        self.assertTrue(mail_cell_is_inbox_noise(cell))

    def test_template_ru(self) -> None:
        cell = (
            "notification@example.com Подскажите, пожалуйста, есть ли возможность оплатить криптовалютой "
            "(например, USDT) или через PayPal?"
        )
        self.assertTrue(mail_cell_is_inbox_noise(cell))

    def test_email_only_from_imap_sync_not_noise(self) -> None:
        """Синк пишет в «Почта» только from_addr — такие строки нельзя считать шумом целиком."""
        self.assertFalse(mail_cell_is_inbox_noise("hi@managementworksmedia.com"))
        self.assertFalse(mail_cell_is_inbox_noise("info@moneydisquantified.org"))

    def test_bounce_delivery_text_is_noise(self) -> None:
        self.assertTrue(mail_cell_is_inbox_noise(_BOUNCE_SNIPPET))

    def test_row_noise_by_domain_column(self) -> None:
        row = pd.Series({"Домен": "hunter.io", "Почта": "x@y.com"})
        self.assertTrue(
            inbox_log_row_is_removable_noise(
                row, mail_col="Почта", domain_col="Домен"
            )
        )

    def test_imap_sync_row_email_only_kept(self) -> None:
        row = pd.Series({"Домен": "example-blog.com", "Почта": "webmaster@example-blog.com"})
        self.assertFalse(
            inbox_log_row_is_removable_noise(
                row, mail_col="Почта", domain_col="Домен"
            )
        )

    def test_real_reply_not_noise(self) -> None:
        cell = (
            "jacob.mallinder@universalmedia365.com We do accept Guest Posts. "
            "Our usual cost is £265.00 GBP + VAT per article."
        )
        self.assertFalse(mail_cell_is_inbox_noise(cell))

    def test_empty_not_noise(self) -> None:
        self.assertFalse(mail_cell_is_inbox_noise(""))
        self.assertFalse(mail_cell_is_inbox_noise("   "))


if __name__ == "__main__":
    unittest.main()

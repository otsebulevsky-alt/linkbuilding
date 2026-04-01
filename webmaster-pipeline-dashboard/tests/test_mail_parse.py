"""Regression checks for webmaster reply parsing (stdlib unittest, no pytest)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lib.mail_parse import domain_from_subject, extract_all_domains
from lib.payment_match import payment_draft_for_message, payment_reply_language


class TestSubjectDomainMarketingMedian(unittest.TestCase):
    def test_plain_subject(self) -> None:
        s = "Content collaboration idea for marketingmedian.com"
        self.assertEqual(domain_from_subject(s), "marketingmedian.com")
        self.assertEqual(extract_all_domains(s, ""), ["marketingmedian.com"])

    def test_re_fwd_prefixes(self) -> None:
        base = "Content collaboration idea for marketingmedian.com"
        for prefix in ("Re: ", "Fwd: ", "RE: "):
            self.assertEqual(domain_from_subject(prefix + base), "marketingmedian.com")


class TestYourWebsiteSubjectPattern(unittest.TestCase):
    def test_interest_collaborating_your_website(self) -> None:
        s = "Interest in collaborating with your website banglarrbhumi.com"
        self.assertEqual(domain_from_subject(s), "banglarrbhumi.com")
        self.assertEqual(extract_all_domains(s, ""), ["banglarrbhumi.com"])


class TestMobidictumCollaborationInbox(unittest.TestCase):
    """Сценарий из входящих: тема «… for mobidictum.com», EN-тело без оплаты."""

    _SUBJ = "Content collaboration idea for mobidictum.com"
    _BODY = (
        "Hello Oleg,\n\n"
        "Thanks for reaching out. We can cover it on our main website, social media, and newsletter.\n\n"
        "Best regards"
    )

    def test_domain_from_subject(self) -> None:
        self.assertEqual(domain_from_subject(self._SUBJ), "mobidictum.com")
        self.assertEqual(extract_all_domains(self._SUBJ, self._BODY), ["mobidictum.com"])

    def test_re_prefix_still_extracts_domain(self) -> None:
        s = "Re: " + self._SUBJ
        self.assertEqual(domain_from_subject(s), "mobidictum.com")

    def test_english_no_payment_yields_en_followup_draft(self) -> None:
        self.assertEqual(payment_reply_language(self._SUBJ, self._BODY), "en")
        our = {"paypal", "crypto", "card"}
        draft = payment_draft_for_message(
            our_canonicals=our, subject=self._SUBJ, body=self._BODY
        )
        self.assertIn("PayPal", draft)
        self.assertIn("cryptocurrency", draft)
        self.assertNotRegex(draft, r"[а-яА-ЯёЁ]")


if __name__ == "__main__":
    unittest.main()

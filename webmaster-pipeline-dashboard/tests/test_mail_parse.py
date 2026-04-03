"""Regression checks for webmaster reply parsing (stdlib unittest, no pytest)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lib.mail_parse import (
    domain_from_subject,
    extract_all_domains,
    extract_candidate_hosts,
    is_automated_bounce_message,
    is_budget_inquiry_message,
    is_non_webmaster_platform_host,
)
from lib.payment_match import (
    is_our_payment_followup_template_only,
    payment_draft_for_message,
    payment_reply_language,
)


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


class TestBudgetInquiryDetection(unittest.TestCase):
    def test_what_is_your_budget_en(self) -> None:
        self.assertTrue(
            is_budget_inquiry_message(subject="Re: collab", body="What is your budget")
        )

    def test_crypto_reply_not_budget_ask(self) -> None:
        self.assertFalse(
            is_budget_inquiry_message(subject="Re: x", body="We accept Crypto currency")
        )

    def test_russian_budget(self) -> None:
        self.assertTrue(
            is_budget_inquiry_message(subject="", body="Подскажите, какой бюджет?")
        )


class TestNonWebmasterPlatformHosts(unittest.TestCase):
    def test_github_and_slack_suffixes(self) -> None:
        self.assertTrue(is_non_webmaster_platform_host("github.com"))
        self.assertTrue(is_non_webmaster_platform_host("docs.github.com"))
        self.assertTrue(is_non_webmaster_platform_host("rantsports.slack.com"))

    def test_real_donor_not_flagged(self) -> None:
        self.assertFalse(is_non_webmaster_platform_host("lawyer-monthly.com"))
        self.assertFalse(is_non_webmaster_platform_host("mobidictum.com"))

    def test_subject_github_yields_empty_extract(self) -> None:
        s = "Re: Content collaboration idea for github.com"
        self.assertIsNone(domain_from_subject(s))
        self.assertEqual(extract_all_domains(s, ""), [])

    def test_mixed_subject_and_github_url(self) -> None:
        subj = "Content collaboration idea for mobidictum.com"
        body = "See https://github.com/org/repo"
        self.assertEqual(extract_candidate_hosts(subj, body), ["mobidictum.com", "github.com"])
        self.assertEqual(extract_all_domains(subj, body), ["mobidictum.com"])


class TestAutomatedBounceDetection(unittest.TestCase):
    def test_mailer_daemon_address(self) -> None:
        self.assertTrue(
            is_automated_bounce_message(
                from_header="Mail Delivery Subsystem <mailer-daemon@googlemail.com>",
                from_addr="mailer-daemon@googlemail.com",
                subject="Address not found",
                body="Your message wasn't delivered to notification@slack.com",
            )
        )

    def test_bounce_body_gmail_style(self) -> None:
        self.assertTrue(
            is_automated_bounce_message(
                from_header="",
                from_addr="",
                subject="New messages from x in Rantsports",
                body=(
                    "Address not found\n\n"
                    "Your message wasn't delivered to notification@slack.com because "
                    "the address couldn't be found or is unable to receive email."
                ),
            )
        )

    def test_normal_webmaster_not_bounce(self) -> None:
        self.assertFalse(
            is_automated_bounce_message(
                from_header="Jacob <j@example.com>",
                from_addr="j@example.com",
                subject="Re: Guest post",
                body="We accept guest posts for £265 + VAT.",
            )
        )


class TestPaymentTemplateNoiseFilter(unittest.TestCase):
    """Исходящий шаблон USDT/PayPal не должен попадать в «Сбор с ответов» как ответ вебмастера."""

    def test_english_template_only_is_noise(self) -> None:
        body = (
            "Could you please let us know if payment via cryptocurrency (e.g. USDT) "
            "or PayPal would be possible?\n\n--\nSent from Gmail"
        )
        self.assertTrue(is_our_payment_followup_template_only(body=body))

    def test_russian_template_only_is_noise(self) -> None:
        body = (
            "Подскажите, пожалуйста, есть ли возможность оплатить криптовалютой "
            "(например, USDT) или через PayPal?\n\nС уважением"
        )
        self.assertTrue(is_our_payment_followup_template_only(body=body))

    def test_webmaster_reply_with_price_not_noise(self) -> None:
        body = (
            "We do accept Guest Posts. Our usual cost is £265.00 GBP + VAT if applicable per article.\n\n"
            "Could you please let us know if payment via cryptocurrency (e.g. USDT) or PayPal would be possible?"
        )
        self.assertFalse(is_our_payment_followup_template_only(body=body))

    def test_body_without_draft_is_not_noise_flag(self) -> None:
        body = "Thanks, we can offer $150 for a guest post."
        self.assertFalse(is_our_payment_followup_template_only(body=body))


if __name__ == "__main__":
    unittest.main()

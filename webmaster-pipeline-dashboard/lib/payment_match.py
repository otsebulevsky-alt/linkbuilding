"""Сопоставление вариантов оплаты в ответе вебмастера со справочником «Возможности оплаты» (Google Sheet)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

# Канонические категории: если в ответе есть упоминание, не попадающее в набор из справочника —
# или упоминаний нет — предлагается черновик уточнения (RU/EN).
RULES: list[tuple[str, re.Pattern[str]]] = [
    ("paypal", re.compile(r"paypal|pay\s*pal|пейпал|пэйпал", re.I)),
    (
        "crypto",
        re.compile(
            r"usdt|tether|u\s*s\s*d\s*t|btc|bitcoin|биткоин|eth|ethereum|"
            r"erc[-\s]?20|trc[-\s]?20|crypto|cryptocurrency|"
            r"крипт(о|овалют|овалюта)?|binance|wallet|metamask",
            re.I,
        ),
    ),
    (
        "bank_wire",
        re.compile(
            r"\bwire\b|swift|iban|sepa|bank\s*transfer|ach\b|"
            r"банк(овский|а)?|перевод\s*на\s*р/с|р/с\b|расч[её]тн|сч[её]т\s*в\s*банк",
            re.I,
        ),
    ),
    (
        "card",
        re.compile(
            r"\bvisa\b|\bmastercard\b|maestro|\bamex\b|credit\s*card|debit\s*card|"
            r"карт(а|ой|е|ы)?(\s*(visa|master|мир))?",
            re.I,
        ),
    ),
    ("wise", re.compile(r"\bwise\b|transferwise|трансфервайз", re.I)),
    ("capitalist", re.compile(r"capitalist|капиталист", re.I)),
    ("sbp", re.compile(r"\bсбп\b|система\s*быстрых\s*платежей", re.I)),
]

DRAFT_RU = (
    "Подскажите, пожалуйста, есть ли возможность оплатить криптовалютой (например, USDT) или через PayPal?"
)
DRAFT_EN = (
    "Could you please let us know if payment via cryptocurrency (e.g. USDT) or PayPal would be possible?"
)


def canonicals_in_text(text: str) -> set[str]:
    if not text or not str(text).strip():
        return set()
    t = str(text).lower()
    found: set[str] = set()
    for cid, rx in RULES:
        if rx.search(t):
            found.add(cid)
    return found


def canonicals_from_reference_dataframe(df: pd.DataFrame) -> set[str]:
    """Все ячейки справочника + заголовки → какие каноны «наши»."""
    if df is None or df.empty:
        return set()
    parts: list[str] = []
    for c in df.columns:
        parts.append(str(c))
    for col in df.columns:
        for v in df[col].astype(str):
            vv = v.strip()
            if vv and vv.lower() not in ("nan", "none", ""):
                parts.append(vv)
    blob = " ".join(parts)
    return canonicals_in_text(blob)


def payment_reply_language(subject: str, body: str) -> str:
    """Латиница без кириллицы → черновик на английском (как у отправителя)."""
    text = f"{subject}\n{body}"
    if re.search(r"[а-яА-ЯёЁ]", text):
        return "ru"
    return "en"


def need_payment_followup(our_canonicals: set[str], their_canonicals: set[str]) -> bool:
    if not our_canonicals:
        return False
    if not their_canonicals:
        return True
    return not their_canonicals.issubset(our_canonicals)


def payment_followup_draft(lang: str) -> str:
    if (lang or "").lower().startswith("en"):
        return DRAFT_EN
    return DRAFT_RU


def payment_draft_for_message(
    *,
    our_canonicals: set[str],
    subject: str,
    body: str,
) -> str:
    """
    Текст для колонки «черновик ответа» или пусто.
    Если справочник не дал ни одного канона — не подставляем фразу (не с чем сверять).
    """
    if not our_canonicals:
        return ""
    their = canonicals_in_text(f"{subject}\n{body}")
    if not need_payment_followup(our_canonicals, their):
        return ""
    lang = payment_reply_language(subject, body)
    return payment_followup_draft(lang)

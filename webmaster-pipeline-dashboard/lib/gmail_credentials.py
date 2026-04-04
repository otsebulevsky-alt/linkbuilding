"""Единая логика Gmail IMAP/SMTP из Secrets: заглушки вроде xxxx не должны перекрывать реальный пароль.

Частый кейс: в Cloud заполнили только GMAIL_SMTP_APP_PASSWORD, а GMAIL_IMAP_APP_PASSWORD оставили
из шаблона «xxxx xxxx xxxx xxxx». Старый код брал IMAP-ключ первым (он непустой) → IMAP login fail,
а SMTP с реальным паролем работал («Прочитать почту» пишет в таблицу и шлёт автоответы по SMTP).
"""

from __future__ import annotations

from typing import Any

from lib.config import _secrets_get, _secrets_get_int


def is_placeholder_gmail_app_password(raw: str) -> bool:
    """True если пароль пустой или явная заглушка из примера (только x)."""
    s = (raw or "").replace(" ", "").replace("\t", "").strip()
    if not s:
        return True
    return all(ch.lower() == "x" for ch in s)


def resolve_imap_user_password(secrets: Any) -> tuple[str, str]:
    user = (_secrets_get(secrets, "GMAIL_IMAP_USER") or _secrets_get(secrets, "GMAIL_SMTP_USER")).strip()
    imap_p = _secrets_get(secrets, "GMAIL_IMAP_APP_PASSWORD").strip()
    smtp_p = _secrets_get(secrets, "GMAIL_SMTP_APP_PASSWORD").strip()
    if imap_p and not is_placeholder_gmail_app_password(imap_p):
        password = imap_p
    else:
        password = smtp_p
    return user, password


def resolve_smtp_host_port_user_password(secrets: Any) -> tuple[str, int, str, str]:
    user = _secrets_get(secrets, "GMAIL_SMTP_USER").strip()
    if not user:
        user = _secrets_get(secrets, "GMAIL_IMAP_USER").strip()
    smtp_p = _secrets_get(secrets, "GMAIL_SMTP_APP_PASSWORD").strip()
    imap_p = _secrets_get(secrets, "GMAIL_IMAP_APP_PASSWORD").strip()
    if smtp_p and not is_placeholder_gmail_app_password(smtp_p):
        password = smtp_p
    else:
        password = imap_p
    host = (_secrets_get(secrets, "GMAIL_SMTP_HOST", "smtp.gmail.com") or "smtp.gmail.com").strip()
    port = _secrets_get_int(secrets, "GMAIL_SMTP_PORT", 587)
    return host, port, user, password

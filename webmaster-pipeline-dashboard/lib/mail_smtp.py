"""Send email via SMTP (Gmail: app password)."""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_smtp_html(
    *,
    host: str,
    port: int,
    user: str,
    password: str,
    to_addr: str,
    subject: str,
    html_body: str,
    from_addr: str | None = None,
    use_tls: bool = True,
    in_reply_to: str | None = None,
    references: str | None = None,
) -> None:
    msg = MIMEMultipart("alternative")
    subj = (subject or "").strip()
    msg["Subject"] = subj if subj else "Re: "
    msg["From"] = from_addr or user
    msg["To"] = to_addr
    if in_reply_to and in_reply_to.strip():
        msg["In-Reply-To"] = in_reply_to.strip()
    if references and references.strip():
        msg["References"] = references.strip()
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(host, port, timeout=60) as server:
        if use_tls:
            server.starttls()
        server.login(user, password)
        server.sendmail(msg["From"], [to_addr], msg.as_string())

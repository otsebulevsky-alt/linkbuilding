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
) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr or user
    msg["To"] = to_addr
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(host, port, timeout=60) as server:
        if use_tls:
            server.starttls()
        server.login(user, password)
        server.sendmail(msg["From"], [to_addr], msg.as_string())

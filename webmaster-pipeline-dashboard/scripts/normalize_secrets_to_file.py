"""
Remove embedded GOOGLE_SERVICE_ACCOUNT_JSON from .streamlit/secrets.toml (if present),
keep GOOGLE_SERVICE_ACCOUNT_FILE pointing at gcp-service-account.json.
Creates secrets.toml.bak before edit. Run from webmaster-pipeline-dashboard/:
  py scripts/normalize_secrets_to_file.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRETS = ROOT / ".streamlit" / "secrets.toml"
FILE_POINTER = '.streamlit/gcp-service-account.json'


def main() -> None:
    if not SECRETS.is_file():
        print("NO_SECRETS_FILE", file=sys.stderr)
        sys.exit(0)
    raw = SECRETS.read_text(encoding="utf-8")
    if "GOOGLE_SERVICE_ACCOUNT_FILE" in raw and "GOOGLE_SERVICE_ACCOUNT_JSON" not in raw:
        print("SKIP_ALREADY_FILE_ONLY")
        sys.exit(0)

    bak = SECRETS.with_suffix(".toml.bak")
    bak.write_text(raw, encoding="utf-8")

    new = raw
    for pattern in (
        r"GOOGLE_SERVICE_ACCOUNT_JSON\s*=\s*'''[\s\S]*?'''\s*\n?",
        r'GOOGLE_SERVICE_ACCOUNT_JSON\s*=\s*"""[\s\S]*?"""\s*\n?',
    ):
        new = re.sub(pattern, "", new, count=1)

    pointer_line = f'GOOGLE_SERVICE_ACCOUNT_FILE = "{FILE_POINTER}"\n\n'
    if "GOOGLE_SERVICE_ACCOUNT_FILE" not in new:
        new = pointer_line + new.lstrip()

    SECRETS.write_text(new, encoding="utf-8")
    print("OK_BACKUP", bak.name)


if __name__ == "__main__":
    main()

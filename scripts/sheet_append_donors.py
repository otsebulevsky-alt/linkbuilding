#!/usr/bin/env python3
"""
Append donor rows from donors-evaluation.csv to the Google Sheet
"[ВНУТРЕННИЙ] Калькулятор доноров".

First run: browser opens for Google OAuth; then credentials are cached.
Requires: pip install gspread google-auth-oauthlib

Usage:
  python sheet_append_donors.py [path/to/donors-evaluation.csv] [--sheet NAME]
"""

import argparse
import csv
import os
import sys
from pathlib import Path

# Default paths (workspace root = 4 levels up from .../internal/seo/linkbuilding/scripts)
SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPT_DIR.parent.parent.parent.parent
DATA_DIR = SCRIPT_DIR.parent / "data"
DEFAULT_CSV = DATA_DIR / "donors-evaluation.csv"
# Канон HACK-382: фрагмент Q94 + JI + 08 (латинская I), не Q94 + J1 + 08.
SPREADSHEET_ID = "1xrjeVD0Q94JI08v2gFvtv1NbiTAbq0fSjv-A-g5pPSs"
DEFAULT_SHEET_NAME = "Telecomasia"


def _credentials_path():
    """Prefer workspace personal/env for OAuth credentials (same as MCP setup)."""
    candidates = [
        WORKSPACE_ROOT / "personal" / "env" / "credentials.json",
        Path(os.environ.get("GSPREAD_CREDENTIALS", "")),
        Path.home() / ".config" / "gspread" / "credentials.json",
    ]
    for p in candidates:
        if p and p.is_file():
            return str(p)
    return None


def main():
    parser = argparse.ArgumentParser(description="Append donors from CSV to Google Sheet.")
    parser.add_argument(
        "csv_path",
        nargs="?",
        default=str(DEFAULT_CSV),
        help="Path to donors-evaluation.csv",
    )
    parser.add_argument(
        "--sheet",
        default=DEFAULT_SHEET_NAME,
        help="Sheet tab name (default: Telecomasia)",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    if not csv_path.is_file():
        print(f"Error: file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    try:
        import gspread
    except ImportError:
        print(
            "Install: pip install gspread google-auth-oauthlib",
            file=sys.stderr,
        )
        sys.exit(1)

    creds_path = _credentials_path()
    if creds_path:
        gc = gspread.oauth(credentials_filename=creds_path)
    else:
        try:
            gc = gspread.oauth()
        except FileNotFoundError as e:
            print(
                "Google OAuth credentials not found. Options:\n"
                "  1) Put credentials.json (from Google Cloud Console, OAuth 2.0 Desktop) in:\n"
                "     personal/env/credentials.json (in workspace root),\n"
                "     or in the default gspread folder (see gspread docs).\n"
                "  2) Run once: gspread will open a browser to log in and save the token.",
                file=sys.stderr,
            )
            raise SystemExit(1) from e

    sh = gc.open_by_key(SPREADSHEET_ID)
    worksheet = sh.worksheet(args.sheet)

    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if not row or all(cell.strip() == "" for cell in row):
                continue
            # Ensure we have 11 columns (A-K)
            while len(row) < 11:
                row.append("")
            rows.append(row[:11])

    if not rows:
        print("No data rows in CSV.")
        return

    # Append: values as list of lists; numbers as numbers
    values = []
    for row in rows:
        out = []
        for i, cell in enumerate(row):
            s = (cell or "").strip()
            if i in (1, 2, 3, 4, 6, 7, 8):  # DR, Traffic, RD, LD, Stagnation, Price, Links
                try:
                    out.append(int(float(s)) if s else 0)
                except ValueError:
                    out.append(s)
            elif i == 5:  # RD/LD
                try:
                    out.append(float(s) if s else 0)
                except ValueError:
                    out.append(s)
            elif i == 9:  # Score
                try:
                    out.append(float(s) if s else 0)
                except ValueError:
                    out.append(s)
            else:
                out.append(s)
        values.append(out)

    worksheet.append_rows(values, value_input_option="USER_ENTERED")
    print(f"Appended {len(values)} rows to sheet '{args.sheet}'.")


if __name__ == "__main__":
    main()

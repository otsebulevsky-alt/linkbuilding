#!/usr/bin/env python3
"""Append content of a batch file to logi-olega-export.txt (no overwrite)."""
import sys
from pathlib import Path

def main():
    if len(sys.argv) != 2:
        print("Usage: append_batch_to_export.py <path_to_batch_file>", file=sys.stderr)
        sys.exit(1)
    src = Path(sys.argv[1]).resolve()
    if not src.exists():
        print(f"Error: file not found: {src}", file=sys.stderr)
        sys.exit(2)
    export_dir = Path(__file__).resolve().parent.parent
    export_file = export_dir / "gmail-backlog" / "gmail-backlog-olega" / "logi-olega-export.txt"
    content = src.read_text(encoding="utf-8", errors="replace")
    with open(export_file, "a", encoding="utf-8") as f:
        f.write(content)
    print(f"Appended {len(content)} chars from {src.name} to {export_file.name}")

if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Parse Gmail batch output and write thread_<id>.txt files."""
import re
import sys
import os

def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_batch.py <output_dir> [batch_file]")
        sys.exit(1)
    out_dir = sys.argv[1]
    if len(sys.argv) >= 3:
        with open(sys.argv[2], "r", encoding="utf-8") as f:
            data = f.read()
    else:
        data = sys.stdin.read()
    blocks = re.split(r"\n---\n\n", data)
    count = 0
    for block in blocks:
        block = block.strip()
        if not block or not block.startswith("Thread ID:"):
            continue
        m = re.match(r"Thread ID: ([a-f0-9]+)", block)
        if not m:
            continue
        tid = m.group(1)
        path = os.path.join(out_dir, "thread_%s.txt" % tid)
        with open(path, "w", encoding="utf-8") as f:
            f.write(block)
        count += 1
    print("Wrote %d thread files" % count)

if __name__ == "__main__":
    main()

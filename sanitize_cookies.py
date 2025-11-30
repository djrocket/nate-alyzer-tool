#!/usr/bin/env python
"""
Sanitize a cookies.txt file to strict Netscape format for yt-dlp.

Actions:
- Ensures the 3-line Netscape header is present
- Keeps only lines with exactly 7 tab-separated fields
- Preserves comment lines starting with '#'

Usage:
  python sanitize_cookies.py -i cookies.txt -o cookies.clean.txt
"""

import argparse
from pathlib import Path


HEADER = (
    "# Netscape HTTP Cookie File\n"
    "# https://curl.haxx.se/rfc/cookie_spec.html\n"
    "# This is a generated file! Do not edit.\n"
)


def sanitize(in_path: Path, out_path: Path) -> None:
    raw = in_path.read_text(encoding="utf-8", errors="ignore").splitlines()

    out_lines = []
    kept = 0
    dropped = 0

    # Always write canonical header
    out_lines.extend(HEADER.splitlines())

    for line in raw:
        if not line:
            continue
        if line.lstrip().startswith("#"):
            # Keep comments after header as-is (optional)
            continue
        parts = line.split("\t")
        if len(parts) == 7:
            out_lines.append("\t".join(p.strip() for p in parts))
            kept += 1
        else:
            dropped += 1

    out_text = "\n".join(out_lines) + "\n"
    out_path.write_text(out_text, encoding="utf-8")
    print(f"Wrote {out_path} (kept {kept} cookies, dropped {dropped} malformed lines)")


def main():
    ap = argparse.ArgumentParser(description="Sanitize cookies.txt to strict Netscape format")
    ap.add_argument("-i", "--input", default="cookies.txt", help="Input cookies file (Netscape-like)")
    ap.add_argument("-o", "--output", default="cookies.clean.txt", help="Output sanitized cookies file")
    args = ap.parse_args()

    sanitize(Path(args.input), Path(args.output))


if __name__ == "__main__":
    main()


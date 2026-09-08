#!/usr/bin/env python3
"""R27.6 Font Cap Build-Step Verification (tasks 19.6, 28.4).

Verifies that any font file intended for the citizen portal fits within
the 40 KB (40,000 bytes) brotli-compressed limit required by R27.6.

If a deployment produces a regional font subset exceeding 40 KB, R27.6 and
R24.1 (150 KB page budget) conflict. This build step failing is the explicit
signal to revisit the numbers rather than silently shipping an oversized file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import brotli

FONT_CAP_BYTES = 40_000  # R27.6 cap: 40 KB brotli-compressed at quality 11
FONT_EXTENSIONS = (".woff2", ".woff", ".ttf", ".otf")


def check_font_cap(static_dir: Path) -> list[str]:
    """Check all font files in static_dir. Returns a list of failure messages."""
    if not static_dir.exists():
        return []

    failures = []
    fonts = [
        p for p in static_dir.iterdir()
        if p.is_file() and p.suffix.lower() in FONT_EXTENSIONS
    ]

    for font_path in fonts:
        data = font_path.read_bytes()
        compressed = len(brotli.compress(data, quality=11))
        if compressed > FONT_CAP_BYTES:
            failures.append(
                f"BUILD STEP FAILED: R27.6 Font cap exceeded for '{font_path.name}'.\n"
                f"Compressed size: {compressed} bytes (cap: {FONT_CAP_BYTES} bytes).\n"
                f"Conflict notice: Where a deployment's confirmed Q7 regional script has no viable "
                f"<= 40 KB subset and weak device coverage, R27.6 and R24.1 conflict.\n"
                f"The build failure is the signal to revisit the numbers rather than ship an oversized file."
            )

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify R27.6 font cap for citizen portal.")
    parser.add_argument(
        "--static-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "apps" / "api" / "app" / "citizen" / "static",
        help="Path to citizen static directory",
    )
    args = parser.parse_args()

    failures = check_font_cap(args.static_dir)
    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    print(
        f"SUCCESS (R27.6): All font files in {args.static_dir} fit within {FONT_CAP_BYTES} bytes brotli-compressed."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

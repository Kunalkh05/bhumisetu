"""Citizen portal font strategy guard (task 19.6).

R27.6 caps any font file at 40 KB. The default path ships no font
file at all — the system font stack (``system-ui, "Noto Sans Devanagari",
"Noto Sans"``) is sufficient on every device in the target market — so
the cap is satisfied trivially. The guard below makes that policy
explicit: any ``@font-face`` in the base template must not point to an
external font file, and any font file placed under
``apps/api/app/citizen/static/`` must fit in 40 KB.

If a deployment ever needs a typeface, this is where it would add a
glyph-subset WOFF2 with ``unicode-range`` and ``font-display: swap``;
the test fails the build if the produced file exceeds 40 KB, which is
the signal to raise the conflict between R27.6 and R24.1 explicitly
rather than ship an oversized file.

Requires no external services. Runs on every PR.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

CITIZEN_DIR = Path(__file__).resolve().parents[2] / "app" / "citizen"
STATIC_DIR = CITIZEN_DIR / "static"
TEMPLATES_DIR = CITIZEN_DIR / "templates"
FONT_CAP_BYTES = 40_000  # R27.6

FONT_EXTENSIONS = (".woff2", ".woff", ".ttf", ".otf")

pytestmark = pytest.mark.perf


def test_default_path_ships_no_font_file() -> None:
    """The citizen static directory contains no font files by default.

    A glyph-subset WOFF2 is added only when a deployment confirms its
    regional script needs one. Adding one here is a deliberate decision,
    not a slip.
    """
    if not STATIC_DIR.exists():
        pytest.skip("citizen static directory does not exist yet")

    fonts = [
        path for path in STATIC_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in FONT_EXTENSIONS
    ]
    assert fonts == [], (
        f"citizen static directory contains font files but the default "
        f"path ships none ({R27_6_REFERENCE}). Remove or move to a build "
        f"step: {[p.name for p in fonts]}"
    )


def test_base_template_uses_system_font_stack() -> None:
    """The base template must not reference an external font file via @font-face.

    The system font stack is sufficient on every device in the target market.
    An @font-face rule that points to an external file would be a regression
    unless the deployment has explicitly added a glyph-subset WOFF2.
    """
    base = (TEMPLATES_DIR / "base.html").read_text(encoding="utf-8")
    assert "system-ui" in base, (
        "base.html does not declare a system font stack. R27.6 / §10.4 require "
        "system-ui, \"Noto Sans Devanagari\", \"Noto Sans\" as the default path."
    )
    # An @font-face with a url() pointing to a local font file is forbidden on
    # the default path. A url() that points to nothing is not a working font.
    font_face_with_url = re.search(
        r"@font-face\s*\{[^}]*url\([^)]*\)",
        base,
        re.DOTALL,
    )
    assert font_face_with_url is None, (
        "base.html contains an @font-face rule with a url(); the default path "
        "ships no font file. If this is a deliberate deployment decision, "
        "ensure the produced WOFF2 fits in 40 KB (R27.6)."
    )


def test_any_font_file_in_static_fits_the_40kb_cap() -> None:
    """If a font file is present, it must fit in 40 KB brotli-compressed.

    The cap is the *compressed* size the citizen would receive, measured at
    brotli quality 11 to match Caddy (R27.6, §10.5). A 40 KB raw file may
    compress to well under 40 KB, so we measure the compressed size.
    """
    if not STATIC_DIR.exists():
        pytest.skip("citizen static directory does not exist yet")

    import brotli

    fonts = [
        path for path in STATIC_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in FONT_EXTENSIONS
    ]
    for path in fonts:
        data = path.read_bytes()
        compressed = len(brotli.compress(data, quality=11))
        assert compressed <= FONT_CAP_BYTES, (
            f"{path.name} brotli-compressed to {compressed} B exceeds the "
            f"R27.6 cap of {FONT_CAP_BYTES} B. Subset further or raise the "
            f"conflict between R27.6 and R24.1 explicitly."
        )


def check_font_cap(static_dir: Path) -> list[str]:
    """Check all font files in static_dir for the R27.6 40 KB compressed limit."""
    if not static_dir.exists():
        return []

    import brotli

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


def test_oversized_font_subset_triggers_build_step_failure_with_conflict_signal(tmp_path: Path) -> None:
    """A font subset exceeding 40 KB fails the build step with the R27.6/R24.1 conflict signal."""
    import os

    # Create an incompressible 45 KB font file (e.g. random bytes that won't compress below 40 KB)
    oversized_font = tmp_path / "oversized-devanagari.woff2"
    oversized_font.write_bytes(os.urandom(45_000))

    failures = check_font_cap(tmp_path)
    assert len(failures) == 1
    msg = failures[0]
    assert "BUILD STEP FAILED: R27.6 Font cap exceeded" in msg
    assert "oversized-devanagari.woff2" in msg
    assert "R27.6 and R24.1 conflict" in msg
    assert "revisit the numbers rather than ship an oversized file" in msg


R27_6_REFERENCE = "R27.6"

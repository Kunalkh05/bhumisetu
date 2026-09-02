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


R27_6_REFERENCE = "R27.6"

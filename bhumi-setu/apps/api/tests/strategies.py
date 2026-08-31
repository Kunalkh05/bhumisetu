"""Shared Hypothesis generators for the domain (§20.8).

One module so that a share vector, a Devanagari string or a stage graph means the
same thing in every test. Three tests inventing three subtly different notions of
"valid ownership share" is how a property passes in one place and fails in another
for reasons nobody can reconstruct.

Implemented now vs. stubbed
---------------------------

Generators with a consumer in the code that exists today are implemented:
:func:`st_devanagari_text`, :func:`st_administrative_code`, :func:`st_ltree_label`.
The rest raise :class:`NotImplementedError` with the task that owns them.

That is deliberate, and it is a change from what ``tasks.md`` asks for — it
suggests creating all six as stubs. A stub nothing exercises is a stub that is
wrong the day someone needs it, and worse, a stub that silently returns something
plausible makes the property test using it pass while testing nothing. Raising is
louder than returning ``st.just(0.5)``.
"""

from __future__ import annotations

import unicodedata

from hypothesis import strategies as st

__all__ = [
    "st_administrative_code",
    "st_cadastral_polygon",
    "st_confidence",
    "st_devanagari_text",
    "st_event_timeline",
    "st_ltree_label",
    "st_share_vector",
    "st_stage_graph",
]


# ---------------------------------------------------------------------------
# Scripts and text (R27.5)
# ---------------------------------------------------------------------------

# Devanagari, split by role because the interesting cases are the combining ones.
# A generator that only emits base consonants would exercise none of what makes
# R27.5 hard.
_DEVANAGARI_CONSONANTS = "कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह"
_DEVANAGARI_VOWELS = "अआइईउऊऋएऐओऔ"
_DEVANAGARI_MATRAS = "ािीुूृेैोौ"          # combining vowel signs
_DEVANAGARI_SIGNS = "ंँ्ः"                  # anusvara, candrabindu, virama, visarga
_ZWJ = "\u200d"
_ZWNJ = "\u200c"
_NUKTA = "\u093c"

# Precomposed consonants that Unicode *decomposes* but does not recompose: they
# sit in the composition-exclusion list, so NFD(क़) is क + nukta while
# NFC(क + nukta) stays decomposed. Including them is the only way to make a
# Devanagari string where NFC and NFD genuinely differ — matras and ordinary
# nukta sequences are already decomposed, so a naive "sometimes normalise to NFD"
# branch produces an identical string and tests nothing.
_DEVANAGARI_PRECOMPOSED = "\u0958\u0959\u095a\u095b\u095c\u095d\u095e\u095f"


@st.composite
def st_devanagari_text(draw, min_size: int = 1, max_size: int = 24) -> str:
    """Devanagari text including the cases that break naive handling.

    Emits combining vowel signs, virama-joined conjuncts, nukta, ZWJ and ZWNJ,
    and mixes composed and decomposed forms. Those are the reason R27.5 is a
    requirement rather than an assumption:

    * a matra is a separate code point, so ``len()`` is not a character count and
      a truncating column silently corrupts the last glyph;
    * NFC and NFD forms of the same name compare unequal, so normalising on write
      would make a read-back differ from the value written — which R27.5 forbids
      in as many words;
    * ZWJ and ZWNJ are invisible, so two names that look identical on screen can
      be different strings, and duplicate detection has to decide which it means.
    """
    length = draw(st.integers(min_value=min_size, max_value=max_size))
    out: list[str] = []
    for _ in range(length):
        base = draw(
            st.sampled_from(
                _DEVANAGARI_CONSONANTS + _DEVANAGARI_VOWELS + _DEVANAGARI_PRECOMPOSED
            )
        )
        out.append(base)
        if draw(st.booleans()):
            out.append(draw(st.sampled_from(_DEVANAGARI_MATRAS)))
        if draw(st.integers(0, 9)) == 0:
            out.append(draw(st.sampled_from(_DEVANAGARI_SIGNS)))
        if draw(st.integers(0, 19)) == 0:
            out.append(_NUKTA)
        if draw(st.integers(0, 19)) == 0:
            out.append(draw(st.sampled_from([_ZWJ, _ZWNJ])))
    text = "".join(out)
    # Sometimes hand back the decomposed form, so any code that assumes NFC is
    # exercised rather than accidentally satisfied.
    if draw(st.booleans()):
        text = unicodedata.normalize("NFD", text)
    return text


# ---------------------------------------------------------------------------
# Administrative codes and ltree labels (R2.1, R2.2)
# ---------------------------------------------------------------------------

# The characters that actually turn up in Indian administrative codes, plus the
# ones that break ltree. '.' is ltree's separator and is the whole reason
# to_ltree_label() exists, so it is over-represented here on purpose.
_CODE_ALPHABET = st.one_of(
    st.characters(min_codepoint=ord("A"), max_codepoint=ord("Z")),
    st.characters(min_codepoint=ord("a"), max_codepoint=ord("z")),
    st.characters(min_codepoint=ord("0"), max_codepoint=ord("9")),
    st.sampled_from(list("._- /()&,")),
)


def st_administrative_code(min_size: int = 1, max_size: int = 24) -> st.SearchStrategy[str]:
    """A raw administrative code, as a government record might carry it.

    Deliberately dirty: periods, hyphens, spaces, slashes and parentheses all
    appear in real district and village codes, and every one of them is illegal in
    an ltree label. Codes that transliterate to nothing are filtered out, because
    :func:`app.db.column_types.to_ltree_label` rejects those by design and the
    parity test is about agreement on *acceptable* input.
    """
    return (
        st.text(alphabet=_CODE_ALPHABET, min_size=min_size, max_size=max_size)
        .map(str.strip)
        # At least one alphanumeric, not merely one "legal" character. A code of
        # only underscores passes an `isalnum() or "_"` filter but transliterates
        # to the empty string, because to_ltree_label() strips leading and
        # trailing underscores — and it is right to reject it, since such a code
        # carries no information. Found by this generator on its first run.
        .filter(lambda s: any(c.isalnum() for c in s))
    )


def st_ltree_label(min_size: int = 1, max_size: int = 16) -> st.SearchStrategy[str]:
    """An already-legal ltree label: ``[A-Za-z0-9_]+``."""
    return st.text(
        alphabet=st.characters(
            whitelist_categories=(),
            whitelist_characters="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_",
        ),
        min_size=min_size,
        max_size=max_size,
    )


# ---------------------------------------------------------------------------
# Not yet implemented. Each names the task that owns it.
# ---------------------------------------------------------------------------


def _owned_by(task: str, what: str, requirement: str) -> st.SearchStrategy:
    raise NotImplementedError(
        f"{what} is implemented by task {task} ({requirement}). It raises rather "
        "than returning a placeholder: a generator that quietly yields something "
        "plausible makes the property test using it pass while testing nothing."
    )


def st_cadastral_polygon() -> st.SearchStrategy:
    """Parcel geometry, including deliberately invalid self-intersecting rings."""
    return _owned_by("17.6", "st_cadastral_polygon", "R15.1-15.3")


def st_share_vector() -> st.SearchStrategy:
    """Ownership shares, summing inside and outside the R6.5 tolerance."""
    return _owned_by("13.6", "st_share_vector", "R6.5, R6.6")


def st_event_timeline() -> st.SearchStrategy:
    """Event sequences including backdated appends, for the as-of predicates."""
    return _owned_by("3.9", "st_event_timeline", "R4.4, R17.1")


def st_stage_graph() -> st.SearchStrategy:
    """Configured stage sets with declared successors and a terminal stage."""
    return _owned_by("2.8", "st_stage_graph", "R5.3, R28.7")


def st_confidence() -> st.SearchStrategy:
    """OCR confidence values, weighted towards the configured thresholds."""
    return _owned_by("16.8", "st_confidence", "R12.1-12.4")

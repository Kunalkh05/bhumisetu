"""No integer literal may reach date arithmetic (R7.2, §20.7).

R7.2: *THE Notice_Service SHALL compute no legally significant date from a period
value embedded in application code.*

That cannot be tested behaviourally. A hardcoded 30 produces a deadline that looks
entirely correct — it is only wrong in a state whose window is 60 days, and nobody
finds out until a landowner's objection is refused as out of time. So it is checked
structurally, by reading the source.

Why an AST walk rather than a grep
----------------------------------

``timedelta(days=30)`` and ``timedelta(days=period_days)`` differ by one node type
and are indistinguishable to a regex that tolerates whitespace and line breaks. The
walk looks for a ``Constant`` in the *keyword argument position* of a date-arithmetic
call, which is exactly the shape that puts a number in the code and nothing else.

What this cannot catch, and what covers it instead
--------------------------------------------------

An AST walk sees literals. It does not see ``PERIOD = 30`` on one line and
``timedelta(days=PERIOD)`` on another, and following that would mean constant
propagation across modules — a static analyser, not a test.

The gap is covered from the other side: ``PolicyResolver.get()`` has no ``default=``
parameter (task 2.2), and a period can only enter the system through
``Policy_Config``. So a module-level constant would have to be *written* somewhere,
and the only writer is ``PolicyService.set``. Between the two, a legal number has no
path into a computed deadline.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]

#: Where platform code lives. `ml/src` and `workers` import the same service
#: modules (§3.2, §3.3), so a literal period there is as damaging as one in `app`.
SOURCE_ROOTS = (
    API_ROOT / "app",
    REPO_ROOT / "ml" / "src",
    REPO_ROOT / "workers",
)

#: Callables that turn a number into a duration. `relativedelta` is included even
#: though it is not a current dependency: the day it is added, this guard should
#: already cover it rather than silently not.
DATE_ARITHMETIC_CALLS = frozenset({"timedelta", "relativedelta", "Duration"})

#: Keyword arguments that carry a period. `days` is the one that matters for
#: statutory windows; the rest are here so a period expressed in weeks or hours
#: cannot slip past by choosing a different unit.
PERIOD_KEYWORDS = frozenset(
    {"days", "weeks", "hours", "minutes", "months", "years", "seconds"}
)

#: Small durations that are plainly not statutory. A retry backoff of 1 second and
#: an OTP validity of 10 minutes are engineering constants, and forcing them
#: through Policy_Config would devalue the mechanism that protects legal periods.
#: `days` is deliberately absent: there is no such thing as a safe literal day
#: count in this platform.
NON_STATUTORY_UNITS = frozenset({"seconds", "milliseconds", "microseconds"})


def python_files() -> list[Path]:
    found: list[Path] = []
    for root in SOURCE_ROOTS:
        if not root.exists():
            continue
        found.extend(
            path
            for path in root.rglob("*.py")
            if ".venv" not in path.parts and "site-packages" not in path.parts
        )
    return found


def called_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _display(path: Path) -> str:
    """Repo-relative where possible. The guard's own tests pass a tmp_path probe,
    which is outside the repo, and relative_to() raises rather than degrading."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return path.name


def literal_period_offences(tree: ast.Module, path: Path) -> list[str]:
    offences: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if called_name(node) not in DATE_ARITHMETIC_CALLS:
            continue

        for keyword in node.keywords:
            if keyword.arg not in PERIOD_KEYWORDS:
                continue
            if keyword.arg in NON_STATUTORY_UNITS:
                continue
            value = keyword.value
            # A unary minus wraps the constant, so `days=-30` is an ast.UnaryOp.
            if isinstance(value, ast.UnaryOp) and isinstance(value.operand, ast.Constant):
                value = value.operand
            if isinstance(value, ast.Constant) and isinstance(value.value, (int, float)):
                offences.append(
                    f"{_display(path)}:{node.lineno} "
                    f"{called_name(node)}({keyword.arg}={value.value!r})"
                )

        # Positional args too: timedelta(30) is days=30 by signature, and a guard
        # that only checked keywords would be trivially avoidable.
        for index, arg in enumerate(node.args):
            if isinstance(arg, ast.Constant) and isinstance(arg.value, (int, float)):
                offences.append(
                    f"{_display(path)}:{node.lineno} "
                    f"{called_name(node)}(positional[{index}]={arg.value!r})"
                )
    return offences


def test_source_roots_are_not_empty() -> None:
    """Fail closed. An empty file list would make the guard below pass vacuously."""
    files = python_files()
    assert files, f"no Python files found under {[str(r) for r in SOURCE_ROOTS]}"
    assert any("app" in str(p) for p in files)


def test_no_integer_literal_reaches_date_arithmetic() -> None:
    offences: list[str] = []
    for path in python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        offences.extend(literal_period_offences(tree, path))

    assert not offences, (
        "A period literal reaches date arithmetic, which R7.2 forbids. Every "
        "statutory period is a Policy_Config value resolved by state, act and "
        "effective date (§4). Resolve it through PolicyResolver and pass the "
        f"resolved value as a variable. Offences: {offences}"
    )


# ---------------------------------------------------------------------------
# The guard's own tests. A lint nobody has watched reject anything is a guess.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        "timedelta(days=30)",
        "timedelta(days=-30)",
        "timedelta(weeks=8)",
        "timedelta(30)",
        "datetime.timedelta(days=365)",
        "relativedelta(months=6)",
        "x = timedelta(days=90) + something",
    ],
)
def test_the_guard_rejects_a_literal_period(source: str, tmp_path: Path) -> None:
    tree = ast.parse(source)
    assert literal_period_offences(tree, tmp_path / "probe.py"), (
        f"{source!r} should have been rejected"
    )


@pytest.mark.parametrize(
    "source",
    [
        "timedelta(days=period_days)",
        "timedelta(days=int(days))",
        "timedelta(days=resolver.get(key, state=s, act=a, as_of=d))",
        "timedelta(seconds=1)",
        "timedelta(seconds=RETRY_BACKOFF_SECONDS)",
        "some_other_call(days=30)",
    ],
)
def test_the_guard_allows_a_resolved_period_and_engineering_constants(
    source: str, tmp_path: Path
) -> None:
    tree = ast.parse(source)
    assert not literal_period_offences(tree, tmp_path / "probe.py"), (
        f"{source!r} should have been allowed"
    )


def test_the_guard_documents_its_own_blind_spot() -> None:
    """A module-level constant passed by name is not detected, by design.

    Following it would mean constant propagation across modules, which is a static
    analyser rather than a test. The gap is closed from the other side: a period can
    only enter through Policy_Config, and PolicyResolver.get() has no default
    parameter (task 2.2). This test records the limitation so nobody later assumes
    coverage that does not exist.
    """
    tree = ast.parse("PERIOD = 30\nd = timedelta(days=PERIOD)")
    assert not literal_period_offences(tree, Path("probe.py"))

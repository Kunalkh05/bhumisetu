"""Field-coverage guards: no personal field ships unannotated, and the redaction
matrix is total (§8.3 layer 3, task 5.5).

Task 5.4 (``tests/test_route_table.py``) is §8.3's *second* layer — every route is a
:class:`~app.api.gated_route.GatedRoute` whose ``response_model`` is a
:class:`~app.security.gate.GatedModel`. That guarantees the gate *runs*; it says
nothing about whether the model's fields are annotated correctly. This file is the
*third* layer, one strength above it, and it is where a personal attribute that was
added to a response without a visibility declaration becomes a red test:

* :func:`test_no_unannotated_sensitive_field` — intersect every gated model's field
  *names* with the personal-data attribute registry (:mod:`app.retention.categories`,
  task 3.3) and require every match to carry a :func:`~app.security.gate.Sensitive`
  annotation. Adding ``contact_mobile`` to a response model without annotating it
  fails the build (§8.3), because ``contact_mobile`` is a classified personal-data
  attribute and an unannotated field is visible to everyone.
* :func:`test_redaction_matrix_is_exhaustive` — for every field of every gated model,
  against an ``OFFICER``, an ``OWNER``, a ``NON_OWNER`` and a ``SERVICE`` principal,
  assert the field is present exactly where its declared visibility permits and absent
  everywhere else (Property 60).

Discovering the models, and excluding test fixtures
---------------------------------------------------

The guard must see *every* gated model the application ships. It finds them by walking
:meth:`GatedModel.__subclasses__` transitively after building the app — ``create_app``
imports every module its routers reach, so a response model wired to an endpoint is
loaded and therefore visible to the walk. The catch is that ``__subclasses__`` sees
*every* subclass the interpreter has loaded, and once pytest has imported the suite
that includes the fixtures in ``tests/test_gate.py`` and the ones below. So the walk is
filtered to production modules — those whose defining module is under the ``app``
package — which drops the test fixtures without an allowlist to maintain. The meta-test
:func:`test_discovery_finds_gated_models_and_excludes_test_only_ones` proves both halves:
the raw walk finds a real gated model, and the production filter leaves this file's own
out.

Why it is not vacuous today
---------------------------

No domain response model exists yet — they arrive with the endpoint tasks — so against
the shipped app both guards iterate an empty set and pass. That is expected and stated
in the design: the value is future-facing, catching the *next* unannotated personal
field. Three things keep "passes today" from meaning "would pass on anything":

1. the personal-data attribute set is asserted non-empty, so gutting ``CATEGORY_MAP``
   fails the guard rather than silently emptying its intersection;
2. the discovery mechanism is shown to actually find a gated model that exists;
3. each check is exercised on a deliberately-broken fixture — an unannotated
   ``contact_mobile``, and a gate that leaks every field — and must flag it.

This mirrors the "guard's own tests" discipline of ``tests/test_route_table.py`` and the
oracle discipline of ``tests/test_gate.py``: a check never observed rejecting anything is
a guess.
"""

from __future__ import annotations

from typing import Callable, Iterable

from app.main import create_app
from app.retention.categories import (
    CATEGORY_MAP,
    OWNER_CONTACT,
    OWNER_IDENTITY,
    personal_data_attributes,
)
from app.security.access import Principal
from app.security.gate import (
    GatedModel,
    Mask,
    ResponseGate,
    Sensitive,
    SensitiveField,
    Visibility,
    principal_owns,
    sensitivity_of,
)
from app.settings import CoreSettings


# ---------------------------------------------------------------------------
# Discovering the shipped gated models
# ---------------------------------------------------------------------------


def _core() -> CoreSettings:
    """Development settings, so ``create_app`` builds without a production
    environment and imports every module its routers reach."""
    return CoreSettings.model_validate({"APP_ENV": "development", "LOG_LEVEL": "WARNING"})


def _all_subclasses(root: type) -> set[type]:
    """Every subclass of ``root``, transitively.

    ``type.__subclasses__`` returns only *direct* children, so a model that subclasses
    another gated model would be missed by a single call. The walk closes over the
    whole tree, with a ``seen`` set so a diamond in the hierarchy cannot loop.
    """
    seen: set[type] = set()
    stack = list(root.__subclasses__())
    while stack:
        cls = stack.pop()
        if cls in seen:
            continue
        seen.add(cls)
        stack.extend(cls.__subclasses__())
    return seen


def _is_production_model(cls: type) -> bool:
    """Whether ``cls`` is a gated model the application ships, not a test fixture.

    The distinction is by defining module: production response models live under the
    ``app`` package, test fixtures under ``tests``. Keying on the module is what lets
    the guard use :meth:`GatedModel.__subclasses__` — which sees every subclass the
    interpreter has loaded, this suite's fixtures included — without sweeping those
    fixtures into the production coverage set, and without an allowlist to keep in sync.
    """
    module = cls.__module__
    return module == "app" or module.startswith("app.")


def discover_production_gated_models() -> list[type[GatedModel]]:
    """Every :class:`GatedModel` the shipped application defines.

    Building the app imports every module its routers reach, so a response model wired
    to an endpoint is loaded and therefore visible to the subclass walk below. Today
    the app wires no domain endpoints, so this is empty — see the module docstring on
    why that is expected and how the guard stays honest anyway. When a response model
    lands it is imported through the route it serves, so it appears here without this
    function changing.
    """
    create_app(_core())
    return sorted(
        (cls for cls in _all_subclasses(GatedModel) if _is_production_model(cls)),
        key=lambda cls: (cls.__module__, cls.__qualname__),
    )


# ---------------------------------------------------------------------------
# test_no_unannotated_sensitive_field
# ---------------------------------------------------------------------------


def _unannotated_personal_fields(
    models: Iterable[type[GatedModel]], personal: frozenset[str]
) -> list[str]:
    """Every ``(model, field)`` whose field *name* is a personal-data attribute but
    which carries no :func:`~app.security.gate.Sensitive` annotation.

    An unannotated field is visible to every principal (the gate treats a missing
    annotation as ``PUBLIC``-equivalent). A field whose name is in the personal-data
    registry is, by that registry's own classification, personal data. The two
    together are the leak: personal data shown to everyone. Returned as
    human-readable strings so a red run names the exact field to annotate.
    """
    offences: list[str] = []
    for model in models:
        for field_name in model.model_fields:
            if field_name in personal and sensitivity_of(model, field_name) is None:
                offences.append(f"{model.__module__}.{model.__qualname__}.{field_name}")
    return offences


def test_no_unannotated_sensitive_field() -> None:
    """R26.1/R26.3/R26.4 structurally: a personal-data attribute cannot reach a
    response model without a visibility declaration.

    Intersects every gated model's field names with the personal-data attribute set
    from ``CATEGORY_MAP`` and requires every match to carry a ``Sensitive(...)``. The
    personal set is asserted non-empty first, so the guard cannot pass by intersecting
    against nothing (§17.1 gutted).

    Feature: bhumisetu, Property 60.
    Validates: Requirements 26.1, 26.3, 26.4, 26.6, 26.7.
    """
    personal = personal_data_attributes(CATEGORY_MAP)
    assert personal, (
        "the personal-data attribute set is empty, so this guard would pass "
        "vacuously — CATEGORY_MAP must classify some attribute as personal"
    )

    offences = _unannotated_personal_fields(discover_production_gated_models(), personal)
    assert not offences, (
        "a GatedModel field whose name is a personal-data attribute carries no "
        "Sensitive(...) annotation, so the gate treats it as visible to everyone and "
        f"it would reach every principal unredacted. Annotate it: {offences}"
    )


# ---------------------------------------------------------------------------
# test_redaction_matrix_is_exhaustive
# ---------------------------------------------------------------------------

#: The permission the matrix uses to exercise the ``PERMISSION`` visibility branch.
#: A real registry permission (§8.5), so the fixture reads like a genuine field.
_MATRIX_PERMISSION = "dsar.dispose"


def _matrix_principals() -> list[tuple[str, Principal, bool]]:
    """The four principals of the redaction matrix, each paired with whether it owns
    the record the field belongs to.

    Ownership is a property of the *instance*, not the principal (see
    :func:`~app.security.gate.principal_owns`), so it travels alongside: an ``OWNER`` is
    a citizen for whom ``owns`` is true, a ``NON_OWNER`` a citizen for whom it is false.
    An officer and a service never own anything — their access to an ``OWNER_ONLY`` field,
    where they have it, comes from being an officer, not from ownership — so both carry
    ``owns=False``. The service holds :data:`_MATRIX_PERMISSION` so the ``PERMISSION``
    branch is exercised on its visible side too, not only its refused side.
    """
    return [
        ("OFFICER", Principal(kind="OFFICER", id="officer-1", scope_paths=("MH",)), False),
        ("OWNER", Principal(kind="CITIZEN", id="owner", case_id=1, owner_record_ids=(1,)), True),
        ("NON_OWNER", Principal(kind="CITIZEN", id="stranger", case_id=2, owner_record_ids=(9,)), False),
        ("SERVICE", Principal(kind="SERVICE", id="svc", permissions=frozenset({_MATRIX_PERMISSION})), False),
    ]


def _matrix_permits(
    annotation: SensitiveField | None, principal: Principal, owns: bool
) -> bool:
    """Whether the *declared* visibility permits ``principal`` to see the field.

    The matrix read straight from the annotation, independent of the gate's code path —
    the oracle discipline of ``tests/test_gate.py``: the gate and this agree only because
    both are correct. An unannotated field is visible (the gate treats it so; requiring
    the annotation in the first place is :func:`test_no_unannotated_sensitive_field`'s job,
    not this one's).

    The final ``raise`` is the exhaustiveness claim: a fifth :class:`Visibility` added
    without a row here makes this fail rather than silently guess, so the matrix stays
    total over the vocabulary a field may declare.
    """
    if annotation is None:
        return True
    visibility = annotation.visibility
    if visibility is Visibility.PUBLIC:
        return True
    if visibility is Visibility.OFFICER_ONLY:
        return principal.kind == "OFFICER"
    if visibility is Visibility.OWNER_ONLY:
        return principal.kind == "OFFICER" or (principal.kind == "CITIZEN" and owns)
    if visibility is Visibility.PERMISSION:
        return bool(annotation.permission) and principal.has_permission(annotation.permission)
    raise AssertionError(f"the redaction matrix does not cover visibility {visibility!r}")


def _gate_presents(
    annotation: SensitiveField | None, principal: Principal, owns: bool
) -> bool:
    """Whether the gate would keep the field in the body for ``principal``.

    This is exactly what ``ResponseGate`` consults to include or omit a field: an
    unannotated field is present, an annotated one is present iff
    :meth:`SensitiveField.visible_to` says so (see ``gate._field_visible``, which every
    principal in the matrix reaches because none is ``None``). Because the gate derives
    body presence from nothing else, agreement here *is* agreement about the serialized
    body — a claim :func:`test_the_matrix_matches_the_serialized_body_for_a_concrete_model`
    discharges concretely on real ``ResponseGate.apply`` output.
    """
    if annotation is None:
        return True
    return annotation.visible_to(principal, owns=owns)


def _matrix_violations(
    models: Iterable[type[GatedModel]],
    principals: list[tuple[str, Principal, bool]],
    present: Callable[[SensitiveField | None, Principal, bool], bool] = _gate_presents,
) -> list[str]:
    """Every ``(model, field, principal)`` where actual presence diverges from what the
    declared visibility permits.

    ``present`` is the actual-presence source, defaulting to the gate's own decision. It
    is a parameter so the guard's own tests can feed it a deliberately-broken gate (one
    that leaks every field) and confirm the comparison catches the divergence.
    """
    offences: list[str] = []
    for model in models:
        for field_name in model.model_fields:
            annotation = sensitivity_of(model, field_name)
            for label, principal, owns in principals:
                permitted = _matrix_permits(annotation, principal, owns)
                actual = present(annotation, principal, owns)
                if actual != permitted:
                    offences.append(
                        f"{model.__qualname__}.{field_name} for {label}: "
                        f"gate presents={actual}, matrix permits={permitted}"
                    )
    return offences


def test_redaction_matrix_is_exhaustive() -> None:
    """Property 60 over every shipped model: each field is present exactly where its
    declared visibility permits, for each of the four principals, and absent otherwise.

    Feature: bhumisetu, Property 60.
    Validates: Requirements 26.1, 26.3, 26.4, 26.6, 26.7.
    """
    principals = _matrix_principals()
    assert {label for label, _, _ in principals} == {"OFFICER", "OWNER", "NON_OWNER", "SERVICE"}

    offences = _matrix_violations(discover_production_gated_models(), principals)
    assert not offences, "redaction matrix diverges from declared visibility: " + "; ".join(offences)


def test_the_matrix_covers_every_visibility() -> None:
    """Exhaustive means total over the vocabulary: every :class:`Visibility` a field may
    declare has a defined row for all four principals, and the gate agrees with it.

    This is the half of the guarantee that is not vacuous today — it holds with zero
    shipped models — because it ranges over the ``Visibility`` enum rather than over the
    (currently empty) set of models. A fifth visibility added without extending
    :func:`_matrix_permits` makes it raise here."""
    principals = _matrix_principals()
    for visibility in Visibility:
        permission = _MATRIX_PERMISSION if visibility is Visibility.PERMISSION else None
        annotation = SensitiveField(visibility=visibility, permission=permission)
        for _label, principal, owns in principals:
            permitted = _matrix_permits(annotation, principal, owns)
            assert isinstance(permitted, bool)
            assert _gate_presents(annotation, principal, owns) == permitted


# ---------------------------------------------------------------------------
# The guards' own tests: prove they bite, on deliberately-broken fixtures
# ---------------------------------------------------------------------------


class _SampleOut(GatedModel):
    """A response model carrying a field of every visibility, for the meta-tests.

    Case-scoped ownership (``__owner_case_id_field__ = "case_id"``) so an ``OWNER`` whose
    ``case_id`` matches the instance owns it and a ``NON_OWNER`` does not — the two citizen
    rows of the matrix. Defined in this test module on purpose: production discovery must
    *exclude* it, which :func:`test_discovery_finds_gated_models_and_excludes_test_only_ones`
    checks.
    """

    __owner_record_id_field__ = None
    __owner_case_id_field__ = "case_id"

    case_id: int = Sensitive(Visibility.PUBLIC)
    public_note: str = Sensitive(Visibility.PUBLIC)
    officer_note: str = Sensitive(Visibility.OFFICER_ONLY)
    owner_name: str = Sensitive(Visibility.OWNER_ONLY, data_category=OWNER_IDENTITY)
    government_identifier: str = Sensitive(
        Visibility.OWNER_ONLY, mask=Mask.TRAILING_4, data_category=OWNER_IDENTITY
    )
    disposal_token: str = Sensitive(Visibility.PERMISSION, permission=_MATRIX_PERMISSION)


def _sample() -> _SampleOut:
    return _SampleOut(
        case_id=1,
        public_note="visible to all",
        officer_note="internal",
        owner_name="Asha Kumari",
        government_identifier="AADHAAR1234567",
        disposal_token="secret",
    )


def test_no_unannotated_sensitive_field_bites_on_an_unannotated_personal_field() -> None:
    """The guard's reason to exist: a personal attribute added to a response without a
    ``Sensitive`` annotation. ``contact_mobile`` is a classified personal-data attribute
    (``OWNER_CONTACT``), so a model exposing it unannotated must be flagged — the design's
    "adding ``contact_mobile`` to a response model without annotating it fails the build".
    """
    personal = personal_data_attributes(CATEGORY_MAP)
    assert "contact_mobile" in personal  # precondition: the leak target is personal

    class _Leaky(GatedModel):
        __owner_record_id_field__ = None
        id: int = Sensitive(Visibility.PUBLIC)
        contact_mobile: str | None = None  # personal, but unannotated -> a leak

    offences = _unannotated_personal_fields([_Leaky], personal)
    assert offences and any("contact_mobile" in offence for offence in offences)


def test_no_unannotated_sensitive_field_accepts_an_annotated_personal_field() -> None:
    """Positive control: the same personal field, annotated, is accepted — otherwise the
    guard would reject correctly-annotated models as they land."""
    personal = personal_data_attributes(CATEGORY_MAP)

    class _Proper(GatedModel):
        __owner_record_id_field__ = None
        id: int = Sensitive(Visibility.PUBLIC)
        contact_mobile: str | None = Sensitive(
            Visibility.OWNER_ONLY, data_category=OWNER_CONTACT
        )

    assert _unannotated_personal_fields([_Proper], personal) == []


def test_redaction_matrix_accepts_the_real_gate() -> None:
    """Positive control: the shipped gate's decision matches the declared visibility for
    every field of a fully-annotated model, so the matrix guard passes what it should."""
    assert _matrix_violations([_SampleOut], _matrix_principals()) == []


def test_redaction_matrix_bites_when_presence_diverges() -> None:
    """A gate that shipped every field to everyone — the failure R26.7 guards against —
    diverges from what the annotations permit. Feeding the checker such a presence source
    must flag every field a principal may not see, proving the comparison bites rather
    than only ever confirming agreement."""
    leak_everything: Callable[[SensitiveField | None, Principal, bool], bool] = (
        lambda annotation, principal, owns: True
    )
    offences = _matrix_violations([_SampleOut], _matrix_principals(), present=leak_everything)

    # A non-owner citizen may see neither the officer note nor another owner's name;
    # a leak-everything gate showing them both is exactly what must be caught.
    assert any("officer_note" in o and "NON_OWNER" in o for o in offences)
    assert any("owner_name" in o and "NON_OWNER" in o for o in offences)
    assert any("disposal_token" in o and "OWNER" in o for o in offences)


def test_the_matrix_matches_the_serialized_body_for_a_concrete_model() -> None:
    """Tie the annotation-level matrix to the real serialized body.

    The matrix above is stated in terms of :meth:`SensitiveField.visible_to`; the gate's
    observable output is a JSON body. This runs :meth:`ResponseGate.apply` on a concrete
    instance and asserts the *keys* it emits for each principal are exactly those the
    matrix permits — so "permitted by the matrix" and "present in the body" are the same
    set. That equivalence is what makes the annotation-level guard a faithful proxy for
    Property 60's "absent from the serialized response body rather than present and
    unrendered".

    Feature: bhumisetu, Property 60.
    Validates: Requirements 26.1, 26.3, 26.4, 26.6, 26.7.
    """
    instance = _sample()
    for label, principal, _declared_owns in _matrix_principals():
        owns = principal_owns(_SampleOut, instance, principal)
        body = ResponseGate.apply(instance, principal, _SampleOut)
        expected = {
            field
            for field in _SampleOut.model_fields
            if _matrix_permits(sensitivity_of(_SampleOut, field), principal, owns)
        }
        assert set(body) == expected, f"{label}: body keys {set(body)} != matrix {expected}"


def test_discovery_finds_gated_models_and_excludes_test_only_ones() -> None:
    """The discovery mechanism is only trustworthy if it (a) actually finds a gated model
    that exists and (b) leaves test fixtures out of the production set.

    Both are shown here: the recursive subclass walk finds this file's own
    :class:`_SampleOut`, so it is not vacuously empty; and the production filter — keyed
    on the defining module — drops it, since it lives under ``tests`` rather than ``app``.
    Without the exclusion, every fixture in ``tests/test_gate.py`` would count as a shipped
    response model."""
    walked = _all_subclasses(GatedModel)
    assert _SampleOut in walked, "the subclass walk failed to find a model that exists"

    production = set(discover_production_gated_models())
    assert _SampleOut not in production, "a test fixture leaked into the production set"
    assert all(_is_production_model(cls) for cls in production)


def test_is_production_model_keys_on_the_defining_module() -> None:
    """The exclusion rule in isolation: a model defined under ``app`` is production, one
    defined by this test module is not."""
    assert _is_production_model(GatedModel)  # app.security.gate
    assert not _is_production_model(_SampleOut)  # tests.test_field_coverage

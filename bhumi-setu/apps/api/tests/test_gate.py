"""The serialization gate without a database: redaction by omission, and masking
(task 5.2, §8.2).

The gate is pure — a transform from a :class:`~app.security.gate.GatedModel` and a
:class:`~app.security.access.Principal` to a body — so all of it is exercised here
without Postgres, Redis, or an ASGI request. The route-level wiring (every router
built with ``route_class=GatedRoute``) and the static coverage guards (every field
annotated, every personal-data field carrying a ``Sensitive``) are tasks 5.3–5.6 and
live with those tasks; what is proven here is the mechanism they rely on.

Two correctness properties are the load-bearing claims:

* **Property 60** — an attribute the visibility matrix hides from a principal is
  *absent* from the body, not present and blanked.
* **Property 61** — a government identifier shown to a citizen renders at most its
  trailing four characters and the full value appears nowhere; a co-owned parcel
  carries a count and an aggregate share, never a per-owner record.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.retention.categories import OWNER_CONTACT, OWNER_IDENTITY
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

# The mask glyph is part of the observable contract; the tests assert against it
# directly rather than importing the private constant, so they check the output a
# client would see rather than the implementation that produced it.
_BULLET = "\u2022"


# ---------------------------------------------------------------------------
# Test models
# ---------------------------------------------------------------------------


class NoteOut(GatedModel):
    """A nested, officer-only note — stands in for R23.5 internal notes."""

    __owner_record_id_field__ = None
    body: str = Sensitive(Visibility.OFFICER_ONLY)


class OwnershipOut(GatedModel):
    """The design's canonical carrier (§8.2): public parcel facts, owner-only
    personal data, a masked identifier, and officer-only internal fields."""

    id: int = Sensitive(Visibility.PUBLIC)
    share: Decimal = Sensitive(Visibility.PUBLIC)
    owner_name: str | None = Sensitive(Visibility.OWNER_ONLY, data_category=OWNER_IDENTITY)
    government_identifier: str | None = Sensitive(
        Visibility.OWNER_ONLY, mask=Mask.TRAILING_4, data_category=OWNER_IDENTITY
    )
    contact_mobile: str | None = Sensitive(Visibility.OWNER_ONLY, data_category=OWNER_CONTACT)
    priority_score: float | None = Sensitive(Visibility.OFFICER_ONLY)
    internal_notes: list[NoteOut] = Sensitive(Visibility.OFFICER_ONLY)


class CitizenParcelOut(GatedModel):
    """The §8.4 "different model": a co-owned parcel as a citizen may see it — the
    count and aggregate share of *other* owners, and no per-owner collection at all."""

    __owner_record_id_field__ = None
    parcel_id: int = Sensitive(Visibility.PUBLIC)
    co_owner_count: int = Sensitive(Visibility.PUBLIC)
    other_share_total: Decimal = Sensitive(Visibility.PUBLIC)


class DisposalOut(GatedModel):
    """Carries a ``PERMISSION``-gated field, to exercise that visibility branch."""

    __owner_record_id_field__ = None
    id: int = Sensitive(Visibility.PUBLIC)
    unmasked_identifier: str = Sensitive(
        Visibility.PERMISSION, permission="dsar.dispose"
    )


class ParcelWithMyOwnership(GatedModel):
    """A wrapper holding a nested :class:`OwnershipOut`, to prove the gate recurses:
    the nested record's owner-only fields and mask obey the same principal."""

    __owner_record_id_field__ = None
    parcel_id: int = Sensitive(Visibility.PUBLIC)
    my_ownership: OwnershipOut = Sensitive(Visibility.PUBLIC)


# ---------------------------------------------------------------------------
# Principals
# ---------------------------------------------------------------------------


def _officer() -> Principal:
    return Principal(kind="OFFICER", id="officer-1", scope_paths=("MH",))


def _owner(record_id: int) -> Principal:
    return Principal(
        kind="CITIZEN", id="owner", case_id=1, owner_record_ids=(record_id,)
    )


def _non_owner(record_id: int) -> Principal:
    return Principal(
        kind="CITIZEN", id="stranger", case_id=2, owner_record_ids=(record_id + 1,)
    )


def _service(permissions: frozenset[str] = frozenset()) -> Principal:
    return Principal(kind="SERVICE", id="svc", permissions=permissions)


# ---------------------------------------------------------------------------
# Sensitive(): validation at model-definition time
# ---------------------------------------------------------------------------


def test_sensitive_records_the_annotation_in_json_schema_extra() -> None:
    ann = sensitivity_of(OwnershipOut, "government_identifier")
    assert ann == SensitiveField(
        visibility=Visibility.OWNER_ONLY,
        mask=Mask.TRAILING_4,
        permission=None,
        data_category=OWNER_IDENTITY,
    )


def test_a_permission_field_must_name_its_permission() -> None:
    with pytest.raises(ValueError, match="must name the permission"):
        Sensitive(Visibility.PERMISSION)


def test_a_permission_is_meaningless_without_permission_visibility() -> None:
    with pytest.raises(ValueError, match="only meaningful with Visibility.PERMISSION"):
        Sensitive(Visibility.OWNER_ONLY, permission="dsar.dispose")


def test_an_unknown_mask_is_refused() -> None:
    with pytest.raises(ValueError, match="unknown mask"):
        Sensitive(Visibility.OWNER_ONLY, mask="LEADING_2")


def test_an_unknown_data_category_is_refused() -> None:
    """Ties the redaction annotation to the retention vocabulary (§17.1): a typo is a
    definition-time error, not a sweep that later cannot find the attribute."""
    with pytest.raises(ValueError, match="unknown data_category"):
        Sensitive(Visibility.OWNER_ONLY, data_category="OWNER_SECRETS")


def test_a_non_visibility_is_refused() -> None:
    with pytest.raises(TypeError, match="visibility must be a Visibility"):
        Sensitive("PUBLIC")  # type: ignore[arg-type]


def test_sensitivity_of_returns_none_for_an_unannotated_field() -> None:
    class Plain(GatedModel):
        __owner_record_id_field__ = None
        note: str

    assert sensitivity_of(Plain, "note") is None


# ---------------------------------------------------------------------------
# visible_to(): the matrix, one cell at a time
# ---------------------------------------------------------------------------


def test_public_is_visible_to_every_kind() -> None:
    ann = SensitiveField(Visibility.PUBLIC)
    for principal in (_officer(), _owner(1), _non_owner(1), _service()):
        assert ann.visible_to(principal)


def test_officer_only_is_visible_only_to_officers() -> None:
    ann = SensitiveField(Visibility.OFFICER_ONLY)
    assert ann.visible_to(_officer())
    assert not ann.visible_to(_owner(1), owns=True)
    assert not ann.visible_to(_non_owner(1))
    assert not ann.visible_to(_service())


def test_owner_only_is_visible_to_officers_and_the_owning_citizen() -> None:
    ann = SensitiveField(Visibility.OWNER_ONLY)
    assert ann.visible_to(_officer())               # officers administer the record
    assert ann.visible_to(_owner(1), owns=True)     # the owning citizen
    assert not ann.visible_to(_owner(1), owns=False)  # a citizen who does not own it
    assert not ann.visible_to(_service())           # a service is neither


def test_permission_is_visible_only_with_the_named_permission() -> None:
    ann = SensitiveField(Visibility.PERMISSION, permission="dsar.dispose")
    assert ann.visible_to(_service(frozenset({"dsar.dispose"})))
    assert not ann.visible_to(_service(frozenset({"config.write"})))
    assert not ann.visible_to(_officer())           # officer without the permission
    assert not ann.visible_to(_owner(1), owns=True)  # citizens hold no permissions


# ---------------------------------------------------------------------------
# principal_owns(): ownership is a citizen concept
# ---------------------------------------------------------------------------


def test_ownership_by_record_id() -> None:
    inst = _sample_ownership(record_id=42)
    assert principal_owns(OwnershipOut, inst, _owner(42))
    assert not principal_owns(OwnershipOut, inst, _non_owner(42))


def test_ownership_is_false_for_officers_and_services() -> None:
    inst = _sample_ownership(record_id=42)
    assert not principal_owns(OwnershipOut, inst, _officer())
    assert not principal_owns(OwnershipOut, inst, _service())


def test_ownership_by_case_id_when_the_model_scopes_on_case() -> None:
    class CaseView(GatedModel):
        __owner_record_id_field__ = None
        __owner_case_id_field__ = "case_id"
        case_id: int = Sensitive(Visibility.PUBLIC)

    inst = CaseView(case_id=7)
    assert principal_owns(CaseView, inst, Principal(kind="CITIZEN", id="c", case_id=7))
    assert not principal_owns(CaseView, inst, Principal(kind="CITIZEN", id="c", case_id=8))


# ---------------------------------------------------------------------------
# ResponseGate.apply(): dispatch and plumbing
# ---------------------------------------------------------------------------


def test_a_redacted_field_is_absent_not_null() -> None:
    """R26.7 in its sharpest form: the key is gone, not present with a null value."""
    inst = _sample_ownership(record_id=42, owner_name="Asha", contact_mobile="9998887776")
    body = ResponseGate.apply(inst, _non_owner(42), OwnershipOut)
    assert "owner_name" not in body
    assert "owner_name" not in body.keys()
    # A null would still be a key; assert the redaction is omission, not blanking.
    assert body == {"id": 42, "share": "0.5"}


def test_apply_gates_each_element_of_a_list() -> None:
    a = _sample_ownership(record_id=1)
    b = _sample_ownership(record_id=2)
    stranger = Principal(kind="CITIZEN", id="stranger", case_id=99, owner_record_ids=(999,))
    bodies = ResponseGate.apply([a, b], stranger, OwnershipOut)
    assert bodies == [{"id": 1, "share": "0.5"}, {"id": 2, "share": "0.5"}]


def test_apply_coerces_a_bare_dict_through_the_declared_model() -> None:
    """Defensive: 5.4 forbids a handler returning a dict, but if one does the gate
    still redacts it rather than passing raw personal data through."""
    payload = {
        "id": 5,
        "share": "0.5",
        "owner_name": "Asha",
        "government_identifier": "AADHAAR123456",
        "contact_mobile": "9998887776",
        "priority_score": 0.9,
        "internal_notes": [],
    }
    body = ResponseGate.apply(payload, _non_owner(5), OwnershipOut)
    assert body == {"id": 5, "share": "0.5"}


def test_apply_with_no_principal_fails_closed() -> None:
    inst = _sample_ownership(record_id=42)
    assert ResponseGate.apply(inst, None, OwnershipOut) == {}


def test_apply_passes_through_a_non_gated_value_unchanged() -> None:
    assert ResponseGate.apply("not a model", _officer()) == "not a model"
    assert ResponseGate.apply(None, _officer()) is None


def test_an_unannotated_field_is_visible() -> None:
    class Mixed(GatedModel):
        __owner_record_id_field__ = None
        plain: int
        secret: str = Sensitive(Visibility.OFFICER_ONLY)

    body = ResponseGate.apply(Mixed(plain=3, secret="x"), _non_owner(1), Mixed)
    assert body == {"plain": 3}


def test_apply_recurses_into_a_nested_gated_model() -> None:
    """The nested record's owner-only fields and mask obey the request's principal:
    when the citizen owns the nested ownership record they see it, masked."""
    nested = _sample_ownership(
        record_id=77, owner_name="Asha", government_identifier="AADHAAR1234567"
    )
    wrapper = ParcelWithMyOwnership(parcel_id=9, my_ownership=nested)

    owner_body = ResponseGate.apply(wrapper, _owner(77), ParcelWithMyOwnership)
    assert owner_body["parcel_id"] == 9
    assert owner_body["my_ownership"]["owner_name"] == "Asha"
    assert owner_body["my_ownership"]["government_identifier"].endswith("4567")
    assert "AADHAAR1234567" not in json.dumps(owner_body)

    stranger_body = ResponseGate.apply(wrapper, _non_owner(77), ParcelWithMyOwnership)
    assert stranger_body["my_ownership"] == {"id": 77, "share": "0.5"}


def test_permission_field_presence_follows_the_permission() -> None:
    inst = DisposalOut(id=1, unmasked_identifier="AADHAAR123456")
    with_perm = ResponseGate.apply(inst, _service(frozenset({"dsar.dispose"})), DisposalOut)
    without = ResponseGate.apply(inst, _service(frozenset()), DisposalOut)
    assert with_perm == {"id": 1, "unmasked_identifier": "AADHAAR123456"}
    assert without == {"id": 1}


# ---------------------------------------------------------------------------
# Property 60: redacted attributes are absent from the response body
# ---------------------------------------------------------------------------


def test_property_60_ownership_matrix_is_exact() -> None:
    """Feature: bhumisetu, Property 60: every attribute the visibility matrix hides
    from a principal is absent from the body. Asserted as the exact key set each of
    the four principal kinds receives, so a field appearing where it should not — an
    officer's note, the priority score, or another owner's name — fails here.

    Validates: Requirements 20.8, 23.5, 26.1, 26.3, 26.4, 26.6, 26.7.
    """
    inst = _sample_ownership(
        record_id=42,
        owner_name="Asha Kumari",
        government_identifier="AADHAAR1234567890",
        contact_mobile="9876543210",
        priority_score=0.91,
        notes=["internal"],
    )

    assert set(ResponseGate.apply(inst, _officer(), OwnershipOut)) == {
        "id",
        "share",
        "owner_name",
        "government_identifier",
        "contact_mobile",
        "priority_score",
        "internal_notes",
    }
    assert set(ResponseGate.apply(inst, _owner(42), OwnershipOut)) == {
        "id",
        "share",
        "owner_name",
        "government_identifier",
        "contact_mobile",
    }
    assert set(ResponseGate.apply(inst, _non_owner(42), OwnershipOut)) == {"id", "share"}
    assert set(ResponseGate.apply(inst, _service(), OwnershipOut)) == {"id", "share"}


def _expected_present(field: str, principal: Principal, record_id: int) -> bool:
    """The visibility matrix, stated from the design rather than read from the gate.

    The gate and this oracle agree only because both are correct — the same
    discipline used for the policy validators (§20.8). Ownership is decided here
    directly from the record id and the principal's owned ids, independent of the
    gate's :func:`principal_owns`.
    """
    ann = sensitivity_of(OwnershipOut, field)
    if ann is None:
        return True
    owns = principal.kind == "CITIZEN" and record_id in principal.owner_record_ids
    if ann.visibility is Visibility.PUBLIC:
        return True
    if ann.visibility is Visibility.OFFICER_ONLY:
        return principal.kind == "OFFICER"
    if ann.visibility is Visibility.OWNER_ONLY:
        return principal.kind == "OFFICER" or (principal.kind == "CITIZEN" and owns)
    if ann.visibility is Visibility.PERMISSION:
        return bool(ann.permission) and principal.has_permission(ann.permission)
    return False


@st.composite
def _ownerships(draw) -> OwnershipOut:
    record_id = draw(st.integers(min_value=1, max_value=100_000))
    return OwnershipOut(
        id=record_id,
        share=draw(
            st.decimals(
                min_value=0, max_value=1, places=4, allow_nan=False, allow_infinity=False
            )
        ),
        owner_name=draw(st.one_of(st.none(), st.text(max_size=16))),
        government_identifier=draw(
            st.one_of(
                st.none(),
                st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", min_size=8, max_size=20),
            )
        ),
        contact_mobile=draw(st.one_of(st.none(), st.text(max_size=16))),
        priority_score=draw(
            st.one_of(st.none(), st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False))
        ),
        internal_notes=draw(st.lists(st.builds(NoteOut, body=st.text(max_size=8)), max_size=2)),
    )


@given(inst=_ownerships())
@settings(max_examples=150)
def test_property_60_presence_matches_visibility_for_any_values(inst: OwnershipOut) -> None:
    """Feature: bhumisetu, Property 60: whatever the field values, an attribute is
    present in the body exactly when the principal may see it and absent otherwise —
    a redacted attribute is never present-and-blanked.

    Validates: Requirements 26.1, 26.3, 26.4, 26.7.
    """
    principals = (_officer(), _owner(inst.id), _non_owner(inst.id), _service())
    for principal in principals:
        body = ResponseGate.apply(inst, principal, OwnershipOut)
        for field in OwnershipOut.model_fields:
            if _expected_present(field, principal, inst.id):
                assert field in body, f"{field} missing for {principal.kind}"
            else:
                assert field not in body, f"{field} leaked to {principal.kind}"


# ---------------------------------------------------------------------------
# Property 61: presented personal data is transformed as declared
# ---------------------------------------------------------------------------


@given(
    identifier=st.text(
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", min_size=8, max_size=20
    )
)
@settings(max_examples=150)
def test_property_61_identifier_masked_to_trailing_4_for_a_citizen(identifier: str) -> None:
    """Feature: bhumisetu, Property 61: for any government identifier presented to a
    citizen, at most its trailing 4 characters appear and the full stored value
    appears nowhere in the body (R26.5).

    Validates: Requirements 26.2, 26.5, 32.5.
    """
    inst = _sample_ownership(record_id=42, government_identifier=identifier)
    body = ResponseGate.apply(inst, _owner(42), OwnershipOut)
    masked = body["government_identifier"]

    # At most the trailing four characters of the original survive: everything
    # before them is the mask glyph, and the suffix is exactly those four.
    assert masked.endswith(identifier[-4:])
    assert set(masked[:-4]) <= {_BULLET}
    assert len(masked) == len(identifier)

    # The full value is nowhere in the serialized body.
    assert identifier not in json.dumps(body, ensure_ascii=False)


@given(
    identifier=st.text(
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", min_size=8, max_size=20
    )
)
@settings(max_examples=60)
def test_property_61_officer_sees_the_full_identifier(identifier: str) -> None:
    """The mask is a citizen-facing rule: an officer, who serves the notice, sees the
    identifier in full and unmasked."""
    inst = _sample_ownership(record_id=42, government_identifier=identifier)
    body = ResponseGate.apply(inst, _officer(), OwnershipOut)
    assert body["government_identifier"] == identifier
    assert _BULLET not in body["government_identifier"]


@given(
    count=st.integers(min_value=0, max_value=50),
    total=st.decimals(min_value=0, max_value=1, places=4, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=60)
def test_property_61_co_owned_parcel_carries_count_and_aggregate_only(
    count: int, total: Decimal
) -> None:
    """Feature: bhumisetu, Property 61: for a co-owned parcel, the citizen response
    carries the count of other ownership records and the aggregate remaining share and
    no per-owner record (R26.2). The §8.4 mechanism — a distinct model shape rather
    than a redaction — is what makes this hold: there is no per-owner field to leak.

    Validates: Requirements 26.2, 32.5.
    """
    inst = CitizenParcelOut(parcel_id=9, co_owner_count=count, other_share_total=total)
    body = ResponseGate.apply(inst, _owner(1), CitizenParcelOut)

    assert set(body) == {"parcel_id", "co_owner_count", "other_share_total"}
    assert body["co_owner_count"] == count
    # No field on the citizen model exposes an individual co-owner.
    assert not any(
        key in body for key in ("owners", "ownership_records", "other_owners", "co_owners")
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample_ownership(
    *,
    record_id: int,
    owner_name: str | None = "Asha",
    government_identifier: str | None = "AADHAAR1234567890",
    contact_mobile: str | None = "9876543210",
    priority_score: float | None = 0.5,
    notes: list[str] | None = None,
) -> OwnershipOut:
    return OwnershipOut(
        id=record_id,
        share=Decimal("0.5"),
        owner_name=owner_name,
        government_identifier=government_identifier,
        contact_mobile=contact_mobile,
        priority_score=priority_score,
        internal_notes=[NoteOut(body=text) for text in (notes or [])],
    )

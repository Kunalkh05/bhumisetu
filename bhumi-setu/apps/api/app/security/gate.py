"""Redaction at serialization, by omission, once, on the way out (§8.2).

Where :mod:`app.security.access` decides *which rows* a principal may see, this
module decides *which attributes of a row* reach the wire. The two are deliberately
separate mechanisms: scope is a ``WHERE`` clause on a query, redaction is a
transform on a response. R26.7 is specific that the redaction happens "at the
interface boundary, such that a redacted attribute is absent from the response body
rather than hidden in the rendered view" — so the mechanism here removes the field
from the serialized body entirely. A citizen reading the JSON, the HTML, or the raw
bytes finds no key, not a ``null`` and not an unrendered value.

Why the visibility rule lives on the field, not in the handler
--------------------------------------------------------------

Every response attribute carries its own visibility as an annotation
(:func:`Sensitive`), and the gate reads those annotations against the request's
:class:`~app.security.access.Principal`. The alternative — each handler deciding
what to strip for whom — is how a co-owner's name leaks the one time an author
forgets. Here the author cannot forget: the routers pass every response through
:meth:`ResponseGate.apply` (task 5.3), the field's own annotation says who may see
it, and masking is applied by the gate rather than by the handler. An endpoint that
returns a :class:`GatedModel` is redacted whether or not its author thought about
redaction.

The four visibilities and how they read the principal
-----------------------------------------------------

* :attr:`Visibility.PUBLIC` — any authenticated principal. The gate is only ever
  reached after :func:`~app.security.access.authenticate`, so "authenticated" is a
  given; a ``PUBLIC`` field is always present.
* :attr:`Visibility.OFFICER_ONLY` — officer principals only. This is how R23.5's
  internal notes, the risk figures, the priority score and officer identity stay
  out of every citizen response (Property 60).
* :attr:`Visibility.OWNER_ONLY` — the citizen who owns the referenced record, and
  officers (who administer it). A citizen who is *not* the owner does not see it,
  which is exactly R26.1: other owners' names, contact details and identifiers are
  absent. Ownership is decided from the principal's ``owner_record_ids`` / ``case_id``
  against the instance (see :func:`principal_owns`).
* :attr:`Visibility.PERMISSION` — gated on a named permission, read through
  ``principal.has_permission`` so the same predicate the rest of Access_Control uses
  decides it.

A service principal is neither an officer nor a citizen, so it sees ``PUBLIC`` and
whatever a ``PERMISSION`` field's permission it holds — never ``OWNER_ONLY`` or
``OFFICER_ONLY`` personal data. That is the fail-safe direction: an unclassified
caller sees less, not more.

Masking is the gate's job, not the field's value
-------------------------------------------------

R26.5 requires a government identifier shown to a citizen to render at most its
trailing four characters. The mask is declared on the annotation
(``mask="TRAILING_4"``) and applied *by the gate on the serialized value*, so the
full value never enters the response body and an endpoint author cannot forget to
mask it (§19.5). The field is excluded from :meth:`~pydantic.BaseModel.model_dump`
and its masked form written in afterwards, so the unmasked value is read from the
model instance — where it legitimately lives — transformed, and only then placed in
the body. Masking is a citizen-facing rule: an officer, who needs the full
identifier to serve a notice, sees it unmasked.

Why unannotated fields are visible rather than hidden
-----------------------------------------------------

The gate treats a field with no :func:`Sensitive` annotation as visible. It does
*not* itself enforce that every field is annotated — that is the job of the static
tests in tasks 5.4 and 5.5, which fail the build when a :class:`GatedModel` carries
an unannotated field or a personal-data field without a ``Sensitive(...)``. Making
the gate fail closed on an unannotated field would silently drop legitimate
non-sensitive fields during development and hide the missing annotation; making the
mistake a red test at PR time is the stronger guarantee (§8.3). The one exception is
a missing principal: with no principal the gate redacts everything, because the
absence of an identity is the one case where guessing generously is unsafe.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, ClassVar, Mapping

from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo

from app.retention.categories import (
    AUDIT_EVENT,
    DOCUMENT_CONTENT,
    LAND_RECORD,
    MODEL_FEATURE,
    NOT_PERSONAL,
    OWNER_CONTACT,
    OWNER_IDENTITY,
)
from app.security.access import Principal

__all__ = [
    "GatedModel",
    "Mask",
    "ResponseGate",
    "Sensitive",
    "SensitiveField",
    "Visibility",
    "principal_owns",
    "sensitivity_of",
]

#: The key under which a :func:`Sensitive` annotation is stored inside a field's
#: ``json_schema_extra``. Namespaced so it never collides with an OpenAPI extension
#: a future field might carry.
_EXTRA_KEY = "bhumisetu"


class Visibility(StrEnum):
    """Who may see an attribute (§8.2).

    A ``StrEnum`` so the value survives a round trip through ``json_schema_extra``
    (which participates in OpenAPI generation) as a plain string, and so a comparison
    against a stored value needs no conversion. The four values are the whole
    vocabulary — a field is visible to everyone authenticated, to officers, to the
    owning citizen, or to a holder of a named permission, and nothing else.
    """

    #: Any authenticated principal. The gate runs only after authentication, so a
    #: PUBLIC field is always present in the body.
    PUBLIC = "PUBLIC"
    #: The citizen who owns the referenced record, plus officers who administer it.
    OWNER_ONLY = "OWNER_ONLY"
    #: Officer principals only (R23.5 internal notes, risk figures, priority score).
    OFFICER_ONLY = "OFFICER_ONLY"
    #: Requires a named permission, checked via ``principal.has_permission``.
    PERMISSION = "PERMISSION"


class Mask:
    """The masks the gate knows how to apply.

    Not an ``Enum``: a mask name is a contract that appears in a field annotation and
    is matched by :func:`_apply_mask`, so it is a plain constant whose value is the
    contract. Only :attr:`TRAILING_4` exists today (R26.5); a new mask is a new
    constant plus a branch in :func:`_apply_mask`.
    """

    #: Render at most the trailing four characters; mask everything before them
    #: (R26.5). The masked prefix preserves length, which for a fixed-width
    #: government identifier discloses nothing the field's type does not already.
    TRAILING_4 = "TRAILING_4"


_KNOWN_MASKS: frozenset[str] = frozenset({Mask.TRAILING_4})

#: The mask glyph. A bullet rather than an ASCII character so a masked value is never
#: mistaken for part of an identifier's real content.
_MASK_GLYPH = "\u2022"

#: Every ``Data_Category`` name a :func:`Sensitive` field may declare. Built from the
#: constants in :mod:`app.retention.categories` so the redaction annotation and the
#: retention classification cannot name two different vocabularies — a typo in
#: ``data_category`` is rejected at model definition rather than discovered when the
#: retention sweep fails to find the attribute (§17.1).
_KNOWN_DATA_CATEGORIES: frozenset[str] = frozenset(
    {
        NOT_PERSONAL,
        OWNER_CONTACT,
        OWNER_IDENTITY,
        MODEL_FEATURE,
        LAND_RECORD,
        DOCUMENT_CONTENT,
        AUDIT_EVENT,
    }
)


def Sensitive(
    visibility: Visibility,
    *,
    mask: str | None = None,
    permission: str | None = None,
    data_category: str | None = None,
    **field_kwargs: Any,
) -> Any:
    """Declare a response field's visibility, mask, gating permission and category.

    A thin wrapper over :func:`pydantic.Field` that records the redaction metadata
    under ``json_schema_extra[{_EXTRA_KEY!r}]`` so :func:`sensitivity_of` can read it
    back and :meth:`ResponseGate.apply` can act on it. Any other keyword (``default``,
    ``description``, validation constraints) passes straight through to ``Field``.

    The arguments are validated at model-definition time — this runs when the class
    body is evaluated, so a mistake fails at import rather than on the first request:

    * a ``PERMISSION`` field must name the permission it requires, and a permission is
      meaningful only for a ``PERMISSION`` field;
    * a ``mask`` must be one the gate knows how to apply;
    * a ``data_category`` must be one of the retention categories (§17.1).

    :param visibility: who may see the field.
    :param mask: an optional mask (currently only ``"TRAILING_4"``) the gate applies
        to the serialized value for a citizen.
    :param permission: the permission a ``PERMISSION`` field requires.
    :param data_category: the ``Data_Category`` this attribute belongs to, tying the
        field to :mod:`app.retention.categories`.
    :returns: a ``FieldInfo`` carrying the annotation.
    """
    if not isinstance(visibility, Visibility):
        raise TypeError(
            f"visibility must be a Visibility, got {type(visibility).__name__}"
        )
    if visibility is Visibility.PERMISSION and not permission:
        raise ValueError(
            "a PERMISSION field must name the permission it requires, e.g. "
            "Sensitive(Visibility.PERMISSION, permission='dsar.dispose')"
        )
    if visibility is not Visibility.PERMISSION and permission is not None:
        raise ValueError(
            "permission= is only meaningful with Visibility.PERMISSION; a field "
            f"with {visibility} does not consult a permission"
        )
    if mask is not None and mask not in _KNOWN_MASKS:
        raise ValueError(
            f"unknown mask {mask!r}; the gate knows {sorted(_KNOWN_MASKS)}"
        )
    if data_category is not None and data_category not in _KNOWN_DATA_CATEGORIES:
        raise ValueError(
            f"unknown data_category {data_category!r}; it must be one of "
            f"{sorted(_KNOWN_DATA_CATEGORIES)} (see app.retention.categories)"
        )
    extra = {
        _EXTRA_KEY: {
            "visibility": visibility.value,
            "mask": mask,
            "permission": permission,
            "data_category": data_category,
        }
    }
    return Field(**field_kwargs, json_schema_extra=extra)


@dataclass(frozen=True)
class SensitiveField:
    """A field's redaction annotation, parsed back out of ``json_schema_extra``.

    Frozen and plain so the gate's decision is a pure function of this and the
    principal. :meth:`visible_to` is the single place the visibility rule is written;
    the gate and the field-coverage matrix test (task 5.5) both call it, so there is
    one definition of "who sees this" rather than two that could drift.
    """

    visibility: Visibility
    mask: str | None = None
    permission: str | None = None
    data_category: str | None = None

    def visible_to(self, principal: Principal, *, owns: bool = False) -> bool:
        """Whether ``principal`` may see this field.

        ``owns`` answers "is this principal the owner of the record being
        serialized?" — the gate computes it once per instance with
        :func:`principal_owns` and passes it in, because ownership is a property of
        the *instance*, not of the annotation. It is only consulted for
        ``OWNER_ONLY``.

        :param principal: the requesting principal.
        :param owns: whether the principal owns the record this field belongs to.
        :returns: ``True`` if the field should appear in the response body.
        """
        visibility = self.visibility
        if visibility is Visibility.PUBLIC:
            return True
        if visibility is Visibility.OFFICER_ONLY:
            return principal.kind == "OFFICER"
        if visibility is Visibility.OWNER_ONLY:
            # Officers administer the record and see the owner's data; the owning
            # citizen sees their own; every other citizen and every service does not.
            if principal.kind == "OFFICER":
                return True
            if principal.kind == "CITIZEN":
                return owns
            return False
        if visibility is Visibility.PERMISSION:
            return self.permission is not None and principal.has_permission(
                self.permission
            )
        # An unknown visibility fails closed rather than open. Unreachable while
        # Visibility is the only source of values, but the safe default if it grows.
        return False


def sensitivity_of(
    model: type[BaseModel], field_name: str
) -> SensitiveField | None:
    """Return the :class:`SensitiveField` annotation on ``model.field_name``, if any.

    Reads the metadata :func:`Sensitive` stored under ``json_schema_extra``. Returns
    ``None`` for a field with no annotation — the gate treats that as visible, and
    the static coverage tests (tasks 5.4, 5.5) are what require the annotation to be
    present. Exposed rather than inlined because task 5.5's redaction matrix reads it
    directly.
    """
    field: FieldInfo | None = model.model_fields.get(field_name)
    if field is None:
        return None
    extra = field.json_schema_extra
    if not isinstance(extra, Mapping):
        return None
    payload = extra.get(_EXTRA_KEY)
    if not isinstance(payload, Mapping):
        return None
    return SensitiveField(
        visibility=Visibility(payload["visibility"]),
        mask=payload.get("mask"),
        permission=payload.get("permission"),
        data_category=payload.get("data_category"),
    )


class GatedModel(BaseModel):
    """Base class for every response model that passes through the gate.

    Being a :class:`GatedModel` is the marker the route-table test (task 5.4) checks:
    a handler whose ``response_model`` is not a subclass of this fails the build, so a
    response cannot reach the wire ungated. The class itself adds no fields; it exists
    to be a type and to declare how ownership is determined for ``OWNER_ONLY`` fields.

    ``__owner_record_id_field__`` names the attribute whose value is the
    ownership-record id, matched against ``principal.owner_record_ids``. It defaults
    to ``"id"`` because the canonical ``OWNER_ONLY`` carrier is an ownership record
    keyed by its own id. A model whose ownership is scoped by case instead sets
    ``__owner_record_id_field__ = None`` and names ``__owner_case_id_field__`` (matched
    against ``principal.case_id``). A model with no ``OWNER_ONLY`` field never has
    either consulted.
    """

    #: The field whose value is the ownership-record id, matched against
    #: ``principal.owner_record_ids`` to decide ``OWNER_ONLY`` visibility.
    __owner_record_id_field__: ClassVar[str | None] = "id"
    #: The field whose value is the case id, matched against ``principal.case_id``.
    __owner_case_id_field__: ClassVar[str | None] = None


def principal_owns(
    model: type[GatedModel], instance: GatedModel, principal: Principal
) -> bool:
    """Whether ``principal`` owns the record ``instance`` represents (for ``OWNER_ONLY``).

    Ownership is a citizen concept: an officer's access to ``OWNER_ONLY`` data comes
    from being an officer, not from owning anything, and a service owns nothing. So
    this returns ``False`` for any non-citizen and lets :meth:`SensitiveField.visible_to`
    grant officers their access separately.

    For a citizen, the record is owned when the model's ownership-record id is among
    the principal's ``owner_record_ids``, or when its case id equals the principal's
    single ``case_id``. Either identifier being absent (an unset class attribute, a
    ``None`` value) simply does not match — the gate then withholds the field, which
    is the fail-closed direction.
    """
    if principal.kind != "CITIZEN":
        return False

    record_field = getattr(model, "__owner_record_id_field__", None)
    if record_field is not None:
        record_id = getattr(instance, record_field, None)
        if record_id is not None and record_id in principal.owner_record_ids:
            return True

    case_field = getattr(model, "__owner_case_id_field__", None)
    if case_field is not None:
        case_id = getattr(instance, case_field, None)
        if (
            case_id is not None
            and principal.case_id is not None
            and case_id == principal.case_id
        ):
            return True

    return False


def _trailing_4(value: str) -> str:
    """Mask all but the trailing four characters of ``value`` (R26.5).

    A value of four characters or fewer is returned whole — "at most the trailing
    four" is the whole of a short value. Government identifiers are longer than four
    characters (Aadhaar is twelve, PAN is ten), so in practice the leading portion is
    always masked and the full value never survives; the short-value case exists only
    so the function is total.
    """
    if len(value) <= 4:
        return value
    return _MASK_GLYPH * (len(value) - 4) + value[-4:]


def _apply_mask(mask: str, value: Any) -> Any:
    """Apply ``mask`` to a serialized ``value``. ``None`` masks to ``None``."""
    if value is None:
        return None
    if mask == Mask.TRAILING_4:
        return _trailing_4(str(value))
    raise ValueError(f"unknown mask {mask!r}")


def _is_gated_sequence(value: Any) -> bool:
    """Whether ``value`` is a non-empty list/tuple of :class:`GatedModel` instances,
    which the gate recurses into so each element is redacted for the principal."""
    return (
        isinstance(value, (list, tuple))
        and len(value) > 0
        and all(isinstance(item, GatedModel) for item in value)
    )


def _gate_instance(
    instance: GatedModel, principal: Principal | None
) -> dict[str, Any]:
    """Redact one :class:`GatedModel` instance for one principal.

    The algorithm is the whole of R26.7: decide each field's fate, then build the body
    once with the invisible and masked fields *excluded* from
    :meth:`~pydantic.BaseModel.model_dump`, and finally write back the masked values
    and the recursively-gated nested models. Excluding first means neither an
    invisible value nor an unmasked one is ever placed in the body — the field is
    absent, not present-and-blanked, and the full masked value is read from the
    instance and transformed rather than dumped and overwritten.
    """
    model = type(instance)
    # Ownership is only meaningful with a principal; without one every field fails
    # _field_visible below and is excluded, so owns is never actually consulted.
    owns = principal is not None and principal_owns(model, instance, principal)

    exclude: set[str] = set()
    to_mask: dict[str, str] = {}
    nested_models: dict[str, GatedModel] = {}
    nested_sequences: dict[str, list[GatedModel]] = {}

    for field_name in model.model_fields:
        annotation = sensitivity_of(model, field_name)
        if not _field_visible(annotation, principal, owns):
            exclude.add(field_name)
            continue

        value = getattr(instance, field_name)

        # A masked field is dropped from the dump and its masked form written back,
        # so the unmasked value never lands in the body. Masking is citizen-facing.
        if (
            annotation is not None
            and annotation.mask is not None
            and principal.kind == "CITIZEN"
            and value is not None
        ):
            exclude.add(field_name)
            to_mask[field_name] = annotation.mask
            continue

        # A nested gated model, or a list of them, is redacted at its own level and
        # written back, so its OWNER_ONLY / masked fields obey the same principal.
        if isinstance(value, GatedModel):
            exclude.add(field_name)
            nested_models[field_name] = value
            continue
        if _is_gated_sequence(value):
            exclude.add(field_name)
            nested_sequences[field_name] = list(value)
            continue

        # A plain, visible field is left for model_dump to serialize.

    body = instance.model_dump(exclude=exclude, mode="json")

    for field_name, mask in to_mask.items():
        body[field_name] = _apply_mask(mask, getattr(instance, field_name))
    for field_name, nested in nested_models.items():
        body[field_name] = _gate_instance(nested, principal)
    for field_name, sequence in nested_sequences.items():
        body[field_name] = [_gate_instance(item, principal) for item in sequence]

    return body


def _field_visible(
    annotation: SensitiveField | None, principal: Principal | None, owns: bool
) -> bool:
    """Whether a field with ``annotation`` is visible to ``principal``.

    An unannotated field is visible (the coverage tests, not the gate, require the
    annotation). A missing principal makes nothing visible — the one case where the
    gate fails closed, because acting without an identity is never safe.
    """
    if principal is None:
        return False
    if annotation is None:
        return True
    return annotation.visible_to(principal, owns=owns)


class ResponseGate:
    """The serialization gate: turn a response into the body a principal may see.

    One entry point, :meth:`apply`, which task 5.3's ``GatedRoute`` calls with the
    handler's return value, the request's principal, and the declared
    ``response_model``. It handles a single :class:`GatedModel`, a list of them, and —
    defensively — a bare ``dict`` it can validate through the declared model. The
    result is a JSON-serializable structure with every field the principal may not see
    absent and every masked field masked.
    """

    @staticmethod
    def apply(
        response: Any,
        principal: Principal | None,
        response_model: Any = None,
    ) -> Any:
        """Redact ``response`` for ``principal`` and return the JSON-able body.

        :param response: the handler's return value — a :class:`GatedModel`, a list of
            them, or (defensively) a ``dict`` that ``response_model`` can validate.
        :param principal: the requesting principal; ``None`` redacts everything.
        :param response_model: the route's declared response model, used only to
            coerce a returned ``dict`` into a :class:`GatedModel` before gating.
        :returns: the gated, JSON-serializable body.
        """
        if response is None:
            return None
        if isinstance(response, GatedModel):
            # A missing principal fails closed inside _gate_instance: every field is
            # excluded and the body is empty.
            return _gate_instance(response, principal)
        if isinstance(response, (list, tuple)):
            return [
                ResponseGate.apply(item, principal, response_model)
                for item in response
            ]
        if (
            isinstance(response, dict)
            and isinstance(response_model, type)
            and issubclass(response_model, GatedModel)
        ):
            return _gate_instance(response_model.model_validate(response), principal)  # type: ignore[arg-type]
        # Not a gated model and nothing to coerce it with. The route-table test (5.4)
        # is what makes this branch unreachable in production; the gate does not crash
        # on a value it was not built to redact, it passes it through unchanged.
        return response

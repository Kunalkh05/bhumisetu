"""Writing a policy value, with change control (§4.5, R28.3, R28.9).

Every write to ``policy_config`` goes through :meth:`PolicyService.set`. Nothing else
inserts into that table, because four things have to happen together and any one of
them being skipped is a defect that only shows up later:

1. the value is validated (task 2.4), so a broken cutoff set cannot take effect;
2. a new row is inserted rather than an existing one updated, which is what gives
   R28.3 its history and R7.8 its frozen deadlines;
3. a ``POLICY_CHANGED`` event is appended carrying the prior and new value;
4. the change is gated on the ``config.write`` permission (R2.5).

Why the event is inserted directly rather than through EventLog.append
---------------------------------------------------------------------

``EventLog.append`` lands in task 3.4 and does something this call site does not
need: it externalises personal-data attributes into ``personal_datum`` references
(§5.4). A policy value is a statutory period or a threshold — never personal data —
so the externalisation would be a no-op, and waiting for 3.4 to write this would
invert the dependency order the plan sets out.

The insert here is therefore correct rather than a shortcut, and it is deliberately
narrow: it sets ``has_pd_refs = false`` explicitly, so if a future policy key ever did
carry personal data the omission would be visible rather than implied. Task 3.4 may
absorb this; nothing here depends on it not doing so.

Two forward dependencies, marked rather than faked
--------------------------------------------------

**R28.9's report assertions.** The CHECK constraint from task 2.1 already refuses an
``ocr.threshold.*`` row with no ``justification_report_id`` — which is what R28.9
literally demands. The *stronger* checks §13.6 describes (the report is not
superseded, matches the current extraction model version and script set, and actually
states a precision figure at the new threshold) need the
``extraction_accuracy_report`` table, which task 16.7 creates.
:func:`_assert_report_supports_threshold` is the seam, and it raises
:class:`ReportAssertionUnavailable` if reached before that table exists rather than
passing silently. A silent pass would mean the first OCR threshold change after 16.7
lands is unvalidated and nobody notices.

**The reband pass.** A ``risk.band_cutoffs`` change must recompute the band of every
stored prediction from its existing probability (R19.9, task 22.10). That needs the
transactional outbox from task 3.8. :meth:`set` records the requirement in
:attr:`PolicyWriteResult.reband_required` so the caller cannot lose it, and the
enqueue is wired in 3.8.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol, Sequence

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.errors import DomainError, ErrorCode
from app.models.extraction_accuracy_report import ExtractionAccuracyReport
from app.services.policy import PLATFORM_WIDE, resolve_raw
from app.services.policy_validators import validate_policy_value

__all__ = [
    "CONFIG_WRITE_PERMISSION",
    "PolicyService",
    "PolicyWriteResult",
    "ReportAssertionUnavailable",
    "WriterPrincipal",
]

#: R2.5. The full permission registry lands in task 5.6; the constant lives here so
#: the check exists from the first write rather than being retrofitted.
CONFIG_WRITE_PERMISSION = "config.write"

#: A change to this key invalidates every stored Risk_Band (R19.9).
BAND_CUTOFFS_KEY = "risk.band_cutoffs"

#: Keys whose write R28.9 gates on an accuracy report.
OCR_THRESHOLD_PREFIX = "ocr.threshold."


class WriterPrincipal(Protocol):
    """What a policy write needs to know about its author.

    A Protocol because ``Principal`` proper arrives with Access_Control in task 5.1.
    Keeping the dependency this way round means the policy service never imports the
    security layer, and the security layer is free to grow.
    """

    id: str
    permissions: frozenset[str] | set[str]


class ReportAssertionUnavailable(RuntimeError):
    """R28.9's stronger checks were reached before task 16.7 built the table.

    Raised rather than passed over. If this silently succeeded, the first OCR
    threshold change after 16.7 lands would go unvalidated and nothing would say so.
    """


class NotAuthorisedToWritePolicy(DomainError):
    """R2.5: only a role holding ``config.write`` may change a policy value."""

    code = ErrorCode.NOT_AUTHORISED
    status_code = 403

    def __init__(self) -> None:
        # R2.3: a 403 carries no body detail, so refusing discloses nothing about
        # what exists.
        super().__init__("Not authorised", details={})


@dataclass(frozen=True)
class PolicyWriteResult:
    """What a write produced, including work the caller must not drop."""

    policy_config_id: int
    event_id: int
    prior_value: Any | None
    new_value: Any
    #: True when a reband pass is owed (task 22.10). Carried in the result rather
    #: than fired here, because the enqueue needs the outbox from task 3.8.
    reband_required: bool


def _assert_report_supports_threshold(
    session: Session, *, policy_key: str, value: Any, report_id: int
) -> None:
    """§13.6's assertions beyond the CHECK constraint.

    A CHECK can only require the reference to be non-null. What R28.9 is really
    asking is that the referenced report *supports* the threshold being set, which
    means reading the report.
    """
    report = session.execute(
        select(ExtractionAccuracyReport).where(ExtractionAccuracyReport.id == report_id)
    ).scalar_one_or_none()
    threshold_key = f"{float(value):g}"
    if report is None:
        raise ReportAssertionUnavailable(
            f"cannot validate {policy_key}: report {report_id} does not exist"
        )
    if report.superseded_at is not None:
        raise ReportAssertionUnavailable(
            f"cannot validate {policy_key}: report {report_id} is superseded"
        )
    precision = report.precision_at_threshold.get(threshold_key)
    if precision is None:
        raise ReportAssertionUnavailable(
            f"cannot validate {policy_key}: report {report_id} does not state "
            f"precision at threshold {threshold_key}"
        )


class PolicyService:
    """The only writer of ``policy_config``."""

    __slots__ = ("_session",)

    def __init__(self, session: Session) -> None:
        self._session = session

    def set(
        self,
        policy_key: str,
        value: Any,
        *,
        state: str = PLATFORM_WIDE,
        act: str | None = None,
        effective_from: date,
        actor: WriterPrincipal,
        justification_report_id: int | None = None,
        occurrence_time: date | None = None,
    ) -> PolicyWriteResult:
        """Insert a new version of ``policy_key`` and record the change.

        :raises NotAuthorisedToWritePolicy: without ``config.write`` (R2.5).
        :raises PolicyValueInvalid: if the value fails its validator (R28.7, R28.8).
        :raises ReportAssertionUnavailable: for an ``ocr.threshold.*`` key, until
            task 16.7 can read the report.
        """
        if CONFIG_WRITE_PERMISSION not in actor.permissions:
            raise NotAuthorisedToWritePolicy()

        # Before anything is written. A validator that ran after the insert would
        # leave the bad row visible to a concurrent reader inside this transaction.
        validate_policy_value(policy_key, value)

        if policy_key.startswith(OCR_THRESHOLD_PREFIX):
            if justification_report_id is None:
                # The CHECK constraint would also catch this, but a domain error
                # naming the requirement is more use than an IntegrityError.
                raise DomainError(
                    f"{policy_key} requires an accuracy report reference (R28.9)",
                    details={"policy_key": policy_key},
                )
            _assert_report_supports_threshold(
                self._session,
                policy_key=policy_key,
                value=value,
                report_id=justification_report_id,
            )

        # R28.3 needs the prior value, read as of the new row's effective date so
        # the recorded "from" is what this change actually supersedes — not
        # whatever happens to be current today.
        prior_value = resolve_raw(
            self._session, policy_key, state=state, act=act, as_of=effective_from
        )

        policy_config_id = self._session.execute(
            text(
                """
                INSERT INTO policy_config
                    (policy_key, state_key, act_key, effective_from, value,
                     justification_report_id, created_by)
                VALUES
                    (:key, :state, :act, :effective_from, CAST(:value AS jsonb),
                     :report, :actor)
                RETURNING id
                """
            ),
            {
                "key": policy_key,
                "state": state,
                "act": act,
                "effective_from": effective_from,
                "value": json.dumps(value),
                "report": justification_report_id,
                "actor": actor.id,
            },
        ).scalar_one()

        event_id = self._append_policy_changed(
            policy_key=policy_key,
            state=state,
            act=act,
            effective_from=effective_from,
            prior_value=prior_value,
            new_value=value,
            actor=actor,
            policy_config_id=policy_config_id,
            occurrence_time=occurrence_time or effective_from,
        )

        # Surface a constraint failure inside the caller's transaction, so a
        # unit_of_work that also changed state abandons that state too (R4.8).
        self._session.flush()

        return PolicyWriteResult(
            policy_config_id=policy_config_id,
            event_id=event_id,
            prior_value=prior_value,
            new_value=value,
            reband_required=policy_key == BAND_CUTOFFS_KEY,
        )

    def _append_policy_changed(
        self,
        *,
        policy_key: str,
        state: str,
        act: str | None,
        effective_from: date,
        prior_value: Any | None,
        new_value: Any,
        actor: WriterPrincipal,
        policy_config_id: int,
        occurrence_time: date,
    ) -> int:
        """R28.3's event. Direct insert; see the module docstring on why.

        ``has_pd_refs`` is set explicitly rather than left to its default, so a
        future policy key carrying personal data would be a visible omission here
        rather than an implied one.
        """
        payload = {
            "policy_key": policy_key,
            "state_key": state,
            "act_key": act,
            "effective_from": effective_from.isoformat(),
            "value": {"from": prior_value, "to": new_value},
        }
        return self._session.execute(
            text(
                """
                INSERT INTO event
                    (event_type, entity_type, entity_id, actor_type, actor_id,
                     occurrence_time, payload, has_pd_refs, provenance)
                VALUES
                    ('POLICY_CHANGED', 'policy_config', :entity_id, 'OFFICER',
                     :actor, :occurrence_time, CAST(:payload AS jsonb), false, 'MANUAL')
                RETURNING id
                """
            ),
            {
                "entity_id": policy_config_id,
                "actor": actor.id,
                "occurrence_time": occurrence_time,
                "payload": json.dumps(payload),
            },
        ).scalar_one()

    def history(
        self, policy_key: str, *, state: str = PLATFORM_WIDE, act: str | None = None
    ) -> Sequence[Any]:
        """R28.3: every version of a key, with its author and effective date.

        Reads ``policy_config`` rather than the event log. Both are complete, but the
        table is the authority on what is *in force* — the log records that a change
        happened, the table records what the configuration is.
        """
        return self._session.execute(
            text(
                """
                SELECT pc.id, pc.effective_from, pc.value, pc.created_at,
                       pc.created_by, pc.justification_report_id
                  FROM policy_config pc
                 WHERE pc.policy_key = :key
                   AND pc.state_key = :state
                   AND coalesce(pc.act_key, '') = coalesce(:act, '')
                 ORDER BY pc.effective_from DESC, pc.id DESC
                """
            ),
            {"key": policy_key, "state": state, "act": act},
        ).all()

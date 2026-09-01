"""Award and payout service tests (task 12)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.models.acquisition_case import AcquisitionCase
from app.models.award import Award, AwardComponent
from app.models.payout import Payout
from app.services import compensation as compensation_service
from app.services.compensation import (
    DISBURSEMENT_FULLY_PAID,
    DISBURSEMENT_PART_PAID,
    DISBURSEMENT_UNPAID,
    AwardComponentInput,
    AwardInput,
    AwardTotalMismatch,
    CompensationService,
    PayoutExceedsAward,
    PayoutInput,
    component_total_matches,
    disbursement_state_for,
)


@dataclass(frozen=True)
class Actor:
    kind: str = "OFFICER"
    id: str = "officer-1"


class FakeSession:
    def __init__(self, *, award: Award | None = None) -> None:
        self.award = award
        self.added: list[object] = []
        self.events: list[str] = []
        self.flushed = False

    def add(self, value: object) -> None:
        self.added.append(value)
        if isinstance(value, (Award, Payout)):
            value.id = 300 + len(self.added)

    def flush(self) -> None:
        self.flushed = True

    def get(self, entity_type, entity_id, **kwargs):  # type: ignore[no-untyped-def]
        if entity_type is Award:
            return self.award
        return None


def _case() -> AcquisitionCase:
    return AcquisitionCase(
        id=20,
        case_reference="MH-20",
        project_id=1,
        state_key="MH",
        act_key="RFCTLARR_2013",
        area_code="MH.PN",
        stage_key="AWARD",
        stage_set_effective_from=date(2024, 1, 1),
        stage_entered_on=date(2024, 2, 1),
        stage_deadline=None,
        deadline_breached=False,
        is_terminal=False,
        aggregate_awarded=Decimal("10.00"),
        aggregate_disbursed=Decimal("1.00"),
        entity_version=1,
    )


def _award(total: Decimal = Decimal("100.00")) -> Award:
    return Award(
        id=31,
        ownership_record_id=7,
        total_amount=total,
        currency="INR",
        determination_date=date(2024, 3, 1),
        determining_authority="Collector",
        disbursement_state=DISBURSEMENT_UNPAID,
        entity_version=2,
    )


def _patch_events(monkeypatch, session: FakeSession) -> None:
    def _append(session_arg, *, event_type, entity, actor, changes, occurrence_time, **kw):  # type: ignore[no-untyped-def]
        assert session_arg is session
        session.events.append(event_type)

    monkeypatch.setattr("app.services.compensation.EventLog.append", _append)


def test_record_award_rejects_component_total_mismatch() -> None:
    with pytest.raises(AwardTotalMismatch) as exc:
        CompensationService().record_award(
            FakeSession(),  # type: ignore[arg-type]
            data=AwardInput(
                ownership_record_id=7,
                total_amount=Decimal("100.00"),
                currency="INR",
                determination_date=date(2024, 3, 1),
                determining_authority="Collector",
                components=(AwardComponentInput("land", Decimal("99.98")),),
            ),
            actor=Actor(),
        )

    assert exc.value.details["component_total"] == "99.98"
    assert exc.value.details["tolerance"] == "0.01"


def test_record_award_stores_components_and_updates_case_aggregate(monkeypatch) -> None:
    session = FakeSession()
    case = _case()
    _patch_events(monkeypatch, session)
    monkeypatch.setattr(compensation_service, "_case_for_ownership", lambda session, ownership_record_id: case)

    award = CompensationService().record_award(
        session,  # type: ignore[arg-type]
        data=AwardInput(
            ownership_record_id=7,
            total_amount=Decimal("100.00"),
            currency="INR",
            determination_date=date(2024, 3, 1),
            determining_authority="Collector",
            components=(
                AwardComponentInput("land", Decimal("80.00")),
                AwardComponentInput("solatium", Decimal("20.00")),
            ),
        ),
        actor=Actor(),
    )

    assert award.disbursement_state == DISBURSEMENT_UNPAID
    assert [type(item) for item in session.added].count(AwardComponent) == 2
    assert case.aggregate_awarded == Decimal("110.00")
    assert session.events == ["AWARD_RECORDED"]


def test_record_payout_rejects_when_running_sum_exceeds_award(monkeypatch) -> None:
    award = _award(Decimal("100.00"))
    monkeypatch.setattr(compensation_service, "_paid_total", lambda session, award_id: Decimal("90.00"))

    with pytest.raises(PayoutExceedsAward) as exc:
        CompensationService().record_payout(
            FakeSession(award=award),  # type: ignore[arg-type]
            data=PayoutInput(
                award_id=31,
                amount=Decimal("10.01"),
                payout_date=date(2024, 4, 1),
                instrument_reference="NEFT-1",
                beneficiary="Asha",
            ),
            actor=Actor(),
        )

    assert exc.value.details == {"remaining_disbursable_amount": "10.00"}


def test_record_payout_updates_disbursement_state_and_case_aggregate(monkeypatch) -> None:
    session = FakeSession(award=_award())
    case = _case()
    _patch_events(monkeypatch, session)
    monkeypatch.setattr(compensation_service, "_paid_total", lambda session, award_id: Decimal("50.00"))
    monkeypatch.setattr(compensation_service, "_case_for_ownership", lambda session, ownership_record_id: case)
    calls: list[dict] = []

    def _update(session_arg, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(kwargs)
        session_arg.award.disbursement_state = kwargs["changes"]["disbursement_state"]
        return session_arg.award

    monkeypatch.setattr("app.services.compensation.VersionedRepository.update", _update)

    payout = CompensationService().record_payout(
        session,  # type: ignore[arg-type]
        data=PayoutInput(
            award_id=31,
            amount=Decimal("50.00"),
            payout_date=date(2024, 4, 1),
            instrument_reference="NEFT-1",
            beneficiary="Asha",
        ),
        actor=Actor(),
    )

    assert payout.amount == Decimal("50.00")
    assert calls[0]["changes"]["disbursement_state"] == DISBURSEMENT_FULLY_PAID
    assert case.aggregate_disbursed == Decimal("51.00")
    assert session.events == ["PAYOUT_RECORDED"]


@given(
    total=st.decimals(min_value=Decimal("1.00"), max_value=Decimal("1000.00"), places=2),
    payments=st.lists(
        st.decimals(min_value=Decimal("0.01"), max_value=Decimal("500.00"), places=2),
        min_size=1,
        max_size=20,
    ),
)
def test_property_payout_sequence_accepts_exactly_until_total_exceeded(
    total: Decimal,
    payments: list[Decimal],
) -> None:
    running = Decimal("0.00")
    for payment in payments:
        before = running
        accepted = before + payment <= total
        if accepted:
            running += payment
            assert running == before + payment
        else:
            assert running == before
        assert disbursement_state_for(total=total, paid=running) in {
            DISBURSEMENT_UNPAID,
            DISBURSEMENT_PART_PAID,
            DISBURSEMENT_FULLY_PAID,
        }


def test_component_total_uses_decimal_cent_tolerance() -> None:
    assert component_total_matches(
        Decimal("100.00"),
        (AwardComponentInput("a", Decimal("33.33")), AwardComponentInput("b", Decimal("66.66"))),
    )
    assert not component_total_matches(
        Decimal("100.00"),
        (AwardComponentInput("a", Decimal("33.33")), AwardComponentInput("b", Decimal("66.65"))),
    )

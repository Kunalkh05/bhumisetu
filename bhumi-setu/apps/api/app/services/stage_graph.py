"""The stage set as data (§4.3), and the deadline derived from it.

R7.2 forbids any legally significant period appearing in code. The stage set goes
further: the *stages themselves* are configuration, because India's acquisition
process is not uniform. One state runs social impact assessment, preliminary
notification, declaration, award, payout, possession; another runs a different act
with different stages and different names. An enum would make onboarding a state a
migration, which is precisely what §4.4 exists to avoid.

So ``acquisition_case.stage_key`` is ``text`` with no enum type and no CHECK
constraint (the column lands with the table in task 8.1). Validity is checked
against the *resolved* graph in this module, not against the schema.

Two dates, and they are not interchangeable
-------------------------------------------

Resolving a deadline reads configuration twice, as of two different dates, and
getting either wrong is a wrong statutory deadline:

``case.stage_set_effective_from``
    pins the *graph*. Set once at case creation and never moved. This is what keeps
    an in-flight case coherent when a state revises its stage set: a case that
    started under a five-stage process keeps resolving against five stages, and does
    not suddenly find its current stage does not exist. §1.2's last row records that
    migrating such a case to a new graph is a deliberate, audited operation rather
    than an automatic one.

``case.stage_entered_on``
    pins the *period*. R28.6 says resolution is against the relevant statutory event
    date, not today — so a case that entered a stage while the period was 365 days
    keeps its 365-day deadline after the period is shortened to 180. Using today
    instead would silently rewrite every open case's deadline the moment an
    administrator changed a period, and R7.8 forbids exactly that.

``period_key`` is a pointer, not a number
-----------------------------------------

A stage carries ``period_key: "period.pn.to_declaration"``, not ``period_days: 365``.
Two consequences. The stage graph itself contains no legal numbers, so it can be
shared across states that differ only in their periods. And the period is resolved
as of ``stage_entered_on`` while the graph is resolved as of
``stage_set_effective_from`` — impossible if the number were embedded in the graph,
because it would then be pinned to the graph's date.

A terminal stage has ``period_key: null`` and therefore no deadline. That is not a
missing value: a case that has reached possession has nothing left to be late for,
which is why :func:`stage_deadline` returns ``None`` rather than refusing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Mapping, Protocol, Sequence

from app.errors import DomainError, ErrorCode
from app.services.policy import PolicyResolver

__all__ = [
    "STAGE_SET_KEY",
    "CaseStageContext",
    "Stage",
    "StageGraph",
    "StageNotInGraph",
    "StageTransitionInvalid",
    "stage_deadline",
]

#: The Policy_Config key holding the stage set.
STAGE_SET_KEY = "policy.stage_set"


class StageNotInGraph(DomainError):
    """A case carries a stage the resolved graph does not declare.

    Reachable in one real situation: a state revised its stage set and a case was
    migrated to the new graph without its ``stage_key`` being remapped. Refusing
    loudly is the point — the alternative is treating the stage as terminal, which
    would silently stop the case ever being reported as late.
    """

    code = ErrorCode.STAGE_NOT_IN_GRAPH
    status_code = 409

    def __init__(self, stage_key: str, *, known: Sequence[str]) -> None:
        super().__init__(
            f"stage {stage_key!r} is not in the resolved stage set",
            details={"stage_key": stage_key, "known_stages": list(known)},
        )


class StageTransitionInvalid(DomainError):
    """R5.4: the target is not a declared successor, and the response says which are."""

    code = ErrorCode.STAGE_TRANSITION_INVALID
    status_code = 409

    def __init__(self, *, current: str, requested: str, permitted: Sequence[str]) -> None:
        super().__init__(
            f"{current!r} cannot transition to {requested!r}",
            details={
                "current_stage": current,
                "requested_stage": requested,
                # R5.4 requires the permitted set to be returned, so an officer is
                # told what is possible rather than only what was refused.
                "permitted_successors": list(permitted),
            },
        )


@dataclass(frozen=True)
class Stage:
    """One stage of the acquisition lifecycle, as configuration declares it."""

    key: str
    label_key: str | None
    successors: tuple[str, ...]
    period_key: str | None
    terminal: bool


@dataclass(frozen=True)
class StageGraph:
    """A resolved stage set. Frozen: it is configuration, not state.

    Constructed only by :meth:`from_policy_value`, which assumes the value has
    already passed ``validate_stage_graph`` on write (task 2.4). This class therefore
    does not re-validate reachability on every read — the write-time check is what
    makes that unnecessary.
    """

    stages: Mapping[str, Stage]
    first_key: str

    @classmethod
    def from_policy_value(cls, value: Any) -> StageGraph:
        raw_stages = value["stages"]
        stages = {
            entry["key"]: Stage(
                key=entry["key"],
                label_key=entry.get("label_key"),
                successors=tuple(entry.get("successors", ())),
                period_key=entry.get("period_key"),
                terminal=bool(entry.get("terminal", False)),
            )
            for entry in raw_stages
        }
        return cls(stages=stages, first_key=raw_stages[0]["key"])

    def stage(self, key: str) -> Stage:
        try:
            return self.stages[key]
        except KeyError:
            raise StageNotInGraph(key, known=sorted(self.stages)) from None

    def successors(self, key: str) -> tuple[str, ...]:
        return self.stage(key).successors

    def is_terminal(self, key: str) -> bool:
        return self.stage(key).terminal

    def assert_transition_permitted(self, *, current: str, requested: str) -> None:
        """R5.3, R5.4. Raises with the permitted set rather than a bare refusal."""
        permitted = self.successors(current)
        if requested not in permitted:
            raise StageTransitionInvalid(
                current=current, requested=requested, permitted=permitted
            )

    @property
    def terminal_keys(self) -> tuple[str, ...]:
        return tuple(sorted(k for k, s in self.stages.items() if s.terminal))

    def ordered_keys(self) -> tuple[str, ...]:
        """Stages in breadth-first order from the first declared stage.

        R22.2's dashboard iterates this rather than a fixed column list, which is
        what lets it render four stages for one state and five for another with no
        branch. Breadth-first from the start, not the declaration order, so a stage
        appears after the stages that can reach it.
        """
        seen = [self.first_key]
        queue = [self.first_key]
        while queue:
            current = queue.pop(0)
            for successor in self.stage(current).successors:
                if successor not in seen:
                    seen.append(successor)
                    queue.append(successor)
        # Any stage not reached is dead configuration; validate_stage_graph rejects
        # that on write, so append defensively rather than silently dropping it.
        seen.extend(sorted(set(self.stages) - set(seen)))
        return tuple(seen)


class CaseStageContext(Protocol):
    """What resolving a deadline needs from a case.

    A Protocol rather than the model, because ``acquisition_case`` does not exist
    until task 8.1 and this logic is testable now. It also keeps the dependency
    pointing the right way: the stage graph knows nothing about the ORM.
    """

    state_key: str
    act_key: str | None
    stage_key: str
    stage_set_effective_from: date
    stage_entered_on: date


def resolve_stage_graph(
    case: CaseStageContext, *, resolver: PolicyResolver
) -> StageGraph:
    """The graph in force for this case — pinned, not current."""
    return StageGraph.from_policy_value(
        resolver.get(
            STAGE_SET_KEY,
            state=case.state_key,
            act=case.act_key,
            as_of=case.stage_set_effective_from,
        )
    )


def stage_deadline(
    case: CaseStageContext, *, resolver: PolicyResolver
) -> date | None:
    """The date this case must leave its current stage by, or ``None`` if terminal.

    Two config reads, at two different dates, for the reasons in the module
    docstring. No arithmetic constant appears here: the day count comes from
    ``Policy_Config`` and reaches ``timedelta`` as a variable, so task 2.6's AST lint
    has nothing to catch and there is nothing for it to miss either.

    :raises PolicyValueMissing: if the stage set or the period is not configured.
        Until Q8 is confirmed nothing is seeded, so this is the expected answer
        rather than a fault (R28.5).
    """
    graph = resolve_stage_graph(case, resolver=resolver)
    stage = graph.stage(case.stage_key)

    if stage.period_key is None:
        # Terminal: nothing left to be late for.
        return None

    days = resolver.get(
        stage.period_key,
        state=case.state_key,
        act=case.act_key,
        # R28.6: the date the case entered the stage, not today.
        as_of=case.stage_entered_on,
    )
    return case.stage_entered_on + timedelta(days=int(days))

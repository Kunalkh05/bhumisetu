"""Declared label dependencies for train/serve leakage guards."""

from __future__ import annotations

__all__ = ["LABEL_SOURCE_ATTRIBUTES"]

# The task-22.6 label function will consume these outcome-side facts. Keeping the
# declaration separate now lets feature extractors be checked before labelling
# code lands.
LABEL_SOURCE_ATTRIBUTES = frozenset(
    {
        "deadline_outcome",
        "stage_exit_occurrence_time",
        "terminal_stage_reached",
    }
)

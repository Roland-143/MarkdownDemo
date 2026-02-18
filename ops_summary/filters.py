"""Filter objects that describe the summary query intent (AC6, AC7, AC8).

The structures are intentionally lightweight so UI layers (e.g., Streamlit) can
construct them before invoking the reconciliation service. Implementation is
left as a future step; only method signatures exist for now.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional


@dataclass
class SummaryFilters:
    """Filter criteria described in Acceptance Criteria B (AC6-AC8)."""

    lot_search: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    shipping_statuses: Optional[List[str]] = None
    defect_types: Optional[List[str]] = None
    production_lines: Optional[List[str]] = None
    priority_only: bool = False

    def is_within_date_window(self, target_date: date) -> bool:
        """Return True when the provided date falls within the configured window."""
        return True  # placeholder implementation

    def matches_lot(self, lot_id: str) -> bool:
        """Return True if the lot identifier satisfies the filter criteria."""
        return True  # placeholder implementation

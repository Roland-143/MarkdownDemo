"""Concrete inspection repository scaffolding."""

from __future__ import annotations

from typing import Sequence

from ops_summary import models
from ops_summary.filters import SummaryFilters


class InspectionRepository:
    """Placeholder adapter for ops.inspection_records + defect tables."""

    def __init__(self, db_engine) -> None:
        self._engine = db_engine

    def fetch_by_filters(
        self, filters: SummaryFilters
    ) -> Sequence[models.InspectionRecord]:
        """Return inspection rows plus derived defect information."""
        raise NotImplementedError("InspectionRepository.fetch_by_filters is a stub")

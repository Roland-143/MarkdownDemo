"""Abstract repository interfaces aligned with db/schema.sql."""

from __future__ import annotations

from typing import Protocol, Sequence

from ops_summary.filters import SummaryFilters
from ops_summary import models


class ProductionRepository(Protocol):
    """Contract for retrieving production records (docs/data_design.md §4.3)."""

    def fetch_by_filters(
        self, filters: SummaryFilters
    ) -> Sequence[models.ProductionRecord]:
        """Return production rows constrained by the provided filters."""
        ...


class InspectionRepository(Protocol):
    """Contract for retrieving inspection rows (docs/data_design.md §4.4)."""

    def fetch_by_filters(
        self, filters: SummaryFilters
    ) -> Sequence[models.InspectionRecord]:
        """Return inspection rows constrained by the provided filters."""
        ...


class ShippingRepository(Protocol):
    """Contract for retrieving shipping rows (docs/data_design.md §4.5)."""

    def fetch_by_filters(
        self, filters: SummaryFilters
    ) -> Sequence[models.ShippingRecord]:
        """Return shipping rows constrained by the provided filters."""
        ...

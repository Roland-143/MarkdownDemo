"""Concrete shipping repository scaffolding."""

from __future__ import annotations

from typing import Sequence

from ops_summary import models
from ops_summary.filters import SummaryFilters


class ShippingRepository:
    """Placeholder adapter for ops.shipping_records."""

    def __init__(self, db_engine) -> None:
        self._engine = db_engine

    def fetch_by_filters(
        self, filters: SummaryFilters
    ) -> Sequence[models.ShippingRecord]:
        """Return shipping rows limited by the provided filters."""
        raise NotImplementedError("ShippingRepository.fetch_by_filters is a stub")

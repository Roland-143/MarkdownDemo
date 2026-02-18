"""Concrete production repository scaffolding.

Future implementations should query ops.production_records (db/schema.sql) or
read spreadsheet sources. For now only method signatures are defined.
"""

from __future__ import annotations

from typing import Sequence

from ops_summary import models
from ops_summary.filters import SummaryFilters


class ProductionRepository:
    """Placeholder for the production data adapter."""

    def __init__(self, db_engine) -> None:
        """Store dependencies such as SQLAlchemy engines."""
        self._engine = db_engine

    def fetch_by_filters(
        self, filters: SummaryFilters
    ) -> Sequence[models.ProductionRecord]:
        """Load production rows limited by the specified filters."""
        raise NotImplementedError("ProductionRepository.fetch_by_filters is a stub")

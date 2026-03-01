"""Reconciliation service scaffold.

The service orchestrates record loading, alignment, summarization, filtering,
and drill-down preparation required by AC1-AC11. Only method signatures and
docstrings are provided; implementation will be added in future iterations.
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from ops_summary import models
from ops_summary.filters import SummaryFilters
from ops_summary.repositories.base import (
    ProductionRepository,
    InspectionRepository,
    ShippingRepository,
)


class ReconciliationService:
    """Coordinates repositories to build the operational summary view."""

    def __init__(
        self,
        production_repo: ProductionRepository,
        inspection_repo: InspectionRepository,
        shipping_repo: ShippingRepository,
    ) -> None:
        self._production_repo = production_repo
        self._inspection_repo = inspection_repo
        self._shipping_repo = shipping_repo

    def build_summary(
        self, filters: SummaryFilters
    ) -> Tuple[List[models.LotSummaryRow], int, Dict[str, models.DrillDownDetail]]:
        """Return (summary_rows, incomplete_count, drilldown_by_key) per AC1-AC11."""
        raise NotImplementedError("ReconciliationService.build_summary is a stub")

    def _align_records(
        self,
        production_rows: Sequence[models.ProductionRecord],
        inspection_rows: Sequence[models.InspectionRecord],
        shipping_rows: Sequence[models.ShippingRecord],
    ) -> Dict[str, models.DrillDownDetail]:
        """Match rows by lot/date and capture missing sources (AC1-AC4)."""
        raise NotImplementedError("ReconciliationService._align_records is a stub")

    def _project_summary_rows(
        self, drilldown_map: Dict[str, models.DrillDownDetail]
    ) -> List[models.LotSummaryRow]:
        """Convert drill-down data into summary rows (AC5-AC8)."""
        raise NotImplementedError(
            "ReconciliationService._project_summary_rows is a stub"
        )

    def _apply_filters(
        self, rows: Sequence[models.LotSummaryRow], filters: SummaryFilters
    ) -> List[models.LotSummaryRow]:
        """Apply lot/date/status/defect filters (AC6) and priority shaping (AC7-AC8)."""
        raise NotImplementedError("ReconciliationService._apply_filters is a stub")

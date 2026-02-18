"""Streamlit controller scaffolding for the operational summary UI.

Functions mirror the Acceptance Criteria requirements but contain no business
logic yet. They provide hook points for filters, table rendering, and
drill-down interactions.
"""

from __future__ import annotations

from typing import Dict, Sequence

from ops_summary.filters import SummaryFilters
from ops_summary import models
from ops_summary.services import reconciliation_service


def render_app(service: reconciliation_service.ReconciliationService) -> None:
    """Entry point that will orchestrate the Streamlit experience."""
    raise NotImplementedError("render_app will orchestrate the Streamlit UI")


def _render_filters_panel() -> SummaryFilters:
    """Render filter widgets and return the resulting SummaryFilters object."""
    raise NotImplementedError("_render_filters_panel is UI scaffolding")


def _render_summary_table(rows: Sequence[models.LotSummaryRow]) -> None:
    """Render the operational summary table (AC5-AC8)."""
    raise NotImplementedError("_render_summary_table is UI scaffolding")


def _render_drilldown(details: Dict[str, models.DrillDownDetail]) -> None:
    """Render the drill-down and traceability view (AC9-AC11)."""
    raise NotImplementedError("_render_drilldown is UI scaffolding")

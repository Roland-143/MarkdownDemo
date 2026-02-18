"""Domain models for the operational summary scaffold.

Structures in this module follow the attributes described in docs/data_design.md
and the Postgres schema defined in db/schema.sql. Only field declarations are
provided—no business logic or validation is implemented yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass
class SourceReference:
    """Traceability metadata for a single row (AC5, AC9-AC11)."""

    source_system: str
    source_file: Optional[str] = None
    source_sheet: Optional[str] = None
    record_identifier: Optional[str] = None


@dataclass
class ProductionRecord:
    """Prototype model for ops.production_records (see docs/data_design.md §4.3)."""

    lot_id: str
    production_date: date
    production_line: Optional[str] = None
    part_number: Optional[str] = None
    units_planned: Optional[int] = None
    units_actual: Optional[int] = None
    downtime_minutes: Optional[int] = None
    line_issue_flag: Optional[bool] = None
    primary_issue: Optional[str] = None
    reference: Optional[SourceReference] = None


@dataclass
class InspectionRecord:
    """Prototype model for ops.inspection_records (docs/data_design.md §4.4)."""

    lot_id: str
    inspection_date: date
    overall_result: Optional[str] = None
    defect_codes: List[str] = field(default_factory=list)
    total_defects: Optional[int] = None
    reference: Optional[SourceReference] = None


@dataclass
class ShippingRecord:
    """Prototype model for ops.shipping_records (docs/data_design.md §4.5)."""

    lot_id: str
    ship_date: Optional[date]
    ship_status: Optional[str] = None
    qty_shipped: Optional[int] = None
    destination_state: Optional[str] = None
    reference: Optional[SourceReference] = None


@dataclass
class LotSummaryRow:
    """Aggregated summary row used by the UI (AC5-AC8)."""

    lot_id: str
    record_date: date
    production_line: Optional[str] = None
    units_planned: Optional[int] = None
    units_actual: Optional[int] = None
    inspection_summary: Optional[str] = None
    defect_types: List[str] = field(default_factory=list)
    total_defects: Optional[int] = None
    ship_status: Optional[str] = None
    ship_date: Optional[date] = None
    qty_shipped: Optional[int] = None
    reconciliation_status: Optional[str] = None
    status_reason: Optional[str] = None
    missing_production: bool = False
    missing_inspection: bool = False
    missing_shipping: bool = False
    priority_flag: bool = False
    reference: Optional[SourceReference] = None


@dataclass
class DrillDownDetail:
    """Detailed source snapshot shown when a row is selected (AC9-AC11)."""

    lot_id: str
    record_date: date
    reconciliation_basis: Optional[str] = None
    production_records: List[ProductionRecord] = field(default_factory=list)
    inspection_records: List[InspectionRecord] = field(default_factory=list)
    shipping_records: List[ShippingRecord] = field(default_factory=list)
    missing_sources: List[str] = field(default_factory=list)
    insufficient_fields: List[str] = field(default_factory=list)
    mismatches: List[str] = field(default_factory=list)

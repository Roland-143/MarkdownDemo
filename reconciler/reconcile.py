"""Core reconciliation logic for the operational summary Streamlit app.

Detailed notes (per project requirement for junior engineers):
- Purpose: reconcile production, inspection, and shipping sources into a single
  summary view that satisfies AC1–AC11.
- Data volume assumption: small enough to fit in memory; time complexity is
  O(P + S + I + U) where P/S/I are row counts for each source and U is the
  number of unique `(lot, record_date)` keys.
- Space complexity: O(P + S + I + U) due to intermediate DataFrames plus the
  resulting summary.
- All pandas DataFrames used here are copies to avoid mutating caller inputs,
  which makes testing deterministic.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .normalize import canonicalize_lot

# Shipping statuses that the UI recognizes for filtering.
_SHIP_STATUS_ALLOWED = {
    "shipped",
    "partial",
    "on_hold",
    "backordered",
    "not_shipped",
    "unknown",
}

# Shipped lots with defects are the "priority" cohort.
_PRIORITY_SHIP_STATUSES = {"shipped", "partial"}

# Inspection column aliases to keep ingestion flexible.
_INSPECTION_DEFECT_COLUMNS = [
    "Defect Type",
    "Defect Code",
    "Defect",
    "defect_type",
    "defect_code",
]
_INSPECTION_QTY_COLUMNS = ["Qty Defects", "Defect Qty", "qty_defects"]


def _normalize_df(df: pd.DataFrame, lot_col: str, date_col: str) -> pd.DataFrame:
    """Return a normalized copy with canonical lot IDs and alignment dates.

    Complexity: O(n) time / space for n rows because every column operation is
    vectorized. This function is intentionally pure (returns a copy) so callers
    never mutate their original DataFrames.
    """
    normalized = df.copy()  # copy guards caller state and makes unit tests easy
    normalized[lot_col] = normalized.get(lot_col)  # missing columns become NaN
    normalized[date_col] = normalized.get(date_col)
    normalized[date_col] = pd.to_datetime(
        normalized[date_col], errors="coerce"
    ).dt.date  # converts any parseable date string to datetime.date
    normalized["lot"] = normalized[lot_col].apply(canonicalize_lot)  # AC1 key
    normalized["record_date"] = normalized[date_col]  # canonical alignment date
    return normalized


def _canonical_ship_status(value: Any) -> str:
    """Normalize shipping status strings (O(1) time/space)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "unknown"
    status = str(value).strip().lower()
    return status if status in _SHIP_STATUS_ALLOWED else "unknown"


def _extract_defect_metrics(
    ins_rows: pd.DataFrame,
) -> Tuple[Optional[int], Optional[str], Optional[str], List[str]]:
    """Summarize inspection rows into totals, top defect, and type list.

    Complexity: O(k) for k inspection rows because each column is scanned once.
    """
    if ins_rows.empty:
        return None, None, None, []

    qty_col = next((c for c in _INSPECTION_QTY_COLUMNS if c in ins_rows.columns), None)
    if qty_col:
        qty_series = pd.to_numeric(ins_rows[qty_col], errors="coerce").fillna(0)
        total_defects = int(qty_series.sum())
    else:
        total_defects = int(len(ins_rows))

    defect_series = None
    for column in _INSPECTION_DEFECT_COLUMNS:
        if column in ins_rows.columns:
            defect_series = ins_rows[column].dropna().astype(str).str.upper()
            break

    defect_types: List[str] = []
    top_defect_code: Optional[str] = None
    summary_string: Optional[str] = None
    if defect_series is not None and not defect_series.empty:
        defect_counts = defect_series.value_counts()
        defect_types = defect_counts.index.tolist()
        top_defect_code = defect_types[0] if defect_types else None
        summary_string = "; ".join(
            f"{code}:{defect_counts[code]}" for code in defect_counts.index
        )

    return total_defects, top_defect_code, summary_string, defect_types


def _collect_reference_hints(rows: pd.DataFrame) -> List[Dict[str, Any]]:
    """Extract traceability hints for drill-down (O(r) for r rows)."""
    hints: List[Dict[str, Any]] = []
    reference_fields = [
        "source_file",
        "source_sheet",
        "source_row_id",
        "import_batch_id",
        "record_id",
    ]
    for _, row in rows.iterrows():
        hint = {
            field: row[field]
            for field in reference_fields
            if field in row and pd.notna(row[field])
        }
        if hint:
            hints.append(hint)
    return hints


def _build_status_and_reasons(
    missing_production: bool,
    missing_inspection: bool,
    missing_shipping: bool,
    critical_missing_fields: List[str],
) -> Tuple[str, Optional[str], List[str]]:
    """Compute reconciliation status, reason, and missing source list (O(1))."""
    missing_sources: List[str] = []
    if missing_production:
        missing_sources.append("production")
    if missing_inspection:
        missing_sources.append("inspection")
    if missing_shipping:
        missing_sources.append("shipping")

    if missing_sources:
        return "missing_sources", ", ".join(missing_sources), missing_sources

    if critical_missing_fields:
        return "insufficient_data", "; ".join(critical_missing_fields), []

    return "reconciled", None, []


def reconcile(
    production: pd.DataFrame,
    shipping: pd.DataFrame,
    inspection: Optional[pd.DataFrame] = None,
) -> Tuple[pd.DataFrame, int, Dict[str, Any]]:
    """Reconcile production, inspection, and shipping DataFrames.

    Steps:
    1. Normalize each input (O(P+S+I)).
    2. Count incomplete rows (missing lot/date) per AC3.
    3. Build union keys and iterate (O(U + per-key row scans)).
    4. Populate summary rows + drill-down metadata.

    Returns:
        summary_df: Table satisfying AC5–AC8.
        incomplete_count: integer count for AC3 metric.
        details: dict used by the UI for AC9–AC11 drill-down.
    """
    prod = _normalize_df(production, "Lot ID", "Date")
    ship = _normalize_df(shipping, "Lot ID", "Ship Date")
    ins = (
        _normalize_df(inspection, "Lot ID", "Inspection Date")
        if inspection is not None
        else None
    )

    def _incomplete(df: pd.DataFrame) -> pd.DataFrame:
        return df[df["lot"].isna() | df["record_date"].isna()]

    prod_incomplete = _incomplete(prod)
    ship_incomplete = _incomplete(ship)
    ins_incomplete = _incomplete(ins) if ins is not None else pd.DataFrame()

    incomplete_count = int(
        len(prod_incomplete) + len(ship_incomplete) + len(ins_incomplete)
    )

    prod_valid = prod.dropna(subset=["lot", "record_date"])
    ship_valid = ship.dropna(subset=["lot", "record_date"])
    ins_valid = ins.dropna(subset=["lot", "record_date"]) if ins is not None else None

    keys = set(zip(prod_valid["lot"], prod_valid["record_date"]))
    keys.update(zip(ship_valid["lot"], ship_valid["record_date"]))
    if ins_valid is not None:
        keys.update(zip(ins_valid["lot"], ins_valid["record_date"]))

    summary_rows: List[Dict[str, Any]] = []
    details: Dict[str, Any] = {}

    for lot, rec_date in sorted(keys):
        prod_rows = prod_valid[
            (prod_valid["lot"] == lot) & (prod_valid["record_date"] == rec_date)
        ]
        ship_rows = ship_valid[
            (ship_valid["lot"] == lot) & (ship_valid["record_date"] == rec_date)
        ]
        ins_rows = (
            ins_valid[
                (ins_valid["lot"] == lot) & (ins_valid["record_date"] == rec_date)
            ]
            if ins_valid is not None
            else pd.DataFrame()
        )

        production_line = (
            prod_rows["Production Line"].iloc[0]
            if not prod_rows.empty and "Production Line" in prod_rows.columns
            else None
        )
        units_planned = (
            prod_rows["Units Planned"].iloc[0]
            if not prod_rows.empty and "Units Planned" in prod_rows.columns
            else None
        )
        units_actual = (
            prod_rows["Units Actual"].iloc[0]
            if not prod_rows.empty and "Units Actual" in prod_rows.columns
            else None
        )

        ship_status = (
            _canonical_ship_status(ship_rows["Ship Status"].iloc[0])
            if not ship_rows.empty and "Ship Status" in ship_rows.columns
            else "unknown"
        )
        ship_date = (
            ship_rows["Ship Date"].iloc[0]
            if not ship_rows.empty and "Ship Date" in ship_rows.columns
            else None
        )
        qty_shipped = (
            ship_rows["Qty Shipped"].iloc[0]
            if not ship_rows.empty and "Qty Shipped" in ship_rows.columns
            else None
        )

        total_defects, top_defect_code, inspection_summary, defect_types = (
            _extract_defect_metrics(ins_rows)
        )

        missing_production = prod_rows.empty
        missing_inspection = ins_valid is None or ins_rows.empty
        missing_shipping = ship_rows.empty

        critical_missing_fields: List[str] = []
        if not missing_production and units_actual is None and units_planned is None:
            critical_missing_fields.append("production metrics missing")
        if not missing_shipping and ship_status == "unknown":
            critical_missing_fields.append("shipping status unknown")
        if not missing_inspection and total_defects is None:
            critical_missing_fields.append("inspection details missing")

        status, status_reason, missing_sources_list = _build_status_and_reasons(
            missing_production,
            missing_inspection,
            missing_shipping,
            critical_missing_fields,
        )

        mismatches: List[str] = []
        if (
            units_actual is not None
            and qty_shipped is not None
            and units_actual != qty_shipped
        ):
            mismatches.append(
                f"Units actual ({units_actual}) != Qty shipped ({qty_shipped})"
            )

        source_refs = {
            "production_rows": prod_rows.to_dict(orient="records")
            if not prod_rows.empty
            else [],
            "inspection_rows": ins_rows.to_dict(orient="records")
            if not ins_rows.empty
            else [],
            "shipping_rows": ship_rows.to_dict(orient="records")
            if not ship_rows.empty
            else [],
            "reference_hints": {
                "production": _collect_reference_hints(prod_rows),
                "inspection": _collect_reference_hints(ins_rows),
                "shipping": _collect_reference_hints(ship_rows),
            },
        }

        summary_rows.append(
            {
                "lot": lot,
                "record_date": rec_date,
                "production_line": production_line,
                "units_planned": units_planned,
                "units_actual": units_actual,
                "inspection_summary": inspection_summary,
                "total_defects": total_defects,
                "top_defect_code": top_defect_code,
                "defect_types": defect_types,
                "defect_types_display": ", ".join(defect_types)
                if defect_types
                else None,
                "ship_status": ship_status,
                "ship_date": ship_date,
                "qty_shipped": qty_shipped,
                "reconciliation_status": status,
                "status_reason": status_reason,
                "missing_production": missing_production,
                "missing_inspection": missing_inspection,
                "missing_shipping": missing_shipping,
                "source_refs": source_refs,
            }
        )

        detail_key = f"{lot}|{rec_date}"
        details[detail_key] = {
            "lot": lot,
            "record_date": str(rec_date),
            "reconciliation_basis": "lot + record_date",
            "missing_sources": missing_sources_list,
            "insufficient_fields": critical_missing_fields,
            "status": status,
            "status_reason": status_reason,
            "mismatches": mismatches,
            "source_refs": source_refs,
        }

    summary_df = pd.DataFrame(summary_rows)

    if summary_df.empty:
        return summary_df, incomplete_count, details

    defect_counts = (
        pd.to_numeric(summary_df["total_defects"], errors="coerce").fillna(0).astype(int)
    )
    summary_df["priority_flag"] = summary_df["ship_status"].isin(
        _PRIORITY_SHIP_STATUSES
    ) & (defect_counts > 0)
    summary_df["priority_badge"] = summary_df["priority_flag"].apply(
        lambda flag: "PRIORITY" if flag else ""
    )
    summary_df["priority_bucket"] = summary_df["priority_flag"].astype(int)
    summary_df["priority_defects"] = defect_counts
    summary_df["priority_date"] = pd.to_datetime(summary_df["record_date"])

    def _source_summary(refs: Dict[str, Any]) -> str:
        prod_ct = len(refs.get("production_rows", []))
        ship_ct = len(refs.get("shipping_rows", []))
        ins_ct = len(refs.get("inspection_rows", []))
        return f"P:{prod_ct} / I:{ins_ct} / S:{ship_ct}"

    summary_df["source_summary"] = summary_df["source_refs"].apply(_source_summary)

    return summary_df, incomplete_count, details

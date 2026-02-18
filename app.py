"""Streamlit front-end for the operational reconciliation tool.

Key capabilities that map directly to the acceptance criteria:
- AC5: Presents a tabular summary that includes production, inspection, and
  shipping metrics plus source references.
- AC6: Sidebar filters for Lot ID, date range, shipping status, defect type,
  and production line.
- AC7: Priority badge and optional filter for shipped lots with defects.
- AC8: Default sort order prioritizes priority rows, defect quantity, and recency.
- AC9-AC11: Detail pane lists source rows, reconciliation basis, and missing data.
"""

from datetime import date
import os
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from pandas.io.formats.style import Styler

from reconciler.reconcile import reconcile

# Column alias dictionaries keep database snake_case columns compatible with
# the spreadsheet-style headers expected by the reconciliation engine.
PRODUCTION_ALIAS_MAP = {
    "Lot ID": ["lot_id", "lot_code"],
    "Date": ["production_date"],
    "Production Line": ["production_line"],
    "Units Planned": ["units_planned"],
    "Units Actual": ["units_actual"],
}

SHIPPING_ALIAS_MAP = {
    "Lot ID": ["lot_id", "lot_code"],
    "Ship Date": ["ship_date"],
    "Ship Status": ["ship_status"],
    "Qty Shipped": ["qty_shipped"],
}

INSPECTION_ALIAS_MAP = {
    "Lot ID": ["lot_id", "lot_code"],
    "Inspection Date": ["inspection_date"],
    "Qty Defects": ["qty_defects"],
    "Defect Type": ["defect_type", "defect_code"],
}

# Table name candidates allow fallback when schemas differ.
PRODUCTION_TABLE_CANDIDATES = [
    "ops.production_records",
    "production_records",
    "public.production_records",
]
SHIPPING_TABLE_CANDIDATES = [
    "ops.shipping_records",
    "shipping_records",
    "public.shipping_records",
]
INSPECTION_TABLE_CANDIDATES = [
    "ops.inspection_records",
    "inspection_records",
    "public.inspection_records",
]
LOT_LOOKUP_CANDIDATES = [
    "ops.lots",
    "lots",
    "public.lots",
]

# Styling constants shared across tables.
TEXT_COLOR = "#000000"
BASE_BG = "#fff4e8"
PRIORITY_BG = "#f5d6c3"
BORDER_ACCENT = "#b76e79"
BORDER_NEUTRAL = "#d9c3b0"

# Load environment variables once; Streamlit reruns this script on every
# interaction so we keep the call at module import time.
load_dotenv()

DB_URL = os.getenv("DATABASE_URL")


def _read_table_from_db(database_url: str, table_name: str) -> pd.DataFrame:
    """Fetch an entire table via SQLAlchemy with resource-safe semantics.

    Time complexity: O(n) for n returned rows because pandas builds a DataFrame
    from the cursor stream. The engine and connection are closed deterministically
    via context managers to avoid connection leaks.
    """
    engine = create_engine(database_url)
    try:
        with engine.connect() as conn:
            query = text(f"SELECT * FROM {table_name}")
            df = pd.read_sql(query, conn)
    finally:
        engine.dispose()
    return df


def _harmonize_columns(df: Optional[pd.DataFrame], alias_map: Dict[str, List[str]]) -> Optional[pd.DataFrame]:
    """Rename DataFrame columns to canonical spreadsheet headers (O(c)).

    Args:
        df: Source DataFrame or None.
        alias_map: Mapping of canonical column names -> list of alias candidates.

    Returns:
        DataFrame with columns renamed where needed. None is passed through.
    """

    if df is None:
        return None

    rename_dict: Dict[str, str] = {}
    for canonical, aliases in alias_map.items():
        if canonical in df.columns:
            continue
        for alias in aliases:
            if alias in df.columns:
                rename_dict[alias] = canonical
                break
    if rename_dict:
        return df.rename(columns=rename_dict)
    return df


def _read_table_with_candidates(database_url: str, candidates: List[str]) -> pd.DataFrame:
    """Attempt to read tables using the provided name fallbacks."""
    errors: List[str] = []
    for table_name in candidates:
        try:
            return _read_table_from_db(database_url, table_name)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{table_name}: {exc}")
    raise RuntimeError("; ".join(errors))


def _load_lot_lookup(database_url: str) -> Dict[Any, Any]:
    """Return a mapping of lot_id -> lot_code using available candidates."""
    lot_df = _read_table_with_candidates(database_url, LOT_LOOKUP_CANDIDATES)
    if "lot_id" not in lot_df.columns:
        raise RuntimeError("lot_id column missing from lot lookup table")
    lot_code_column = (
        "lot_code"
        if "lot_code" in lot_df.columns
        else ("Lot ID" if "Lot ID" in lot_df.columns else None)
    )
    if lot_code_column is None:
        raise RuntimeError("lot_code column missing from lot lookup table")
    return dict(zip(lot_df["lot_id"], lot_df[lot_code_column]))


def _inject_lot_codes(
    df: Optional[pd.DataFrame], lot_lookup: Optional[Dict[Any, Any]]
) -> Optional[pd.DataFrame]:
    """Ensure a `Lot ID` column exists by preferring raw strings then lookup."""
    if df is None:
        return None

    def _has_actual_values(series: pd.Series) -> bool:
        non_empty = series.dropna().astype(str).str.strip()
        return non_empty.ne("").any()

    if "Lot ID" in df.columns and _has_actual_values(df["Lot ID"]):
        return df

    new_df = df.copy()
    if "lot_id_raw" in new_df.columns and _has_actual_values(new_df["lot_id_raw"]):
        new_df["Lot ID"] = new_df["lot_id_raw"]
        return new_df

    if lot_lookup and "lot_id" in new_df.columns:
        new_df["Lot ID"] = new_df["lot_id"].map(lot_lookup)
        return new_df

    return df


def _render_filters(summary_df: pd.DataFrame) -> Dict[str, Any]:
    """Render sidebar controls and return selected filter values (O(n) to gather unique options)."""
    st.sidebar.header("Filters (AC6)")

    lot_filter = st.sidebar.text_input(
        "Lot (accepts partial canonical ids)",
        placeholder="e.g. 20260112",
    )

    record_dates = summary_df["record_date"].dropna()
    min_date = record_dates.min() if not record_dates.empty else date.today()
    max_date = record_dates.max() if not record_dates.empty else date.today()
    date_range: Tuple[date, date] = st.sidebar.date_input(
        "Record date range",
        value=(min_date, max_date),
    )

    ship_status_options = sorted(summary_df["ship_status"].dropna().unique())
    selected_ship_status = st.sidebar.multiselect(
        "Shipping status",
        options=ship_status_options,
        default=ship_status_options,
    )

    prod_lines = sorted(
        {line for line in summary_df["production_line"].dropna()}
    )
    production_line_selection = st.sidebar.multiselect(
        "Production line",
        options=prod_lines,
        default=prod_lines,
    )

    defect_type_options = sorted(
        {
            defect
            for defect_list in summary_df["defect_types"]
            if isinstance(defect_list, list)
            for defect in defect_list
        }
    )
    defect_type = st.sidebar.selectbox(
        "Defect type",
        options=["All"] + defect_type_options,
        index=0,
    )

    priority_only = st.sidebar.checkbox(
        "Priority lots (shipped with defects)",
        value=False,
    )

    return {
        "lot": lot_filter.strip().upper(),
        "date_range": date_range,
        "ship_status": selected_ship_status,
        "production_lines": production_line_selection,
        "defect_type": defect_type,
        "priority_only": priority_only,
    }


def _apply_filters(summary_df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    """Apply filters sequentially; each pass is O(n) over the current DataFrame."""
    filtered = summary_df.copy()

    # Lot filter supports partial matches on canonical ids.
    lot_filter = filters["lot"]
    if lot_filter:
        filtered = filtered[filtered["lot"].str.contains(lot_filter, na=False)]

    # Date range filter is inclusive of both endpoints.
    start_date, end_date = filters["date_range"]
    filtered = filtered[
        (filtered["record_date"] >= start_date) & (filtered["record_date"] <= end_date)
    ]

    # Shipping status filter uses multiselect to allow combined views.
    ship_statuses = filters["ship_status"]
    if ship_statuses:
        filtered = filtered[filtered["ship_status"].isin(ship_statuses)]

    # Production line filter excludes rows whose line is not in the selection.
    production_lines = filters["production_lines"]
    if production_lines:
        filtered = filtered[
            filtered["production_line"].isin(production_lines)
            | filtered["production_line"].isna()
        ]

    # Defect type filter matches against the canonical list for each row.
    defect_type = filters["defect_type"]
    if defect_type != "All":
        filtered = filtered[
            filtered["defect_types"].apply(
                lambda types: defect_type in types if isinstance(types, list) else False
            )
        ]

    # Priority-only toggle isolates high-risk lots (AC7).
    if filters["priority_only"]:
        filtered = filtered[filtered["priority_flag"]]

    return filtered


def _display_summary_table(filtered: pd.DataFrame) -> None:
    """Render the summary table with visual emphasis; sorting is O(n log n)."""
    if filtered.empty:
        st.warning("No summary rows match the selected filters.")
        return

    # Sorting matches AC8 priority order.
    sorted_df = filtered.sort_values(
        ["priority_bucket", "priority_defects", "priority_date"],
        ascending=[False, False, False],
    )

    display_columns = [
        "priority_badge",
        "lot",
        "record_date",
        "production_line",
        "units_planned",
        "units_actual",
        "inspection_summary",
        "total_defects",
        "ship_status",
        "ship_date",
        "qty_shipped",
        "reconciliation_status",
        "status_reason",
        "source_summary",
    ]

    beige_base = "#fff4e8"
    beige_priority = "#f5d6c3"  # beige with a red hue accent
    border_accent = "#b76e79"  # complementary outline color
    border_neutral = "#d9c3b0"

    def _priority_style(row: pd.Series) -> List[str]:
        badge_value = row.get("priority_badge", row.get("Priority", ""))
        if badge_value:
            style = (
                f"background-color: {PRIORITY_BG}; "
                f"color: {TEXT_COLOR}; "
                f"border: 1px solid {BORDER_ACCENT}"
            )
        else:
            style = (
                f"background-color: {BASE_BG}; "
                f"color: {TEXT_COLOR}; "
                f"border: 1px solid {BORDER_NEUTRAL}"
            )
        return [style] * len(row)

    styled = (
        sorted_df[display_columns]
        .fillna("None")
        .rename(
            columns={
                "priority_badge": "Priority",
                "record_date": "Record Date",
                "production_line": "Production Line",
                "units_planned": "Units Planned",
                "units_actual": "Units Actual",
                "inspection_summary": "Inspection Results",
                "total_defects": "Total Defects",
                "ship_status": "Ship Status",
                "ship_date": "Ship Date",
                "qty_shipped": "Qty Shipped",
                "reconciliation_status": "Status",
                "status_reason": "Status Detail",
                "source_summary": "Source Counts",
            }
        )
        .style.apply(_priority_style, axis=1)
    )

    st.dataframe(styled, use_container_width=True)


def _style_generic_table(df: pd.DataFrame) -> Styler:
    """Apply beige theme styling to any DataFrame."""
    return (
        df.fillna("None")
        .style.set_properties(
            **{
                "background-color": BASE_BG,
                "color": TEXT_COLOR,
                "border": f"1px solid {BORDER_NEUTRAL}",
            }
        )
    )


def _render_detail_view(filtered: pd.DataFrame, details: Dict[str, Dict[str, Any]]) -> None:
    """Allow the analyst to drill into a specific summary row (linear in number of filtered rows)."""
    if filtered.empty:
        return

    st.subheader("Drill-down and Traceability")

    options = [
        f"{row.lot} | {row.record_date}"
        for row in filtered.itertuples()
    ]
    selection = st.selectbox(
        "Select a lot/date combination",
        options=options,
    )

    if not selection:
        return

    lot, rec_date = [token.strip() for token in selection.split("|", maxsplit=1)]
    key = f"{lot}|{rec_date}"
    detail_payload = details.get(key)

    if not detail_payload:
        st.error("Detail payload missing (this should not happen).")
        return

    st.markdown("**Summary row snapshot**")
    summary_mask = (filtered["lot"].astype(str) == lot) & (
        filtered["record_date"].astype(str) == rec_date
    )
    summary_rows = filtered[summary_mask]
    if not summary_rows.empty:
        st.dataframe(_style_generic_table(summary_rows), use_container_width=True)
    else:
        st.json(detail_payload)

    if detail_payload["missing_sources"]:
        st.warning(f"Missing sources: {', '.join(detail_payload['missing_sources'])}")

    if detail_payload["insufficient_fields"]:
        st.info(
            "Insufficient data fields: "
            + ", ".join(detail_payload["insufficient_fields"])
        )

    if detail_payload["mismatches"]:
        st.error("Mismatches detected: " + "; ".join(detail_payload["mismatches"]))

    st.markdown("**Source rows**")
    for section in ["production_rows", "inspection_rows", "shipping_rows"]:
        with st.expander(section.replace("_", " ").title(), expanded=False):
            rows = detail_payload["source_refs"].get(section, [])
            if rows:
                st.dataframe(
                    _style_generic_table(pd.DataFrame(rows)),
                    use_container_width=True,
                )
            else:
                st.write("No rows available.")


def main() -> None:
    """Entry point executed by Streamlit; orchestration remains O(n) in the size of loaded tables."""
    st.set_page_config(page_title="Operational Summary Reconciler", layout="wide")
    st.title("Operational Summary Reconciler")

    st.sidebar.header("Data source")
    mode = st.sidebar.radio(
        "Choose data source",
        ["Upload CSVs", "Connect to DB"],
        index=1,
    )

    production_df: Optional[pd.DataFrame] = None
    shipping_df: Optional[pd.DataFrame] = None
    inspection_df: Optional[pd.DataFrame] = None

    if mode == "Upload CSVs":
        st.sidebar.write("Upload production, shipping, and optional inspection CSV files.")
        prod_file = st.sidebar.file_uploader("Production CSV", type=["csv"])
        ship_file = st.sidebar.file_uploader("Shipping CSV", type=["csv"])
        ins_file = st.sidebar.file_uploader("Inspection CSV (optional)", type=["csv"])

        if prod_file:
            production_df = _harmonize_columns(pd.read_csv(prod_file), PRODUCTION_ALIAS_MAP)
        if ship_file:
            shipping_df = _harmonize_columns(pd.read_csv(ship_file), SHIPPING_ALIAS_MAP)
        if ins_file:
            inspection_df = _harmonize_columns(pd.read_csv(ins_file), INSPECTION_ALIAS_MAP)
    else:
        st.sidebar.write("Uses DATABASE_URL from the .env file (Render-hosted Postgres).")
        if not DB_URL:
            st.error("DATABASE_URL is not configured. Create .env with the provided Render URL.")
        else:
            load_errors: List[str] = []
            with st.spinner("Querying Render Postgres..."):
                try:
                    lot_lookup = _load_lot_lookup(DB_URL)
                except Exception as exc:  # noqa: BLE001
                    lot_lookup = None
                    load_errors.append(f"Lot lookup load failed: {exc}")

                try:
                    prod_raw = _read_table_with_candidates(
                        DB_URL, PRODUCTION_TABLE_CANDIDATES
                    )
                    prod_raw = _inject_lot_codes(prod_raw, lot_lookup)
                    production_df = _harmonize_columns(
                        prod_raw,
                        PRODUCTION_ALIAS_MAP,
                    )
                except Exception as exc:  # noqa: BLE001
                    production_df = None
                    load_errors.append(f"Production table load failed: {exc}")

                try:
                    ship_raw = _read_table_with_candidates(
                        DB_URL, SHIPPING_TABLE_CANDIDATES
                    )
                    ship_raw = _inject_lot_codes(ship_raw, lot_lookup)
                    shipping_df = _harmonize_columns(
                        ship_raw,
                        SHIPPING_ALIAS_MAP,
                    )
                except Exception as exc:  # noqa: BLE001
                    shipping_df = None
                    load_errors.append(f"Shipping table load failed: {exc}")

                try:
                    ins_raw = _read_table_with_candidates(
                        DB_URL, INSPECTION_TABLE_CANDIDATES
                    )
                    ins_raw = _inject_lot_codes(ins_raw, lot_lookup)
                    inspection_df = _harmonize_columns(
                        ins_raw,
                        INSPECTION_ALIAS_MAP,
                    )
                except Exception as exc:  # noqa: BLE001
                    inspection_df = None
                    load_errors.append(f"Inspection table load failed: {exc}")
            if load_errors:
                st.error("One or more tables failed to load automatically. Use the developer panel to review details.")
                for message in load_errors:
                    st.sidebar.error(message)
            else:
                st.sidebar.success("Loaded tables from the database.")
                st.success("Loaded tables from the database.")

    if production_df is None or shipping_df is None:
        st.info("Provide both production and shipping data to run reconciliation.")
        return

    summary_df, incomplete_count, details = reconcile(
        production_df,
        shipping_df,
        inspection_df,
    )

    st.sidebar.metric("Incomplete records", incomplete_count)

    if summary_df.empty:
        st.warning("No valid rows were produced after reconciliation.")
        return

    filters = _render_filters(summary_df)
    filtered_df = _apply_filters(summary_df, filters)

    _display_summary_table(filtered_df)
    _render_detail_view(filtered_df, details)

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "Priority = shipped lots with >0 defects. Sorting matches AC8."
    )


if __name__ == "__main__":
    main()

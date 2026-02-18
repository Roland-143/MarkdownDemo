"""Unit tests for normalization helpers and reconciliation engine.

Each test includes explicit comments to keep junior engineers oriented.
"""

import pandas as pd

from reconciler.normalize import canonicalize_lot
from reconciler.reconcile import reconcile


def test_canonicalize_basic_variants():
    """Canonicalization handles OCR typos, punctuation, and blanks."""
    assert canonicalize_lot("Lot-20260112-001") == "20260112001"
    assert canonicalize_lot("L0T 2026 0112 001") == "20260112001"
    assert canonicalize_lot("") is None
    assert canonicalize_lot(None) is None


def test_reconcile_missing_sources_and_incomplete_counts():
    """Rows missing Lot or Date are counted while valid rows surface with flags."""
    prod = pd.DataFrame(
        [
            {"Date": "2026-01-12", "Lot ID": "Lot-20260112-001", "Units Actual": 90},
            {"Date": "", "Lot ID": "Lot-20260112-999"},  # incomplete, should not join
        ]
    )
    ship = pd.DataFrame(
        [
            {"Ship Date": "2026-01-12", "Lot ID": "LOT20260112001", "Ship Status": "shipped"},
        ]
    )

    summary, incomplete, details = reconcile(prod, ship)

    assert incomplete == 1
    row = summary.iloc[0]
    assert row["lot"] == "20260112001"
    assert bool(row["missing_inspection"])  # no inspection input provided
    assert row["reconciliation_status"] == "missing_sources"
    key = f"{row['lot']}|{row['record_date']}"
    assert "inspection" in details[key]["missing_sources"]


def test_reconcile_insufficient_data_reason():
    """Presence of all sources but missing critical metrics triggers insufficient_data."""
    prod = pd.DataFrame(
        [
            {"Date": "2026-02-01", "Lot ID": "Lot-1", "Units Planned": None, "Units Actual": None},
        ]
    )
    ship = pd.DataFrame(
        [
            {"Ship Date": "2026-02-01", "Lot ID": "Lot-1", "Ship Status": "shipped"},
        ]
    )
    ins = pd.DataFrame(
        [
            {"Inspection Date": "2026-02-01", "Lot ID": "Lot-1", "Qty Defects": 0},
        ]
    )

    summary, _, details = reconcile(prod, ship, ins)
    row = summary.iloc[0]
    assert row["reconciliation_status"] == "insufficient_data"
    key = f"{row['lot']}|{row['record_date']}"
    assert "production metrics missing" in details[key]["insufficient_fields"]


def test_reconcile_priority_and_mismatch_detection():
    """Shipped lots with defects receive priority badges and mismatch notes."""
    prod = pd.DataFrame(
        [
            {"Date": "2026-03-01", "Lot ID": "Lot-XYZ", "Units Actual": 100},
        ]
    )
    ship = pd.DataFrame(
        [
            {"Ship Date": "2026-03-01", "Lot ID": "Lot-xyz", "Ship Status": "shipped", "Qty Shipped": 98},
        ]
    )
    ins = pd.DataFrame(
        [
            {"Inspection Date": "2026-03-01", "Lot ID": "Lot-xyz", "Qty Defects": 2, "Defect Type": "Crack"},
            {"Inspection Date": "2026-03-01", "Lot ID": "Lot-xyz", "Qty Defects": 1, "Defect Type": "Chip"},
        ]
    )

    summary, _, details = reconcile(prod, ship, ins)
    row = summary.iloc[0]
    assert bool(row["priority_flag"])
    assert row["priority_badge"] == "PRIORITY"
    assert summary["total_defects"].iloc[0] == 3

    key = f"{row['lot']}|{row['record_date']}"
    assert any("Units actual" in note for note in details[key]["mismatches"])

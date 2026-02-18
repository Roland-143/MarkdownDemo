# Operational Summary Reconciler

Streamlit-based tool that reconciles production, inspection, and shipping sources so operations analysts can answer leadership questions quickly without spreadsheet gymnastics. The implementation follows the user story, database schema in `db/schema.sql`, and design notes in the `docs/` directory.

---

## Project Description
- **Goal:** align disparate spreadsheets (or the Render-hosted Postgres database) by canonical Lot ID + Date, surface completeness issues, and highlight shipped lots that still carry defects.
- **User workflow:** upload CSV exports or pull from the shared Postgres instance → review the prioritized summary table → drill into any row to see raw source records, alignment basis, and missing fields.
- **Tech stack:** Python 3.10+, pandas for in-memory reconciliation, Streamlit for the UI, SQLAlchemy for optional DB connectivity, pytest for unit tests.

For background and earlier AI-produced artifacts, review:
- `docs/architecture_design_records.md` – rationale for the simplified client-server, monolith approach.
- `docs/data_design.md` – canonical data model, field mapping, and ERD.
- `docs/assumptions_scope.md` – bounds on data freshness, row counts, and spreadsheet quirks.
- `docs/tech_stack_decision_records.md` – why pandas + Streamlit were selected.

---

## Setup
1. **Clone** the repo (or open it via GitHub Codespaces / local IDE).
2. **Create `.env`** in the project root and paste the provided Render 
3. **Create a virtual environment and install dependencies:**
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. **(Optional) Apply schema locally:** `psql $DATABASE_URL -f db/schema.sql` if you need to recreate the Render schema elsewhere.

---

## Running the Streamlit App
```bash
streamlit run app.py
```
Two modes are available from the sidebar:
1. **Upload CSVs** – Provide production, shipping, and optional inspection exports. The app reconciles them entirely in memory.
2. **Connect to DB** – Uses `DATABASE_URL` to pull from `ops.production_records`, `ops.shipping_records`, and `ops.inspection_records` via SQLAlchemy (connections are closed via context managers to avoid leaks).

The summary view includes Lot ID, Record Date, Production Line, Units Planned/Actual, inspection summaries, shipping status, ship date, shipping quantity, reconciliation status, and source reference counts (AC5). Priority rows (shipped lots with `total_defects > 0`) receive a badge and pastel background (AC7). Default sorting matches AC8 (priority badge → defect quantity → most recent date). Filters for Lot, date range, ship status, defect type, and production line live in the sidebar (AC6).

Selecting a row in the "Drill-down and Traceability" section opens its detail payload, including raw source rows, reconciliation basis, missing sources, insufficient data flags, and mismatch notes (AC9-AC11).

---

## Usage Examples
1. **Answer “Which shipped lots still have open defects this week?”**
   - Apply the date range filter to the target week.
   - Toggle “Priority lots” to view only shipped lots with defects.
   - Sort order already highlights the worst offenders; click one to view defect descriptions and shipping notes.
2. **Trace a leadership question like “Why is Lot 20260112 late?”**
   - Use the Lot filter (`20260112`).
   - Review the status reason column; if it shows `missing_sources`, the sidebar metric also lists incomplete counts.
   - Use the drill-down expander to inspect the source rows; mismatched units (production vs shipping) are clearly flagged.
3. **Spot gaps in inspection coverage.**
   - Filter defect type to a specific defect (e.g., `CRACK`).
   - Switch off “Priority lots” to review all rows and confirm inspection data exists; rows without inspection data will show `missing_sources` and list `"inspection"` under missing sources, satisfying AC2 and AC4.

---

## Running Tests
```bash
pytest -q
```
The tests cover normalization edge cases plus reconciliation behaviors for missing sources, insufficient data, and priority flag handling.

---

## Acceptance Criteria Mapping
- **AC1** – `reconciler.normalize.canonicalize_lot` + the set-union join on `(lot, record_date)` in `reconciler.reconcile.reconcile`.
- **AC2 / AC3 / AC4** – Summary rows stay visible even when sources are missing; counts for incomplete rows show in the sidebar, and `status_reason` communicates missing or insufficient data.
- **AC5** – Display columns include production, inspection, shipping metrics, and source counts; `source_refs` feed the drill-down view with record-level provenance.
- **AC6** – Sidebar filters cover Lot ID, date range, ship status, defect type, and production line; shipping status filter allows multiple selections.
- **AC7 / AC8** – Priority badge + checkbox filter, plus default sort by priority bucket → defect quantity → most recent record date.
- **AC9 / AC10 / AC11** – Detail panel surfaces the reconciliation basis (“lot + record_date”), missing sources, insufficient fields, mismatches, and the affected period via `record_date`.

---

## Developer Notes
- Keep comments synchronized with the implementation—every module, function, and non-trivial line carries context plus Big-O notes for onboarding engineers.
- CI/CD is not wired yet; run `pytest` locally before pushing.
- Future extensions: hook up scheduled ETL to populate `ops.operational_summaries`, add export-to-CSV, and enrich inspection support once the upstream sheet is finalized.

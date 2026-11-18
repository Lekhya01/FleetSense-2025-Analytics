# FleetSense – MetroCab Analytics (2025)

A beginner-friendly Phase 1 data analytics project using the official NYC TLC **Yellow Taxi** monthly Parquet files for January–December 2025.

## What this project does
1. Downloads the 12 monthly 2025 Yellow Taxi Parquet files and taxi-zone lookup CSV.
2. Combines the files with DuckDB, allowing minor monthly schema differences.
3. Removes exact duplicate-like records using a repeatable trip key.
4. Runs basic quality checks and writes failing rows to `quarantine` with reason codes.
5. Creates `trips`, `zones`, `calendar`, and `hourly_demand` warehouse tables.
6. Provides a Streamlit dashboard with date and zone filters, hourly demand, monthly trend and CR-1 revenue comparison.

## Beginner setup (Windows PowerShell)

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pipeline.ingest
python -m pipeline.build
python -m pipeline.validate
streamlit run dashboard/app.py
```

Or use `make all` on a system with Make installed. Run `make dashboard` to start the dashboard.

## Data source

Official TLC page: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page

The source page lists 2025 Yellow Taxi Parquet files from January through December and the taxi-zone lookup. TLC notes that trip records are supplied by technology providers and may not be fully accurate. The 2025 datasets include a `cbd_congestion_fee` field.

## Important definitions
- Trips: count of valid trips.
- Revenue including charges: sum of `total_amount`.
- Base fare: sum of `fare_amount`.
- Average fare: average `fare_amount`.
- Trip duration: drop-off timestamp minus pickup timestamp, in minutes.
- Utilisation proxy: trips per zone/hour. This is not true vehicle utilisation because vehicle availability/idle time is not included.
- CR-1 comparison: `total_amount` versus `fare_amount`, grouped by pickup zone. The difference includes all non-base-fare components captured in total amount; do not label it as tolls alone.

## Notes and limitations
- The data is large. Keep it in Parquet/DuckDB; do not load all 12 months into a pandas DataFrame.
- The trip key is a practical deduplication key for this beginner project, not a TLC-issued unique trip ID.
- This starter code uses basic validation rules. Review the quarantined records and document exclusions before publishing results.
- `total_amount - fare_amount` is a broad difference. For finance reporting, document which itemized components are included and reconcile them against TLC's data dictionary.
- The dashboard is local until deployed to Streamlit Community Cloud.

## Folder guide
- `pipeline/`: download, build and validation scripts.
- `sql/`: warehouse SQL documentation / models.
- `metrics/`: central metric definitions.
- `dashboard/`: Streamlit application.
- `tests/`: starter automated tests.
- `docs/`: design, findings and runbook templates.
- `data/`: downloaded data and DuckDB database (never commit these files).

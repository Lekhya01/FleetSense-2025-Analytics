# Runbook

1. Create and activate a Python 3.11 virtual environment.
2. Install requirements with `pip install -r requirements.txt`.
3. Download source data with `python -m pipeline.ingest`.
4. Build tables with `python -m pipeline.build`.
5. Run quality checks with `python -m pipeline.validate`.
6. Start dashboard with `streamlit run dashboard/app.py`.
7. Run tests with `pytest -q`.

To add or refresh a month, update the month list in `pipeline/ingest.py`, download it, and rebuild the warehouse. Keep all source files outside Git.

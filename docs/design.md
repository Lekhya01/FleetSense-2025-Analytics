# Technical Design (starter)

## Business question
Which NYC pickup zones and hours have the highest Yellow Taxi demand in 2025, and how does fare revenue vary by zone?

## Source
NYC TLC 2025 Yellow Taxi monthly Parquet files (Jan–Dec 2025) and TLC taxi zone lookup CSV.

## Processing
Download monthly Parquet -> DuckDB staging -> deduplicated trips -> quarantine checks -> warehouse dimensions and hourly demand -> Streamlit dashboard.

## Metrics
See `metrics/definitions.py`. Revenue comparison for CR-1 is shown by pickup zone.

## Risks and decisions
- Source records can contain errors; quarantine rather than silently discard.
- Schema can vary; read Parquet with `union_by_name=true`.
- A trip key is constructed because no single guaranteed unique trip ID is assumed.
- The difference between total amount and fare amount includes more than tolls; describe it carefully.

"""Build a small DuckDB warehouse from the downloaded 2025 Parquet files."""
from pathlib import Path
import duckdb

DB = "data/fleetsense.duckdb"
PARQUET_GLOB = "data/raw/yellow_tripdata_2025-*.parquet"


def main() -> None:
    files = list(Path("data/raw").glob("yellow_tripdata_2025-*.parquet"))
    if not files:
        raise SystemExit("No 2025 Parquet files found. Run: make download")

    con = duckdb.connect(DB)
    # The source files are combined by column name because TLC can evolve schemas.
    con.execute(f"""
        CREATE OR REPLACE TABLE trips_staging AS
        SELECT * FROM read_parquet('{PARQUET_GLOB}', union_by_name = true)
    """)

    # Standardize only the fields needed for Phase 1. Keep source columns in staging.
    con.execute("""
        CREATE OR REPLACE TABLE trips AS
        SELECT
            md5(concat_ws('|',
                coalesce(cast(tpep_pickup_datetime as varchar), ''),
                coalesce(cast(tpep_dropoff_datetime as varchar), ''),
                coalesce(cast(PULocationID as varchar), ''),
                coalesce(cast(DOLocationID as varchar), ''),
                coalesce(cast(fare_amount as varchar), ''),
                coalesce(cast(total_amount as varchar), '')
            )) AS trip_key,
            try_cast(tpep_pickup_datetime AS TIMESTAMP) AS pickup_datetime,
            try_cast(tpep_dropoff_datetime AS TIMESTAMP) AS dropoff_datetime,
            try_cast(passenger_count AS INTEGER) AS passenger_count,
            try_cast(trip_distance AS DOUBLE) AS trip_distance,
            try_cast(PULocationID AS INTEGER) AS pickup_location_id,
            try_cast(DOLocationID AS INTEGER) AS dropoff_location_id,
            try_cast(fare_amount AS DOUBLE) AS fare_amount,
            try_cast(tip_amount AS DOUBLE) AS tip_amount,
            try_cast(tolls_amount AS DOUBLE) AS tolls_amount,
            try_cast(extra AS DOUBLE) AS extra_amount,
            try_cast(mta_tax AS DOUBLE) AS mta_tax,
            try_cast(improvement_surcharge AS DOUBLE) AS improvement_surcharge,
            try_cast(congestion_surcharge AS DOUBLE) AS congestion_surcharge,
            try_cast(cbd_congestion_fee AS DOUBLE) AS cbd_congestion_fee,
            try_cast(airport_fee AS DOUBLE) AS airport_fee,
            try_cast(total_amount AS DOUBLE) AS total_amount,
            try_cast(payment_type AS INTEGER) AS payment_type,
            date_trunc('month', try_cast(tpep_pickup_datetime AS TIMESTAMP)) AS pickup_month,
            hour(try_cast(tpep_pickup_datetime AS TIMESTAMP)) AS pickup_hour,
            dayofweek(try_cast(tpep_pickup_datetime AS TIMESTAMP)) AS pickup_weekday,
            date_diff('minute', try_cast(tpep_pickup_datetime AS TIMESTAMP),
                try_cast(tpep_dropoff_datetime AS TIMESTAMP)) AS trip_duration_minutes
        FROM trips_staging
        QUALIFY row_number() OVER (PARTITION BY trip_key ORDER BY pickup_datetime) = 1
    """)

    zone_file = Path("data/raw/taxi_zone_lookup.csv")
    if zone_file.exists():
        con.execute(f"""
            CREATE OR REPLACE TABLE zones AS
            SELECT * FROM read_csv_auto('{zone_file.as_posix()}')
        """)
    else:
        con.execute("CREATE OR REPLACE TABLE zones (LocationID INTEGER, Borough VARCHAR, Zone VARCHAR, service_zone VARCHAR)")

    con.execute("""
        CREATE OR REPLACE TABLE calendar AS
        SELECT DISTINCT CAST(pickup_datetime AS DATE) AS calendar_date,
               year(pickup_datetime) AS year,
               month(pickup_datetime) AS month,
               day(pickup_datetime) AS day,
               dayname(pickup_datetime) AS weekday_name
        FROM trips WHERE pickup_datetime IS NOT NULL
    """)

    con.execute("""
        CREATE OR REPLACE TABLE hourly_demand AS
        SELECT CAST(pickup_datetime AS DATE) AS pickup_date,
               pickup_hour, pickup_location_id, count(*) AS trip_count
        FROM trips
        WHERE pickup_datetime IS NOT NULL AND pickup_location_id IS NOT NULL
        GROUP BY 1, 2, 3
    """)
    count = con.execute("SELECT count(*) FROM trips").fetchone()[0]
    print(f"Warehouse ready: {count:,} unique trips in {DB}")
    con.close()


if __name__ == "__main__":
    main()

"""Simple beginner-friendly data-quality checks and quarantine output."""
import duckdb


def main() -> None:
    con = duckdb.connect("data/fleetsense.duckdb")
    con.execute("""
        CREATE OR REPLACE TABLE quarantine AS
        SELECT *, CASE
            WHEN pickup_datetime IS NULL OR dropoff_datetime IS NULL THEN 'MISSING_DATETIME'
            WHEN dropoff_datetime <= pickup_datetime THEN 'INVALID_TRIP_TIME'
            WHEN fare_amount < 0 OR total_amount < 0 THEN 'NEGATIVE_FARE'
            WHEN trip_distance < 0 THEN 'NEGATIVE_DISTANCE'
            WHEN trip_duration_minutes > 1440 THEN 'TRIP_OVER_24_HOURS'
            ELSE 'VALID'
        END AS reason_code
        FROM trips
        WHERE pickup_datetime IS NULL OR dropoff_datetime IS NULL
           OR dropoff_datetime <= pickup_datetime
           OR fare_amount < 0 OR total_amount < 0
           OR trip_distance < 0 OR trip_duration_minutes > 1440
    """)
    total = con.execute("SELECT count(*) FROM trips").fetchone()[0]
    bad = con.execute("SELECT count(*) FROM quarantine").fetchone()[0]
    print(f"Rows checked: {total:,}")
    print(f"Rows quarantined: {bad:,}")
    print(f"Rows passing basic checks: {total - bad:,}")
    print("Quarantine reasons:")
    print(con.execute("SELECT reason_code, count(*) AS rows FROM quarantine GROUP BY 1 ORDER BY 2 DESC").df())
    con.close()


if __name__ == "__main__":
    main()

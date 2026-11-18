"""Central place for the project's business metric SQL."""
METRICS_SQL = """
SELECT
    count(*) AS trips,
    sum(total_amount) AS revenue_including_tolls_surcharges,
    sum(fare_amount) AS base_fare_revenue,
    avg(fare_amount) AS average_fare,
    avg(trip_duration_minutes) AS average_trip_duration_minutes,
    sum(tolls_amount + extra_amount + mta_tax + improvement_surcharge
        + congestion_surcharge + cbd_congestion_fee + airport_fee)
        AS tolls_and_surcharges
FROM trips
WHERE pickup_datetime IS NOT NULL
  AND dropoff_datetime > pickup_datetime
"""

# CR-1: show gross total amount, base fare, and their difference by pickup zone.
ZONE_REVENUE_SQL = """
SELECT pickup_location_id,
       sum(total_amount) AS revenue_with_tolls_surcharges,
       sum(fare_amount) AS revenue_without_tolls_surcharges,
       sum(total_amount - fare_amount) AS tolls_surcharges_difference
FROM trips
GROUP BY pickup_location_id
ORDER BY revenue_with_tolls_surcharges DESC
"""

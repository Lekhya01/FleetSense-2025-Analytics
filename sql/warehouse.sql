-- Main warehouse tables are created in pipeline/build.py.
-- Fact-like table: trips (one row per deduplicated trip record).
-- Dimension: zones (TLC LocationID, Borough, Zone, service_zone).
-- Dimension: calendar (one row per pickup date).
-- Aggregate: hourly_demand (date + hour + pickup zone).

-- Example: hourly demand by pickup zone
SELECT pickup_date, pickup_hour, pickup_location_id, SUM(trip_count) AS trips
FROM hourly_demand
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;

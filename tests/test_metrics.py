
from metrics.definitions import METRICS_SQL


def test_metric_definitions_are_present():
    assert "count(*) as trips" in METRICS_SQL.lower()
    assert "revenue_including_tolls_surcharges" in METRICS_SQL.lower()
    assert "average_fare" in METRICS_SQL.lower()
    assert "tolls_and_surcharges" in METRICS_SQL.lower()

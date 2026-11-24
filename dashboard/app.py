
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st



st.set_page_config(
    page_title="FleetSense 2025 Analytics",
    page_icon="🚕",
    layout="wide"
)

st.title("🚕 FleetSense 2025 - NYC Taxi Analytics Dashboard")
st.markdown(
    "Full-year analysis of NYC Yellow Taxi trips | January–December 2025"
)


# =========================================================
# 2. DATABASE CONNECTION
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "fleetsense_full_year.duckdb"

if not DB_PATH.exists():
    st.error(f"Database not found: {DB_PATH}")
    st.info("Please run main.py first.")
    st.stop()


@st.cache_resource
def get_connection():
    return duckdb.connect(str(DB_PATH), read_only=True)


con = get_connection()


# =========================================================
# 3. CHECK DATABASE TABLE
# =========================================================

try:
    table_check = con.execute("""
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_name = 'trips'
    """).fetchone()[0]

    if table_check == 0:
        st.error("Trips table not found in database.")
        st.stop()

    columns = [
        row[0]
        for row in con.execute("DESCRIBE trips").fetchall()
    ]

except Exception as e:
    st.error(f"Database error: {e}")
    st.stop()


required_columns = [
    "tpep_pickup_datetime",
    "trip_category"
]

missing_columns = [
    col for col in required_columns if col not in columns
]

if missing_columns:
    st.error(f"Missing columns: {missing_columns}")
    st.stop()


# =========================================================
# 4. HELPER FUNCTION
# =========================================================

def query_df(sql, params=None):
    if params is None:
        params = []

    return con.execute(sql, params).df()


# =========================================================
# 5. DATE RANGE
# =========================================================

date_info = query_df("""
    SELECT
        MIN(CAST(tpep_pickup_datetime AS DATE)) AS min_date,
        MAX(CAST(tpep_pickup_datetime AS DATE)) AS max_date
    FROM trips
    WHERE tpep_pickup_datetime IS NOT NULL
      AND CAST(tpep_pickup_datetime AS DATE)
          BETWEEN DATE '2025-01-01' AND DATE '2025-12-31'
""")

if date_info.empty or pd.isna(date_info.iloc[0]["min_date"]):
    st.error("No 2025 trip records found in the database.")
    st.stop()

db_min_date = pd.Timestamp(date_info.iloc[0]["min_date"]).date()
db_max_date = pd.Timestamp(date_info.iloc[0]["max_date"]).date()

year_start = pd.Timestamp("2025-01-01").date()
year_end = pd.Timestamp("2025-12-31").date()


# =========================================================
# 6. SIDEBAR FILTERS
# =========================================================

st.sidebar.title("📊 Dashboard Filters")

st.sidebar.caption("Default selection: Full year 2025")

selected_dates = st.sidebar.date_input(
    "Select Date Range",
    value=(year_start, year_end),
    min_value=year_start,
    max_value=year_end
)

if isinstance(selected_dates, (tuple, list)):
    if len(selected_dates) == 2:
        start_date, end_date = selected_dates
    elif len(selected_dates) == 1:
        start_date = selected_dates[0]
        end_date = selected_dates[0]
    else:
        start_date, end_date = year_start, year_end
else:
    start_date = selected_dates
    end_date = selected_dates

# Keep the selected date range within available 2025 data.
start_date = max(start_date, db_min_date)
end_date = min(end_date, db_max_date)

if start_date > end_date:
    st.warning("Please select a valid date range.")
    st.stop()

airport_filter = st.sidebar.selectbox(
    "Airport Classification",
    [
        "All Trips",
        "Airport Trips",
        "Non-Airport Trips"
    ],
    index=0
)


# =========================================================
# 7. FILTER CONDITIONS
# =========================================================

where_clause = """
    CAST(tpep_pickup_datetime AS DATE) BETWEEN ? AND ?
    AND CAST(tpep_pickup_datetime AS DATE)
        BETWEEN DATE '2025-01-01' AND DATE '2025-12-31'
"""

params = [start_date, end_date]

if airport_filter == "Airport Trips":
    where_clause += " AND trip_category = ?"
    params.append("Airport Trip")

elif airport_filter == "Non-Airport Trips":
    where_clause += " AND trip_category = ?"
    params.append("Non-Airport Trip")


# =========================================================
# 8. AIRPORT VS NON-AIRPORT SUMMARY
# =========================================================

st.markdown("---")
st.subheader("✈️ Airport vs Non-Airport Trip Summary")

summary = query_df(
    f"""
    SELECT
        trip_category,
        COUNT(*) AS total_trips,
        ROUND(COALESCE(SUM(revenue), 0), 2) AS total_revenue,
        ROUND(COALESCE(AVG(fare_amount), 0), 2) AS average_fare,
        ROUND(COALESCE(AVG(duration_minutes), 0), 2) AS average_duration
    FROM trips
    WHERE {where_clause}
    GROUP BY trip_category
    ORDER BY trip_category
    """,
    params
)

if summary.empty:
    st.warning("No trips found for selected filters.")
    st.stop()


# =========================================================
# 9. KPI METRICS
# =========================================================

total_trips = int(summary["total_trips"].sum())
total_revenue = float(summary["total_revenue"].sum())

average_fare = query_df(
    f"""
    SELECT COALESCE(AVG(fare_amount), 0)
    FROM trips
    WHERE {where_clause}
    """,
    params
).iloc[0, 0]

average_duration = query_df(
    f"""
    SELECT COALESCE(AVG(duration_minutes), 0)
    FROM trips
    WHERE {where_clause}
    """,
    params
).iloc[0, 0]

st.subheader("📌 Key Performance Indicators")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Trips", f"{total_trips:,}")
c2.metric("Total Revenue", f"${total_revenue:,.2f}")
c3.metric("Average Fare", f"${float(average_fare):,.2f}")
c4.metric("Average Duration", f"{float(average_duration):.2f} min")

st.caption(f"Selected period: {start_date} to {end_date}")


# =========================================================
# 10. AIRPORT VS NON-AIRPORT CHART
# =========================================================

fig = px.bar(
    summary,
    x="trip_category",
    y="total_trips",
    color="trip_category",
    title="Airport vs Non-Airport Trip Count",
    text="total_trips",
    barmode="group"
)

st.plotly_chart(fig, width="stretch")

st.dataframe(
    summary,
    width="stretch",
    hide_index=True
)


# =========================================================
# 11. MONTHLY TRIP DEMAND
# =========================================================

st.markdown("---")
st.subheader("📅 Monthly Trip Demand - January to December 2025")

monthly = query_df(
    f"""
    SELECT
        STRFTIME(
            CAST(tpep_pickup_datetime AS TIMESTAMP),
            '%Y-%m'
        ) AS month,
        trip_category,
        COUNT(*) AS total_trips,
        ROUND(COALESCE(SUM(revenue), 0), 2) AS total_revenue
    FROM trips
    WHERE {where_clause}
    GROUP BY
        STRFTIME(
            CAST(tpep_pickup_datetime AS TIMESTAMP),
            '%Y-%m'
        ),
        trip_category
    ORDER BY month, trip_category
    """,
    params
)

if not monthly.empty:
    fig = px.line(
        monthly,
        x="month",
        y="total_trips",
        color="trip_category",
        markers=True,
        title="Monthly Trips - Airport vs Non-Airport"
    )

    st.plotly_chart(fig, width="stretch")

    st.dataframe(
        monthly,
        width="stretch",
        hide_index=True
    )
else:
    st.info("No monthly data available.")


# =========================================================
# 12. MONTHLY REVENUE
# =========================================================

st.subheader("💰 Monthly Revenue Analysis")

if not monthly.empty:
    fig = px.bar(
        monthly,
        x="month",
        y="total_revenue",
        color="trip_category",
        barmode="group",
        title="Monthly Revenue - Airport vs Non-Airport"
    )

    st.plotly_chart(fig, width="stretch")


# =========================================================
# 13. HOURLY DEMAND
# =========================================================

st.markdown("---")
st.subheader("🕒 Hourly Trip Demand")

hourly = query_df(
    f"""
    SELECT
        EXTRACT(
            HOUR FROM CAST(tpep_pickup_datetime AS TIMESTAMP)
        ) AS pickup_hour,
        trip_category,
        COUNT(*) AS total_trips
    FROM trips
    WHERE {where_clause}
    GROUP BY
        EXTRACT(
            HOUR FROM CAST(tpep_pickup_datetime AS TIMESTAMP)
        ),
        trip_category
    ORDER BY pickup_hour, trip_category
    """,
    params
)

if not hourly.empty:
    hourly["pickup_hour"] = hourly["pickup_hour"].astype(int)

    fig = px.line(
        hourly,
        x="pickup_hour",
        y="total_trips",
        color="trip_category",
        markers=True,
        title="Trips by Hour - Airport vs Non-Airport"
    )

    fig.update_xaxes(dtick=1)

    st.plotly_chart(fig, width="stretch")
    st.dataframe(hourly, width="stretch", hide_index=True)


# =========================================================
# 14. WEEKDAY DEMAND
# =========================================================

st.markdown("---")
st.subheader("📆 Weekday Demand Analysis")

weekday = query_df(
    f"""
    SELECT
        DAYNAME(
            CAST(tpep_pickup_datetime AS TIMESTAMP)
        ) AS weekday,
        DAYOFWEEK(
            CAST(tpep_pickup_datetime AS TIMESTAMP)
        ) AS weekday_number,
        trip_category,
        COUNT(*) AS total_trips
    FROM trips
    WHERE {where_clause}
    GROUP BY
        DAYNAME(
            CAST(tpep_pickup_datetime AS TIMESTAMP)
        ),
        DAYOFWEEK(
            CAST(tpep_pickup_datetime AS TIMESTAMP)
        ),
        trip_category
    ORDER BY weekday_number, trip_category
    """,
    params
)

if not weekday.empty:
    fig = px.bar(
        weekday,
        x="weekday",
        y="total_trips",
        color="trip_category",
        barmode="group",
        title="Weekday Trips - Airport vs Non-Airport"
    )

    st.plotly_chart(fig, width="stretch")
    st.dataframe(weekday, width="stretch", hide_index=True)


# =========================================================
# 15. TRIP DURATION ANALYSIS
# =========================================================

st.markdown("---")
st.subheader("⏱️ Trip Duration Analysis")

duration = query_df(
    f"""
    SELECT
        trip_category,
        ROUND(AVG(duration_minutes), 2) AS average_duration,
        ROUND(MIN(duration_minutes), 2) AS minimum_duration,
        ROUND(MAX(duration_minutes), 2) AS maximum_duration
    FROM trips
    WHERE {where_clause}
      AND duration_minutes IS NOT NULL
    GROUP BY trip_category
    """,
    params
)

if not duration.empty:
    fig = px.bar(
        duration,
        x="trip_category",
        y="average_duration",
        color="trip_category",
        title="Average Trip Duration",
        text="average_duration"
    )

    st.plotly_chart(fig, width="stretch")
    st.dataframe(duration, width="stretch", hide_index=True)


# =========================================================
# 16. PRODUCTIVITY PROXY
# =========================================================

st.markdown("---")
st.subheader("🚕 Distance per Hour - Productivity Proxy")

if "distance_per_hour" in columns:
    productivity = query_df(
        f"""
        SELECT
            trip_category,
            ROUND(AVG(distance_per_hour), 2)
                AS average_distance_per_hour
        FROM trips
        WHERE {where_clause}
          AND distance_per_hour IS NOT NULL
        GROUP BY trip_category
        """,
        params
    )

    if not productivity.empty:
        fig = px.bar(
            productivity,
            x="trip_category",
            y="average_distance_per_hour",
            color="trip_category",
            title="Average Distance per Hour"
        )

        st.plotly_chart(fig, width="stretch")
        st.dataframe(productivity, width="stretch", hide_index=True)
else:
    st.info("distance_per_hour column is not available.")

st.caption(
    "Note: Distance per hour is a productivity proxy, "
    "not actual vehicle utilization."
)


# =========================================================
# 17. TOP PICKUP ZONES
# =========================================================

st.markdown("---")
st.subheader("📍 Top 10 Pickup Zones")

if "PULocationID" in columns:
    top_zones = query_df(
        f"""
        SELECT
            PULocationID,
            trip_category,
            COUNT(*) AS total_trips,
            ROUND(COALESCE(SUM(revenue), 0), 2) AS total_revenue
        FROM trips
        WHERE {where_clause}
        GROUP BY PULocationID, trip_category
        ORDER BY total_trips DESC
        LIMIT 10
        """,
        params
    )

    if not top_zones.empty:
        fig = px.bar(
            top_zones,
            x="PULocationID",
            y="total_trips",
            color="trip_category",
            barmode="group",
            title="Top Pickup Zones"
        )

        st.plotly_chart(fig, width="stretch")
        st.dataframe(top_zones, width="stretch", hide_index=True)
else:
    st.info("PULocationID column is not available.")


# =========================================================
# 18. REVENUE COMPONENTS
# =========================================================

st.markdown("---")
st.subheader("💵 Revenue Components")

revenue_columns = [
    "fare_amount",
    "tip_amount",
    "tolls_amount",
    "extra",
    "mta_tax",
    "improvement_surcharge",
    "congestion_surcharge",
    "airport_fee"
]

available_revenue_columns = [
    col for col in revenue_columns if col in columns
]

if available_revenue_columns:
    component_sql = ", ".join(
        [
            f"ROUND(COALESCE(SUM({col}), 0), 2) AS {col}"
            for col in available_revenue_columns
        ]
    )

    revenue_components = query_df(
        f"""
        SELECT
            trip_category,
            {component_sql}
        FROM trips
        WHERE {where_clause}
        GROUP BY trip_category
        """,
        params
    )

    st.dataframe(
        revenue_components,
        width="stretch",
        hide_index=True
    )
else:
    st.info("No revenue component columns available.")


# =========================================================
# 19. AIRPORT ZONE MAPPING
# =========================================================

st.markdown("---")
st.subheader("✈️ Airport Zone Mapping")

mapping_exists = con.execute("""
    SELECT COUNT(*)
    FROM information_schema.tables
    WHERE table_name = 'airport_zone_mapping'
""").fetchone()[0]

if mapping_exists:
    mapping_result = query_df("""
        SELECT zone_id, airport_name
        FROM airport_zone_mapping
        ORDER BY zone_id
    """)

    st.dataframe(
        mapping_result,
        width="stretch",
        hide_index=True
    )
else:
    st.info("Airport mapping table is not available.")

st.caption(
    "Airport Trip = pickup OR drop-off zone belongs to "
    "zone IDs 1, 132 or 138."
)


# =========================================================
# 20. TRIP DATA EXPLORER
# =========================================================

st.markdown("---")
st.subheader("🔎 Trip Data Explorer")

preview = query_df(
    f"""
    SELECT *
    FROM trips
    WHERE {where_clause}
    LIMIT 1000
    """,
    params
)

st.write(
    f"Showing up to 1,000 records. "
    f"Total filtered trips: {total_trips:,}"
)

st.dataframe(
    preview,
    width="stretch",
    height=400
)

csv_data = preview.to_csv(index=False).encode("utf-8")

st.download_button(
    label="⬇️ Download Trip Data CSV",
    data=csv_data,
    file_name="fleetsense_2025_trip_data.csv",
    mime="text/csv"
)


# =========================================================
# 21. FOOTER
# =========================================================

st.markdown("---")

st.markdown("""
**FleetSense 2025 Analytics Dashboard**

Full-year NYC Yellow Taxi analysis  
Airport zones: 1, 132 and 138  
Categories: Airport Trip and Non-Airport Trip
""")

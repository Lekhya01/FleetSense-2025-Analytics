import sys
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st



# 1. PROJECT CONFIGURATION


PROJECT_ROOT = Path(__file__).resolve().parent.parent

st.set_page_config(
    page_title="FleetSense Analytics",
    page_icon="🚕",
    layout="wide"
)

st.title("🚕 FleetSense | NYC Taxi Analytics")
st.caption("2025 NYC Yellow Taxi Trip Records | Interactive Dashboard")


# 2. DATABASE CONNECTION

@st.cache_resource
def get_connection():

    database_files = list(PROJECT_ROOT.glob("data/**/*.duckdb"))
    database_files += list(PROJECT_ROOT.glob("data/**/*.db"))

    for db_path in database_files:
        try:
            connection = duckdb.connect(
                str(db_path),
                read_only=True
            )

            tables = connection.execute(
                "SHOW TABLES"
            ).df()["name"].tolist()

            if "trips" in tables:
                return connection, db_path

            connection.close()

        except Exception:
            continue

    return None, None


con, database_path = get_connection()

if con is None:
    st.error("DuckDB database or trips table not found.")

    st.code(
        "python -m pipeline.ingest\n"
        "python -m pipeline.build"
    )

    st.stop()



# 3. DETECT ACTUAL DATABASE COLUMNS


schema = con.execute("DESCRIBE trips").df()

available_columns = schema["column_name"].tolist()


def find_column(possible_names):

    for name in possible_names:
        if name in available_columns:
            return name

    return None


pickup_date_col = find_column([
    "pickup_datetime",
    "tpep_pickup_datetime"
])

pickup_zone_col = find_column([
    "pickup_location_id",
    "PULocationID"
])

dropoff_zone_col = find_column([
    "dropoff_location_id",
    "DOLocationID"
])

total_col = find_column([
    "total_amount"
])

fare_col = find_column([
    "fare_amount"
])

distance_col = find_column([
    "trip_distance"
])

if not pickup_date_col or not total_col:
    st.error("Required columns are missing from the trips table.")
    st.dataframe(schema, width="stretch")
    st.stop()



# 4. SIDEBAR FILTERS


st.sidebar.title("🎛️ Dashboard Filters")

st.sidebar.success("Database connected")

with st.sidebar.expander("Database details"):
    st.write("Database:", database_path.name)
    st.write("Table: trips")
    st.write("Available columns:", available_columns)


minimum_date, maximum_date = con.execute(
    f"""
    SELECT
        MIN(CAST("{pickup_date_col}" AS DATE)),
        MAX(CAST("{pickup_date_col}" AS DATE))
    FROM trips
    """
).fetchone()


if minimum_date is None:
    st.warning("No trip data available.")
    st.stop()


selected_dates = st.sidebar.date_input(
    "Select date range",
    value=(minimum_date, maximum_date),
    min_value=minimum_date,
    max_value=maximum_date
)


# IMPORTANT: Convert selected dates into two
# individual values before passing them to DuckDB.

if isinstance(selected_dates, (tuple, list)):

    if len(selected_dates) == 2:
        start_date = selected_dates[0]
        end_date = selected_dates[1]

    elif len(selected_dates) == 1:
        start_date = selected_dates[0]
        end_date = selected_dates[0]

    else:
        start_date = minimum_date
        end_date = maximum_date

else:
    start_date = selected_dates
    end_date = selected_dates


date_filter = f"""
CAST("{pickup_date_col}" AS DATE)
BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
"""

params = [
    str(start_date),
    str(end_date)
]



# 5. KPI CARDS


st.subheader("📌 Key Performance Indicators")

kpi_fields = [
    f'COUNT(*) AS total_trips',
    f'SUM("{total_col}") AS total_revenue'
]

if fare_col:
    kpi_fields.append(
        f'AVG("{fare_col}") AS average_fare'
    )

if distance_col:
    kpi_fields.append(
        f'AVG("{distance_col}") AS average_distance'
    )


kpi_sql = f"""
SELECT
    {", ".join(kpi_fields)}
FROM trips
WHERE {date_filter}
"""

kpi = con.execute(
    kpi_sql,
    params
).df().iloc[0]


c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "🚕 Total Trips",
    f"{int(kpi['total_trips']):,}"
)

c2.metric(
    "💰 Total Revenue",
    f"${(kpi['total_revenue'] or 0):,.2f}"
)

if fare_col:
    c3.metric(
        "💵 Average Fare",
        f"${(kpi['average_fare'] or 0):,.2f}"
    )
else:
    c3.metric("Average Fare", "N/A")

if distance_col:
    c4.metric(
        "📏 Average Distance",
        f"{(kpi['average_distance'] or 0):,.2f} miles"
    )
else:
    c4.metric("Average Distance", "N/A")


st.divider()



# 6. MONTHLY LINE CHART


st.subheader("📈 Monthly Trip Trends")

monthly = con.execute(
    f"""
    SELECT
        strftime("{pickup_date_col}", '%Y-%m') AS month,
        COUNT(*) AS trips,
        SUM("{total_col}") AS revenue
    FROM trips
    WHERE {date_filter}
    GROUP BY 1
    ORDER BY 1
    """,
    params
).df()


if not monthly.empty:

    fig = px.line(
        monthly,
        x="month",
        y="trips",
        markers=True,
        title="Monthly Number of Trips",
        labels={
            "month": "Month",
            "trips": "Total Trips"
        },
        template="plotly_white"
    )

    fig.update_layout(
        hovermode="x unified"
    )

    st.plotly_chart(
        fig,
        width="stretch"
    )

    st.markdown("**Monthly Summary Table**")

    st.dataframe(
        monthly,
        width="stretch",
        hide_index=True
    )


st.divider()



# 7. TOP 10 PICKUP LOCATIONS - BAR CHART


st.subheader("📊 Top 10 Pickup Locations")

if pickup_zone_col:

    zone_data = con.execute(
        f"""
        SELECT
            "{pickup_zone_col}" AS pickup_zone,
            COUNT(*) AS trips,
            SUM("{total_col}") AS revenue
        FROM trips
        WHERE {date_filter}
        GROUP BY 1
        ORDER BY trips DESC
        LIMIT 10
        """,
        params
    ).df()

    if not zone_data.empty:

        fig = px.bar(
            zone_data.sort_values("trips"),
            x="trips",
            y="pickup_zone",
            orientation="h",
            text="trips",
            title="Top 10 Pickup Zones by Trip Count",
            labels={
                "trips": "Number of Trips",
                "pickup_zone": "Pickup Zone ID"
            },
            template="plotly_white"
        )

        fig.update_traces(
            textposition="outside"
        )

        st.plotly_chart(
            fig,
            width="stretch"
        )

        st.markdown("**Pickup Location Details**")

        st.dataframe(
            zone_data,
            width="stretch",
            hide_index=True
        )

else:
    st.info("Pickup location column is unavailable.")


st.divider()



# 8. REVENUE BREAKDOWN - DONUT CHART

st.subheader("🍩 Revenue Breakdown")

revenue_columns = [
    column for column in [
        "fare_amount",
        "tolls_amount",
        "extra_amount",
        "mta_tax",
        "improvement_surcharge",
        "congestion_surcharge",
        "airport_fee",
        "cbd_congestion_fee"
    ]
    if column in available_columns
]


if revenue_columns:

    revenue_sql = ", ".join(
        f'SUM("{column}") AS "{column}"'
        for column in revenue_columns
    )

    revenue_data = con.execute(
        f"""
        SELECT {revenue_sql}
        FROM trips
        WHERE {date_filter}
        """,
        params
    ).df()

    revenue_long = revenue_data.melt(
        var_name="Revenue Type",
        value_name="Amount"
    )

    revenue_long = revenue_long.dropna()

    revenue_long = revenue_long[
        revenue_long["Amount"] > 0
    ]

    if not revenue_long.empty:

        fig = px.pie(
            revenue_long,
            names="Revenue Type",
            values="Amount",
            hole=0.45,
            title="Revenue Components",
            template="plotly_white"
        )

        st.plotly_chart(
            fig,
            width="stretch"
        )

else:
    st.info("Revenue component columns are unavailable.")


st.divider()



# 9. DAILY TRIP ACTIVITY - AREA CHART

st.subheader("📉 Daily Trip Activity")

daily = con.execute(
    f"""
    SELECT
        CAST("{pickup_date_col}" AS DATE) AS trip_date,
        COUNT(*) AS trips
    FROM trips
    WHERE {date_filter}
    GROUP BY 1
    ORDER BY 1
    """,
    params
).df()


if not daily.empty:

    fig = px.area(
        daily,
        x="trip_date",
        y="trips",
        title="Daily Trip Volume",
        labels={
            "trip_date": "Date",
            "trips": "Number of Trips"
        },
        template="plotly_white"
    )

    st.plotly_chart(
        fig,
        width="stretch"
    )


st.divider()



# 10. TOP 10 DROP-OFF LOCATIONS


st.subheader("📍 Top 10 Drop-off Locations")

if dropoff_zone_col:

    dropoff = con.execute(
        f"""
        SELECT
            "{dropoff_zone_col}" AS dropoff_zone,
            COUNT(*) AS trips,
            SUM("{total_col}") AS revenue
        FROM trips
        WHERE {date_filter}
        GROUP BY 1
        ORDER BY trips DESC
        LIMIT 10
        """,
        params
    ).df()

    st.dataframe(
        dropoff,
        width="stretch",
        hide_index=True
    )

else:
    st.info("Drop-off location column is unavailable.")


st.divider()


# 11. COMPLETE TRIP DATA TABLE


st.subheader("📋 Trip Records")

preview = con.execute(
    f"""
    SELECT *
    FROM trips
    WHERE {date_filter}
    LIMIT 100
    """,
    params
).df()


st.caption("Showing up to 100 actual trip records")

st.dataframe(
    preview,
    width="stretch",
    height=400,
    hide_index=True
)



# 12. DOWNLOAD CSV REPORT

csv_data = preview.to_csv(
    index=False
).encode("utf-8")

st.download_button(
    label="⬇️ Download Trip Records CSV",
    data=csv_data,
    file_name="fleetsense_trip_report.csv",
    mime="text/csv"
)



# 13. FOOTER

st.divider()

st.caption(
    "Data source: NYC Taxi & Limousine Commission (TLC) "
    "2025 Yellow Taxi Trip Records."
)

st.success("FleetSense dashboard execution completed.")

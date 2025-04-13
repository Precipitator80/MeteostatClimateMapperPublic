# INSTALLATION INSTRUCTIONS
# To create a virtual environment for this project, use the following command:
#   python -m venv .venv
# Then, select it using the following command.
#   .venv\Scripts\activate
# If this does not work on Windows, try running the following command to change the execution policy for the process.
#   Set-ExecutionPolicy Unrestricted -Scope Process
# Install any required modules.
#   pip install -r requirements.txt
# Dev note: The list of required modules can be updated using the pipreqs module.
#   pip install pipreqs
#   pipreqs . --ignore ".venv" --force
# Finally, start the app.
#   .streamlit run .\main.py.

# MODULES
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
import folium
import streamlit as st
from streamlit_folium import st_folium

import meteostat_functions

MAP_KEY = "m"
STATIONS_KEY = "stations"
CUSTOM_DATE_RANGE_STATIONS_KEY = "custom_date_range_stations"
BOUNDS_START = {
    "_southWest": {"lat": 51.76953957596099, "lng": 8.861846923828127},
    "_northEast": {"lat": 52.52791908000258, "lng": 11.059112548828125},
}
CENTER_START = [52.15, 9.96]
ZOOM_START = 10

# Define mappings for variables and months.
VARIABLE_MAP = {
    "tmax": "Max Temp (°C)",
    "tavg": "Average Temp (°C)",
    "tmin": "Min Temp (°C)",
    "prcp": "Precip (mm)",
    "tsun": "Sunshine (hrs)",
    "wspd": "Wind (km/h)",
    "pres": "Pressure (hPa)",
}

MONTH_MAP = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}

st.set_page_config(layout="wide")


def main():
    # Give the page and sidebar titles.
    st.title("Meteostat Climate Mapper")
    st.sidebar.title("Map Controls")

    # Checkbox to toggle update on pan.
    st.sidebar.checkbox("Update on Pan", key="update_on_pan", value=False)

    # Manual update button.
    manual_update = st.sidebar.button("Load Stations in Bounds Now")

    # Number input for stations to fetch.
    st.sidebar.number_input(
        "Number of Stations to Fetch (0 for all in bounds)",
        min_value=0,
        max_value=100,
        key="fetch_limit",
        value=50,
    )

    # Add toggle for custom date range
    st.sidebar.toggle("Use Custom Date Range", key="use_custom_date_range", value=False)

    # Add date input fields for custom date ranges.
    if st.session_state.use_custom_date_range:
        # Get the current date and year.
        current_date = datetime.now()
        current_year = current_date.year

        # Set initial values for the date range.
        if "start_date" not in st.session_state:
            st.session_state.start_date = date(current_year - 1, 1, 1)
            st.session_state.end_date = date(current_year, 1, 1)

        # Update the date range using a date input.
        st.sidebar.date_input(
            "Start Date",
            key="start_date",
            min_value=datetime(1900, 1, 1),
            max_value=st.session_state.end_date - relativedelta(years=1),
        )
        st.sidebar.date_input(
            "End Date",
            key="end_date",
            min_value=st.session_state.start_date + relativedelta(years=1),
            max_value=current_date,
        )

    # Determine which stations key to use for this pass.
    station_key_to_use = STATIONS_KEY
    data_key_to_use = station_key_to_use + "-data"
    if st.session_state.use_custom_date_range:
        station_key_to_use = CUSTOM_DATE_RANGE_STATIONS_KEY

    # Initialise dictionaries of station markers.
    if station_key_to_use not in st.session_state:
        st.session_state[station_key_to_use] = dict()
        st.session_state[data_key_to_use] = dict()

    # Clear map button
    clear_map = st.sidebar.button("Clear Map")
    if clear_map:
        st.session_state[station_key_to_use].clear()

    # Check whether to query for new stations.
    if (
        MAP_KEY not in st.session_state
        or st.session_state.update_on_pan
        or manual_update
    ):
        bounds = BOUNDS_START
        if MAP_KEY in st.session_state:
            bounds = st.session_state[MAP_KEY]["bounds"]

        meteostat_functions.update_markers(
            st.session_state[station_key_to_use],
            st.session_state[data_key_to_use],
            bounds,
        )

    # Use a feature group passed to the Streamlit map to add markers without re-rendering the map.
    fg = folium.FeatureGroup(name=station_key_to_use)
    for station_id in st.session_state[station_key_to_use]:
        marker = st.session_state[station_key_to_use][station_id]
        # Ignore any stations without data (no generated marker).
        if marker is not None:
            fg.add_child(marker)

    # Carry forward map parameters if possible in case the map must be re-rendered.
    # This happens on occasion, possibly due to Streamlit jank.
    if MAP_KEY in st.session_state:
        center = st.session_state[MAP_KEY]["center"]
        zoom = st.session_state[MAP_KEY]["zoom"]
    else:
        center = CENTER_START
        zoom = ZOOM_START

    # Finally, render the map.
    render_map(center, zoom, fg, data_key_to_use)


@st.fragment
def render_map(center, zoom, fg, data_key_to_use):
    # Render a starting map with constant parameters to avoid re-rendering it.
    m = folium.Map(location=CENTER_START, zoom_start=ZOOM_START)

    # Render the streamlit folium map.
    output = st_folium(
        m,
        center=center,
        zoom=zoom,
        key=MAP_KEY,
        feature_group_to_add=fg,
        width=1600,
        height=900,
    )

    # Render a data frame for the last clicked on marker.
    if (
        MAP_KEY in st.session_state
        and "last_object_clicked" in st.session_state[MAP_KEY]
        and st.session_state[MAP_KEY]["last_object_clicked"] is not None
    ):
        # Get the data for the last clicked marker.
        last_obj = st.session_state[MAP_KEY]["last_object_clicked"]
        df = st.session_state[data_key_to_use][(last_obj["lat"], last_obj["lng"])]
        render_climate_data_frame(df)

    # If updating on pan, compare the previous bounds to the current bounds.
    # Rerun only if the bounds have changed (map moved).
    bounds = output["bounds"]
    if st.session_state.update_on_pan and (
        "prev_bounds" not in st.session_state
        or st.session_state["prev_bounds"] != bounds
    ):
        st.session_state["prev_bounds"] = bounds
        st.rerun()


def render_climate_data_frame(df: pd.DataFrame):
    readable_df = make_climate_data_frame_readable(df)

    # Apply conditional formatting to the data.
    # Use FINAL display names as formatting is applied to the final data frame.
    def climate_style(styler):
        # Exclude the "Total" column from all formatting.
        columns_to_format = [col for col in styler.data.columns if col != "Total"]

        # Apply scales to each variable type.
        temp_vars = [
            name
            for name in ["Max Temp (°C)", "Average Temp (°C)", "Min Temp (°C)"]
            if name in styler.data.index
        ]

        if temp_vars:
            styler.background_gradient(
                cmap="coolwarm",
                axis=1,
                subset=pd.IndexSlice[temp_vars, columns_to_format],
                vmin=-40,
                vmax=40,
            )

        if "Precip (mm)" in styler.data.index:
            styler.background_gradient(
                cmap="Greens",
                axis=1,
                subset=pd.IndexSlice[["Precip (mm)"], columns_to_format],
                vmin=0,
                vmax=225,
            )

        if "Sunshine (hrs)" in styler.data.index:
            styler.background_gradient(
                cmap="afmhot",
                axis=1,
                subset=pd.IndexSlice[["Sunshine (hrs)"], columns_to_format],
                vmin=0,
                vmax=270,
            )

        if "Wind (km/h)" in styler.data.index:
            styler.background_gradient(
                cmap="PuBu",
                axis=1,
                subset=pd.IndexSlice[["Wind (km/h)"], columns_to_format],
                vmin=0,
                vmax=30,
            )

        if "Pressure (hPa)" in styler.data.index:
            styler.background_gradient(
                cmap="bwr",
                axis=1,
                subset=pd.IndexSlice[["Pressure (hPa)"], columns_to_format],
                vmin=960,
                vmax=1040,
            )

        # Show data to one decimal place.
        styler.format("{:.1f}")
        return styler

    st.dataframe(
        readable_df.style.pipe(climate_style),
        height=400,
        use_container_width=True,
    )


@st.cache_data
def make_climate_data_frame_readable(df):
    # Add columns for any missing months.
    df = df.reindex(range(1, 13)).reset_index()

    # Transpose the data frame to match the orientation of those on Wikipedia.
    df_transposed = (
        df.reset_index()
        .melt(id_vars="month")
        .pivot(index="variable", columns="month")
        .droplevel(0, axis=1)
    )

    # Change the order of rows to match that on Wikipedia.
    df_ordered = df_transposed.loc[
        [var for var in VARIABLE_MAP.keys() if var in df_transposed.index]
    ]

    # Rename rows and columns to make them more readable.
    df_renamed = df_ordered.rename(index=VARIABLE_MAP).rename(columns=MONTH_MAP)

    # Add averages and totals.
    df_renamed["Average"] = df_renamed.mean(axis=1)  # Average across all months.
    df_renamed["Total"] = df_renamed.sum(axis=1)  # Total across all months.

    return df_renamed


if __name__ == "__main__":
    main()

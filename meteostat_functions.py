from datetime import datetime
from dateutil.relativedelta import relativedelta
from meteostat import Monthly, Normals, Point, Stations
import pandas as pd
import folium
import streamlit as st
from folium.plugins import BeautifyIcon

import climate_classifier

# Koppen climate colour scheme from Wikipedia (https://en.wikipedia.org/wiki/K%C3%B6ppen_climate_classification)
KOPPEN_COLOURS = {
    # Tropical (A)
    "Af": "#00FF00",  # Tropical rainforest
    "Am": "#007F00",  # Tropical monsoon
    "Aw": "#00AA00",  # Tropical savanna
    # Arid (B)
    "BWh": "#FF0000",  # Hot desert
    "BWk": "#FF7F7F",  # Cold desert
    "BSh": "#FFA500",  # Hot semi-arid
    "BSk": "#FFD37F",  # Cold semi-arid
    # Temperate (C)
    "Csa": "#FFEE00",  # Hot-summer Mediterranean
    "Csb": "#D0D000",  # Warm-summer Mediterranean
    "Csc": "#A0A000",  # Cold-summer Mediterranean
    "Cwa": "#FFFF00",  # Monsoon-influenced humid subtropical
    "Cwb": "#E0E000",  # Subtropical highland
    "Cwc": "#C0C000",  # Cold subtropical highland
    "Cfa": "#B2FF4D",  # Humid subtropical
    "Cfb": "#66FF33",  # Temperate oceanic
    "Cfc": "#33CC00",  # Subpolar oceanic
    # Continental (D)
    "Dsa": "#4DA6FF",  # Hot-summer humid continental
    "Dsb": "#1A75FF",  # Warm-summer humid continental
    "Dsc": "#005CE6",  # Subarctic continental
    "Dwa": "#99CCFF",  # Monsoon-influenced hot-summer
    "Dwb": "#6699FF",  # Monsoon-influenced warm-summer
    "Dwc": "#3366FF",  # Monsoon-influenced subarctic
    "Dfa": "#00BFFF",  # Hot-summer humid continental
    "Dfb": "#0080FF",  # Warm-summer humid continental
    "Dfc": "#004C99",  # Subarctic
    # Polar (E)
    "ET": "#FFFFFF",  # Tundra
    "EF": "#888888",  # Ice cap
    # Default fallbacks
    None: "#CCCCCC",  # For stations without normals
}


def update_markers(marker_array, data_array, bounds):
    # Fetch stations and generate markers for any stations not yet added.
    for _, station in fetch_stations(bounds).iterrows():
        station_id = station.name
        if station_id not in marker_array:
            # Try to fetch either normal or monthly data.
            normals = None
            try:
                if not st.session_state.use_custom_date_range:
                    normals = get_latest_normal_by_station_id(station_id)
                else:
                    normals = get_monthly_as_normal(
                        station_id,
                        datetime.combine(
                            st.session_state.start_date, datetime.min.time()
                        ),
                        datetime.combine(
                            st.session_state.end_date - relativedelta(days=1),
                            datetime.min.time(),
                        ),
                    )
            except Exception:
                print(
                    f"Failed to get normal / monthly data for station with ID {station_id}."
                )

            # Store all non-null normals, but only calculate Köppen for normals with full average temperature and precipitation data.
            if normals is not None:
                # Set popup text and marker colour.
                popup = (
                    f"<b>{station['name']}</b><br>Elevation: {station['elevation']}m"
                )
                color = KOPPEN_COLOURS[None]

                # Turn sunshine data into hours rather than minutes.
                if "tsun" in normals:
                    normals["tsun"] = normals["tsun"] / 60

                data_array[(station["latitude"], station["longitude"])] = normals
                if (
                    not normals[["tavg", "prcp"]].isna().any(axis=1).any()
                    and len(normals.index) == 12
                ):
                    koppen = climate_classifier.calculate_koppen_climate_from_normals(
                        normals
                    )
                    climate_type = koppen.iloc[0]
                    if isinstance(climate_type, str):
                        popup += f"\nKöppen: {climate_type}"
                        color = KOPPEN_COLOURS[climate_type]

                marker_array[station_id] = folium.Marker(
                    location=[station["latitude"], station["longitude"]],
                    popup=popup,
                    icon=BeautifyIcon(
                        icon="info",
                        icon_shape="circle",
                        background_color=color,
                        border_color="black",
                        text_color="white",
                    ),
                    # icon=folium.Icon(color="blue", icon="cloud")
                )
            else:
                # If the station has no data or an exception occurred, do not add a marker.
                # Set the key to None in the dictionary so that it is not processed in future.
                marker_array[station_id] = None


def fetch_stations(bounds: dict):
    """
    Fetch weather stations with safe sampling without loading all stations
    """
    top_left = (bounds["_northEast"]["lat"], bounds["_southWest"]["lng"])
    bottom_right = (bounds["_southWest"]["lat"], bounds["_northEast"]["lng"])

    # Do an initial fetch of stations.
    limit = st.session_state.fetch_limit
    stations = Stations().bounds(top_left, bottom_right).fetch(limit)
    if not stations.empty:
        # Use the number of stations retrieved to try a sampled fetch.
        # The limit in the sampled fetch must not exceed the number of stations, hence the safety calculation.
        safe_sample = min(limit, len(stations))
        return Stations().bounds(top_left, bottom_right).fetch(safe_sample, sample=True)

    return pd.DataFrame()


def get_latest_normal(point: Point) -> {pd.DataFrame, pd.DataFrame}:
    """
    Fetches the latest normal climate data for the given location.

    Args:
        point (Point): The geographical point (latitude and longitude) for which to fetch the normals data.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: A tuple containing:
            - DataFrame of the nearest station with normals data.
            - DataFrame of the latest normals data for the specified point.

    Raises:
        ValueError: If no nearby stations with available normals data are found.
    """
    # Fetch nearby stations.
    nearby_stations = Stations().nearby(point._lat, point._lon).fetch(10)

    # Find the nearest station with available normals data.
    for station_id in nearby_stations.index:
        if not Normals(station_id).fetch().empty:
            break
    else:
        raise ValueError("No nearby stations with available normals data found.")

    return nearby_stations.loc[station_id], get_latest_normal_by_station_id(station_id)


def get_latest_normal_by_station_id(station_id: int) -> {pd.DataFrame}:
    # Fetch normals data.
    data = Normals(station_id).fetch()
    if data.empty:
        return

    # Extract the start and end year of the latest normal and return just this part of the normals data.
    latest_year_index = -1
    start_year = data.index.levels[0][latest_year_index]
    end_year = data.index.levels[1][latest_year_index]
    return data.loc[(start_year, end_year)]


def get_monthly_as_normal(
    station_id: int, start: datetime, end: datetime
) -> pd.DataFrame:
    # Group monthly data by the month number and get the mean.
    monthly = Monthly(station_id, start, end).fetch()
    if monthly.empty:
        return
    return monthly.groupby(monthly.index.month).mean()

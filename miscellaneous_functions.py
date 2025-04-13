from datetime import datetime
import matplotlib.pyplot as plt
from meteostat import Hourly, Point, Stations
import pandas as pd

import climate_classifier
import meteostat_functions


def plot_normal(name: str, point: Point, ax: plt.Axes):
    """
    Plots the normal weather data for a specified location.

    Args:
        name (str): The name of the location.
        point (Point): The geographical point (latitude and longitude) for which to plot the data.
        ax (plt.Axes): The matplotlib Axes object on which to plot the data.

    Returns:
        None
    """
    # Retrieve the latest normal.
    station, latest_normal = meteostat_functions.get_latest_normal(point)

    # Calculate yearly precipitation and mean temperature.
    total_precipitation = latest_normal["prcp"].sum()
    avg_temperature = latest_normal["tavg"].mean()

    # Plot precipitation data on the primary y-axis.
    ax.bar(
        latest_normal.index,
        latest_normal["prcp"],
        label="Precipitation",
        color="tab:blue",
    )
    ax.set_ylabel(f"Precipitation (mm)\nTotal: {total_precipitation:.2f} mm")

    # Create a secondary y-axis and plot temperature data on it. This renders it above precipitation.
    ax2 = ax.twinx()
    ax2.plot(
        latest_normal.index, latest_normal["tmax"], label="Max Temp", color="tab:red"
    )
    ax2.plot(
        latest_normal.index, latest_normal["tavg"], label="Avg Temp", color="tab:orange"
    )
    ax2.plot(
        latest_normal.index, latest_normal["tmin"], label="Min Temp", color="tab:cyan"
    )
    ax2.set_ylabel(f"Temperature (°C)\nAvg Temp: {avg_temperature:.2f} °C")
    ax2.set_xlabel("Month")
    ax2.set_title(
        f"Weather Data for {station['name']} (nearest normals station to {name})"
    )

    # Swap the y-axis ticks and label positions to have temperature on the left.
    ax.yaxis.tick_right()
    ax2.yaxis.tick_left()
    ax.yaxis.set_label_position("right")
    ax2.yaxis.set_label_position("left")

    # Combine legends from both y-axes.
    lines, labels = ax.get_legend_handles_labels()
    bars, bar_labels = ax2.get_legend_handles_labels()
    ax.legend(lines + bars, labels + bar_labels, loc="upper left")


def calculate_rain_hours(
    name: str, point: Point, start: datetime, end: datetime, threshold: float = 0
):
    """
    Calculates the average number of rain hours per day for a given location over a specified period.

    Args:
        name (str): The name of the location.
        point (Point): The geographical point (latitude and longitude) for which to calculate rain hours.
        start (datetime): The start date of the period for analysis.
        end (datetime): The end date of the period for analysis.
        threshold (float, optional): The precipitation threshold to consider rain hours.

    Returns:
        pd.Series: A Series containing information of interest.

    Raises:
        ValueError: If no nearby stations with available hourly data are found.
    """
    # Fetch nearby stations.
    nearby_stations = Stations().nearby(point._lat, point._lon).fetch(10)

    # Find the nearest station with available hourly data.
    for station_id in nearby_stations.index:
        if not Hourly(station_id, start, end).fetch().empty:
            break
    else:
        raise ValueError("No nearby stations with available hourly data found.")

    # Fetch hourly data.
    data = Hourly(station_id, start, end).fetch()

    # Calculate mean rain hours.
    hours = data["prcp"].notnull().sum()
    rain_hours = data["prcp"].gt(threshold).sum()
    num_days = hours / 24
    avg_rain_hours_per_day = rain_hours / num_days

    # Create a pandas Series to return the results.
    return pd.Series(
        {
            "Target Location": name,
            "Nearest Station ID": station_id,
            "Nearest Station Name": nearby_stations.loc[station_id]["name"],
            "Average Rain Hours/Day": avg_rain_hours_per_day,
            "Total Precipitation": data["prcp"].sum(),
            "Average Temperature": data["temp"].mean(),
            "Total Hours": hours,
            "Rain Hours": rain_hours,
            "Number of Days": num_days,
        }
    )


def print_koppen_data():
    # Set time period for dailies, monthlies or yearlies.
    startYear, endYear = 2023, 2023
    start = datetime(startYear, 1, 1, 0, 0, 0)
    end = datetime(endYear, 12, 31, 0, 0, 0)

    # Create points for several locations.
    # Taken from https://www.meteotemplate.com/template/plugins/climateClassification/koppen.php (Accessed 26.08.2024 and 05.04.2025).
    locations = {
        "Iquitos (Af)": Point(-3.74419, -73.25171),
        "Mangalore (Am)": Point(12.91340, 74.85452),
        "Calcutta (Aw)": Point(22.56834, 88.36002),
        "Monterrey (BSh)": Point(36.59820, -121.88960),
        "Williston (BSk)": Point(48.14751, -103.61654),
        "Alice Springs (BWh)": Point(-23.69862, 133.88076),
        "Lovelock (BWk)": Point(40.17931, -118.47378),
        "Buenos Aires (Cfa)": Point(-34.60649, -58.39394),
        "Canberra (Cfb)": Point(-35.29526, 149.11793),
        "Reykjavik (Cfc)": Point(64.14566, -21.95202),
        "Rome (Csa)": Point(41.88779, 12.57002),
        "Olympia (Csb)": Point(47.03914, -122.89815),
        "Kathmandu (Cwa)": Point(27.71628, 85.32249),
        "Johannesburg (Cwb)": Point(-26.20608, 28.03717),
        "Almaty (Dfa)": Point(43.23858, 76.88926),
        "Oslo (Dfb)": Point(59.91334, 10.74959),
        "Dawson Creek (Dfc)": Point(55.75849, -120.23886),
        "Jakutsk (Dfd)": Point(62.03688, 129.74441),
        "Hakkari (Dsa)": Point(37.577, 43.739),
        "Chakhcharan (Dsb)": Point(34.5225, 65.251667),
        "Anchorage (Dsc)": Point(61.216667, -149.893611),
        "Seoul (Dwa)": Point(37.566667, 126.983333),
        "Khutag (Dwb)": Point(49.3925, 102.7025),
        "Irkutsk (Dwc)": Point(52.289167, 104.28),
        "Nuuk (ET)": Point(64.176667, -51.736111),
        "Byrd (EF)": Point(-80.0147, -119.5656),
    }

    # Create climatographs.
    fig, axs = plt.subplots(len(locations), 1, figsize=(10, 8), sharex=True)
    i = 0
    for name, point in locations.items():
        # Create the climatographs from normals data.
        plot_normal(name, point, axs[i])
        i = i + 1
    # Plot the climatographs.
    plt.tight_layout()
    plt.show()

    # Analyse rain hours and climate type.
    rain_results, koppen_results = [], []
    for name, point in locations.items():
        # Rain data.
        rain_results.append(calculate_rain_hours(name, point, start, end))
        # Köppen climate classification.
        koppen_results.append(climate_classifier.calculate_koppen_climate(name, point))
    # Combine each set of results into a single DataFrame and print it.
    rain_results_df = pd.DataFrame(rain_results)
    print("Rain Hours:")
    print(rain_results_df)
    print("----------")
    koppen_results_df = pd.DataFrame(koppen_results)
    print("Climate Classification:")
    print(koppen_results_df)
    print("----------")

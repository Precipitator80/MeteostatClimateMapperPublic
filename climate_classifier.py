from meteostat import Point
import pandas as pd

import meteostat_functions


def calculate_koppen_climate(
    name: str, point: Point, isotherm: int = 0
) -> pd.DataFrame:
    """
    Determines the Köppen climate classification for a specified location based on climate normals.

    Args:
        name (str): The name of the location.
        point (Point): The geographical point (latitude and longitude) for which to determine the climate classification.
        isotherm (int, optional): The isotherm value to determine the primary label for temperate or continental climates.

    Returns:
        pd.Series: A Series containing information of interest.
    """
    station, data = meteostat_functions.get_latest_normal(point)

    return pd.concat(
        [
            calculate_koppen_climate_from_normals(data, isotherm),
            pd.Series(
                {
                    "Target Location": name,
                    "Nearest Station ID / WMO": station["wmo"],
                    "Nearest Station Name": station["name"],
                }
            ),
        ]
    )


def calculate_koppen_climate_from_normals(data: pd.DataFrame, isotherm: int = 0):
    # print(data)

    # Divide by average annual temperature
    min_monthly_temp = data["tavg"].min()
    avg_monthly_temp = data["tavg"].mean()
    max_monthly_temp = data["tavg"].max()
    yearly_prcp = data["prcp"].sum()

    # Define summer and winter months for the Northern Hemisphere.
    northern_summer_months = [4, 5, 6, 7, 8, 9]
    northern_winter_months = [1, 2, 3, 10, 11, 12]

    # Calculate mean temperatures for summer and winter.
    northern_summer_mean = data[data.index.isin(northern_summer_months)]["tavg"].mean()
    northern_winter_mean = data[data.index.isin(northern_winter_months)]["tavg"].mean()

    # Determine which period is actually summer based on mean temperature.
    if northern_summer_mean >= northern_winter_mean:
        summer_months, winter_months = northern_summer_months, northern_winter_months
    else:
        summer_months, winter_months = northern_winter_months, northern_summer_months

    summer_data: pd.DataFrame = data[data.index.isin(summer_months)]
    winter_data: pd.DataFrame = data[data.index.isin(winter_months)]

    # Calculate the precipitation threshold that arid climates must lie under.
    summer_prcp = summer_data["prcp"].sum()
    winter_prcp = winter_data["prcp"].sum()
    prcp_threshold = 20 * avg_monthly_temp
    if summer_prcp >= 0.7 * yearly_prcp:
        prcp_threshold = prcp_threshold + 280
    elif winter_prcp < 0.7 * yearly_prcp:
        prcp_threshold = prcp_threshold + 140

    # Check for each of the climate types.
    tertiary_label = ""  # Default value for teriary label.
    if max_monthly_temp < 10:  # Step 1: Check for Polar Climates (E).
        primary_label = "E"
        if max_monthly_temp >= 0:
            secondary_label = "T"  # Tundra
        else:
            secondary_label = "F"  # Ice Cap
    elif yearly_prcp < prcp_threshold:  # Step 2: Check for Arid Climates (B).
        primary_label = "B"
        if yearly_prcp < prcp_threshold / 2:
            secondary_label = "W"  # Arid desert
        else:
            secondary_label = "S"  # Semi-arid steppe
        if avg_monthly_temp >= 18:
            tertiary_label = "h"  # Hot
        else:
            tertiary_label = "k"  # Cold
    elif min_monthly_temp >= 18:  # Step 3: Check for Tropical Climates (A).
        primary_label = "A"
        min_monthly_prcp = data["prcp"].min()
        if min_monthly_prcp >= 60:
            secondary_label = "f"  # Rainforest
        else:
            tropical_rain_ratio = 100 - 0.04 * yearly_prcp
            if min_monthly_prcp >= tropical_rain_ratio:
                secondary_label = "m"  # Monsoon
            else:
                secondary_label = (
                    "w"  # Savanna (w vs s is trivial due to low temp range)
                )
    else:  # Step 4: Check for Temperate (C) and Continental (D) Climates.
        # Check the primary label.
        primary_label = "C" if min_monthly_temp >= isotherm else "D"

        # Check dry season label.
        driest_summer_month = summer_data["prcp"].min()
        wettest_summer_month = summer_data["prcp"].max()
        driest_winter_month = winter_data["prcp"].min()
        wettest_winter_month = winter_data["prcp"].max()
        if wettest_summer_month >= 10 * driest_winter_month:
            secondary_label = "w"  # Dry Winter
        elif wettest_winter_month >= 3 * driest_summer_month and driest_summer_month < (
            40 if primary_label == "C" else 30
        ):
            secondary_label = "s"  # Dry Summer
        else:
            secondary_label = "f"  # No Dry Season

        # Check temperature label.
        if data["tavg"].gt(10).sum() >= 4:
            if max_monthly_temp >= 22:
                tertiary_label = "a"  # Hot Summer
            else:
                tertiary_label = "b"  # Warm Summer
        elif min_monthly_temp <= -38:
            tertiary_label = "d"  # Very Cold Winter
        else:
            tertiary_label = "c"  # Cold Summer

    # Combine the labels.
    climate_classification = primary_label + secondary_label + tertiary_label

    return pd.Series(
        {
            "Köppen climate classification": climate_classification,
            "Min Monthly Temp": min_monthly_temp,
            "Avg Monthly Temp": avg_monthly_temp,
            "Max Monthly Temp": max_monthly_temp,
            "Precipitation Threshold": prcp_threshold,
            "Yearly Precipitation": yearly_prcp,
        }
    )

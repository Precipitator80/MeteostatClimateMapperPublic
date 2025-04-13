# Meteostat Climate Mapper

This application offers an interactive way to browse per-station climate data. Additionally, a date selection allows the user to use monthly data to observe recent trends.

## Features

- Specify the number of stations to fetch and press the load stations button.
  - Alternatively, switch on update on pan to fetch stations each time you move the map (still within the specified number to fetch).
  - Note: Some stations fetched from Meteostat may have incomplete data. These will not be shown on the map, but still count as part of the fetch count.
- Click on weather stations on the map to view their data in a data frame.
  - Conditional formatting, averages and totals are included for easier analysis.
- Specify a custom date range to observe recent trends.
  - The specified period must be at least a year.
  - The map can be cleared to avoid confusion when switching date ranges.

## Accessing the Application Online

The application should be accessible on Streamlit Community Cloud.

## Local Installation Instructions

1. Create a virtual environment for the project.
    - `python -m venv .venv`
2. Select the virtual environment.
    - `.venv\Scripts\activate`
3. If the virtual environment does not activate on Windows, try changing the execution policy for the process.
    - `Set-ExecutionPolicy Unrestricted -Scope Process`
4. Install any required modules.
    - `pip install -r requirements.txt`
    - Dev note: The list of required modules can be updated using the pipreqs module
    - `pip install pipreqs`
    - `pipreqs . --ignore ".venv" --force`
5. Finally, start the app.
    - `.streamlit run .\main.py`

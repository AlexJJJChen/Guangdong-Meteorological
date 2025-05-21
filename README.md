# Guangdong Meteorological Disaster Risk Analysis Platform

This project develops an interactive dashboard for analyzing meteorological disaster risks (Flood and Fire) across Guangdong Province, China. It integrates real-time and forecasted weather data with static geographical and land-use information to provide a comprehensive risk assessment. The platform features an interactive map for visualizing risk levels and an AI-powered chatbot for querying weather and risk information.

## Features

* **Interactive Risk Map:** Visualize flood and fire risk levels across different cities in Guangdong Province.
* **Time-based Risk Analysis:** View risk assessments for current conditions and various forecast horizons (3h, 6h, 12h, 24h, 48h, 72h).
* **Dynamic Data Refresh:** Update live weather data with a single click.
* **AI Chatbot:** An intelligent assistant capable of answering questions about weather conditions and disaster risks in Guangdong Province, leveraging the displayed data.
* **Two Disaster Types:** Dedicated analysis and visualization for both Flood and Fire risks.
* **Data Preprocessing:** Scripts to process static geographical (DEM, Land Use) and administrative boundary data.

## Technologies Used

* **Frontend:** Dash (Plotly Dash) for interactive web applications.
* **Mapping:** Plotly Express for geographical visualizations with Mapbox.
* **Geospatial Data Handling:** `geopandas` and `rasterio` for processing vector (shapefiles) and raster (GeoTIFFs) data.
* **Weather Data:** OpenWeatherMap API for fetching current and forecasted weather data.
* **Risk Modeling:** Custom Python logic for calculating flood and fire risk indices based on meteorological and geographical factors.
* **Chatbot:** OpenAI API (GPT models) for natural language understanding and generation.
* **Environment Management:** `python-dotenv` for securely managing API keys.
* **Data Storage:** JSON and GeoJSON files for processed data.

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository_url>
cd <repository_name>
```

### 2. Set up Virtual Environment 
```bash
python -m venv venv
# On Windows
.\venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
OPENAI_API_KEY="your_openai_api_key_here"
```

### 5. Prepare Static Data
```bash
python preprocess_static_data.py
```

### 6. Fetch Initial Weather Data
```bash
python data_fetcher.py
```

## Running the Application
```bash
python dashboard_app.py
```
Open your web browser and navigate to the address displayed in your terminal (e.g., http://127.0.0.1:8050/)


## Project Framework

This project is organized into several key Python scripts and modules, each responsible for distinct stages of the data workflow and application logic. The following outlines the Input, Main Functions (Doing), and Output for each file in greater detail:


### 1. preprocess_static_data.py

- **Input**:
  - DEM (Digital Elevation Model) raster files (`.tif`) representing elevation data of Guangdong.[SRTM30米-广东省 -- DEM数据产品](https://data.casearth.cn/thematic/dem/435)
  - Land use/land cover raster files (`.tif`), classifying areas like forest, cropland, impervious surface, etc. [The 30 m annual land cover datasets and its dynamics in China from 1985 to 2023](https://zenodo.org/records/12779975)
  - Administrative boundary shapefiles (`.shp`), containing city-level polygons.

- **Main Functions**:
  - Loads, checks, and reprojects DEM and land-use data to a common coordinate reference system (WGS84), matching the administrative boundaries for spatial consistency.
  - Clips raster data to city boundaries using spatial masking, extracting city-specific elevation and land cover arrays.
  - Calculates each city’s **"lowland index"** (proportion of area below a province-wide lowland threshold, e.g., the 30th percentile of provincial elevation) and identifies proportions of land use categories (e.g., impervious surface, forest, wetland).
  - Computes fire risk **land cover weights** by applying predefined multipliers to the land use type fractions in each city.
  - Collects city-level metadata, including centroid (latitude/longitude), administrative codes, and computed indices, for downstream use.

- **Output**:
  - Generates `guangdong_cities_meta.json`, a structured JSON file with per-city metadata: city name, admin code, coordinates, lowland index, impervious fraction, and fire risk weight.
  - Creates `guangdong_border.geojson`, containing all Guangdong city boundary polygons in GeoJSON format for geospatial visualization and mapping.


### 2. data_fetcher.py

- **Input**:
  - `guangdong_cities_meta.json` as the authoritative source for city details and coordinates.

- **Main Functions**:
  - For each city, retrieves real-time and multi-horizon weather forecasts (3h, 6h, 12h, 24h, 48h, 72h) via OpenWeatherMap's API, using each city's latitude and longitude.
  - Parses API returns for key weather parameters: temperature, humidity, wind speed and direction, and precipitation.
  - For forecast data, locates the nearest available forecast interval to each target horizon and translates times from UTC to Beijing time for consistency with user expectations.
  - Logs and handles missing or erroneous data gracefully to ensure ongoing operation.

- **Output**:
  - Writes all retrieved weather data into `guangdong_weather.json`, organizing the results per city and per forecast period for seamless access by risk modeling modules.


### 3. risk_model.py

- **Input**:
  - `guangdong_cities_meta.json` (city geospatial and land use metadata).
  - `guangdong_weather.json` (latest weather data, both current and forecast horizons).

- **Main Functions**:
  - Implements algorithms to assess both flood and fire risk for each city at the selected forecast time, based on city land surface features and weather inputs:
    - **Flood Risk**: Combines precipitation, lowland index, and impervious fraction using a weighted sum (flood index = α × precipitation + β × lowland index + γ × impervious fraction), followed by classification into risk levels (`very low`, `low`, `medium`, `high`, `very high`) according to thresholds.
    - **Fire Risk**: Adapts the Angström formula, blending temperature, humidity, wind speed, and the precomputed land cover-based fire weight to get a fire risk score and classify it similarly to the flood risk.
  - Handles missing weather or metadata entries robustly, ensuring outputs are returned only for valid city/time pairs.
  - Can batch process all cities and all relevant forecast periods.

- **Output**:
  - Returns a dictionary mapping each city name to a detailed risk assessment object, including all risk scores, classified labels (risk levels), and the specific weather data used in the calculation. This output is passed to both the dashboard and chatbot modules for visualization and user queries.


### 4. chatbot_service.py

- **Input**:
  - Per-city risk assessment data (from `risk_model.py`), latest weather data, city metadata, and user input queries (natural language).

- **Main Functions**:
  - Prepares a natural language “context” summary for the AI model, synthesizing recent risk and weather index results for one or more key cities (by default, the first cities or always prioritizing Guangzhou if available).
  - Sends system and user prompts to the OpenAI GPT API, constructing a dialogue in which the user asks about risk, weather trends, or city comparisons, and the assistant provides focused, concise answers deeply grounded in the current data context.
  - Handles missing risk data, parameterizes the level of response detail (e.g., risk levels, numerical scores, and forecast period), and gracefully relays errors or unavailable responses.

- **Output**:
  - Returns formatted chatbot responses ready for display in the app’s interactive chatbox, maintaining accessible, context-driven dialogue for user inquiries.


### 5. dashboard_app.py

- **Input**:
  - `guangdong_cities_meta.json` (for city definitions and geographic references), `guangdong_border.geojson` (city polygons), `guangdong_weather.json` (real-time and forecast weather), and risk evaluation results (from `risk_model.py`).

- **Main Functions**:
  - Builds an interactive Dash web application featuring:
    - Risk type and forecast time selection (e.g., current, 24h, 72h).
    - A side panel with live data refresh, risk switching, and AI chatbot query controls.
    - Main map visualization using Plotly Mapbox, displaying risk level distribution across Guangdong cities in color-coded choropleth, with hover details including risk level, score, and key weather parameters.
    - Callbacks that auto-update the display and stored chat context when inputs change or new data is fetched, and trigger risk modeling and chatbot response functions in real time.
  - Integrates data loads, live map rendering, and chat-based Q&A, with graceful handling of missing or stub data on first launch.

- **Output**:
  - Provides an interactive browser-based dashboard for risk map viewing, live AI chat, and seamless user operations.

### 6. ui_theme.py

- **Input**:
  - None.

- **Main Functions**:
  - Stores a dictionary/list of CSS style rules that define the theme for dashboard components, including colors, padding, margins, fonts, dropdown/button styles, panel backgrounds, hover effects, headers, and chat area appearance.
  - Ensures a consistent and modern visual appearance throughout the Dash app.

- **Output**:
  - Theme object(s) imported by `dashboard_app.py` to apply a unified look and feel across the entire application UI.


### Workflow Overview

The project follows a data pipeline pattern:
- **Static preprocessing** (`preprocess_static_data.py`) → **Weather fetching** (`data_fetcher.py`) → **Risk estimation** (`risk_model.py`)
- **Dashboard** (`dashboard_app.py`) draws on all outputs, orchestrates user interactions, and pushes data to the AI chatbot module (`chatbot_service.py`).
- **User experience and presentation** are unified via `ui_theme.py`.

All modules communicate through clearly defined JSON file outputs and Python dictionary structures, ensuring modularity, reproducibility, and scalability across updates and new disaster types.
```</MARKDOWN_RESPONSE

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
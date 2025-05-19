import dash
from dash import dcc, html, Input, Output, State, ctx # Added State and ctx
import plotly.express as px
import pandas as pd
import json
from data_fetcher import update_weather_json # (modified to be callable)
from risk_model import estimate_region_risk #
from ui_theme import dashboard_theme #
from chatbot_service import get_chatbot_response, get_weather_context_for_chatbot # New import
import os
import time # For refresh button logic

# --- Global Variables & Initial Data Loading ---
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
GUANGDONG_CITIES_META_FILE = os.path.join(DATA_DIR, 'admin_unit', 'guangdong_cities_meta.json')
GUANGDONG_GEOJSON_FILE = os.path.join(DATA_DIR, 'admin_unit', 'guangdong_border.geojson')
GUANGDONG_WEATHER_FILE = os.path.join(DATA_DIR, 'guangdong_weather.json')

# Ensure data files exist or try to create them
if not os.path.exists(GUANGDONG_CITIES_META_FILE) or not os.path.exists(GUANGDONG_GEOJSON_FILE):
    print(f"Warning: Metadata or GeoJSON file not found. Please run preprocess_static_data.py.")
    # You might want to exit or handle this more gracefully
    # For now, the app might fail if these are missing.
    # As a fallback, create dummy files if they are missing to allow the app to start
    if not os.path.exists(os.path.join(DATA_DIR, 'admin_unit')):
        os.makedirs(os.path.join(DATA_DIR, 'admin_unit'))
    if not os.path.exists(GUANGDONG_CITIES_META_FILE):
        with open(GUANGDONG_CITIES_META_FILE, 'w') as f: json.dump([], f) # Empty list
    if not os.path.exists(GUANGDONG_GEOJSON_FILE):
         with open(GUANGDONG_GEOJSON_FILE, 'w') as f: json.dump({"type": "FeatureCollection", "features": []}, f) # Empty GeoJSON

# Initial data load
try:
    with open(GUANGDONG_CITIES_META_FILE, 'r', encoding='utf-8') as f:
        cities_meta = json.load(f) #
except FileNotFoundError:
    print(f"ERROR: {GUANGDONG_CITIES_META_FILE} not found. Please run `preprocess_static_data.py`.")
    cities_meta = [] # Fallback to empty list

try:
    with open(GUANGDONG_GEOJSON_FILE, 'r', encoding='utf-8') as f:
        geojson = json.load(f) #
except FileNotFoundError:
    print(f"ERROR: {GUANGDONG_GEOJSON_FILE} not found. Please run `preprocess_static_data.py`.")
    geojson = {"type": "FeatureCollection", "features": []} # Fallback

cities_meta_dict = {c['city_name']: c for c in cities_meta} if cities_meta else {}
city_list = [c['city_name'] for c in cities_meta] if cities_meta else []

# Initial weather data load or update
if not os.path.exists(GUANGDONG_WEATHER_FILE) or (os.path.exists(GUANGDONG_WEATHER_FILE) and os.path.getsize(GUANGDONG_WEATHER_FILE) < 100): # check if file is too small/empty
    print("Weather data file not found or empty, attempting to fetch initial data...")
    # Determine base path correctly. If dashboard_app.py is in project root, base_path is "."
    # If it's in a subfolder like 'app', base_path might be ".."
    # Assuming dashboard_app.py is at the same level as the 'data' folder parent (e.g. in project_root/app/)
    project_root_for_data_fetcher = os.path.join(os.path.dirname(__file__), '..')
    update_weather_json(base_path=project_root_for_data_fetcher)


risk_time_options = [
    {'label': '现在 (Now)', 'value': 'now'},
    {'label': '3小时预报 (3h Fcst)', 'value': 'forecast-3h'},
    {'label': '6小时预报 (6h Fcst)', 'value': 'forecast-6h'},
    {'label': '12小时预报 (12h Fcst)', 'value': 'forecast-12h'},
    {'label': '24小时预报 (24h Fcst)', 'value': 'forecast-24h'},
    {'label': '48小时预报 (48h Fcst)', 'value': 'forecast-48h'},
    {'label': '72小时预报 (72h Fcst)', 'value': 'forecast-72h'},
]

def build_dataframe(risk_results, disaster_type="flood"): #
    records = []
    if not cities_meta_dict: # Handle case where cities_meta might be empty
        return pd.DataFrame(records)
        
    for city, v in risk_results.items():
        if city not in cities_meta_dict: # Ensure city exists in meta
            print(f"Warning: City '{city}' from risk results not found in cities_meta_dict.")
            continue
        record = {
            'city': city,
            'lat': cities_meta_dict[city]['lat'],
            'lon': cities_meta_dict[city]['lon'],
            'flood_score': v.get('flood_score', float('nan')),
            'flood_risk_level': v.get('flood_risk_level', '未知'),
            'fire_score': v.get('fire_score', float('nan')),
            'fire_risk_level': v.get('fire_risk_level', '未知'),
            'precip': v.get('precip', float('nan')),
            'temperature': v.get('temperature', float('nan')),
            'humidity': v.get('humidity', float('nan')),
            'wind_speed': v.get('wind_speed', float('nan'))
        }
        records.append(record)
    return pd.DataFrame(records)

app = dash.Dash(__name__, external_stylesheets=dashboard_theme) #
app.title = "粤港澳灾害风险仪表盘 (Guangdong Risk Dashboard)"

# --- App Layout ---
app.layout = html.Div([
    # Hidden div to store current weather/risk data as JSON for the chatbot
    dcc.Store(id='current-weather-risk-data-store'),

    html.Div([ # Main container for a more structured layout
        # Header
        html.Div(
            html.H1("粤港澳气象灾害风险分析平台 (Guangdong Meteorological Disaster Risk Analysis Platform)", 
                    style={'textAlign': 'center', 'color': '#333', 'padding': '20px 0', 'borderBottom': '2px solid #007bff'}),
            style={'marginBottom': '20px'}
        ),

        # App content: Controls on left, Map on right
        html.Div([
            # Left Control Panel
            html.Div([
                dcc.Tabs(id="disaster-tabs", value="flood", children=[
                    dcc.Tab(label="洪灾风险分析 (Flood Risk)", value="flood"),
                    dcc.Tab(label="火灾风险分析 (Fire Risk)", value="fire")
                ], style={'marginBottom': '20px'}),
                
                html.H4("数据与显示控制 (Controls)", style={'marginTop': '0px'}),
                dcc.Dropdown(
                    id='risk-time',
                    options=risk_time_options,
                    value='forecast-24h', #
                    clearable=False,
                    style={'marginBottom': '15px'}
                ),
                html.Button('更新实时数据 (Refresh Live Data)', id='refresh-btn', n_clicks=0, className='button', style={'width': '100%', 'marginBottom': '20px'}),

                # Chatbot Area
                html.Div([
                    html.H4("智能助手 (Smart Assistant)", style={'marginTop': '10px', 'marginBottom': '10px'}),
                    dcc.Loading( # Loading indicator for chat responses
                        id="loading-chat",
                        type="default",
                        children=[
                            html.Div(id='chat-history-container', children=[
                                dcc.Textarea(
                                    id='chat-history',
                                    value="助手: 您好！我可以根据当前数据显示的广东省天气和风险情况，回答您的问题。\n",
                                    readOnly=True,
                                    style={'width': '100%', 'height': '250px', 'marginBottom': '10px', 'resize': 'none'}
                                )
                            ])
                        ]
                    ),
                    dcc.Input(
                        id='chat-input', 
                        type='text', 
                        placeholder='咨询天气、风险或相关建议...', # (original was search-box)
                        style={'width': 'calc(80% - 10px)', 'marginRight': '10px', 'padding': '10px'}
                    ),
                    html.Button('发送 (Send)', id='chat-send-btn', n_clicks=0, className='button', style={'width': '20%', 'padding': '10px'})
                ], style={"marginTop": "20px", "padding": "15px", "border": "1px solid #ddd", "borderRadius": "5px", "backgroundColor": "#f9f9f9"})

            ], className="control-panel", style={"width": "30%", "display": "inline-block", "verticalAlign": "top", "padding": "20px", "boxSizing": "border-box"}), # Adjusted width
            
            # Right Map Panel
            html.Div([
                dcc.Loading( # Loading indicator for the map
                    id="loading-map",
                    type="default",
                    children=dcc.Graph(id='risk-map', style={'height': 'calc(100vh - 150px)'}) # Adjusted height
                )
            ], className="map-panel", style={"width": "68%", "display": "inline-block", "verticalAlign": "top", "padding": "20px", "boxSizing": "border-box", "marginLeft": "2%"})

        ], style={'display': 'flex', 'flexDirection': 'row'})
    ], style={'padding': '0 20px'}) # Overall page padding
])


# --- Callbacks ---

# Callback to update map and store data for chatbot
@app.callback(
    [Output('risk-map', 'figure'),
     Output('current-weather-risk-data-store', 'data')],
    [Input('disaster-tabs', 'value'),
     Input('risk-time', 'value'),
     Input('refresh-btn', 'n_clicks')]
)
def update_map_and_store_data(tab_value, risk_time_value, refresh_clicks):
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    
    weather_dict_path = GUANGDONG_WEATHER_FILE
    
    # If refresh button was clicked, update weather data
    if 'refresh-btn' in changed_id:
        print("Refresh button clicked. Updating weather data...")
        # Determine base path correctly for data_fetcher
        project_root_for_data_fetcher = os.path.join(os.path.dirname(__file__), '..')
        update_weather_json(base_path=project_root_for_data_fetcher)
        # Add a small delay to ensure file system has updated
        time.sleep(1) 
        print("Weather data update complete.")

    # 1. Load (potentially updated) weather data
    try:
        with open(weather_dict_path, 'r', encoding="utf-8") as f:
            weather_dict = json.load(f) #
    except FileNotFoundError:
        print(f"Error: {weather_dict_path} not found. Returning empty map and data.")
        fig = px.choropleth_mapbox() # Empty figure
        fig.update_layout(
            mapbox_style="carto-positron",
            mapbox_zoom=5,
            mapbox_center={"lat": 23.5, "lon": 113.3},
            title_text="数据加载失败 (Data Loading Failed)",
            height=800
        )
        return fig, {}
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {weather_dict_path}. File might be corrupted or empty.")
        fig = px.choropleth_mapbox() # Empty figure
        fig.update_layout(
            mapbox_style="carto-positron",
            mapbox_zoom=5,
            mapbox_center={"lat": 23.5, "lon": 113.3},
            title_text="气象数据错误 (Weather Data Error)",
            height=800
        )
        return fig, {}

    if not cities_meta:
        print("Error: cities_meta is empty. Cannot generate map.")
        # Return an empty map or a message
        fig = px.choropleth_mapbox() # Empty figure
        fig.update_layout(
            mapbox_style="carto-positron",
            mapbox_zoom=5,
            mapbox_center={"lat": 23.5, "lon": 113.3},
            title_text="城市元数据缺失 (City Metadata Missing)",
            height=800
        )
        return fig, {}


    # 2. Call risk assessment model
    results = estimate_region_risk(cities_meta, weather_dict, risk_time_value) #
    
    # 3. Build dataframe for the map
    df = build_dataframe(results, disaster_type=tab_value) #

    # 4. Prepare data for chatbot store
    chatbot_context_data = {
        "weather_dict": weather_dict,
        "risk_results": results,
        "risk_time_selection": risk_time_value,
        "cities_meta": cities_meta # Pass along cities_meta as well
    }

    # 5. Draw the map
    if df.empty:
        fig = px.choropleth_mapbox() # Empty figure
        fig.update_layout(
            mapbox_style="carto-positron",
            mapbox_zoom=5,
            mapbox_center={"lat": 23.5, "lon": 113.3},
            title_text="无数据显示 (No Data to Display)",
            height=800
        )
        return fig, chatbot_context_data


    map_color_col = 'flood_risk_level' if tab_value == 'flood' else 'fire_risk_level'
    map_score_col = 'flood_score' if tab_value == 'flood' else 'fire_score'
    map_title = "广东省洪涝灾害风险等级分布 ({})" if tab_value == "flood" else "广东省森林火险气象等级分布 ({})"
    
    # Add risk time label to title
    selected_time_label = next((opt['label'] for opt in risk_time_options if opt['value'] == risk_time_value), risk_time_value)
    map_title = map_title.format(selected_time_label)


    fig = px.choropleth_mapbox(
        df, geojson=geojson, locations='city', featureidkey="properties.地级", #
        color=map_color_col,
        mapbox_style="carto-positron", # Using a different mapbox style for potentially better visuals
        hover_name='city',
        hover_data={
            # "城市": df['city'], # Already in hover_name
            "风险等级": df[map_color_col],
            "风险指数": df[map_score_col].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "N/A"),
            "降水(mm)": df['precip'].apply(lambda x: f"{x:.1f}" if pd.notnull(x) else "N/A"),
            "温度(°C)": df['temperature'].apply(lambda x: f"{x:.1f}" if pd.notnull(x) else "N/A"),
            "湿度(%)": df['humidity'].apply(lambda x: f"{x:.0f}" if pd.notnull(x) else "N/A"),
            "风速(m/s)": df['wind_speed'].apply(lambda x: f"{x:.1f}" if pd.notnull(x) else "N/A"),
            # We need to remove columns not present for hover_data to work if they were direct df columns
            'city': False # Don't show the city column again if it's the hover_name
        },
        color_discrete_map={ #
            "极低风险": "#5abaff",
            "低风险": "#56bb6c",
            "中风险": "#efcb67",
            "高风险": "#ec5736",
            "极高风险": "#ad1457",
            "未知": "#cccccc" # Added a color for unknown status
        },
        category_orders={ # Ensure consistent ordering of risk levels in legend
            map_color_col: ["极低风险", "低风险", "中风险", "高风险", "极高风险", "未知"]
        },
        zoom=6, #
        center={"lat": 23.5, "lon": 113.3}, #
        opacity=0.7, #
        # height parameter removed to allow CSS or style prop to control it
        labels={map_color_col: '风险等级 (Risk Level)'}, #
        title=map_title
    )
    fig.update_traces(marker_line_width=0.5, marker_line_color='white') # (changed line color and width)
    fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, title_x=0.5)
    
    return fig, chatbot_context_data


# Callback for Chatbot
@app.callback(
    Output('chat-history', 'value'),
    Output('chat-input', 'value'), # Clear input after sending
    Input('chat-send-btn', 'n_clicks'),
    State('chat-input', 'value'),
    State('chat-history', 'value'),
    State('current-weather-risk-data-store', 'data') # Get context from the store
)
def update_chat(send_clicks, user_input, chat_history_val, stored_data):
    if send_clicks > 0 and user_input:
        if not stored_data:
            bot_response = "抱歉，系统当前的气象和风险数据尚未加载，请稍后再试或点击刷新数据。(Sorry, current weather/risk data is not loaded yet.)"
        else:
            weather_dict = stored_data.get("weather_dict")
            cities_meta_from_store = stored_data.get("cities_meta") # Make sure this is passed
            risk_results = stored_data.get("risk_results")
            risk_time_selection = stored_data.get("risk_time_selection")

            # Prepare context for the chatbot
            weather_context_for_ai = get_weather_context_for_chatbot(
                weather_dict, cities_meta_from_store, risk_results, risk_time_selection
            )
            
            # Get response from chatbot service
            bot_response = get_chatbot_response(user_input, weather_context_for_ai)

        # Append user message and bot response to chat history
        new_chat_history = chat_history_val + f"您 (You): {user_input}\n助手 (Assistant): {bot_response}\n\n"
        return new_chat_history, "" # Clear input box
    return dash.no_update, dash.no_update # No change if no input or button not clicked

if __name__ == "__main__":
    # Create dummy data files if they don't exist, to allow the app to start for the first time
    # This is more for local development convenience.
    # In production, these files should be reliably generated by preprocess_static_data.py and data_fetcher.py.
    
    # Check and create dummy guangdong_cities_meta.json if not exists
    if not os.path.exists(GUANGDONG_CITIES_META_FILE):
        print(f"'{GUANGDONG_CITIES_META_FILE}' not found. Creating a dummy file. Please run 'preprocess_static_data.py' for actual data.")
        os.makedirs(os.path.dirname(GUANGDONG_CITIES_META_FILE), exist_ok=True)
        with open(GUANGDONG_CITIES_META_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f) # Empty list of cities

    # Check and create dummy guangdong_border.geojson if not exists
    if not os.path.exists(GUANGDONG_GEOJSON_FILE):
        print(f"'{GUANGDONG_GEOJSON_FILE}' not found. Creating a dummy file. Please run 'preprocess_static_data.py' for actual data.")
        os.makedirs(os.path.dirname(GUANGDONG_GEOJSON_FILE), exist_ok=True)
        with open(GUANGDONG_GEOJSON_FILE, 'w', encoding='utf-8') as f:
            json.dump({"type": "FeatureCollection", "features": []}, f)

    # Check and create dummy guangdong_weather.json if not exists
    # The update_map callback will attempt to call update_weather_json if it's missing or empty.
    if not os.path.exists(GUANGDONG_WEATHER_FILE):
         print(f"'{GUANGDONG_WEATHER_FILE}' not found. It will be generated on first data refresh or app start if possible.")
         # Creating an empty JSON structure to prevent load errors before first actual fetch
         os.makedirs(os.path.dirname(GUANGDONG_WEATHER_FILE), exist_ok=True)
         with open(GUANGDONG_WEATHER_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)


    app.run(debug=True, host='127.0.0.1', port=8050)    
import requests
from datetime import datetime, timedelta, timezone
import json
import os # Added for path joining

# ========== 配置 ==========


API_KEY = os.getenv("API_KEY") 
WEATHER_BASE_URL = "http://api.openweathermap.org/data/2.5/weather"
FORECAST_BASE_URL = "http://api.openweathermap.org/data/2.5/forecast"  # 未来预报接口
LANG = "zh_cn"


# ========== 气象数据获取 ==========

def get_weather_by_latlon(lat, lon):
    if not API_KEY:
        print("Error: OpenWeatherMap API_KEY is not set.")
        return None
    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY,
        "units": "metric",
        "lang": LANG
    }
    try:
        resp = requests.get(WEATHER_BASE_URL, params=params, timeout=10)
        resp.raise_for_status() # Raises an HTTPError for bad responses (4XX or 5XX)
        d = resp.json()
        return {
            "temperature": d["main"]["temp"],
            "humidity": d["main"]["humidity"],
            "wind_speed": d["wind"]["speed"],
            "wind_direction": d["wind"].get("deg", None),
            "precipitation": d.get("rain", {}).get("1h", 0.0) #
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching current weather for lat={lat}, lon={lon}: {e}")
        return None
    except KeyError as e:
        print(f"KeyError parsing current weather data for lat={lat}, lon={lon}: {e}")
        return None


def get_forecast_by_latlon(lat, lon, hours=[3, 6, 12, 24, 48, 72]):
    if not API_KEY:
        print("Error: OpenWeatherMap API_KEY is not set.")
        return {}
    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY,
        "units": "metric",
        "lang": LANG
    }
    forecasts = {}
    try:
        resp = requests.get(FORECAST_BASE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if "list" not in data: return forecasts
        for hour in hours:
            # The API provides forecasts in 3-hour intervals.
            # We need to find the forecast entry closest to the desired hour.
            # dt is unix timestamp. dt_txt is string.
            # For simplicity, we'll use the index, assuming the first few entries cover our needs.
            # idx = (hour // 3) -1 if hour % 3 == 0 and hour > 0 else hour // 3
            # OpenWeatherMap's free forecast provides 3-hour steps.
            # So 3h is index 0 (or 1 if current time is past the first interval), 6h is index 1 or 2 etc.
            # The original code used `idx = hour // 3`. Let's refine this to pick the correct forecast.
            # The API returns a list of 3-hour forecasts. `data['list'][0]` is the next 3-hour forecast.
            # `data['list'][1]` is the one after that (6 hours from start of list).
            
            target_timestamp = datetime.now(timezone.utc) + timedelta(hours=hour)
            
            closest_forecast = None
            min_time_diff = float('inf')

            for fc_item in data["list"]:
                fc_time = datetime.fromtimestamp(fc_item["dt"], timezone.utc)
                time_diff = abs((fc_time - target_timestamp).total_seconds())
                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    closest_forecast = fc_item
            
            if closest_forecast:
                fc = closest_forecast
                dt_bj = utc_str_to_bj_time(fc["dt_txt"]) #
                forecasts[f"{hour}h"] = {
                    "datetime": dt_bj,
                    "temperature": fc["main"]["temp"],
                    "humidity": fc["main"]["humidity"],
                    "wind_speed": fc["wind"]["speed"],
                    "wind_direction": fc["wind"].get("deg", None),
                    "precipitation": fc.get("rain", {}).get("3h", 0.0) #
                }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching forecast for lat={lat}, lon={lon}: {e}")
    except KeyError as e:
        print(f"KeyError parsing forecast data for lat={lat}, lon={lon}: {e}")
    return forecasts


# ========== 时区转换 ==========
def utc_str_to_bj_time(utc_str, fmt="%Y-%m-%d %H:%M:%S"):
    """UTC字符串转北京时间字符串"""
    try:
        utc_dt = datetime.strptime(utc_str, fmt).replace(tzinfo=timezone.utc)
        bj_dt = utc_dt.astimezone(timezone(timedelta(hours=8))) #
        return bj_dt.strftime(fmt)
    except ValueError:
        print(f"Error converting UTC string {utc_str} to Beijing time.")
        return utc_str


# ========== 更新天气数据 ==========
def update_weather_json(base_path=".."): # Added base_path for flexibility
    meta_file_path = os.path.join(base_path, "data", "admin_unit", "guangdong_cities_meta.json")
    output_file_path = os.path.join(base_path, "data", "guangdong_weather.json")
    
    # Ensure data directory exists
    os.makedirs(os.path.join(base_path, "data"), exist_ok=True)

    if not os.path.exists(meta_file_path):
        print(f"Error: City metadata file not found at {meta_file_path}")
        # Create a dummy file or return an empty dict to prevent crash if it's missing
        # and the app needs to run for the first time.
        # For a real scenario, ensure preprocess_static_data.py has run.
        placeholder_data = {}
        with open(output_file_path, 'w', encoding="utf-8") as f1:
            json.dump(placeholder_data, f1, ensure_ascii=False, indent=2)
        return placeholder_data


    with open(meta_file_path, encoding="utf-8") as f:
        cities_meta = json.load(f)

    all_weather = {}
    if not API_KEY:
        print("Critical Error: OpenWeatherMap API_KEY not set in data_fetcher.py. Cannot fetch weather.")
        # Save empty data to avoid crashing app that reads this file
        with open(output_file_path, 'w', encoding="utf-8") as f1:
            json.dump(all_weather, f1, ensure_ascii=False, indent=2)
        return all_weather

    for city in cities_meta:
        city_name = city['city_name']
        # city_code = city['adcode'] # Not used in API calls here
        lat = city['lat']
        lon = city['lon']
        print(f"[+] Fetching weather for {city_name} ... (lat={lat:.3f}, lon={lon:.3f})")
        now_weather = get_weather_by_latlon(lat, lon)
        forecast = get_forecast_by_latlon(lat, lon) # Uses default hours
        
        # Ensure now_weather is not None before trying to access it
        current_weather_data = now_weather if now_weather else {}
        
        all_weather[city_name] = {
            'adcode': city.get('adcode'), # Use .get for safety
            'lon': lon,
            'lat': lat,
            'weather': {
                'now': current_weather_data,
                'forecast': forecast
            }
        }
    with open(output_file_path, 'w', encoding="utf-8") as f1:
        json.dump(all_weather, f1, ensure_ascii=False, indent=2)
    print(f"\n[*] Guangdong city weather data collection complete, saved to {output_file_path}")

    return all_weather

if __name__ == "__main__":
    # Determine the base path relative to the current script location
    # This allows running the script directly from its directory
    current_script_path = os.path.dirname(os.path.abspath(__file__))
    project_base_path = os.path.join(current_script_path, "..") # Assumes this script is in a 'scripts' or similar subdir
    
    # If you are running this from the project root, base_path should be "."
    # For this example, assuming it's in a subdirectory like the original structure.
    # Example: if data_fetcher.py is in /project_root/scripts/data_fetcher.py
    # then project_base_path will be /project_root/
    
    # Make sure to run preprocess_static_data.py first to generate guangdong_cities_meta.json
    print("Attempting to update weather JSON data...")
    print(f"Looking for city metadata relative to: {project_base_path}")
    update_weather_json(base_path=project_base_path)
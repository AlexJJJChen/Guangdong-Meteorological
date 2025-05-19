from data_fetcher import update_weather_json

import numpy as np
import rasterio
from rasterio.mask import mask
import geopandas as gpd
import json


# --------- 洪水风险相关参数 ---------
ALPHA = 1.0    # 降水量权重（标准建议：1.0-1.5）
BETA = 1.2     # 低地指数权重（建议：1.0-2.0）
GAMMA = 1.5    # 不透水面权重（建议：1.0-2.0）

# 风险阈值
FIRE_RISK_THRESHOLDS = {
    "very_low": 0.0,
    "low": 1.5,
    "medium": 2.5,
    "high": 3.5
}

FLOOD_RISK_THRESHOLDS = {
    "very_low": 1.0,
    "low": 2.0,
    "medium": 3.0,
    "high": 4.5
}

# ========== 火灾风险算法 ==========
def calc_fire_index(temp, humidity, wind_factor, weight):
    """Angström修改公式"""
    score = (temp / 20.0) - (humidity / 10.0) + wind_factor
    return score * weight

def classify_fire_risk(score):
    if score <= FIRE_RISK_THRESHOLDS["very_low"]:
        return "极低风险"
    elif score <= FIRE_RISK_THRESHOLDS["low"]:
        return "低风险"
    elif score <= FIRE_RISK_THRESHOLDS["medium"]:
        return "中风险"
    elif score <= FIRE_RISK_THRESHOLDS["high"]:
        return "高风险"
    else:
        return "极高风险"


# ========== 洪水风险算法 ==========

def calc_flood_index(precip, lowland_index, impervious_frac):
    """precip:mm, lowland_index:0-1, impervious_frac:0-1"""
    return ALPHA*precip + BETA*lowland_index + GAMMA*impervious_frac

def classify_flood_risk(score):
    if score <= FLOOD_RISK_THRESHOLDS["very_low"]:
        return "极低风险"
    elif score <= FLOOD_RISK_THRESHOLDS["low"]:
        return "低风险"
    elif score <= FLOOD_RISK_THRESHOLDS["medium"]:
        return "中风险"
    elif score <= FLOOD_RISK_THRESHOLDS["high"]:
        return "高风险"
    else:
        return "极高风险"


# ========== 汇总数据进行估计 ==========

def estimate_region_risk(cities_meta, weather_dict, weather_time='now'):
    """
    输入所有城市元信息(cities_meta)和weather_dict
    返回每个城市的洪水风险结果
    weather_time:
    - 'now'         取当前天气
    - 'forecast-3h' 取3小时预报
    - 'forecast-6h' 取6小时预报
    依次类推...
    """
    results = {}
    for city_info in cities_meta:
        city_name = city_info["city_name"]
        city_weather = weather_dict.get(city_name, {})
        weather_data = None

        # 选择天气数据
        if weather_time == 'now':
            weather_data = (
                city_weather.get('weather', {}).get('now', None)
            )
        elif weather_time.startswith('forecast-'):
            forecast_hr = weather_time.split('-')[1]  # 提取'3h'、'6h'这类
            weather_data = (
                city_weather
                .get('weather', {})
                .get('forecast', {})
                .get(forecast_hr, None)
            )
        else:
            print(f"Unknown weather_time: {weather_time}")
            weather_data = None

        if weather_data is None:
            print(f"Warning: Weather data missing for {city_name} at {weather_time}.")
            continue

        precip = weather_data.get('precipitation', 0.0)
        temp = weather_data.get('temperature', 0.0)
        humidity = weather_data.get('humidity', 0.0)
        wind_speed = weather_data.get('wind_speed', 0.0)

        lowland_index = city_info["lowland_index"]
        impervious_frac = city_info["impervious_frac"]
        fire_weight = city_info.get("fire_risk_weight", 1.0)

        flood_score = calc_flood_index(precip, lowland_index, impervious_frac)
        flood_risk_class = classify_flood_risk(flood_score)

        fire_score = calc_fire_index(temp, humidity, wind_speed, fire_weight)
        fire_risk_class = classify_fire_risk(fire_score)

        results[city_name] = {
            "flood_score": flood_score,
            "flood_risk_level": flood_risk_class,
            "fire_score": fire_score,
            "fire_risk_level": fire_risk_class,

            "precip": precip,
            "lowland_index": lowland_index,
            "impervious_frac": impervious_frac,
            "temperature": temp,
            "humidity": humidity,
            "wind_speed": wind_speed,
            "fire_weight": fire_weight
        }
    return results


if __name__ == "__main__":

    with open("../data/admin_unit/guangdong_cities_meta.json", encoding="utf-8") as f:
        cities_meta = json.load(f)

    with open("../data/guangdong_weather.json", encoding="utf-8") as f:
        weather_dict = json.load(f)

    # weather_dict = update_weather_json()

    results = estimate_region_risk(cities_meta, weather_dict, 'forecast-24h')

    print(results)



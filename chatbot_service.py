import openai
from openai import OpenAI
import json

# IMPORTANT: Set your OpenAI API key as an environment variable
# or replace "YOUR_OPENAI_API_KEY" with your actual key.
# Consider using environment variables for better security.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 
if OPENAI_API_KEY == "YOUR_OPENAI_API_KEY" or not OPENAI_API_KEY:
    print("Warning: OpenAI API key is not configured in chatbot_service.py. Chatbot will not function.")
    # You might want to raise an error or handle this more gracefully
else:
    openai.api_key = OPENAI_API_KEY

def get_weather_context_for_chatbot(weather_dict, cities_meta, risk_results, risk_time_selection):
    """
    Prepares a concise weather and risk context for the chatbot,
    using weather data directly tied to the risk assessment.
    """
    context_lines = [f"Current data selection is for: {risk_time_selection}."]
    if not risk_results: # weather_dict might still be useful for general questions, but risk_results is key here
        return "Risk assessment data is not available at the moment."

    # Provide a general overview or pick a few example cities
    # For simplicity, let's pick the first few cities or a prominent one like Guangzhou
    
    # Use cities present in risk_results for summary
    cities_to_summarize = list(risk_results.keys())[:2] 
    if "广州市" in risk_results and "广州市" not in cities_to_summarize:
        # Ensure Guangzhou is included if available and not already in the short list
        if len(cities_to_summarize) < 2 :
             cities_to_summarize.append("广州市")
        elif len(cities_to_summarize) == 2 and "广州市" not in cities_to_summarize : # replace if not already there
            if cities_to_summarize[0] != "广州市": # avoid duplicate if it was the first one
                 cities_to_summarize[1] = "广州市" # replace second element
            # if Guangzhou was already the first, no change needed here.


    for city_name in cities_to_summarize:
        if city_name in risk_results:
            city_risk_info = risk_results[city_name]

            # The weather data used for risk calculation is directly in city_risk_info
            # as per risk_model.py
            temp = city_risk_info.get('temperature', 'N/A')
            precip = city_risk_info.get('precip', 'N/A') # This is the precipitation used in the risk calculation
            humidity = city_risk_info.get('humidity', 'N/A')
            wind_speed = city_risk_info.get('wind_speed', 'N/A')
            
            # The label for precipitation depends on whether it's current (1h) or forecast (3h)
            # This information is implicitly handled by data_fetcher.py when populating 'precipitation' field for risk_model.py
            precip_label = "Precipitation" # Generic label, as risk_time_selection gives overall time context

            context_lines.append(
                f"\nCity: {city_name}\n"
                f"  Flood Risk: {city_risk_info.get('flood_risk_level')} (Score: {city_risk_info.get('flood_score', 0):.2f})\n"
                f"  Fire Risk: {city_risk_info.get('fire_risk_level')} (Score: {city_risk_info.get('fire_score', 0):.2f})\n"
                f"  Weather conditions used for this assessment:\n"
                f"    Temperature: {temp}°C\n"
                f"    {precip_label}: {precip}mm\n"
                f"    Humidity: {humidity}%\n"
                f"    Wind Speed: {wind_speed}m/s"
            )
    
    if not cities_to_summarize and risk_results:
        context_lines.append("\nNo specific city data to summarize, but risk assessment data for the region is loaded.")
    elif not risk_results: # Should have been caught earlier, but as a safeguard
        context_lines = ["Risk assessment data is not available at the moment."]


    return "\n".join(context_lines)


def get_chatbot_response(user_query, weather_context):
    if not openai.api_key or openai.api_key == "YOUR_OPENAI_API_KEY": # Check if API key is placeholder
        return "OpenAI API key not configured. Cannot connect to the assistant."

    try:
        system_prompt = (
            "You are a helpful assistant for a disaster risk dashboard focused on Guangdong province, China. "
            "You are provided with the current weather and risk assessment context for selected cities. "
            "This context includes risk levels, scores, and the specific weather data (temperature, precipitation, humidity, wind speed) that contributed to those assessments for the selected time period. "
            "Use this information to answer user questions about weather, flood risks, and fire risks in the region. "
            "If the user asks about a specific city in Guangdong not detailed in the immediate context, "
            "acknowledge that you have general data for Guangdong (if true based on overall context) and try to provide a relevant answer based on the overall situation or typical patterns. "
            "If the query is outside your scope of weather/risk in Guangdong, politely state your limitations. "
            "Be concise and helpful. The available weather data is from OpenWeatherMap."
            "Refer to precipitation as 'relevant period precipitation' if unsure if it's 1h or 3h, but the user knows the forecast period from 'risk_time_selection'."
        )
        # Using the provided API key and base URL
        api_key = OPENAI_API_KEY # Ensured it's not the placeholder
        api_base = "https://api.openai-next.com/v1"
        client = OpenAI(api_key=api_key, base_url=api_base)

        completion = client.chat.completions.create(
            model="gpt-4.1-2025-04-14", # User-specified model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Current Context for Guangdong Province (selected cities shown):\n{weather_context}\n\nUser Question: {user_query}"}
            ],
            temperature=0.7,
            max_tokens=250 # Increased slightly for potentially more detailed answers
        )
        return completion.choices[0].message.content
    except openai.APIError as e:
        print(f"OpenAI API Error: {e}")
        return f"Sorry, I encountered an error trying to connect to the assistant: {e}"
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return "Sorry, an unexpected error occurred while processing your request."

if __name__ == '__main__':
    # This is for testing the chatbot service directly
    sample_weather_dict = { # Still useful for broader context if chatbot needs it, though not primary for risk explanation
        "广州市": {
            "weather": {
                "now": {"temperature": 30, "precipitation": 0, "humidity": 70, "wind_speed": 3, "description": "clear sky"},
                "forecast": {"3h": {"temperature": 31, "precipitation": 0.5, "humidity": 68, "wind_speed": 3.2, "description": "light rain"}}
            }
        },
        "深圳市": {
             "weather": {
                "now": {"temperature": 29, "precipitation": 0.1, "humidity": 75, "wind_speed": 2.5, "description": "few clouds"},
                "forecast": {"3h": {"temperature": 30, "precipitation": 0.0, "humidity": 72, "wind_speed": 2.8, "description": "scattered clouds"}}
            }
        }
    }
    sample_cities_meta = [ # Not directly used in the modified context string but passed to the function
        {"city_name": "广州市", "lat": 23.1291, "lon": 113.2644},
        {"city_name": "深圳市", "lat": 22.5431, "lon": 114.0579}
    ]
    sample_risk_results = { # This is the key input now for weather details in context
        "广州市": {
            "flood_score": 2.5, "flood_risk_level": "中风险",
            "fire_score": 1.8, "fire_risk_level": "低风险",
            "precip": 0.5, "temperature": 31, "humidity": 68, "wind_speed": 3.2 # Weather data used for this forecast
        },
         "深圳市": {
            "flood_score": 1.5, "flood_risk_level": "低风险",
            "fire_score": 2.1, "fire_risk_level": "中风险",
            "precip": 0.0, "temperature": 30, "humidity": 72, "wind_speed": 2.8
        }
    }
    sample_risk_time = "forecast-3h"

    test_context = get_weather_context_for_chatbot(sample_weather_dict, sample_cities_meta, sample_risk_results, sample_risk_time)
    print("---- Context for Chatbot ----")
    print(test_context)
    print("\n---- Chatbot Test Response ----")
    if OPENAI_API_KEY != "YOUR_OPENAI_API_KEY" and OPENAI_API_KEY: # Check again for safety
        test_query = "What is the flood risk in Guangzhou and why? What's the temperature there?"
        response = get_chatbot_response(test_query, test_context)
        print(f"Q: {test_query}\nA: {response}")

        test_query_2 = "Tell me about Shenzhen's fire risk and the wind speed."
        response_2 = get_chatbot_response(test_query_2, test_context)
        print(f"\nQ: {test_query_2}\nA: {response_2}")
    else:
        print("Skipping chatbot response test as API key is not set or is the placeholder.")
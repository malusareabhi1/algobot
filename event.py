import streamlit as st
import requests
from datetime import datetime
from typing import List

# Set your OpenWeatherMap API key here
OPENWEATHER_API_KEY = "your_api_key_here"

# Local in-memory event storage
events_db = []

# ---------- Scoring Logic ----------
def score_weather(temp: float, wind: float, rain: float, condition: str, event_type: str) -> str:
    score = 0
    if event_type.lower() == "cricket":
        if 15 <= temp <= 30: score += 30
        if rain < 20: score += 25
        if wind < 20: score += 20
        if condition in ['Clear', 'Clouds']: score += 25
    elif event_type.lower() == "wedding":
        if 18 <= temp <= 28: score += 30
        if rain < 10: score += 30
        if wind < 15: score += 25
        if condition in ['Clear', 'Clouds']: score += 15

    if score >= 90:
        return "✅ Good"
    elif score >= 65:
        return "🟡 Okay"
    else:
        return "❌ Poor"

# ---------- Weather API ----------
def fetch_weather_forecast(location: str):
    try:
        url = f"http://api.openweathermap.org/data/2.5/forecast?q={location}&appid={OPENWEATHER_API_KEY}&units=metric"
        res = requests.get(url)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        st.error(f"Weather API error: {str(e)}")
        return None

def get_weather_for_date(weather_data, event_date: str):
    target_date = datetime.strptime(event_date, "%Y-%m-%d")
    for forecast in weather_data.get("list", []):
        forecast_time = datetime.fromtimestamp(forecast["dt"])
        if forecast_time.date() == target_date.date():
            return forecast
    return None

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Smart Event Planner", layout="centered")
st.title("📅 Smart Event Planner")
st.write("Plan your outdoor events with weather intelligence powered by OpenWeatherMap.")

with st.form("event_form"):
    st.subheader("➕ Create a New Event")
    name = st.text_input("Event Name")
    location = st.text_input("Event Location (City)", value="Mumbai")
    date = st.date_input("Event Date", value=datetime.today())
    event_type = st.selectbox("Event Type", ["Cricket", "Wedding", "Hiking", "Team Outing"])

    submitted = st.form_submit_button("Create Event")

    if submitted:
        event_id = len(events_db) + 1
        new_event = {
            "id": event_id,
            "name": name,
            "location": location,
            "date": date.strftime("%Y-%m-%d"),
            "event_type": event_type,
            "weather": None,
            "suitability": None
        }
        events_db.append(new_event)
        st.success(f"✅ Event '{name}' created successfully!")

# ---------- List Events ----------
st.subheader("📋 Events List")

if not events_db:
    st.info("No events created yet.")
else:
    for event in events_db:
        with st.expander(f"{event['name']} ({event['event_type']}) on {event['date']} in {event['location']}"):
            st.write(f"**Event ID:** {event['id']}")
            st.write(f"**Location:** {event['location']}")
            st.write(f"**Date:** {event['date']}")
            st.write(f"**Event Type:** {event['event_type']}")

            if st.button(f"Check Weather for Event ID {event['id']}", key=f"weather_btn_{event['id']}"):
                weather_data = fetch_weather_forecast(event["location"])
                if weather_data:
                    forecast = get_weather_for_date(weather_data, event["date"])
                    if forecast:
                        temp = forecast["main"]["temp"]
                        wind = forecast["wind"]["speed"]
                        rain = forecast.get("rain", {}).get("3h", 0.0)
                        condition = forecast["weather"][0]["main"]

                        suitability = score_weather(temp, wind, rain, condition, event["event_type"])

                        event["weather"] = {
                            "temperature": temp,
                            "wind": wind,
                            "rain": rain,
                            "condition": condition
                        }
                        event["suitability"] = suitability

                        st.success(f"Weather on {event['date']}:")
                        st.write(f"🌡️ Temp: {temp}°C | 🌬️ Wind: {wind} km/h | 🌧️ Rain: {rain} mm | ⛅ Condition: {condition}")
                        st.write(f"🧠 Suitability Score: **{suitability}**")
                    else:
                        st.warning("⚠️ No forecast available for this date.")
                else:
                    st.error("❌ Failed to fetch weather.")


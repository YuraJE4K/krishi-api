import requests
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# ------------------ CROP LOGIC ------------------ #
STATIC_PATH = os.path.join(BASE_DIR, "database")  # for images
PRICE_PATH = os.path.join(BASE_DIR, "database/json/prices.json")
DETAILS_PATH = os.path.join(BASE_DIR, "database/json/details.json")
SCHEME_PATH = os.path.join(BASE_DIR, "database/json/schemes.json")
USER_PATH = os.path.join(BASE_DIR, "database/json/user.json")
USER_HISTORY_PATH = os.path.join(BASE_DIR, "database/json/user_history.json")
crops = {
    "wheat": {
        "temp": (10, 25),
        "moisture": (40, 60),
        "weather": ["cool", "dry", "sunny"],
    },
    "onion": {
        "temp": (13, 24),
        "moisture": (45, 60),
        "weather": ["mild", "dry", "clear"],
    },
    "orange": {
        "temp": (13, 37),
        "moisture": (50, 70),
        "weather": ["warm", "dry", "sunny"],
    },
    "soybean": {
        "temp": (15, 32),
        "moisture": (60, 75),
        "weather": ["humid", "warm", "cloudy"],
    },
    "grapes": {
        "temp": (15, 35),
        "moisture": (30, 50),
        "weather": ["dry", "hot", "sunny"],
    },
    "sitaphal": {
        "temp": (15, 30),
        "moisture": (35, 50),
        "weather": ["dry", "warm", "hot"],
    },
    "gram": {
        "temp": (15, 25),
        "moisture": (35, 55),
        "weather": ["cool", "dry", "mild"],
    },
    "maize": {
        "temp": (18, 27),
        "moisture": (55, 75),
        "weather": ["humid", "warm", "sunny"],
    },
    "sugarcane": {
        "temp": (20, 35),
        "moisture": (70, 85),
        "weather": ["humid", "dry", "warm"],
    },
    "banana": {
        "temp": (20, 30),
        "moisture": (75, 85),
        "weather": ["humid", "warm", "tropical"],
    },
    "tur": {
        "temp": (20, 30),
        "moisture": (40, 55),
        "weather": ["dry", "warm", "sunny"],
    },
    "turmeric": {
        "temp": (20, 30),
        "moisture": (70, 90),
        "weather": ["humid", "warm", "wet"],
    },
    "cashew": {
        "temp": (20, 30),
        "moisture": (40, 60),
        "weather": ["warm", "humid", "dry"],
    },
    "mosambi": {
        "temp": (20, 35),
        "moisture": (50, 70),
        "weather": ["dry", "sunny", "warm"],
    },
    "cotton": {
        "temp": (21, 30),
        "moisture": (50, 70),
        "weather": ["dry", "sunny", "warm"],
    },
    "rice": {
        "temp": (21, 37),
        "moisture": (80, 90),
        "weather": ["hot", "humid", "wet"],
    },
    "mango": {
        "temp": (24, 30),
        "moisture": (50, 65),
        "weather": ["warm", "dry", "humid"],
    },
    "pomegranate": {
        "temp": (25, 35),
        "moisture": (30, 50),
        "weather": ["hot", "dry", "arid"],
    },
    "bajra": {
        "temp": (25, 35),
        "moisture": (40, 50),
        "weather": ["dry", "hot", "sunny"],
    },
    "jowar": {
        "temp": (26, 33),
        "moisture": (40, 60),
        "weather": ["warm", "dry", "arid"],
    },
}

from datetime import datetime
import json


def load_history():
    if not os.path.exists(USER_HISTORY_PATH):
        return {}
    with open(USER_HISTORY_PATH) as f:
        return json.load(f)


def save_history(data):
    with open(USER_HISTORY_PATH, "w") as f:
        json.dump(data, f, indent=2)


def add_history(user_id, action_type, query, path):
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except:
        data = []

    user = next((u for u in data if u["user_id"] == user_id), None)

    if not user:
        user = {"user_id": user_id, "history": []}
        data.append(user)

    user["history"].append(
        {"type": action_type, "query": query, "timestamp": datetime.now().isoformat()}
    )

    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def map_weather(user_weather, humidity, temp):
    tags = []

    if "rain" in user_weather:
        tags += ["wet", "humid"]
    elif "cloud" in user_weather:
        tags += ["cloudy"]
    else:
        tags += ["sunny", "dry"]

    if temp > 30:
        tags.append("hot")
    elif temp < 20:
        tags.append("cool")
    else:
        tags.append("warm")

    if humidity > 70:
        tags.append("humid")
    elif humidity < 40:
        tags.append("dry")

    return tags


def recommend_crop(temp, moisture, weather):
    tags = map_weather(weather, moisture, temp)
    result = []

    for crop, data in crops.items():
        score = 0

        if data["temp"][0] <= temp <= data["temp"][1]:
            score += 2

        if data["moisture"][0] <= moisture <= data["moisture"][1]:
            score += 2

        score += len(set(tags) & set(data["weather"]))

        if score >= 3:
            result.append((crop, score))

    result.sort(key=lambda x: x[1], reverse=True)

    return result[:3]  # top 3


# ------------------ WEATHER API ------------------ #

WEATHER_API = "80b939cfa272396308802b1e2b11cd34"


def get_weather(city):
    url = "https://api.openweathermap.org/data/2.5/weather"

    params = {"q": city, "appid": WEATHER_API, "units": "metric"}

    res = requests.get(url, params=params)
    data = res.json()

    if data.get("cod") != 200:
        return {"error": "City not found"}

    return {
        "temp": data["main"]["temp"],
        "humidity": data["main"]["humidity"],
        "weather": data["weather"][0]["main"],
    }


# ------------------ MARKET PRICE API ------------------ #

PRICE_API = "579b464db66ec23bdd000001bc43ceb877b64c1b63adf4a89bab8f4f"
RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"


def get_prices(commodity, state):
    url = f"https://api.data.gov.in/resource/{RESOURCE_ID}"

    params = {
        "api-key": PRICE_API,
        "format": "json",
        "filters[commodity]": commodity,
        "filters[state]": state.title(),
        "limit": 10,
    }

    res = requests.get(url, params=params)
    data = res.json()

    records = data.get("records", [])

    if not records:
        return {"error": "No data found"}

    result = []

    for item in records:
        result.append({"market": item["market"], "price": item["modal_price"]})

    return result


def get_forecast(city, days):
    url = "https://api.openweathermap.org/data/2.5/forecast"

    params = {"q": city, "appid": WEATHER_API, "units": "metric"}

    res = requests.get(url, params=params)
    data = res.json()

    if data.get("cod") != "200":
        return {"error": "City not found"}

    index = days * 8  # 8 data points per day (3-hour intervals)

    forecast = data["list"][index]

    return {
        "temp": forecast["main"]["temp"],
        "humidity": forecast["main"]["humidity"],
        "weather": forecast["weather"][0]["main"],
    }

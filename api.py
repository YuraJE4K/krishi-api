from flask import request, jsonify
from helper import (
    recommend_crop,
    get_weather,
    get_prices,
    get_forecast,
    load_history,
    save_history,
)
import json
import os
import requests
import datetime
from flask_cors import CORS

API_KEY = os.environ.get("API_KEY")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={API_KEY}"

# ✅ chat sessions
chat_sessions = {}


def register_routes(app):

    CORS(app)  # 🔥 allow WordPress requests

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    PRICE_PATH = os.path.join(BASE_DIR, "database/json/prices.json")
    DETAILS_PATH = os.path.join(BASE_DIR, "database/json/details.json")
    SCHEME_PATH = os.path.join(BASE_DIR, "database/json/schemes.json")

    def load_json(path):
        with open(path) as f:
            return json.load(f)

    # ---------------- CROP REPORT ---------------- #
    @app.route("/crop-report", methods=["POST"])
    def crop_report():
        try:
            data = request.get_json()

            city = data.get("city")
            crop = data.get("crop")

            if not city or not crop:
                return jsonify({"error": "City and crop required"})

            # 🌤 Weather
            weather_data = get_weather(city)

            if "error" in weather_data:
                return jsonify({"error": weather_data["error"]})

            temp = weather_data.get("temp", 0)
            humidity = weather_data.get("humidity", 0)
            weather = weather_data.get("weather", "clear")

            # 🌾 Crop recommendations
            recommendations = recommend_crop(temp, humidity, weather)

            # 💰 Market prices (simple version)
            try:
                market = get_prices(crop, "maharashtra")  # fixed state
            except:
                market = []

            # 🧠 Simple AI advice (no Gemini needed)
            advice = []

            if temp > 35:
                advice.append("High temperature detected — ensure proper irrigation")
            if humidity < 30:
                advice.append("Low humidity — risk of dry soil, increase watering")
            if humidity > 80:
                advice.append("High humidity — risk of fungal diseases")

            if crop.lower() in [r[0] for r in recommendations]:
                advice.append(f"{crop} is suitable for current conditions")
            else:
                advice.append(f"{crop} may not be optimal in current weather")

            return jsonify({
                "weather": weather_data,
                "recommendations": recommendations,
                "market": market,
                "advice": advice
            })

        except Exception as e:
            print("CROP REPORT ERROR:", e)
            return jsonify({"error": "Server error"})
        
    # ---------------- WEATHER ---------------- #
    @app.route("/weather", methods=["GET"])
    def weather():
        city = request.args.get("city")
        user_id = request.args.get("user_id", "guest")

        if not city:
            return jsonify({"error": "City required"})

        data = get_weather(city)

        try:
            history = load_history()

            if user_id not in history:
                history[user_id] = {"searches": []}

            history[user_id]["searches"].append(
                {
                    "type": "weather",
                    "input": {"city": city},
                    "output": data,
                    "time": str(datetime.datetime.now()),
                }
            )

            history[user_id]["searches"] = history[user_id]["searches"][-5:]
            save_history(history)

        except Exception as e:
            print("History error:", e)

        return jsonify(data)

    # ---------------- CROP ---------------- #
    @app.route("/crop", methods=["POST"])
    def crop():
        data = request.json

        temp = float(data.get("temp", 0))
        humidity = float(data.get("humidity", 0))
        weather = data.get("weather", "clear")
        user_id = data.get("user_id", "guest")

        crops = recommend_crop(temp, humidity, weather)

        try:
            history = load_history()

            if user_id not in history:
                history[user_id] = {"searches": []}

            history[user_id]["searches"].append(
                {
                    "type": "crop",
                    "input": {
                        "temp": temp,
                        "humidity": humidity,
                        "weather": weather,
                    },
                    "output": crops,
                    "time": str(datetime.datetime.now()),
                }
            )

            history[user_id]["searches"] = history[user_id]["searches"][-5:]
            save_history(history)

        except Exception as e:
            print("History error:", e)

        return jsonify({"recommendations": crops})

    # ---------------- PRICES ---------------- #
    @app.route("/prices", methods=["GET"])
    def prices():
        commodity = request.args.get("commodity")
        state = request.args.get("state")

        if not commodity or not state:
            return jsonify({"error": "Commodity and state required"})

        data = get_prices(commodity, state)
        return jsonify(data)

    # ---------------- FORECAST ---------------- #
    @app.route("/forecast", methods=["GET"])
    def forecast():
        city = request.args.get("city")
        days = int(request.args.get("days", 0))
        user_id = request.args.get("user_id", "guest")

        data = get_forecast(city, days)

        try:
            history = load_history()

            if user_id not in history:
                history[user_id] = {"searches": []}

            history[user_id]["searches"].append(
                {
                    "type": "forecast",
                    "input": {"city": city, "days": days},
                    "output": data,
                    "time": str(datetime.datetime.now()),
                }
            )

            history[user_id]["searches"] = history[user_id]["searches"][-5:]
            save_history(history)

        except Exception as e:
            print("History error:", e)

        return jsonify(data)

    # ---------------- DETAILS ---------------- #
    @app.route("/details", methods=["GET"])
    def crop_details():
        crop = request.args.get("name")
        user_id = request.args.get("user_id", "guest")

        if not crop:
            return jsonify({"error": "No crop provided"})

        details = load_json(DETAILS_PATH)

        crop = crop.lower().strip()

        if crop in details:
            data = details[crop]

            try:
                history = load_history()

                if user_id not in history:
                    history[user_id] = {"searches": []}

                history[user_id]["searches"].append(
                    {
                        "type": "details",
                        "input": {"crop": crop},
                        "output": data,
                        "time": str(datetime.datetime.now()),
                    }
                )

                history[user_id]["searches"] = history[user_id]["searches"][-5:]
                save_history(history)

            except Exception as e:
                print("History error:", e)

            return jsonify(data)

        return jsonify({"error": "Crop not found"})

    # ---------------- PRICE (LOCAL JSON) ---------------- #
    @app.route("/price", methods=["GET"])
    def get_price():
        crop = request.args.get("crop")
        user_id = request.args.get("user_id", "guest")

        if not crop:
            return jsonify({"error": "No crop provided"})

        prices = load_json(PRICE_PATH)

        crop = crop.lower().strip()

        if crop not in prices:
            return jsonify({"error": f"{crop} not found"})

        try:
            history = load_history()

            if user_id not in history:
                history[user_id] = {"searches": []}

            history[user_id]["searches"].append(
                {
                    "type": "price",
                    "crop": crop,
                    "output": prices[crop],
                    "time": str(datetime.datetime.now()),
                }
            )

            history[user_id]["searches"] = history[user_id]["searches"][-5:]
            save_history(history)

        except Exception as e:
            print("History error:", e)

        return jsonify(prices[crop])

    # ---------------- CHAT (GEMINI) ---------------- #
    @app.route("/chat", methods=["POST"])
    def chat():
        try:
            data = request.get_json()

            user_msg = data.get("message")
            user_id = data.get("user_id", "guest")
            mode = data.get("mode", "farmer")

            if not user_msg:
                return jsonify({"reply": "Invalid request"}), 400

            if user_id not in chat_sessions:
                chat_sessions[user_id] = []

            chat_sessions[user_id].append(f"User: {user_msg}")
            chat_sessions[user_id] = chat_sessions[user_id][-6:]

            prompt = f"""
You are a helpful agriculture assistant.
Keep answers short and in bullet points.
Mode: {mode}

Conversation:
{chr(10).join(chat_sessions[user_id])}

Bot:
"""

            payload = {"contents": [{"parts": [{"text": prompt}]}]}

            response = requests.post(URL, json=payload)
            result = response.json()

            if "candidates" not in result:
                return jsonify({"reply": "⚠️ AI error"})

            reply = result["candidates"][0]["content"]["parts"][0]["text"]

            chat_sessions[user_id].append(f"Bot: {reply}")

            # save chat history
            try:
                history = load_history()

                if user_id not in history:
                    history[user_id] = {"searches": [], "chat": []}

                if "chat" not in history[user_id]:
                    history[user_id]["chat"] = []

                history[user_id]["chat"].append(
                    {
                        "user": user_msg,
                        "bot": reply,
                        "time": str(datetime.datetime.now()),
                    }
                )

                history[user_id]["chat"] = history[user_id]["chat"][-10:]
                save_history(history)

            except Exception as e:
                print("Chat history error:", e)

            return jsonify({"reply": reply})

        except Exception as e:
            print("ERROR:", e)
            return jsonify({"reply": "⚠️ Server error"}), 500

    # ---------------- SCHEMES ---------------- #
    @app.route("/scheme-data", methods=["GET"])
    def get_schemes():
        try:
            schemes = load_json(SCHEME_PATH)
            return jsonify(schemes)
        except Exception as e:
            return jsonify({"error": str(e)})

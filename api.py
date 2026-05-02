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
    # ---------------- CIRCUIT CONTROL ---------------- #
    device_state = {
        "outputs": {
            f"output{i}": "OFF" for i in range(1, 17)
        }
    }
    
    @app.route("/circuit", methods=["GET", "POST"])
    def circuit():
    
        if request.method == "POST":
            data = request.get_json()
    
            for key, value in data.items():
                if key in device_state["outputs"] and value in ["ON", "OFF"]:
                    device_state["outputs"][key] = value
    
            return jsonify({"status": "updated", "outputs": device_state["outputs"]})
    
        return jsonify(device_state)
    # ---------------- CROP REPORT (ADVANCED) ---------------- #
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
    
            # 🌾 Recommendations
            recommendations = recommend_crop(temp, humidity, weather)
    
            # 🎯 Best crop
            best_crop = recommendations[0][0] if recommendations else "Unknown"
    
            # 💰 Market
            try:
                market = get_prices(crop, "maharashtra")
            except:
                market = []
    
            avg_price = 0
            if isinstance(market, list) and len(market) > 0:
                prices = [m.get("price", 0) for m in market if m.get("price")]
                avg_price = sum(prices) / len(prices) if prices else 0
    
            # 📈 Profit estimation (basic model)
            estimated_yield = 2000  # kg per acre (simple assumption)
            estimated_cost = 30000  # ₹ per acre
    
            revenue = estimated_yield * avg_price
            profit = revenue - estimated_cost
    
            # ⚠️ Risk analysis
            risks = []
            if temp > 35:
                risks.append("High temperature stress")
            if humidity > 80:
                risks.append("Fungal disease risk")
            if humidity < 30:
                risks.append("Dry soil risk")
    
            # 🧠 Smart advice
            advice = []
    
            if crop.lower() == best_crop:
                advice.append(f"{crop} is highly suitable currently")
            else:
                advice.append(f"Consider switching to {best_crop} for better yield")
    
            if avg_price > 3000:
                advice.append("Market prices are strong — good selling opportunity")
            elif avg_price < 1500:
                advice.append("Low market price — consider storing crop")
    
            if profit > 0:
                advice.append("Farming looks profitable under current conditions")
            else:
                advice.append("Profit margin is low — optimize costs")
    
            # 🧠 AI-style summary (no API needed)
            summary = f"""
    In {city}, current conditions show {temp}°C temperature and {humidity}% humidity.
    The best crop right now is {best_crop}. Market average price is ₹{int(avg_price)}.
    
    Estimated profit for {crop} is ₹{int(profit)} per acre.
    
    Key risks: {', '.join(risks) if risks else 'Low risk'}.
    """
    
            return jsonify({
                "weather": weather_data,
                "recommendations": recommendations,
                "best_crop": best_crop,
                "market": market,
                "avg_price": avg_price,
                "profit": profit,
                "risks": risks,
                "advice": advice,
                "summary": summary
            })
    
        except Exception as e:
            print("CROP REPORT ERROR:", e)
            return jsonify({"error": "Server error"})

    # ---------------- SCHEMES ---------------- #
    @app.route("/scheme-data", methods=["GET"])
    def get_schemes():
        try:
            schemes = load_json(SCHEME_PATH)
            return jsonify(schemes)
        except Exception as e:
            return jsonify({"error": str(e)})
        
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


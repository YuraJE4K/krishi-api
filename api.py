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

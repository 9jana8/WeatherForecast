import sqlite3
from transformers import pipeline
from huggingface_hub import InferenceClient
import requests
import torch
from flask import Flask, request, jsonify, render_template
import re

app = Flask(__name__)

generator = pipeline("text-generation", model="gpt2")
    
# First function to query the temperature in a city on a specific date   
def query_temperature_in_city(
        city: str,
        date: str) -> float:
    connection = sqlite3.connect("weather.db")
    cursor = connection.cursor()
    cursor.execute("""
        SELECT WeatherData.temperature_avg
        FROM WeatherData
        JOIN Cities ON WeatherData.city_id = Cities.id
        WHERE Cities.city = ?
        AND WeatherData.date = ?
        """, (city, date))
    temperature = cursor.fetchone()
    connection.close()
    return temperature[0] if temperature else None

# Second function to query the maximum temperature in a city in a specific time span
def query_max_temperature_in_time_span_per_city(
        city: str,
        date_from: str,
        date_to: str) -> float:
    # TODO(jana): Add an assert that checks data format
    connection = sqlite3.connect("weather.db")
    cursor = connection.cursor()
    cursor.execute("""
        SELECT MAX(WeatherData.temperature_max)
        FROM WeatherData
        JOIN Cities ON WeatherData.city_id = Cities.id
        WHERE Cities.city = ?
        AND WeatherData.date BETWEEN ? AND ?
        """, (city, date_from, date_to))
    max_temperature = cursor.fetchone()[0]
    connection.close()
    return max_temperature if max_temperature else None

def generate_human_response(city, date_from, date_to) -> str:
    # Check out which function was called
    max_temperature = query_max_temperature_in_time_span_per_city("Belgrade", "2018-01-01", "2018-01-01")

    # Prepare the message to generate a human-like response
    if max_temperature is not None:
        answer = f"The maximum temperature in {city} between {date_from} and {date_to} was {max_temperature}°C."
    else:
        answer = f"Sorry, I couldn't find the data for the temperatures in {city} during that time period."

    # Use Hugging Face model to make the answer sound more natural
    response = generator(f"Question: What was the temperature in {city} between {date_from} and {date_to}? Answer: {answer}", max_length=100)
    return response[0]['generated_text']

# Get lists of possible cities
def get_unique_cities():
    connection = sqlite3.connect("weather.db")
    cursor = connection.cursor()
    cursor.execute("SELECT city FROM Cities")
    cities = [row[0] for row in cursor.fetchall()]
    connection.close()
    return cities

# Extract City and Date from User Input
def extract_city_and_date(user_query: str):
    cities = get_unique_cities()
    found_city = None
    found_date = None
    for city in cities:
        if city.lower() in user_query.lower():
            found_city = city
            break
    date_pattern = r'\b(\d{4}-\d{2}-\d{2}|\d{2}-\d{2}-\d{4}|\w+ \d{1,2}, \d{4})\b'
    date_match = re.search(date_pattern, user_query)
    found_date = date_match.group(0) if date_match else None
    if date_match:
        found_date = date_match.group()
    return found_city, found_date

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/query", methods=["POST"])
def query():
    data = request.get_json()
    if not data or "user_query" not in data:
        return jsonify({"error": "Missing 'user_query' in JSON data"}), 400

    user_query = data["user_query"]
    
    city, date = extract_city_and_date(user_query=user_query)

    if not city or not date:
        return jsonify({"error": "Could not find city or date in query"}), 400

    response_text = generate_human_response(city, date, date)

    return jsonify({"response": response_text})

if __name__ == '__main__':
    app.run(debug=True)

    # Connect to database
    connection = sqlite3.connect("weather.db")
    cursor = connection.cursor()

    # Query data from SQL
    cursor.execute("""
        SELECT Cities.city, WeatherData.date, WeatherData.temperature_avg
        FROM WeatherData
        JOIN Cities ON WeatherData.city_id = Cities.id
        WHERE Cities.city = 'Belgrade'
        LIMIT 10
        """)
    rows = cursor.fetchall()
    for row in rows:
        print(row)

    connection.close()
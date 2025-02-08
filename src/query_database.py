import sqlite3
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
from huggingface_hub import InferenceClient
import requests
import torch
from flask import Flask, request, jsonify, render_template
import re
import difflib

app = Flask(__name__)

generator = pipeline("text-generation", model="gpt2")

prompt = """
You are a weather data assistant. Only answer with exact numerical weather data. 
Provide the minimum and maximum temperature for Belgrade between 2019-07-20 and 2019-07-30.
Do NOT add any additional details beyond temperature.
"""
    
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

def query_min_temperature_in_time_span_per_city(
        city: str,
        date_from: str,
        date_to: str) -> float:
    connection = sqlite3.connect("weather.db")
    cursor = connection.cursor()
    cursor.execute("""
        SELECT MIN(WeatherData.temperature_min)
        FROM WeatherData
        JOIN Cities ON WeatherData.city_id = Cities.id
        WHERE Cities.city = ?
        AND WeatherData.date BETWEEN ? AND ?
        """, (city, date_from, date_to))
    min_temperature = cursor.fetchone()[0]
    connection.close()
    return min_temperature if min_temperature else None

def is_response_trustworthy(original, generated):
    generated_text = generated[0]["generated_text"]  
    similarity = difflib.SequenceMatcher(None, original, generated_text).ratio()
    return similarity > 0.8

# Structure API response
def generate_human_response(user_query) -> str:
    result = extract_city_and_date(user_query)
    print(f"Result from extract_city_and_date: {result}")  # Debugging line

    if len(result) == 3:
        city, date_from, date_to = result
        print(f"City: {city}, Date From: {date_from}, Date To: {date_to}")
        # Check out which function was called
        min_temperature = query_min_temperature_in_time_span_per_city(city, date_from, date_to)
        max_temperature = query_max_temperature_in_time_span_per_city(city, date_from, date_to)
        print(f"Min Temperature: {min_temperature}, Max Temperature: {max_temperature}")
        if min_temperature is not None and max_temperature is not None:
            answer = f"The minimum temperature in {city} between {date_from} and {date_to} was {min_temperature}°C, and the maximum temperature was {max_temperature}°C."
        else:
            answer = f"Sorry, I couldn't find the data for the temperatures in {city} during that time period."
    elif len(result) == 2:
        city, date = result
        print(f"City: {city}, Date: {date}")
        temperature = query_temperature_in_city(city, date)
        if temperature is not None:
            answer = f"The temperature in {city} on {date} was {temperature}°C."
        else:
            answer = f"Sorry, I couldn't find the data for the temperature in {city} on {date}."
    else:
        return "Sorry, I couldn't understand the query. Please provide a city and a date."
    
    response = generator(f'Answer: {answer}', max_length=100, truncation=True)
    response_text = response[0]["generated_text"]

    if is_response_trustworthy(answer, response):
        return response_text
    else:
        return answer  # Use the original database response if GPT-2 hallucinates

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
    found_dates = []
    for city in cities:
        if city.lower() in user_query.lower():
            found_city = city
            break
    date_pattern = r'\b(\d{4}-\d{2}-\d{2}|\d{2}-\d{2}-\d{4}|\w+ \d{1,2}, \d{4})\b'
    date_matches = re.findall(date_pattern, user_query)

    if len(date_matches) >= 1:
        found_dates.append(date_matches[0])
    if len(date_matches) >= 2:
        found_dates.append(date_matches[1])
  
    if len(found_dates) == 2:
        return found_city, found_dates[0], found_dates[1]
    
    elif len(found_dates) == 1:
        return found_city, found_dates[0]

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/query", methods=["POST"])
def query():
    data = request.get_json()
    if not data or "user_query" not in data:
        return jsonify({"error": "Missing 'user_query' in JSON data"}), 400

    user_query = data["user_query"]
    
    result = extract_city_and_date(user_query=user_query)
    if not result and len(result) < 2:
        return jsonify({"error": "Could not find city and date in query"}), 400

    response_text = generate_human_response(user_query=user_query)

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

    connection = sqlite3.connect("weather.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT Cities.city, WeatherData.date, WeatherData.temperature_min, WeatherData.temperature_max
        FROM WeatherData
        JOIN Cities ON WeatherData.city_id = Cities.id
        WHERE Cities.city = 'Belgrade'
        AND WeatherData.date BETWEEN '2018-01-01' AND '2018-01-31'
    """)
    rows = cursor.fetchall()
    for row in rows:
        print(row)

    connection.close()
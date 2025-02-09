import sqlite3
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
from flask import Flask, request, jsonify, render_template
import re
import difflib
from datetime import datetime

app = Flask(__name__)

generator = pipeline("text-generation", model="gpt2")
    
    
# Function 1
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


# Function 2
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


# Function 3
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


def query_city_comparison(city1: str, city2: str, date: str) -> str:
    connection = sqlite3.connect("weather.db")
    cursor = connection.cursor()
    cursor.execute("""
        SELECT Cities.city, WeatherData.date, WeatherData.temperature_max 
        FROM WeatherData
        JOIN Cities ON WeatherData.city_id = Cities.id
        WHERE Cities.city IN (?, ?)
        AND WeatherData.date = ?
        LIMIT 10
        """, (city1, city2, date))
    rows = cursor.fetchall()
    connection.close()
    if len(rows) != 2:
        return "Data not available for both cities on the given date."
    temp1 = rows[0][1]
    temp2 = rows[1][1]
    if temp1 > temp2:
        return f"{rows[0][0]} had a higher temperature ({temp1}°C) than {rows[1][0]} ({temp2}°C) on {date}."
    elif temp2 > temp1:
        return f"{rows[1][0]} had a higher temperature ({temp2}°C) than {rows[0][0]} ({temp1}°C) on {date}."
    else:
        return f"Both {city1} and {city2} had the same temperature ({temp1}°C) on {date}."
    

# For HF GPT-2 model hallucination detection
def is_response_trustworthy(original, generated):
    generated_text = generated[0]["generated_text"]  
    similarity = difflib.SequenceMatcher(None, original, generated_text).ratio()
    return similarity > 0.8


# Structure API response
def generate_human_response(user_query) -> str:
    result = extract_city_and_date(user_query)
    found_cities, found_dates = result
    key_words = query_key_words(user_query)
    answer = ""

    # If querying max/min temperature in a time span
    if len(found_cities)==1 and len(found_dates)==2:
        city = found_cities[0]
        date_from = found_dates[0]
        date_to = found_dates[1]

        if 'maximum' in key_words:
            max_temperature = query_max_temperature_in_time_span_per_city(city, date_from, date_to)
            if max_temperature is not None:
                answer = f"The maximum temperature in {city} between {date_from} and {date_to} was {max_temperature}°C."

        elif 'minimum' in key_words:
            min_temperature = query_min_temperature_in_time_span_per_city(city, date_from, date_to)
            if min_temperature is not None:
                answer = f"The minimum temperature in {city} between {date_from} and {date_to} was {min_temperature}°C."

    # If querying highest temperature between two cities
    elif len(found_cities)==2 and len(found_dates)==1:
        city1, city2 = found_cities[:2]
        date = found_dates[0]
        if all(word in key_words for word in ['highest', 'temperature', 'between']):
            return query_city_comparison(city1, city2, date)
        
    # If querying temperature in a single city on a specific date
    elif len(found_cities)==1 and len(found_dates)==1:
        city = found_cities[0]
        date = found_dates[0]
        temperature = query_temperature_in_city(city, date)
        if temperature is not None:
            answer = f"The temperature in {city} on {date} was {temperature}°C."

    # If the query was not understood      
    else:
        return "Sorry, I couldn't understand the query. Please provide at least one city and a date."
    
    # Generate a response with GPT-2
    response = generator(f'Answer: {answer}', max_length=100, truncation=True)
    response_text = response[0]["generated_text"]

    # Check trustworthiness and return final response
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
    found_cities = []
    found_dates = []

    for city in cities:
        if city.lower() in user_query.lower():
            found_cities.append(city)
            break

    date_pattern = r'(\d{4}-\d{2}-\d{2}|\d{2}-\d{2}-\d{4}|\w+ \d{1,2}, \d{4})'
    date_matches = re.findall(date_pattern, user_query)

    for date_match in date_matches:
        converted = convert_date_format(date_match)
        if converted:
            found_dates.append(converted)

    return found_cities, found_dates


# Helping function to detect YYYY-MM-DD, MM-DD-YYYY, and Month DD, YYYY date formats for extract_city_and_date()    
def convert_date_format(date_str: str) -> str:
    try: 
        return datetime.strptime(date_str, "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        try: 
            return datetime.strptime(date_str, "%m-%d-%Y").strftime("%Y-%m-%d")
        except ValueError:
            try:
                return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
            except ValueError:
                return None


# Helping function to detect which query is needed    
def query_key_words(user_query: str):
    key_words = ['maximum', 'minimum', 'highest', 'temperature', 'between', 'freezing', 'degrees']
    found_words = []
    for word in key_words:
        if word in user_query.lower():
            found_words.append(word)
            return found_words
    return False


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
    if result is None or len(result) < 2:
        return jsonify({"error": "results is none or either city or date were not provided"}), 400

    response_text = generate_human_response(user_query=user_query)

    return jsonify({"response": response_text})


if __name__ == '__main__':
    app.run(debug=True)

    connection = sqlite3.connect("weather.db")
    cursor = connection.cursor()

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
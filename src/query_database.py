import sqlite3
from transformers import pipeline
import re
import difflib
from datetime import datetime
from db_utils import create_connection

generator = pipeline("text-generation", model="gpt2")

def query_temperature_in_city(
        city: str,
        date: datetime,
        connection: sqlite3.Connection) -> float:
    assert isinstance(date, datetime), "date must be datetime object"
    date_str = date.strftime("%Y-%m-%d")
    print(date_str)
    cursor = connection.cursor()
    cursor.execute("""
        SELECT WeatherData.temperature_avg
        FROM WeatherData
        JOIN Cities ON WeatherData.city_id = Cities.id
        WHERE Cities.city = ?
        AND WeatherData.date = ?
        """, (city, date_str))
    temperature = cursor.fetchone()
    return temperature[0] if temperature else None


def query_max_temperature_in_time_span_per_city(
        city: str,
        date_from: datetime,
        date_to: datetime,
        connection: sqlite3.Connection) -> float:
    assert isinstance(date_from, datetime) and isinstance(date_to, datetime), "dates must be a datetime objects"
    assert date_from <= date_to, "date_from needs to be before the date date_to"
    date_from_str = date_from.strftime("%Y-%m-%d")
    date_to_str = date_to.strftime("%Y-%m-%d")
    cursor = connection.cursor()
    cursor.execute("""
        SELECT MAX(WeatherData.temperature_max)
        FROM WeatherData
        JOIN Cities ON WeatherData.city_id = Cities.id
        WHERE Cities.city = ?
        AND WeatherData.date BETWEEN ? AND ?
        """, (city, date_from_str, date_to_str))
    max_temperature = cursor.fetchone()[0]
    return max_temperature if max_temperature else None


def query_min_temperature_in_time_span_per_city(
        city: str,
        date_from: datetime,
        date_to: datetime,
        connection: sqlite3.Connection) -> float:
    assert isinstance(date_to, datetime) and isinstance(date_from, datetime), "dates must be datetime objects"
    assert date_from <= date_to, "date_from needs to be before, or the same day as date_to"
    date_from_str = date_from.strftime("%Y-%m-%d")
    date_to_str = date_to.strftime("%Y-%m-%d")
    cursor = connection.cursor()
    cursor.execute("""
        SELECT MIN(WeatherData.temperature_min)
        FROM WeatherData
        JOIN Cities ON WeatherData.city_id = Cities.id
        WHERE Cities.city = ?
        AND WeatherData.date BETWEEN ? AND ?
        """, (city, date_from_str, date_to_str))
    min_temperature = cursor.fetchone()[0]
    return min_temperature if min_temperature else None


def query_city_comparison(
        city1: str, 
        city2: str, 
        date: datetime, 
        connection: sqlite3.Connection) -> str:
    assert isinstance(date, datetime), "date must be an datetime object"
    date_str = date.strftime("%Y-%m-%d")
    cursor = connection.cursor()
    cursor.execute("""
        SELECT 
            city1.city AS city1_alias, 
            city2.city AS city2_alias, 
            city1.temperature_max AS temperature1_alias, 
            city2.temperature_max AS temperature2_alias,
                CASE
                    WHEN city1.temperature_max > city2.temperature_max THEN city1.city
                    WHEN city2.temperature_max > city1.temperature_max THEN city2.city
                    ELSE 'Both cities had the same temperature'
                END AS higher_temp_city
        FROM
            WeatherData wd1    
        JOIN
            Cities city1 ON wd1.city_id = city1.id
        JOIN
            WeatherData wd2 ON wd2.city_id = city2.id
        JOIN
            Cities city2 ON wd2.city_id = city2.id
        WHERE
            wd1.date = ? AND wd2.date = ?
            AND city1.city = ? AND city2.city = ? 
        """, (date_str, date_str, city1, city2))
    rows = cursor.fetchall()
    return rows
    


def is_response_trustworthy(original: str, generated: str) -> bool:
    similarity = difflib.SequenceMatcher(None, original, generated).ratio()
    return similarity > 0.8



def generate_human_response(user_query) -> str:
    result = extract_city_and_date(user_query)
    found_cities, found_dates = result
    key_words = query_key_words(user_query)
    answer = ""

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

    elif len(found_cities)==2 and len(found_dates)==1:
        city1, city2 = found_cities[:2]
        date = found_dates[0]
        if all(word in key_words for word in ['highest', 'temperature', 'between']):
            return query_city_comparison(city1, city2, date)
        
    elif len(found_cities)==1 and len(found_dates)==1:
        city = found_cities[0]
        date = found_dates[0]
        temperature = query_temperature_in_city(city, date)
        if temperature is not None:
            answer = f"The temperature in {city} on {date} was {temperature}°C."
    
    else:
        return "Sorry, I couldn't understand the query. Please provide at least one city and a date."
    
    response = generator(f'Answer: {answer}', max_length=100, truncation=True)
    response_text = response[0]["generated_text"]

    if is_response_trustworthy(answer, response_text):
        return response_text
    else:
        return answer  # Use the original database response if GPT-2 hallucinates



def get_unique_cities(connection: sqlite3.Connection):
    cursor = connection.cursor()
    cursor.execute("SELECT city FROM Cities")
    cities = [row[0] for row in cursor.fetchall()]
    print(type(cities)) # debuging line
    return cities


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


def convert_date_format(date_str: str) -> datetime | None:
    for format in ("%B %d, %Y", "%m-%d-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, format) # Return datetime object
        except ValueError:
            continue # Try the next format
    return None


  
def query_key_words(user_query: str):
    key_words = ['maximum', 'minimum', 'highest', 'temperature', 'between', 'freezing', 'degrees']
    found_words = []
    for word in key_words:
        if word in user_query.lower():
            found_words.append(word)
            return found_words
    return False



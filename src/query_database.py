import sqlite3
from datetime import datetime

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
    if temperature:
        return temperature[0]
    return None


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
    if max_temperature and max_temperature[0] is not None:
        return max_temperature[0]
    return None


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
    if min_temperature and min_temperature[0] is not None:
        return min_temperature[0]
    return None


def query_city_comparison(city1: str, city2: str, date: datetime, connection: sqlite3.Connection) -> str:
    assert isinstance(date, datetime), "date must be an datetime object"
    date_str = date.strftime("%Y-%m-%d")
    cursor = connection.cursor()
    cursor.execute("""
        SELECT 
            c1.city AS city1_alias, 
            c2.city AS city2_alias, 
            w1.temperature_max AS temperature1_alias, 
            w2.temperature_max AS temperature2_alias,
                CASE
                    WHEN w1.temperature_max > w2.temperature_max THEN w1.temperature_max
                    WHEN w2.temperature_max > w1.temperature_max THEN w2.temperature_max
                    ELSE 'Both cities had the same temperature'
                END AS higher_temp
        FROM
            WeatherData w1    
        JOIN
            Cities c1 ON w1.city_id = c1.id
        JOIN
            WeatherData w2 ON w2.city_id = c2.id
        JOIN
            Cities c2 ON w2.city_id = c2.id
        WHERE
            w1.date = ? AND w2.date = ?
            AND c1.city = ? AND c2.city = ? 
        """, (date_str, date_str, city1, city2))
    result = cursor.fetchone()
    if result:
        _, _, _, _, higher_temp = result
        return higher_temp if higher_temp != 'Both cities had the same temperature' else '0'
    return None

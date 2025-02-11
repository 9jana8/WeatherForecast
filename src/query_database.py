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

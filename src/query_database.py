import sqlite3

# TODO(jana): Implement couple of functions

def query_temperature_in_city(
        city: str,
        date: str) -> float:
    # TODO(jana): Add an assert that checks data format
    pass

if __name__ == '__main__':
    # Connect to database
    connection = sqlite3.connect("weather.db")
    cursor = connection.cursor()

    # Query data from SQL
    cursor.execute("""
        SELECT Cities.city, WeatherData.date, WeatherData.temperature_avg
        FROM WeatherData
        JOIN Cities ON WeatherData.city_id = Cities.id
        WHERE Cities.city = 'Belgrade'
        LIMIT 100
        """)
    rows = cursor.fetchall()
    for row in rows:
        print(row)

    connection.close()
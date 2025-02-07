import sqlite3

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
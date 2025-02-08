import sqlite3
from data_utils import load_data
import argparse

if __name__ == '__main__':
    # Load the data
    parser = argparse.ArgumentParser(description="Build SQLite database from .csv file")
    parser.add_argument("filename", help="The name of the file to process")
    args = parser.parse_args()
    df = load_data(args.filename)
    print("database is being built")

    connection = sqlite3.connect('weather.db')
    cursor = connection.cursor()

    # FYI: SQLite does not automatically check whether the city_id exists in the Cities table. By default, foreign key constraints (which ensure that referenced values exist in the parent table) are not enforced in SQLite unless explicitly enabled.
    cursor.execute('PRAGMA foreign_keys = ON;')

    # Create Cities table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Cities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,       -- primary key, indexed by default
        city TEXT NOT NULL,
        country TEXT NOT NULL,
        lat FLOAT,
        lon FLOAT
    )"""
    )
    connection.commit()

    # Create table WeatherData
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS WeatherData (
        id INTEGER PRIMARY KEY AUTOINCREMENT,       -- primary key, indexed by default
        city_id INTEGER,                            -- Foreign key to Cities table, not indexed by default
        date DATE,
        temperature_avg FLOAT,
        temperature_min FLOAT,
        temperature_max FLOAT,
        wind_direction FLOAT,
        wind_speed FLOAT,
        pressure FLOAT,
        FOREIGN KEY(city_id) REFERENCES Cities(id)
    )"""
    )
    connection.commit()

    # Indexing columns for faster queries
    # Without Indexing: SQLite has to perform a full table scan for each query.
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_city_id ON WeatherData(city_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_city_name ON Cities(city);')
    connection.commit()

    # Insert data to Cities 
    for index, row in df[['city', 'country', 'Latitude', 'Longitude']].drop_duplicates().iterrows():
        cursor.execute("""
        INSERT OR IGNORE INTO Cities (city, country, lat, lon)
        VALUES (?, ?, ?, ?)""",
        (row['city'], row['country'], row['Latitude'], row['Longitude']))
    connection.commit()
    print("Cities table is filled")

    # Insert data to WeatherData. Whenever you need to pass a single parameter to SQL query make it a TUPLE.
    for index, row in df.iterrows():
        cursor.execute('SELECT id FROM Cities WHERE city = ?', (row['city'],))
        city_id = cursor.fetchone()[0]

        cursor.execute("""
        INSERT INTO WeatherData (city_id, date, temperature_avg, temperature_min, temperature_max, wind_direction, wind_speed, pressure)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (city_id, row['date'].strftime('%Y-%m-%d'), row['tavg'], row['tmin'], row['tmax'], row['wdir'], row['wspd'], row['pres']))
    connection.commit()
    print("WeatherData table is filled")

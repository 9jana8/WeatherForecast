import sqlite3
from data_utils import load_data
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process two files - .csv and .db file")
    parser.add_argument("csv_file", help="The name of the .csv file to process")
    parser.add_argument("db_file", help="The name of the .db file to process")
    args = parser.parse_args()
    
    df = load_data(args.csv_file)

    print("database is being built")
    connection = sqlite3.connect(args.db_file)
    cursor = connection.cursor()

    cursor.execute('PRAGMA foreign_keys = ON;')

    # Create Cities table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Cities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,       -- primary key, indexed by default
        city TEXT NOT NULL,
        country TEXT NOT NULL,
        lat FLOAT,
        lon FLOAT
    )""")
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
    )""")
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

    connection.close()
    print("Database connection closed")
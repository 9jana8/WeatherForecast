import sqlite3

def create_connection(filename) -> sqlite3.Connection:
    try:
        connection = sqlite3.connect(filename)
        print(f"Connection to SQLite DB successful: {filename}")
        return connection
    except sqlite3.Error as error:
        print(f"Error: {error}")
        return None
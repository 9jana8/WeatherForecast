import sqlite3

def create_connection(filename) -> sqlite3.Connection:
    assert filename.endswith('.db'), 'Error: Database file must have a .db extension'
    try:
        connection = sqlite3.connect(filename)
        print(f"Connection to SQLite DB successful: {filename}")
        return connection
    except sqlite3.Error as error:
        print(f"Error: {error}")
        return None
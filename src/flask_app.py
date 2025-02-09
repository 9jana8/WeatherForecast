from flask import Flask, request, jsonify, render_template
import sqlite3
from query_database import extract_city_and_date, generate_human_response
import argparse

app = Flask(__name__)

def create_connection(filename) -> sqlite3.Connection:
    try:
        connection = sqlite3.connect(filename)
        print(f"Connection to SQLite DB successful: {args.filename}")
        return connection
    except sqlite3.Error as error:
        print(f"Error: {error}")
        return None


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
    parser = argparse.ArgumentParser(description="Query SQLite database")
    parser.add_argument("filename", help="The name of the SQLite database file")
    args = parser.parse_args()
    connection = create_connection(args.filename)

    app.run(debug=True)

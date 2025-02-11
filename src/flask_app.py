from flask import Flask, request, jsonify, render_template
import argparse
from db_utils import create_connection
from chatgpt_bot import generate_response

app = Flask(__name__)

# Initialize database connection globally
parser = argparse.ArgumentParser(description="Query SQLite database")
parser.add_argument("filename", help="The name of the SQLite database file")
args = parser.parse_args()
connection = create_connection(args.filename)

@app.route("/")
def home():
    return render_template("index.html")


@app.route('/query', methods=['POST'])
def query():
    data = request.get_json()
    if not data or "user_query" not in data:
        return jsonify({"error": "Missing 'user_query' in JSON data"}), 400
    user_query = data["user_query"]
    print(f"debugging user_query: {user_query}")
    # Za Urosa: nije htelo da radi dok nisam napravila connection ovde 
    connection = create_connection(args.filename)  
    try: 
        response = generate_response(user_query, connection)
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500 
    
    return jsonify({"response": response})


if __name__ == '__main__':
    try:
        app.run(debug=True)
    finally:
        if connection:
            connection.close()

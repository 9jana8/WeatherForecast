from flask import Flask, request, jsonify, render_template
import argparse
from db_utils import create_connection
from chat_bot import get_assistant_query, fetch_temperature, respond_to_user, extract_city_date, response_messages, query_messages

app = Flask(__name__)

# Initialize database connection globally
parser = argparse.ArgumentParser(description="Query SQLite database")
parser.add_argument("filename", help="The name of the SQLite database file")
args = parser.parse_args()
connection = create_connection(args.filename)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        user_query = request.form['user_query']
        assistant_query = get_assistant_query(user_query, query_messages)
        daily_queries, max_time_span_param, min_time_span_param = extract_city_date(assistant_query)
        connection = create_connection(args.filename)  
        temp = []
        if daily_queries is not None:
            cities_daily = [city for city, _ in daily_queries]
            date_objects_daily = [date for _, date in daily_queries]
            query_type = 'daily'
            temp = []
            for city, date_object in zip(cities_daily, date_objects_daily):
                temp.append(fetch_temperature(city, date_object, query_type, connection))
                print(f'db_response (daily): {temp}')
  
        if max_time_span_param is not None:
            city_max, date_from_object_max, date_to_object_max = max_time_span_param
            print(f'city in max time span: {city_max}, date_from: {date_from_object_max}, date_to: {date_to_object_max}\n')
            query_type = 'max_span'
            temp = fetch_temperature(city_max, date_from_object_max, query_type, connection, date_to_object_max)
            print(f'db_response: {temp}')

        if min_time_span_param is not None:
            city_min, date_from_object_min, date_to_object_min = min_time_span_param
            query_type = 'min_span'
            temp = fetch_temperature(city_min, date_from_object_min, query_type, connection, date_to_object_min)
            print(f'db_response: {temp}')
        print(f"Final temp data: {temp}")
        final_response = respond_to_user(temp, response_messages, user_query)
        print(f"Final assistant response: {final_response}")
        return render_template('index.html', user_query=user_query, assistant_response=final_response)

    return render_template('index.html')



if __name__ == '__main__':
    try:
        app.run(debug=True)
    finally:
        if connection:
            connection.close()

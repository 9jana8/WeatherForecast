import openai
from query_database import query_temperature_in_city, query_max_temperature_in_time_span_per_city, query_min_temperature_in_time_span_per_city, query_city_comparison
import argparse
from db_utils import create_connection
import json
import sqlite3
from datetime import datetime
from typing import Optional, Tuple, Union


API_KEY = "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"
URL = "https://openrouter.ai/api/v1/chat/completions"
BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "mistralai/mistral-7b-instruct:free"

# tests
user_query = "What is the weather in Belgrade on 2020-10-01?"
user_query1 = "What was the maximum temperature in Paris between 2020-10-01 and 2020-10-05?"

client = openai.OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL
)


def extract_city_and_date(user_query, model=MODEL) -> dict:
    prompt_ = f"""
    Extract all cities and dates from the following query and return a valid JSON response.
    The output should strictly follow this format without any explanations:
    {{
        "city": ["<city1>", "<city2>", ...],
        "date": ["<date1>", "<date2>", ...]
    }}
    If a city or date is missing, return an empty list for that key.
    
    User Query: "{user_query}"
    """
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt_}],
        temperature=0.1
    )
    extracted_info = response.choices[0].message.content.strip()
    print("Raw API Response for extract_city_and_date:", extracted_info)
    try:
        return json.loads(extracted_info)  # Convert response to a dictionary
    except json.JSONDecodeError:
        print("Error: Unexpected API response format")
        return {'city': [], 'date': []}


def determine_query_type(user_input: str, model=MODEL) -> int:
    prompt = f"""
    Analyze the user query to determine what type of weather question they are asking.
    Return:
        1: If asking for the temperature of one city on one day.
        2: If asking for the maximum temperature between two dates in one city.
        3: If asking for the minimum temperature between two dates in one city.
        4: If asking which city had a higher temperature on some day.
    Return only one integer: 1, 2, 3 or 4.
    User Query: "{user_input}"
    """
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    number = response.choices[0].message.content.strip()
    print("Raw API Response:", number)
    try:
        return int(number)
    except ValueError:
        print("Error: Unexpected API response format")
        return -1


def provide_params(user_input: str, connection: sqlite3.Connection) -> Optional[Union[Tuple[str, str, float],
                                                                                      Tuple[str, str, str, float],
]]:
    user_input_extracted = extract_city_and_date(user_input)
    cities = user_input_extracted.get('city', [])
    dates = user_input_extracted.get('date', [])
    date_objects = [datetime.strptime(date, "%Y-%m-%d") for date in dates]
    query_number = determine_query_type(user_input)
    if query_number == 1:
        city_value = cities[0]
        date_value = dates[0]
        date_object = date_objects[0]
        temp_value = query_temperature_in_city(city_value, date_object, connection)
        return city_value, date_value, temp_value
    elif query_number == 2:
        city_value = cities[0]
        if date_objects[0] <= date_objects[1]:
            date_from_object = date_objects[0]
            date_to_object = date_objects[1]
        temp_value = query_max_temperature_in_time_span_per_city(city_value, date_from_object, date_to_object, connection)
        date_from_value = date_from_object.strftime("%Y-%m-%d")
        date_to_value = date_to_object.strftime("%Y-%m-%d")
        return city_value, date_from_value, date_to_value, temp_value
    elif query_number == 3:
        city_value = cities[0]
        if date_objects[0] <= date_objects[1]:
            date_from_object = date_objects[0]
            date_to_object = date_objects[1]
        temp_value = query_min_temperature_in_time_span_per_city(city_value, date_from_object, date_to_object, connection)
        date_from_value = date_from_object.strftime("%Y-%m-%d")
        date_to_value = date_to_object.strftime("%Y-%m-%d")
        return city_value, date_from_value, date_to_value, temp_value
    elif query_number == 4:
        city_first_value = cities[0]
        city_second_value = cities[1]
        date_value = dates[0]
        date_object = date_objects[0]
        temp_value = query_city_comparison(city_first_value, city_second_value, date_object, connection)
        return city_first_value, city_second_value, date_value, temp_value
    else:
        return None


def generate_response(user_input: str, connection: sqlite3.Connection, model=MODEL) -> str:
    query_number = determine_query_type(user_input)
    if query_number == 1:
        city_value, date_value, temp_value = provide_params(user_input, connection)
    if query_number == 2:
        city_value, date_from_value, date_to_value, temp_value = provide_params(user_input, connection)
    if query_number == 3:
        city_value, date_from_value, date_to_value, temp_value = provide_params(user_input, connection)
    if query_number == 4:
        city_value1, city_value2, date_value, temp_value = provide_params(user_input, connection)
    text = """
    Users will ask you about the weather in a specific city. \
    You do not have the exact information about the weather, but you are required to act as though you do. \
    For every weather-related query, you should respond by providing placeholders for the temperature, date, and city name. \
    Your answer should contain this format: <TEMP> <DD-MM-YYY> <CITY>, where:
    - <TEMP> represents the temperature (in Celsius).
    - <DD-MM-YYY> represents the date in day-month-year format.
    - <CITY> represents the city name.

    Example: "The temperature in <CITY> is <TEMP> on <DD-MM-YYY>."
    """
    if query_number == 1:
        prompt = f"""
        Summarize the text delimited by triple backticks into a maximum of one sentence. \
        Do not describe your purpose as a weather assistant; the user is aware of that. 
        You should respond by providing placeholders for the temperature, date, and city name.
        ```{text}```

        Please provide the placeholders <TEMP>, <DATE>, and <CITY> as described above, and replace 
        them with {temp_value}, {date_value}, and {city_value}.
        """
    elif query_number == 2 or query_number == 3:
        prompt = f"""
        Summarize the text delimited by triple backticks into a maximum of one sentence. \
        Do not describe your purpose as a weather assistant; the user is aware of that. 
        You should respond by providing placeholders for the temperature, date range, and city name.
        ```{text}```

        Please provide the placeholders <TEMP>, <DD-MM-YYY> and <DD-MM-YYY>, and <CITY> as described 
        above, and replace them with {temp_value}, {date_from_value} and {date_to_value}, and {city_value}.
        """
    elif query_number == 4:
        prompt = f"""
        Summarize the text delimited by triple backticks into a maximum of one sentence. \
        Do not describe your purpose as a weather assistant; the user is aware of that. You should 
        respond by providing placeholders for the temperature, date, and cities.
        ```{text}```

        Please provide the placeholders <TEMP>, <DD-MM-YYY>, <CITY> as described above, and replace 
        them with {temp_value}, {date_value}, {city_value1} and {city_value2}.
        """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        if response and response.choices and response.choices[0].message:
            print(f"API RESPONSE: {response.choices[0].message.content}")
            return response.choices[0].message.content
        else:
            print("Error: Unexpected API response format:", response)
            return "An error occurred while generating the response."

    except Exception as e:
        print("Exception occurred:", e)
        return "An error occurred while communicating with the API."
    
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Query SQLite database")
    parser.add_argument("filename", help="The name of the SQLite database file")
    args = parser.parse_args()
    connection = create_connection(args.filename)
        
    res = generate_response(user_query, connection)
    print(res)    

    print(f"API response for detecting query of the first use_input: {determine_query_type(user_query)}")
    print(f"API response for detecting query of the first use_input: {determine_query_type(user_query1)}")
    
    connection.close()
import openai
from query_database import query_temperature_in_city, query_max_temperature_in_time_span_per_city, query_min_temperature_in_time_span_per_city, query_city_comparison
import argparse
from db_utils import create_connection
import sqlite3
from datetime import datetime
import os
import re


API_KEY = os.getenv("API_KEY")  # Retrieve the API key
URL = "https://openrouter.ai/api/v1/chat/completions"
BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "mistralai/mistral-7b-instruct:free"


system_prompt = """
    I am not the user. I am leveraging you to read data from the database and talk to the actual user.
    You are a weather bot. The user will ask you various queries about temperatures.

    Don't try to give me that exact information because you don't really know it. Instead, you must
    query a database. Write <TEMP><CITY><DD-MM-YYYY>, send that query and wait for the response. 
    As a response you will get a single float number denoting temperature in Celsius 
    on that day in that city. 

    Use the exact format: <TEMP><CITY><DD-MM-YYYY>. For example:
    - <TEMP><Berlin><15-01-2024>
    - <TEMP><Belgrade><01-10-2020>

    Don't put the actual temperature before you read the query response from the database.
    Once you are ready to give the final answer to the user using the data you read from the 
    database, write ---Response to the actual user--- and then follow it by the actual response.
    You will respond to the actual user only when you receive back number. 
    Everything that is sent by the user will start with "---USER---" 
    

    You must:
    1. Always enclose CITY in angle brackets <>.
    2. Wait for the database response before answering the user.
    3. Once you receive the temperature value, respond to the user using this format:
       ---Response to the actual user--- The temperature in <CITY> on <DD-MM-YYYY> was <VALUE>°C.
    4. Stop after the first "---Assistant---" and wait for the temperature response.
    5. The user's messages will always start with "---USER---".

    **Failure to follow the exact format will result in incorrect responses.**
"""


# pravi se stalno, me treba da bude globalna. neka ide u Flask
client = openai.OpenAI(api_key=API_KEY, base_url=BASE_URL)


def get_assistant_query(user_query: str) -> str:
    """Ask the AI to format a database query and return it."""
    messages = [
        {"role": "system", "content": "You are a helpful weather bot."},
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': f'---USER--- {user_query}'}]

    response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.1)

    return response.choices[0].message.content


def extract_city_date(response: str):
    """Extract city and date from AI-generated query."""
    match = re.search(r"<TEMP><([\w\s]+)><(\d{2}-\d{2}-\d{4})>", response)
    if match:
        city = match.group(1)
        date = datetime.strptime(match.group(2), "%d-%m-%Y")
        return city, date
    return None, None


def fetch_temperature(city: str, date: datetime, connection: sqlite3.Connection, model=MODEL) -> str:    
    temp = query_temperature_in_city(city, date, connection)
    return str(temp) if temp is not None else "No data available"
    

def respond_to_user(temp: str, city: str, date: str) -> str:
    """Generate a user response based on temperature data. Expand messages for context."""
    messages = [
        {"role": "system", "content": "You are a helpful weather bot."},
        {'role': 'system', 'content': system_prompt},
        {'role': 'assistant', 'content': f"<TEMP><{city}><{date}>"},
        {'role': 'user', 'content': f"The temperature for {city} on {date} is {temp}°C."},
    ]
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.1
    )
    return response.choices[0].message.content

    

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Query SQLite database")
    parser.add_argument("filename", help="The name of the SQLite database file")
    args = parser.parse_args()

    connection = create_connection(args.filename)
    user_query = input("Enter your weather query: ")

    assistant_query = get_assistant_query(user_query)
    print("Assistant Query:", assistant_query)

    city, date_object = extract_city_date(assistant_query)

    if city and date_object:
        temp = fetch_temperature(city, date_object, connection)
        date_str = date_object.strftime("%d-%m-%Y")
        final_response = respond_to_user(temp, city, date_str)
        print(final_response)
    else:
        print("Invalid query format received from AI.") 

    connection.close()
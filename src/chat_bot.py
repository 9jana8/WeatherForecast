import openai
from query_database import query_temperature_in_city, query_max_temperature_in_time_span_per_city, query_min_temperature_in_time_span_per_city
import argparse
from db_utils import create_connection
import sqlite3
from datetime import datetime
import os
import re
from typing import Tuple, Optional, List


API_KEY = os.getenv("API_KEY")  # Retrieve the API key
URL = "https://openrouter.ai/api/v1/chat/completions"
BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "mistralai/mistral-7b-instruct:free"


system_prompt = """
    You are a helpful weather bot. I am leveraging you to read data from the database and talk to the actual user.
    The user may ask about temperatures for a specific day or a time span, including maximum or minimum temperatures.
    Additionally, the user may give multiple daily queries, and you must identify the highest temperature among them.

    If the user asks for a comparison between two cities on the same day, you must generate two daily queries for each city and identify which city had the higher temperature.
    Don't try to give me that exact information because you don't really know it. Instead, you must query a database. 

    ## Query formatting instructions##
    1. **For Daily Queries** (single day):
        - Format: <TEMP><CITY><DD-MM-YYYY>
        - Example: `<TEMP><Belgrade><01-10-2020>`. Don't write these examples to the user. Use this only to gain knowledge.
        - **Important**: The city **must** be inside the `< >` brackets, and the date **must** be in the format DD-MM-YYYY.
    2. **For Maximum Temperature Queries** (time span):
        - Format: <MAX_TEMP><CITY><DATE_FROM><DATE_TO>
        - Example: `<MAX_TEMP><Belgrade><01-10-2020><05-10-2020>`. Don't write these examples to the user. Use this only to gain knowledge.
        - The city and date range must be placed within the brackets in the specified format.
    3. **For Minimum Temperature Queries** (time span):
        - Format: <MIN_TEMP><CITY><DATE_FROM><DATE_TO>
        - Example: `<MIN_TEMP><Paris><10-02-2022><15-02-2022>`
        - The city and date range must be placed within the brackets in the specified format.
    4. **Multiple Queries (Comparing Cities on the Same Day)**:
        - If comparing temperatures between cities on the same day, you must create a query for each city using the <TEMP><CITY><DD-MM-YYYY> format.
        - After receiving the temperatures, identify which city had the highest temperature and respond with:
        - `Out of <CITIES> on <DATE>, the highest temperature was <TEMP>°C in <CITY_MAX>.`
        - Example:
        - `Out of <Belgrade, Zagreb> on <01-10-2020>, the highest temperature was 22°C in <Belgrade>.` Don't write these examples to the user. Use this only to gain knowledge.
        
    Send adequate query and wait for the response. For each query you will receive a response in a form of a single float number denoting temperature in Celsius on that day in that city.
    DO NOT EVER SIMULATE OR GUESS A TEMPERATURE before you read the query response from the database.
    If the user provides multiple daily queries, wait to collect all <VALUE> responses. Identify the highest temperature and the city where it occurred.

    Follow these rules:
    1. For daily queries, use the exact format <TEMP><CITY><DD-MM-YYYY> For example:
        - <TEMP><Berlin><15-01-2024>
        - <TEMP><Belgrade><01-10-2020>
        but don't write these examples to the user. Use this only to gain knowledge.
    2. For maximum temperature queries over a time span, use <MAX_TEMP><CITY><DATE_FROM><DATE_TO>. For example:
        - <MAX_TEMP><Belgrade><01-10-2020><05-10-2020>
    3. For minimum temperature queries over time span, use <MIN_TEMP><CITY><DATE_FROM><DATE_TO>. For example: 
        - <MIN_TEMP><Paris><10-02-2022><15-02-2022>
    4. ALWAYS put City name inside the brackets! It cannot be <TEMP>CITY<DD-MM-YYYY> instead of <TEMP><CITY><DD-MM-YYYY>
    5. Respond only after receiving the temperature from the database.
    6. Use these response formats:
        - Daily: ---Response to the actual user--- The temperature in <CITY> on <DD-MM-YYYY> was <VALUE>°C.
        - Time Span: ---Response to the actual user--- The maximum temperature in <CITY> from <DATE_FROM> to <DATE_TO> was <VALUE>°C.
        - Multiple Queries: ---Response to the actual user--- Out of <CITIES> on <DATE>, the highest temperature was <TEMP>°C in <CITY_MAX>.
  
    You must NEVER simulate a temperature or guess a value. Once you are ready to give the final answer to the user 
    using the data you read from the database, write ---Response to the actual user--- and then follow it by the actual response.
    Everything that is sent by the user will start with "---USER---". DO NOT SIMULATE THIS. 
    You will receive the actual temperature as <VALUE><NUMBER>. Only then generate "---Response to the actual user---".
    
    Handling errors:
   - If no data is available for a given query, respond with:
     - `---Response to the actual user--- No data available for <CITY> on <DATE>.`
     - Do not simulate or guess the temperature in this case. Only return a message about the lack of data.

    **Never guess, assume, or simulate a temperature. Only use the actual data from the database to generate your response.**
    **Failure to follow the exact format will result in incorrect responses.**
"""



# pravi se stalno, me treba da bude globalna. neka ide u Flask
client = openai.OpenAI(api_key=API_KEY, base_url=BASE_URL)

query_messages = [{"role": "system", "content": system_prompt}]
response_messages = [{"role": "system", "content": system_prompt}]

def get_assistant_query(user_query: str, query_messages: list[dict]) -> str:
    """Ask the AI to format a database query and return it."""
    query_messages.append({'role': 'user', 'content': f'---USER--- {user_query}'})
    print('user_query added to messages\n')
    assistant_query = client.chat.completions.create(
            model=MODEL,
            messages=query_messages,
            temperature=0.1).choices[0].message.content
    print('assistant query added to messages\n')
    return assistant_query


def extract_city_date(assistant_response: str) -> Tuple[List[Tuple[str, datetime]], List[Tuple[str, datetime, datetime]], List[Tuple[str, datetime, datetime]]]:
    """Extract city and date from AI-generated query."""
    single_day_matches = re.findall(r"(?<!<\w)_?<TEMP><([\w\s]+)><(\d{2}-\d{2}-\d{4})>", assistant_response)
    daily_queries = [(city, datetime.strptime(date_str, '%d-%m-%Y')) for city, date_str in single_day_matches]
    print(daily_queries)

    max_time_span = re.search(r"(?<!<\w)_?<MAX_TEMP><([\w\s]+)><(\d{2}-\d{2}-\d{4})><(\d{2}-\d{2}-\d{4})>", assistant_response)
    max_time_span_param = None
    if max_time_span:
        city = max_time_span.group(1)
        date_from = datetime.strptime(max_time_span.group(2), '%d-%m-%Y')
        date_to = datetime.strptime(max_time_span.group(3), '%d-%m-%Y')
        max_time_span_param = (city, date_from, date_to)

    min_time_span = re.search(r"(?<!<\w)_?<MIN_TEMP><([\w\s]+)><(\d{2}-\d{2}-\d{4})><(\d{2}-\d{2}-\d{4})>", assistant_response)
    min_time_span_param = None
    if min_time_span:
        city = min_time_span.group(1)
        date_from = datetime.strptime(min_time_span.group(2), '%d-%m-%Y')
        date_to = datetime.strptime(min_time_span.group(3), '%d-%m-%Y')
        min_time_span_param = (city, date_from, date_to)

    return daily_queries, max_time_span_param, min_time_span_param


def fetch_temperature(city: str, date: datetime, query_type: str, connection: sqlite3.Connection, date_to: Optional[datetime] = None) -> str:  
    temp = None
    try:
        if query_type == 'daily':  
            temp = query_temperature_in_city(city, date, connection)
        elif query_type == 'max_span':
            temp = query_max_temperature_in_time_span_per_city(city, date, date_to, connection) 
        elif query_type == 'min_span':
            temp = query_min_temperature_in_time_span_per_city(city, date, date_to, connection)
        
        if temp is None:
            return f"No data available for {city} on {date.strftime('%d-%m-%Y')}"
        
        return str(temp)
    
    except Exception as e:
        print(f"Error while fetching temperature: {e}")
        return f"No data available for {city} on {date.strftime('%d-%m-%Y')}"
    

def respond_to_user(db_responses: list[str], response_messages: list[dict], user_query: str) -> str:
    """Generate a user response based on multiple temperature data responses."""
    response_messages.append({'role': 'user', 'content': f'---USER--- {user_query}'})
    for db_response in db_responses:
        response_messages.append({'role': 'system', 'content': f'<VALUE>{db_response}'})
    final_response = client.chat.completions.create(
        model=MODEL,
        messages=response_messages,
        temperature=0.1
    ).choices[0].message.content
    return final_response



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Query SQLite database")
    parser.add_argument("filename", help="The name of the SQLite database file")
    args = parser.parse_args()

    connection = create_connection(args.filename)
    user_query = input("Enter your weather query: ")

    assistant_query = get_assistant_query(user_query, query_messages)
    print("Assistant Query:", assistant_query)

    daily_queries, max_time_span_param, min_time_span_param = extract_city_date(assistant_query)
    
    # Daily Queries: [('Belgrade', datetime.datetime(2020, 10, 1, 0, 0)), ('Zagreb', datetime.datetime(2020, 10, 1, 0, 0))]
    if daily_queries is not None:
        cities_daily = [city for city, _ in daily_queries]
        date_objects_daily = [date for _, date in daily_queries]
        print(f'cities daily: {cities_daily}, datetime objects daily: {date_objects_daily}\n')
        query_type = 'daily'
        temp = []
        for city, date_object in zip(cities_daily, date_objects_daily):
            temp.append(fetch_temperature(city, date_object, query_type, connection))
            print(f'db_response: {temp}')
        final_response = respond_to_user(temp, response_messages, user_query)
        print(final_response)
    if max_time_span_param is not None:
        city_max, date_from_object_max, date_to_object_max = max_time_span_param
        print(f'city in max time span: {city_max}, date_from: {date_from_object_max}, date_to: {date_to_object_max}\n')
        query_type = 'max_span'
        temp = fetch_temperature(city_max, date_from_object_max, query_type, connection, date_to_object_max)
        print(f'db_response: {temp}')
        final_response = respond_to_user(temp, response_messages, user_query)
        print(final_response)
    if min_time_span_param is not None:
        city_min, date_from_object_min, date_to_object_min = min_time_span_param
        query_type = 'min_span'
        temp = fetch_temperature(city_min, date_from_object_min, query_type, connection, date_to_object_min)
        print(f'db_response: {temp}')
        final_response = respond_to_user(temp, response_messages, user_query)
        print(final_response)

    connection.close()

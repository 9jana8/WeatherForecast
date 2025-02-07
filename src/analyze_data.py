import pandas as pd
import matplotlib.pyplot as plt
import pprint
import seaborn as sns
from data_utils import load_data


# TODO(jana): Don't hardcode input file path, use argparser

if __name__ == '__main__':
    filepath = r'..\daily_weather_data.csv'

    # Load the data
    df = load_data(filepath)

    # Pretty print the data
    pp = pprint.PrettyPrinter(indent=4)

    unique_cities = df['city'].unique().tolist()
    print('Available cities in the dataset:')
    for city in unique_cities:
        print(f'- {city}')

    city_counts = df['city'].value_counts().to_dict()
    pp.pprint(f'Number of records per city: {city_counts}') 

    num_unique_cities = df['city'].nunique()
    pp.pprint(f'Number of unique cities: {num_unique_cities}')

    # Visualize the data
    # Example: Plot temperature trends for a specific city
    city_name = 'Belgrade'
    city_data = df[df['city'] == city_name]

    plt.figure(figsize=(12, 6))
    sns.lineplot(x=city_data['date'], y=city_data['tavg'], label=city_name)
    plt.xticks(rotation=45)
    plt.title(f'Temperature Trends in {city_name}')
    plt.xlabel('Date')
    plt.ylabel('Temperature (°C)')
    plt.legend()
    plt.show()

    plt.figure(figsize=(12, 6))
    sns.scatterplot(x=city_data['date'], y=city_data['tavg'], label=city_name, color='red')
    plt.xticks(rotation=45)
    plt.title(f'Temperature Trends in {city_name}')
    plt.xlabel('Date')
    plt.ylabel('Temperature (°C)')
    plt.legend()
    plt.show()

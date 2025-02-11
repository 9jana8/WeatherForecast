import pandas as pd
import matplotlib.pyplot as plt
import pprint
import seaborn as sns
from data_utils import load_data
import argparse


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Analyze .csv file")
    parser.add_argument("filename", help="The name of the file to process")
    args = parser.parse_args()

    df = load_data(args.filename)

    pp = pprint.PrettyPrinter(indent=4)

    unique_cities = df['city'].unique().tolist()
    print('Available cities in the dataset:')
    for city in unique_cities:
        print(f'- {city}')

    city_counts = df['city'].value_counts().to_dict()
    pp.pprint(f'Number of records per city: {city_counts}') 

    num_unique_cities = df['city'].nunique()
    pp.pprint(f'Number of unique cities: {num_unique_cities}')

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

import pandas as pd
import matplotlib.pyplot as plt
import pprint
import seaborn as sns

# load the data
df = pd.read_csv(r'..\daily_weather_data.csv')

# Pretty print the data
pp = pprint.PrettyPrinter(indent=4)

unique_cities = df["city"].unique().tolist()
print("Available cities in the dataset:")
for city in unique_cities:
    print(f"- {city}")

city_counts = df["city"].value_counts().to_dict()
pp.pprint(f"Number of records per city: {city_counts}") 

num_unique_cities = df["city"].nunique()
pp.pprint(f"Number of unique cities: {num_unique_cities}")

# Filling all tavg, tmin, tmax, wdir, wspd, pres missing values with 0 for now
df.fillna(0, inplace=True)
#consider forward filling missing values, it will fill missing values with the most recent valid (non-null) value from the previous row.
# df.fillna(method="ffill", inplace=True)  # Forward fill missing values

# improve data type: date is currently an object (string). it should be converted to datetime.
df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", dayfirst=True)
print(df["date"].dtype)

# Visualize the data
# Example: Plot temperature trends for a specific city
city_name = "Belgrade"
city_data = df[df["city"] == city_name]

plt.figure(figsize=(12, 6))
sns.lineplot(x=city_data["date"], y=city_data["tavg"], label=city_name)
plt.xticks(rotation=45)
plt.title(f"Temperature Trends in {city_name}")
plt.xlabel("Date")
plt.ylabel("Temperature (°C)")
plt.legend()
plt.show()

plt.figure(figsize=(12, 6))
sns.scatterplot(x=city_data["date"], y=city_data["tavg"], label=city_name, color="red")
plt.xticks(rotation=45)
plt.title(f"Temperature Trends in {city_name}")
plt.xlabel("Date")
plt.ylabel("Temperature (°C)")
plt.legend()
plt.show()

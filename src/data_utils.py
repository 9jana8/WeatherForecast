import pandas as pd

def load_data(filepath: str):
    assert filepath.endswith('.csv'), 'Only CSV files are supported'

    df = pd.read_csv(filepath)

    df.fillna(0, inplace=True)

    #consider forward filling missing values, it will fill missing values with the most recent valid (non-null) value from the previous row.
    # df.fillna(method="ffill", inplace=True)  # Forward fill missing values

    # improve data type: date is currently an object (string). it should be converted to datetime.
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", dayfirst=True)

    return df
import requests
import pandas as pd
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from flask import Flask, render_template
#import joblib  # To save model if needed

# -------- CONFIGURATION --------
API_KEY = ''  # Replace with your own paid API key
CITIES = [
    {"name": "Bowie", "lat": 38.9577, "lon": -76.7460},
    {"name": "Baltimore", "lat": 39.2904, "lon": -76.6122},
    {"name": "Annapolis", "lat": 38.9784, "lon": -76.4922}
]
DAYS = 5  # OpenWeatherMap 3.0 allows max 5 days back

app = Flask(__name__)

# -------- STEP 1: FETCH HISTORICAL WEATHER --------
def fetch_historical_data(city, days=5):
    records = []
    base_url = "https://api.openweathermap.org/data/3.0/onecall/timemachine"

    for i in range(1, days + 1):
        dt = datetime.utcnow() - timedelta(days=i)
        timestamp = int(dt.replace(hour=16, minute=0, second=0).timestamp())

        params = {
            "lat": city['lat'],
            "lon": city['lon'],
            "dt": timestamp,
            "appid": API_KEY,
            "units": "imperial"
        }

        response = requests.get(base_url, params=params)
        print(f"\n📡 Requesting {city['name']} for {dt.date()} → {response.url}")

        if response.status_code == 200:
            data = response.json()
            data_points = data.get('data', [])

            if not data_points:
                print(f"⚠️ No 'data' returned for {city['name']} on {dt.date()}")
                continue

            print(f"✅ Retrieved {len(data_points)} entry for {city['name']} on {dt.date()}")
            for hour in data_points:
                records.append({
                    'city': city['name'],
                    'datetime': datetime.fromtimestamp(hour['dt']),
                    'temp': hour['temp'],
                    'humidity': hour['humidity'],
                    'pressure': hour['pressure'],
                    'wind': hour.get('wind_speed', 0),
                    'clouds': hour.get('clouds', 0)
                })
        else:
            print(f"❌ Error {response.status_code} for {city['name']} on {dt.date()}: {response.text}")

    return pd.DataFrame(records)

# -------- STEP 2: COMBINE DATA FOR ALL CITIES --------
def get_combined_data(cities, days=5):
    all_data = pd.DataFrame()
    for city in cities:
        df = fetch_historical_data(city, days)
        print(f"📊 {city['name']}: {len(df)} records collected.")
        all_data = pd.concat([all_data, df], ignore_index=True)
    return all_data

# -------- STEP 3: TRAIN MODEL --------
def train_model(df):
    features = ['humidity', 'pressure', 'wind', 'clouds']
    target = 'temp'

    X = df[features]
    y = df[target]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = LinearRegression()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print("\n📈 Model Evaluation:")
    print(f"→ Mean Squared Error: {mse:.2f}")
    print(f"→ R² Score: {r2:.2f}")

    return model, mse, r2

# -------- STEP 4: PREDICT FUTURE TEMPERATURE --------
def predict_temperature(model, humidity, pressure, wind, clouds):
    input_features = [[humidity, pressure, wind, clouds]]
    prediction = model.predict(input_features)
    return prediction[0]

# -------- STEP 5: Prepare data for the Flask app --------
@app.route('/')
def index():
    df = get_combined_data(CITIES, DAYS)

    if not df.empty:
        model, mse, r2 = train_model(df)

        # Example predictions
        predictions = [
            f"Predicted Temp (Humidity=60%, Pressure=1012 hPa, Wind=8 mph, Clouds=25%): {predict_temperature(model, 60, 1012, 8, 25):.2f}°F",
            f"Predicted Temp (Humidity=85%, Pressure=1008 hPa, Wind=15 mph, Clouds=75%): {predict_temperature(model, 85, 1008, 15, 75):.2f}°F"
        ]

        # Prepare data for chart
        df_sorted = df.sort_values("datetime")
        chart_data = {}

        for city in df_sorted["city"].unique():
            city_df = df_sorted[df_sorted["city"] == city]
            chart_data[city] = [
                {"x": row["datetime"].isoformat(), "y": row["temp"]}
                for _, row in city_df.iterrows()
            ]

        return render_template(
            'index13.html',
            r2=r2,
            mse=mse,
            predictions=predictions,
            data=df.tail(100).to_dict(orient='records'),
            chart_data=chart_data
        )
    else:
        return render_template('index13.html', error="No data collected. Check API key, timestamps, or network connection.")

if __name__ == '__main__':
    app.run(debug=True)

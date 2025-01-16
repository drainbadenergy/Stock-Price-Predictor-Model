import pandas as pd
import yfinance as yf
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score

itc_stocks = yf.Ticker("ITC.NS")
itc_stocks = itc_stocks.history(period="max")

# Clean up data
del itc_stocks["Dividends"]
del itc_stocks["Stock Splits"]

# Shift close prices to get the "next day's close" in the Tomorrow column
itc_stocks["Tomorrow"] = itc_stocks["Close"].shift(-1)
itc_stocks["Target"] = (itc_stocks["Tomorrow"] > itc_stocks["Close"].astype(int))

# Define the model
model = RandomForestClassifier(n_estimators=500, min_samples_split=3, random_state=1)
predictors = ["Close", "Volume", "Open", "High", "Low"]

def predict(train, test, predictors, model):
    model.fit(train[predictors], train["Target"])
    preds = model.predict_proba(test[predictors])[:, 1]
    preds[preds >= 0.7] = 1
    preds[preds < 0.7] = 0
    preds = pd.Series(preds, index=test.index, name="Predictions")
    combined = pd.concat([test["Target"], preds], axis=1)
    return combined

def backtest(data, model, predictors, start=2500, step=250):
    all_predictions = []

    for i in range(start, len(data), step):
        train = data.iloc[0:i].copy()
        test = data.iloc[i:(i + step)].copy()
        predictions = predict(train, test, predictors, model)
        all_predictions.append(predictions)
    return pd.concat(all_predictions)

horizons = [2, 5, 60, 250, 1000]
new_predictors = []

for horizon in horizons:
    rolling_averages = itc_stocks.rolling(horizon).mean()
    ratio_column = f"Close_Ratio_{horizon}"
    itc_stocks[ratio_column] = itc_stocks["Close"] / rolling_averages["Close"]

    trend_column = f"Trend_{horizon}"
    itc_stocks[trend_column] = itc_stocks.shift(1).rolling(horizon).sum()["Target"]

    new_predictors += [ratio_column, trend_column]

itc_stocks = itc_stocks.dropna()
predictions = backtest(itc_stocks, model, predictors)

# Print precision score and value counts
print(precision_score(predictions["Target"], predictions["Predictions"]))
print(predictions["Predictions"].value_counts())

# New output: whether stock price will go up and the predicted price
last_price = itc_stocks["Close"].iloc[-1]
predicted_movement = "up" if predictions["Predictions"].iloc[-1] == 1 else "down"
predicted_price = itc_stocks["Tomorrow"].iloc[-1]  # Predicted next day's price

print(f"Predicted stock movement: {predicted_movement}")
print(f"Predicted price for next day: {predicted_price}")


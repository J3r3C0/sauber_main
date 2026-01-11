
import pandas as pd
from prophet import Prophet

def predict_prophet(df, periods=12):
    df_prophet = df.copy()
    df_prophet.columns = ["ds", "y"]
    model = Prophet()
    model.fit(df_prophet)
    future = model.make_future_dataframe(periods=periods, freq="H")
    forecast = model.predict(future)

    trend_direction = (
        "BUY" if forecast["yhat"].iloc[-1] > forecast["yhat"].iloc[-periods] else "SELL"
    )

    return {
        "trend": trend_direction,
        "yhat_now": forecast["yhat"].iloc[-periods],
        "yhat_future": forecast["yhat"].iloc[-1]
    }

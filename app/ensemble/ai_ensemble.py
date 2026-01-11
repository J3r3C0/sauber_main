
import pandas as pd
import os
from ai_ensemble.prophet_model import predict_prophet
from ai_ensemble.xgboost_model import predict_xgb
from ai_ensemble.lightgbm_model import predict_lgb
from feature_generator import generate_features

def run_ensemble_analysis(symbol, df):
    df = generate_features(df)
    last_row = df.iloc[[-1]]

    xgb_signal = predict_xgb("models/xgb_model.json", last_row)[0]
    entry = predict_lgb("models/lgb_entry.txt", last_row)[0]
    sl = predict_lgb("models/lgb_sl.txt", last_row)[0]
    tp = predict_lgb("models/lgb_tp.txt", last_row)[0]

    prophet_data = predict_prophet(df[["ds", "y"]])
    trend = prophet_data.get("trend", "BUY")

    gpt_input = {
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "trend": trend
    }

    return {
        "xgb_signal": "BUY" if xgb_signal == 1 else "SELL",
        "prophet": prophet_data,
        "final": gpt_input,
        "gpt": f"Trend laut Prophet: {trend}, Entry: {entry}, SL: {sl}, TP: {tp}"
    }


import lightgbm as lgb
import numpy as np
import pandas as pd
import os

def train_lgb_model(X, y, save_path="models/lgb_model.txt"):
    model = lgb.LGBMRegressor()
    model.fit(X, y)
    os.makedirs("models", exist_ok=True)
    model.booster_.save_model(save_path)

def predict_lgb(model_path, X):
    model = lgb.Booster(model_file=model_path)
    preds = model.predict(X)
    return preds

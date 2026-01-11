
import xgboost as xgb
import numpy as np
import pandas as pd
import os

def train_xgb_model(X, y, save_path="models/xgb_model.json"):
    model = xgb.XGBClassifier(use_label_encoder=False, eval_metric='logloss')
    model.fit(X, y)
    os.makedirs("models", exist_ok=True)
    model.save_model(save_path)

def predict_xgb(model_path, X):
    model = xgb.XGBClassifier()
    model.load_model(model_path)
    return model.predict(X)

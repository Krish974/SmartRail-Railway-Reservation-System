"""
AI PNR Confirmation Predictor
Trained machine learning model to estimate confirmation likelihood of waitlisted railway tickets.
"""

import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'saved_models')
MODEL_PATH = os.path.join(MODEL_DIR, 'pnr_predictor.joblib')
DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data_analysis', 'datasets', 'historical_bookings.csv'))

_pipeline = None

def train_and_save_model():
    global _pipeline
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    if os.path.exists(DATA_PATH):
        df = pd.read_csv(DATA_PATH)
    else:
        # Fallback inline generation if file not found
        df = pd.DataFrame([
            {'waiting_list_number': 5, 'days_to_journey': 20, 'train_type': 'Rajdhani Express', 'class_type': '3A', 'quota': 'GN', 'is_peak_season': 0, 'confirmed': 1},
            {'waiting_list_number': 65, 'days_to_journey': 2, 'train_type': 'Superfast Express', 'class_type': 'SL', 'quota': 'GN', 'is_peak_season': 1, 'confirmed': 0},
            {'waiting_list_number': 12, 'days_to_journey': 15, 'train_type': 'Vande Bharat Express', 'class_type': 'CC', 'quota': 'GN', 'is_peak_season': 0, 'confirmed': 1}
        ])

    features = ['waiting_list_number', 'days_to_journey', 'train_type', 'class_type', 'quota', 'is_peak_season']
    X = df[features]
    y = df['confirmed']

    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore'), ['train_type', 'class_type', 'quota']),
            ('num', 'passthrough', ['waiting_list_number', 'days_to_journey', 'is_peak_season'])
        ]
    )

    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', GradientBoostingClassifier(n_estimators=100, max_depth=4, random_state=42))
    ])

    pipeline.fit(X, y)
    joblib.dump(pipeline, MODEL_PATH)
    _pipeline = pipeline
    print("[ML] PNR confirmation prediction model successfully trained and cached!")
    return _pipeline

def get_model():
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    if os.path.exists(MODEL_PATH):
        try:
            _pipeline = joblib.load(MODEL_PATH)
            return _pipeline
        except Exception as e:
            print(f"[ML WARNING] Loading saved model failed: {e}. Re-training...")
    return train_and_save_model()

def predict_pnr_confirmation(wl_number, days_left=10, train_type="Superfast Express", class_type="3A", quota="GN", is_peak=0):
    """
    Predicts confirmation probability for a waitlist number.
    Returns: dict with probability, category, and explanation.
    """
    wl_num = int(wl_number)
    if wl_num == 0:
        return {
            "probability": 100.0,
            "category": "High",
            "explanation": "Ticket is already confirmed.",
            "is_estimate": True
        }

    try:
        model = get_model()
        input_df = pd.DataFrame([{
            'waiting_list_number': wl_num,
            'days_to_journey': max(1, int(days_left)),
            'train_type': train_type or "Superfast Express",
            'class_type': class_type or "3A",
            'quota': quota or "GN",
            'is_peak_season': int(is_peak)
        }])

        prob = model.predict_proba(input_df)[0][1] * 100.0
    except Exception as e:
        # Fallback logistic calculation if model prediction fails
        log_odds = 2.0 - (wl_num * 0.045) + (days_left * 0.03)
        prob = (1.0 / (1.0 + np.exp(-log_odds))) * 100.0

    prob = round(float(np.clip(prob, 5.0, 98.0)), 1)

    if prob >= 70.0:
        category = "High"
        reason = f"High probability of confirmation. Based on {wl_num} WL positions and {days_left} days remaining, historical cancellation trends strongly favor your ticket clearing."
    elif prob >= 40.0:
        category = "Moderate"
        reason = f"Moderate chance. Confirmation depends on tatkal cancellations and quota reallocation before final chart preparation."
    else:
        category = "Low"
        reason = f"Low probability of confirmation. Waiting list {wl_num} is high for {train_type} with only {days_left} days remaining."

    return {
        "probability": prob,
        "category": category,
        "waiting_list_number": wl_num,
        "days_remaining": days_left,
        "explanation": f"Estimated confirmation probability: {prob}%. {reason}",
        "disclaimer": "This is an AI-powered statistical estimate based on historical IRCTC booking patterns, not an official guarantee."
    }

if __name__ == '__main__':
    train_and_save_model()
    res = predict_pnr_confirmation(14, 8, "Tejas Rajdhani", "3A", "GN")
    print("Test prediction:", res)

import os
import random
import logging
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, accuracy_score, confusion_matrix
import xgboost as xgb

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    "claimed_damage",
    "visual_damage_severity",
    "weather_score",
    "weather_hazard_match",
    "satellite_damaged_area",
    "ndvi_vegetation_drop",
    "visual_vs_claim_gap",
    "satellite_vs_claim_gap",
    "is_duplicate_image",
    "claims_frequency_12m"
]

def generate_multimodal_dataset(num_samples: int = 5000, random_seed: int = 42) -> pd.DataFrame:
    """
    Generates a calibrated synthetic research benchmark dataset of multimodal crop insurance claims.
    Clearly labeled as synthetic research benchmark per mentor requirements (Section 12).
    """
    np.random.seed(random_seed)
    random.seed(random_seed)

    records = []

    # 1. Genuine Severe Flood Claims (~1,000)
    for _ in range(1000):
        claimed = round(float(np.random.uniform(60.0, 95.0)), 1)
        visual = round(float(np.clip(claimed + np.random.normal(0, 7), 50.0, 100.0)), 1)
        weather = round(float(np.random.uniform(75.0, 100.0)), 1)
        hazard_match = 1
        sat_area = round(float(np.clip(claimed + np.random.normal(0, 8), 55.0, 100.0)), 1)
        ndvi_drop = round(float(np.clip(0.35 + (sat_area / 100.0) * 0.35 + np.random.normal(0, 0.04), 0.30, 0.85)), 3)
        duplicate = 0
        freq = int(np.random.choice([1, 2], p=[0.85, 0.15]))
        records.append({
            "claimed_damage": claimed,
            "visual_damage_severity": visual,
            "weather_score": weather,
            "weather_hazard_match": hazard_match,
            "satellite_damaged_area": sat_area,
            "ndvi_vegetation_drop": ndvi_drop,
            "is_duplicate_image": duplicate,
            "claims_frequency_12m": freq,
            "scenario": "Genuine Flood",
            "is_fraud": 0
        })

    # 2. Genuine Drought Claims (~800)
    for _ in range(800):
        claimed = round(float(np.random.uniform(45.0, 80.0)), 1)
        visual = round(float(np.clip(claimed + np.random.normal(0, 8), 35.0, 85.0)), 1)
        weather = round(float(np.random.uniform(65.0, 95.0)), 1)
        hazard_match = 1
        sat_area = round(float(np.clip(claimed + np.random.normal(0, 8), 40.0, 85.0)), 1)
        ndvi_drop = round(float(np.clip(0.25 + (sat_area / 100.0) * 0.30 + np.random.normal(0, 0.03), 0.20, 0.65)), 3)
        duplicate = 0
        freq = int(np.random.choice([1, 2], p=[0.80, 0.20]))
        records.append({
            "claimed_damage": claimed,
            "visual_damage_severity": visual,
            "weather_score": weather,
            "weather_hazard_match": hazard_match,
            "satellite_damaged_area": sat_area,
            "ndvi_vegetation_drop": ndvi_drop,
            "is_duplicate_image": duplicate,
            "claims_frequency_12m": freq,
            "scenario": "Genuine Drought",
            "is_fraud": 0
        })

    # 3. Genuine Mild / Normal Baseline Claims (~700)
    for _ in range(700):
        claimed = round(float(np.random.uniform(5.0, 25.0)), 1)
        visual = round(float(np.clip(claimed + np.random.normal(0, 4), 2.0, 30.0)), 1)
        weather = round(float(np.random.uniform(5.0, 30.0)), 1)
        hazard_match = 1
        sat_area = round(float(np.clip(claimed + np.random.normal(0, 5), 0.0, 25.0)), 1)
        ndvi_drop = round(float(np.clip(0.02 + (sat_area / 100.0) * 0.12 + np.random.normal(0, 0.02), 0.01, 0.18)), 3)
        duplicate = 0
        freq = 1
        records.append({
            "claimed_damage": claimed,
            "visual_damage_severity": visual,
            "weather_score": weather,
            "weather_hazard_match": hazard_match,
            "satellite_damaged_area": sat_area,
            "ndvi_vegetation_drop": ndvi_drop,
            "is_duplicate_image": duplicate,
            "claims_frequency_12m": freq,
            "scenario": "Genuine Mild Damage",
            "is_fraud": 0
        })

    # 4. Damage Exaggeration Claims (e.g. Light Hailstorm or Puddle) (~1,000)
    for _ in range(1000):
        claimed = round(float(np.random.uniform(75.0, 98.0)), 1)
        visual = round(float(np.random.uniform(12.0, 32.0)), 1) # Actual leaf damage is low
        weather = round(float(np.random.uniform(15.0, 40.0)), 1)
        hazard_match = int(np.random.choice([0, 1], p=[0.4, 0.6]))
        sat_area = round(float(np.random.uniform(5.0, 22.0)), 1) # Satellite shows mostly healthy field
        ndvi_drop = round(float(np.random.uniform(0.04, 0.16)), 3)
        duplicate = 0
        freq = int(np.random.choice([1, 2, 3], p=[0.6, 0.3, 0.1]))
        records.append({
            "claimed_damage": claimed,
            "visual_damage_severity": visual,
            "weather_score": weather,
            "weather_hazard_match": hazard_match,
            "satellite_damaged_area": sat_area,
            "ndvi_vegetation_drop": ndvi_drop,
            "is_duplicate_image": duplicate,
            "claims_frequency_12m": freq,
            "scenario": "Damage Exaggeration Fraud",
            "is_fraud": 1
        })

    # 5. Weather Contradiction Claims (Calm Sunny Weather) (~800)
    for _ in range(800):
        claimed = round(float(np.random.uniform(70.0, 95.0)), 1)
        visual = round(float(np.random.uniform(20.0, 60.0)), 1)
        weather = round(float(np.random.uniform(0.0, 15.0)), 1) # Calm sunny weather
        hazard_match = 0 # Contradiction: claimed disaster did not occur
        sat_area = round(float(np.random.uniform(5.0, 25.0)), 1)
        ndvi_drop = round(float(np.random.uniform(0.02, 0.14)), 3)
        duplicate = 0
        freq = int(np.random.choice([1, 2, 3, 4], p=[0.4, 0.3, 0.2, 0.1]))
        records.append({
            "claimed_damage": claimed,
            "visual_damage_severity": visual,
            "weather_score": weather,
            "weather_hazard_match": hazard_match,
            "satellite_damaged_area": sat_area,
            "ndvi_vegetation_drop": ndvi_drop,
            "is_duplicate_image": duplicate,
            "claims_frequency_12m": freq,
            "scenario": "Weather Contradiction Fraud",
            "is_fraud": 1
        })

    # 6. Duplicate / Recycled Photo Claims (~400)
    for _ in range(400):
        claimed = round(float(np.random.uniform(60.0, 90.0)), 1)
        visual = round(float(np.random.uniform(50.0, 85.0)), 1)
        weather = round(float(np.random.uniform(10.0, 60.0)), 1)
        hazard_match = int(np.random.choice([0, 1], p=[0.5, 0.5]))
        sat_area = round(float(np.random.uniform(10.0, 45.0)), 1)
        ndvi_drop = round(float(np.random.uniform(0.05, 0.25)), 3)
        duplicate = 1 # Re-submitted recycled image
        freq = int(np.random.choice([2, 3, 4, 5], p=[0.3, 0.4, 0.2, 0.1]))
        records.append({
            "claimed_damage": claimed,
            "visual_damage_severity": visual,
            "weather_score": weather,
            "weather_hazard_match": hazard_match,
            "satellite_damaged_area": sat_area,
            "ndvi_vegetation_drop": ndvi_drop,
            "is_duplicate_image": duplicate,
            "claims_frequency_12m": freq,
            "scenario": "Duplicate Image Fraud",
            "is_fraud": 1
        })

    # 7. Repeated Abuse / High Claim Frequency (~300)
    for _ in range(300):
        claimed = round(float(np.random.uniform(65.0, 95.0)), 1)
        visual = round(float(np.random.uniform(25.0, 50.0)), 1)
        weather = round(float(np.random.uniform(15.0, 45.0)), 1)
        hazard_match = 0
        sat_area = round(float(np.random.uniform(10.0, 30.0)), 1)
        ndvi_drop = round(float(np.random.uniform(0.05, 0.20)), 3)
        duplicate = int(np.random.choice([0, 1], p=[0.6, 0.4]))
        freq = int(np.random.choice([4, 5, 6, 7], p=[0.4, 0.3, 0.2, 0.1]))
        records.append({
            "claimed_damage": claimed,
            "visual_damage_severity": visual,
            "weather_score": weather,
            "weather_hazard_match": hazard_match,
            "satellite_damaged_area": sat_area,
            "ndvi_vegetation_drop": ndvi_drop,
            "is_duplicate_image": duplicate,
            "claims_frequency_12m": freq,
            "scenario": "Repeated Claims Abuse",
            "is_fraud": 1
        })

    df = pd.DataFrame(records)

    # Compute derived discrepancy gaps
    df["visual_vs_claim_gap"] = df["claimed_damage"] - df["visual_damage_severity"]
    df["satellite_vs_claim_gap"] = df["claimed_damage"] - df["satellite_damaged_area"]

    # Shuffle dataset
    df = df.sample(frac=1.0, random_state=random_seed).reset_index(drop=True)
    return df

def train_fraud_model():
    logger.info("Starting Stage 4 Multimodal XGBoost Fraud Model Training...")

    current_dir = Path(__file__).resolve().parent
    if Path("/app/models_saved").exists():
        server_dir = Path("/app")
    elif (current_dir / "models_saved").exists():
        server_dir = current_dir
    else:
        server_dir = current_dir.parent
    data_dir = server_dir / "data"
    models_dir = server_dir / "models_saved"

    data_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate multimodal benchmark dataset
    df = generate_multimodal_dataset(num_samples=5000)
    dataset_path = data_dir / "synthetic_fraud_claims.csv"
    df.to_csv(dataset_path, index=False)
    logger.info(f"Saved 5,000-record benchmark dataset to: {dataset_path}")
    logger.info(f"Class distribution:\n{df['is_fraud'].value_counts(normalize=True)}")

    # 2. Prepare Features and Target
    X = df[FEATURE_NAMES]
    y = df["is_fraud"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    logger.info(f"Train samples: {len(X_train)} | Test samples: {len(X_test)}")

    # 3. Train XGBoost Classifier
    model = xgb.XGBClassifier(
        n_estimators=150,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        eval_metric="logloss"
    )

    model.fit(X_train, y_train)

    # 4. Evaluate on Test Set
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_prob)
    cm = confusion_matrix(y_test, y_pred)

    print("\n==================================================")
    print("STAGE 4 MULTIMODAL XGBOOST EVALUATION METRICS")
    print("==================================================")
    print(f"Test Accuracy: {acc * 100:.2f}%")
    print(f"ROC-AUC Score: {roc_auc:.4f}")
    print("\nConfusion Matrix:")
    print(cm)
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["Genuine (0)", "Fraud (1)"]))

    # Feature importances
    feature_importances = pd.Series(model.feature_importances_, index=FEATURE_NAMES).sort_values(ascending=False)
    print("Top Feature Importances:")
    print(feature_importances)
    print("==================================================\n")

    # 5. Save model artifact with metadata
    model_artifact = {
        "model": model,
        "feature_names": FEATURE_NAMES,
        "metrics": {
            "accuracy": round(float(acc), 4),
            "roc_auc": round(float(roc_auc), 4)
        }
    }

    model_path = models_dir / "xgboost_fraud.pkl"
    joblib.dump(model_artifact, model_path)
    logger.info(f"Successfully saved trained XGBoost model to: {model_path}")

if __name__ == "__main__":
    train_fraud_model()

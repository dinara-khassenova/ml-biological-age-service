from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score


# ================== PATHS ==================

DATA_PATH = Path("data/processed/train_processed.csv")

ARTIFACTS_DIR = Path("app/ml/artifacts")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = ARTIFACTS_DIR / "bioage_ridge_model.joblib"
META_PATH = ARTIFACTS_DIR / "bioage_ridge_model_meta.json"


# ================== CONFIG ==================

TARGET = "Age (years)"

FEATURES = [
    "Height (cm)",
    "Weight (kg)",
    "BMI",
    "Cholesterol Level (mg/dL)",
    "Blood Glucose Level (mg/dL)",
    "Stress Levels",
    "Vision Sharpness",
    "Hearing Ability (dB)",
    "Bone Density (g/cm²)",
    "BP_Systolic",
    "BP_Diastolic",
]


# ================== TRAIN ==================

def main(test_size: float = 0.2, random_state: int = 42):
    print("Loading processed dataset:", DATA_PATH)

    df = pd.read_csv(DATA_PATH)

    # --- валидация структуры ---
    missing = [c for c in FEATURES + [TARGET] if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in processed dataset: {missing}")

    X = df[FEATURES]
    y = df[TARGET]

    # --- train / validation split ---
    X_train, X_val, y_train, y_val = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
    )

    # --- pipeline ---
    model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=1.0)),
        ]
    )

    print("Training model...")
    model.fit(X_train, y_train)

    # --- validation ---
    preds = model.predict(X_val)

    mae = mean_absolute_error(y_val, preds)
    r2 = r2_score(y_val, preds)

    print(f"Validation MAE: {mae:.2f}")
    print(f"Validation R2 : {r2:.3f}")

    # --- save model ---
    joblib.dump(model, MODEL_PATH)

    # --- extract coefficients ---
    ridge = model.named_steps["ridge"]

    coefficients = {
        feature: float(coef)
        for feature, coef in zip(FEATURES, ridge.coef_)
    }

    # --- save metadata ---
    meta = {
        "model_type": "Ridge Regression",
        "target": TARGET,
        "features": FEATURES,
        "metrics": {
            "mae": float(mae),
            "r2": float(r2),
        },
        "coefficients": coefficients,
        "notes": (
            "Numeric-only model trained on processed dataset. "
            "Blood pressure split into systolic/diastolic. "
            "Coefficients are global and used for per-request interpretation."
        ),
    }

    META_PATH.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("Saved artifacts:")
    print(" -", MODEL_PATH)
    print(" -", META_PATH)


if __name__ == "__main__":
    main()

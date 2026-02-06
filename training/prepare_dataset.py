from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd


# ================== PATHS ==================

RAW_DIR = Path("data/raw")
OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)

TRAIN_RAW = RAW_DIR / "train.csv"
TRAIN_OUT = OUT_DIR / "train_processed.csv"


# ================== CONFIG ==================

TARGET = "Age (years)"
BP_COL = "Blood Pressure (s/d)"

# Кандидаты на числовые фичи (берём только реально числовые)
CANDIDATE_FEATURES = [
    "Height (cm)",
    "Weight (kg)",
    "BMI",
    "Cholesterol Level (mg/dL)",
    "Blood Glucose Level (mg/dL)",
    "Stress Levels",
    "Vision Sharpness",
    "Hearing Ability (dB)",
    "Bone Density (g/cm²)",  
]


_BP_RE = re.compile(r"^\s*(\d{2,3})\s*/\s*(\d{2,3})\s*$")


# ================== HELPERS ==================

def split_blood_pressure(series: pd.Series):
    """
    Парсит '120/80' → (120, 80).
    Всё, что не парсится, становится NaN.
    """
    systolic, diastolic = [], []

    for v in series:
        if pd.isna(v):
            systolic.append(np.nan)
            diastolic.append(np.nan)
            continue

        m = _BP_RE.match(str(v))
        if not m:
            systolic.append(np.nan)
            diastolic.append(np.nan)
        else:
            systolic.append(float(m.group(1)))
            diastolic.append(float(m.group(2)))

    return systolic, diastolic


# ================== PREPARE ==================

def prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # --- обязательные колонки ---
    if TARGET not in df.columns:
        raise ValueError(f"Target column '{TARGET}' not found in train.csv")

    if BP_COL not in df.columns:
        raise ValueError(f"Blood pressure column '{BP_COL}' not found in train.csv")

    # --- давление → 2 числовых фичи ---
    df["BP_Systolic"], df["BP_Diastolic"] = split_blood_pressure(df[BP_COL])

    print("=== Feature availability check ===")

    numeric_features: list[str] = []

    for col in CANDIDATE_FEATURES:
        if col not in df.columns:
            print(f"{col}: column missing")
            continue

        # пробуем привести к числу
        numeric_col = pd.to_numeric(df[col], errors="coerce")
        valid_count = int(numeric_col.notna().sum())

        print(f"{col}: {valid_count}")

        # оставляем ТОЛЬКО реально числовые колонки
        if valid_count > 0:
            df[col] = numeric_col
            numeric_features.append(col)

    print("\nUsing numeric features:")
    for col in numeric_features:
        print(" -", col)

    # --- финальный список колонок ---
    final_columns = (
        numeric_features
        + ["BP_Systolic", "BP_Diastolic"]
        + [TARGET]
    )

    out = df[final_columns].copy()

    # --- медианное заполнение ---
    medians = out.median(numeric_only=True)
    out = out.fillna(medians)

    # --- дефолты для давления (если всё было битое) ---
    out["BP_Systolic"] = out["BP_Systolic"].fillna(120.0)
    out["BP_Diastolic"] = out["BP_Diastolic"].fillna(80.0)

    # --- финальный контроль ---
    if out.isna().any().any():
        raise RuntimeError(
            "NaN values still present after filling:\n"
            f"{out.isna().sum()}"
        )

    return out


# ================== MAIN ==================

def main():
    print("Loading raw dataset:", TRAIN_RAW)

    df = pd.read_csv(TRAIN_RAW)
    processed = prepare(df)

    processed.to_csv(TRAIN_OUT, index=False)

    print("\nProcessed dataset saved to:", TRAIN_OUT)
    print("Final shape:", processed.shape)
    print("Final columns:")
    for c in processed.columns:
        print(" -", c)


if __name__ == "__main__":
    main()

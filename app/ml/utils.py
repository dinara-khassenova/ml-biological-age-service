import json
from pathlib import Path
from typing import List


def load_features_from_meta() -> List[str]:
    meta_path = Path("ml/artifacts/bioage_ridge_model_meta.json")
    if not meta_path.exists():
        raise FileNotFoundError("Model meta.json not found")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    features = meta.get("features")

    if not features or not isinstance(features, list):
        raise ValueError("Invalid or missing 'features' in model meta.json")

    return features

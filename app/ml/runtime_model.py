from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple
from pathlib import Path
import os
import json

from ml.base import Validator, Predictor
from ml.validators import BioAgeDataValidator
from ml.predictors import BioAgePredictorStub, BioAgePredictorML

from models.ml_model import MLModel
from models.validation import ValidationError
from models.assessment import AssessmentResult



ARTIFACTS_DIR = Path(
    os.getenv("ML_ARTIFACTS_DIR", "/app/ml/artifacts")
)

MODEL_FILE = ARTIFACTS_DIR / os.getenv(
    "ML_MODEL_FILE", "bioage_ridge_model.joblib"
)

META_FILE = ARTIFACTS_DIR / os.getenv(
    "ML_MODEL_META", "bioage_ridge_model_meta.json"
)

@dataclass
class RuntimeMLModel:
    """
    Runtime-обёртка над MLModel из БД.

    Источники правды:
    - UI и валидация → MLModel.feature_names (БД)
    - ML-логика → joblib + meta.json
    """

    meta: MLModel
    validator: Validator = field(init=False)
    predictor: Predictor = field(init=False)

    def __post_init__(self) -> None:
        # --- базовая проверка ---
        if not self.meta.feature_names:
            raise ValueError("MLModel.feature_names is empty")
        
        if not MODEL_FILE.exists():
            raise FileNotFoundError(
                f"ML artifact not found: {MODEL_FILE.resolve()}"
            )

        # --- проверка согласованности с meta.json (если есть) ---
        if META_FILE.exists():
            meta_json = json.loads(META_FILE.read_text(encoding="utf-8"))
            model_features = meta_json.get("features", [])

            if model_features and self.meta.feature_names != model_features:
                raise RuntimeError(
                    "Feature mismatch between DB (MLModel.feature_names) "
                    "and model meta.json"
                )

        # --- валидатор (по данным из БД) ---
        self.validator = BioAgeDataValidator(
            required_features=self.meta.feature_names
        )

        # --- predictor ---
        if MODEL_FILE.exists():
            self.predictor = BioAgePredictorML(
                model_path=str(MODEL_FILE),
                feature_names=self.meta.feature_names,
            )
        else:
            # fallback для dev / тестов
            self.predictor = BioAgePredictorStub()

    def validate(self, answers: Dict[str, Any]) -> Tuple[bool, List[ValidationError]]:
        """
        Валидация входных данных.
        """
        return self.validator.validate(answers)

    def predict(self, answers: Dict[str, Any]) -> AssessmentResult:
        """
        ML-предсказание (биологический возраст + факторы).
        """
        return self.predictor.predict(answers)


from typing import Any, Dict, List
import joblib
import pandas as pd
import numpy as np

from ml.base import Predictor
from models.assessment import AssessmentResult
from models.enum import FactorGroup


def _py(v: Any) -> Any:
    """
    Делает значение JSON-совместимым:
    - numpy scalar -> python scalar
    """
    if hasattr(v, "item") and callable(getattr(v, "item")):
        return v.item()
    return v


class BioAgePredictorStub(Predictor):
    """Fallback-заглушка (оставляем для тестов)."""

    def predict(self, answers: Dict[str, Any]) -> AssessmentResult:
        return AssessmentResult(
            biological_age=40.0,
            factors=[],
            validation_errors=[],
        )


class BioAgePredictorML(Predictor):
    """
    Реальный ML-предиктор для биологического возраста.
    """

    def __init__(self, model_path: str, feature_names: List[str]):
        self.model = joblib.load(model_path)
        self.feature_names = feature_names

        # Ожидаем pipeline: imputer -> scaler -> ridge
        self.imputer = self.model.named_steps["imputer"]
        self.scaler = self.model.named_steps["scaler"]
        self.ridge = self.model.named_steps["ridge"]

    def predict(self, answers: Dict[str, Any]) -> AssessmentResult:
        # 1) DataFrame из входных данных
        row = {f: answers.get(f) for f in self.feature_names}
        X = pd.DataFrame([row])

        # 2) Pipeline шаги
        X_imputed = self.imputer.transform(X)
        X_scaled = self.scaler.transform(X_imputed)

        # 3) Предсказание возраста
        biological_age = float(self.ridge.predict(X_scaled)[0])

        # 4) Вклад факторов
        # X_scaled: np.ndarray, coef_: np.ndarray
        contributions = X_scaled[0] * self.ridge.coef_

        factors_raw = [
            (name, _py(value), float(contrib))
            for name, value, contrib in zip(
                self.feature_names,
                X.iloc[0].values,   # <- numpy scalars (int64/float64)
                contributions,      # <- numpy float64
            )
        ]

        # 5) Топ факторов (по величине вклада)
        
        # 5) Разделяем по знаку вклада
        pos = [t for t in factors_raw if t[2] > 0]   # POSITIVE contribution -> increases age
        neg = [t for t in factors_raw if t[2] < 0]   # NEGATIVE contribution -> decreases age

        top_pos = sorted(pos, key=lambda x: x[2], reverse=True)[:3]
        top_neg = sorted(neg, key=lambda x: x[2])[:3]  # самые отрицательные

        factors = []

        for name, value, contrib in top_pos:
            factors.append(
                {
                    "name": name,
                    "value": value,
                    "group": FactorGroup.POSITIVE.value,
                    "description": f"Увеличивает биологический возраст (+{contrib:.2f})",
                }
            )

        for name, value, contrib in top_neg:
            factors.append(
                {
                    "name": name,
                    "value": value,
                    "group": FactorGroup.NEGATIVE.value,
                    "description": f"Снижает биологический возраст ({contrib:.2f})",
                }
            )


        return AssessmentResult(
            biological_age=round(biological_age, 1),
            factors=factors,
            validation_errors=[],
        )

from typing import Any, Dict
from ml.base import Predictor
from models.assessment import AssessmentResult
from models.enum import FactorGroup

class BioAgePredictorStub(Predictor):
    """Заглушка предиктора (вместо реальной ML модели)."""

    def predict(self, answers: Dict[str, Any]) -> AssessmentResult:
        age_raw = answers.get("age", 40)
        bmi_raw = answers.get("bmi", 25)
        glucose_raw = answers.get("glucose", 5.2)

        age = float(age_raw) if isinstance(age_raw, (int, float)) else 40.0
        bmi = float(bmi_raw) if isinstance(bmi_raw, (int, float)) else 25.0
        glucose = float(glucose_raw) if isinstance(glucose_raw, (int, float)) else 5.2

        factors = [
            {
                "name": "bmi",
                "value": bmi,
                "group": FactorGroup.NEUTRAL.value,  
                "description": "ИМТ - в пределах нормы",
            },
            {
                "name": "glucose",
                "value": glucose,
                "group": FactorGroup.POSITIVE.value,  
                "description": "Глюкоза - оптимальная",
            },
        ]

        biological_age = age + (bmi - 22.0) * 0.5

        return AssessmentResult(
            biological_age=round(biological_age, 1),
            factors=factors,
        )
        
class BioAgePredictorML(Predictor):
    """
    Реальный ML предиктор (пример расширения через наследование).
    В будущем здесь будет загрузка модели и предсказание.
    """

    def __init__(self, model_path: str):
        self.model_path = model_path
        # self.model = load_model(model_path)

    def predict(self, answers: Dict[str, Any]) -> AssessmentResult:
        # features = self._prepare_features(answers)
        # prediction = self.model.predict(features)
        # return ...
        return BioAgePredictorStub().predict(answers)

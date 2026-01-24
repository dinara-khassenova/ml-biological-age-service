from typing import Any, Dict
from ml.base import Predictor
from models.factor import Factor
from models.assessment import AssessmentResult

class BioAgePredictorStub(Predictor):
    """Заглушка предиктора (вместо реальной ML модели)."""

    def predict(self, answers: Dict[str, Any]) -> AssessmentResult:
        factors = [
            Factor(
                name="bmi",
                value=answers.get("bmi"),
                group="NEUTRAL",
                description="Индекс массы тела - в пределах нормы",
            ),
            Factor(
                name="glucose",
                value=answers.get("glucose"),
                group="POSITIVE",
                description="Уровень глюкозы - оптимальный",
            ),
        ]

        age = answers.get("age", 40)
        biological_age = age + (answers.get("bmi", 25) - 22) * 0.5

        return AssessmentResult(
            biological_age=round(float(biological_age), 1),
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

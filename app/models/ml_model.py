from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from ml.base import Validator, Predictor
from ml.validators import BioAgeDataValidator
from ml.predictors import BioAgePredictorStub
from models.validation import ValidationError
from models.assessment import AssessmentResult

@dataclass
class MLModel:
    """
    ML модель, доступная в сервисе.

    Attributes:
        id (int): идентификатор модели
        name (str): название модели
        price_per_task (int): стоимость одного расчёта в кредитах
        feature_names (List[str]): список признаков, ожидаемых моделью
        validator (Validator): валидатор входных данных
        predictor (Predictor): предиктор (заглушка / реальная модель)
    """
    id: int
    name: str
    feature_names: List[str]
    price_per_task: int = 25
    validator: Validator = field(default_factory=BioAgeDataValidator)
    predictor: Predictor = field(default_factory=BioAgePredictorStub)

    def __post_init__(self) -> None:
        if not self.feature_names:
            raise ValueError("feature_names не должен быть пустым")
        if self.price_per_task <= 0:
            raise ValueError("price_per_task должен быть > 0")

    def validate(self, answers: Dict[str, Any]) -> Tuple[bool, List[ValidationError]]:
        """Делегирует валидацию валидатору модели."""
        return self.validator.validate(answers)

    def predict(self, answers: Dict[str, Any]) -> AssessmentResult:
        """Делегирует предсказание предиктору модели."""
        return self.predictor.predict(answers)

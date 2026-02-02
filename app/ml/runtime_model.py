from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from ml.base import Validator, Predictor
from ml.validators import BioAgeDataValidator
from ml.predictors import BioAgePredictorStub

from models.ml_model import MLModel
from models.validation import ValidationError
from models.assessment import AssessmentResult


@dataclass
class RuntimeMLModel:
    """
    Runtime-обёртка над MLModel из БД.

    В БД лежат метаданные (MLModel).
    В коде мы добавляем поведение: validate/predict через валидатор/предиктор.
    """

    meta: MLModel
    validator: Validator = field(default_factory=BioAgeDataValidator)
    predictor: Predictor = field(default_factory=BioAgePredictorStub)

    def __post_init__(self) -> None:
        self.validator = BioAgeDataValidator(required_features=self.meta.feature_names)

    @property
    def id(self) -> int:
        if self.meta.id is None:
            raise ValueError("MLModel.id is None")
        return int(self.meta.id)

    @property
    def name(self) -> str:
        return self.meta.name

    @property
    def feature_names(self) -> List[str]:
        return self.meta.feature_names

    @property
    def price_per_task(self) -> int:
        return self.meta.price_per_task

    def validate(self, answers: Dict[str, Any]) -> Tuple[bool, List[ValidationError]]:
        return self.validator.validate(answers)

    def predict(self, answers: Dict[str, Any]) -> AssessmentResult:
        return self.predictor.predict(answers)

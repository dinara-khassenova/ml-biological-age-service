from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

from models.validation import ValidationError
from models.assessment import AssessmentResult


class Validator(ABC):
    """Абстрактный базовый класс для валидаторов данных."""

    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> Tuple[bool, List[ValidationError]]:
        """Валидация одной записи."""
        raise NotImplementedError


class Predictor(ABC):
    """Абстрактный базовый класс для предикторов (ML моделей)."""

    @abstractmethod
    def predict(self, answers: Dict[str, Any]) -> AssessmentResult:
        """Предсказание по одной анкете."""
        raise NotImplementedError

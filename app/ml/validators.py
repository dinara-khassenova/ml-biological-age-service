from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from ml.base import Validator
from models.validation import ValidationError


@dataclass
class BioAgeDataValidator(Validator):
    """
    Валидатор входных данных для расчёта биологического возраста.

    Несколько параметров для примера

    """
    required_features: Optional[List[str]] = None

    def validate(self, data: Dict[str, Any]) -> Tuple[bool, List[ValidationError]]:
        errors: List[ValidationError] = []

        required = self.required_features or ["age"]

        # Проверка required + типы 
        for field in required:
            if field not in data:
                errors.append(ValidationError(field, "Поле обязательно"))
                continue

            if not isinstance(data[field], (int, float)):
                errors.append(ValidationError(field, "Должно быть числом"))

        # Доменная логика 
        age = data.get("age")
        if age is not None and (age < 0 or age > 120):
            errors.append(
                ValidationError("age", "Возраст должен быть в диапазоне от 0 до 120")
            )

        bmi = data.get("bmi")
        if bmi is not None and (not isinstance(bmi, (int, float)) or bmi < 10 or bmi > 60):
            errors.append(
                ValidationError("bmi", "BMI должен быть в диапазоне от 10 до 60")
            )

        glucose = data.get("glucose")
        if glucose is not None and (not isinstance(glucose, (int, float)) or glucose < 0):
            errors.append(
                ValidationError("glucose", "Уровень глюкозы должен быть неотрицательным числом")
            )

        return len(errors) == 0, errors

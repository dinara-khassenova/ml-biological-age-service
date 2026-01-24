from typing import Any, Dict, List, Tuple

from ml.base import Validator
from models.validation import ValidationError


class BioAgeDataValidator(Validator):
    """
    Валидатор входных данных для расчёта биологического возраста.

    Примечание: Несколько признаков для примера.
    """

    def validate(self, data: Dict[str, Any]) -> Tuple[bool, List[ValidationError]]:
        errors: List[ValidationError] = []

        # age (required)
        age = data.get("age")
        if age is None:
            errors.append(ValidationError("age", "Поле 'age' обязательно"))
        elif not isinstance(age, (int, float)) or age < 0 or age > 120:
            errors.append(ValidationError("age", "Возраст должен быть в диапазоне от 0 до 120"))

        # bmi (optional)
        bmi = data.get("bmi")
        if bmi is not None and (not isinstance(bmi, (int, float)) or bmi < 10 or bmi > 60):
            errors.append(ValidationError("bmi", "BMI должен быть в диапазоне от 10 до 60"))

        # glucose (optional)
        glucose = data.get("glucose")
        if glucose is not None and (not isinstance(glucose, (int, float)) or glucose < 0):
            errors.append(ValidationError("glucose", "Уровень глюкозы должен быть неотрицательным числом"))

        return (len(errors) == 0, errors)
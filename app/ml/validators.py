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

        # age
        if "age" in data:
            age = data["age"]
            if not isinstance(age, (int, float)) or age < 0 or age > 120:
                errors.append(ValidationError("age", "Возраст должен быть в диапазоне от 0 до 120"))
        else:
            errors.append(ValidationError("age", "Поле 'age' обязательно"))

        # bmi
        if "bmi" in data:
            bmi = data["bmi"]
            if not isinstance(bmi, (int, float)) or bmi < 10 or bmi > 60:
                errors.append(ValidationError("bmi", "BMI должен быть в диапазоне от 10 до 60"))

        # glucose
        if "glucose" in data:
            glucose = data["glucose"]
            if not isinstance(glucose, (int, float)) or glucose < 0:
                errors.append(ValidationError("glucose", "Уровень глюкозы в крови должен быть неотрицательным числом"))

        return (len(errors) == 0, errors)
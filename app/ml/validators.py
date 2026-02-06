from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from ml.base import Validator
from models.validation import ValidationError


@dataclass
class BioAgeDataValidator(Validator):
    """
    Валидатор входных данных для модели биологического возраста.
    Проверяет наличие и числовой тип всех required_features.
    """

    required_features: Optional[List[str]] = None

    def validate(self, data: Dict[str, Any]) -> Tuple[bool, List[ValidationError]]:
        errors: List[ValidationError] = []

        if not self.required_features:
            return True, errors

        for field in self.required_features:
            if field not in data:
                errors.append(
                    ValidationError(field, "Поле обязательно")
                )
                continue

            value = data[field]
            if not isinstance(value, (int, float)):
                errors.append(
                    ValidationError(field, "Должно быть числом")
                )

        return len(errors) == 0, errors

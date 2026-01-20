from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from constants import TASK_STATUSES
from models.factor import Factor
from models.validation import ValidationError


@dataclass
class AssessmentResult:
    """
    Результат ML расчёта.

    Attributes:
        biological_age (float): рассчитанный биологический возраст
        factors (List[Factor]): список факторов
        validation_errors (List[ValidationError]): ошибки валидации (если были)
    """
    biological_age: float
    factors: List[Factor]
    validation_errors: List[ValidationError] = field(default_factory=list)


@dataclass
class AssessmentTask:
    """
    Заявка пользователя на расчёт биологического возраста.

    Правила:
    - ответы можно добавлять только до начала обработки
    - обработка начинается только после успешной валидации
    - оплата происходит только после успешного завершения (по ТЗ)

    Attributes:
        id (int): идентификатор задачи
        user_id (int): идентификатор пользователя
        model_id (int): идентификатор ML модели (по начинаем с одной модели)
        answers (Dict[str, Any]): входные данные анкеты
        validation_errors (List[ValidationError]): ошибки валидации
        charged_amount (Optional[int]): сколько списали (фиксируем факт списания)
        status (str): CREATED -> VALIDATED -> PROCESSING -> DONE / FAILED
        result (Optional[AssessmentResult]): результат
        error_message (Optional[str]): текст ошибки выполнения (если FAILED)
        created_at (datetime): дата создания (UTC)
    """
    id: int
    user_id: int
    model_id: int 
    answers: Dict[str, Any] = field(default_factory=dict)
    validation_errors: List[ValidationError] = field(default_factory=list)
    charged_amount: Optional[int] = None
    status: str = "CREATED"    # CREATED -> VALIDATED -> PROCESSING -> DONE/FAILED
    result: Optional[AssessmentResult] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.status not in TASK_STATUSES:
            raise ValueError("Некорректный статус задачи")

    def add_answer(self, field_name: str, value: Any) -> None:
        """Добавляет/обновляет одно поле анкеты."""
        if self.status != "CREATED":
            raise ValueError("Нельзя изменять ответы после начала обработки")
        self.answers[field_name] = value

    def set_validation_result(self, is_valid: bool, errors: List["ValidationError"]) -> None:
        """Если валидацию данные не прошли, пока оставляем статус CREATED для возможной корректировки данных"""
        if self.status != "CREATED":
            raise ValueError("Валидацию можно сохранить только в статусе CREATED")
        self.validation_errors = list(errors)
        self.status = "VALIDATED" if is_valid else "CREATED"

    def start_processing(self) -> None:
        if self.status != "VALIDATED":
            raise ValueError("start_processing() возможен только после успешной валидации")
        self.status = "PROCESSING"

    def set_result(self, result: "AssessmentResult", charged_amount: int) -> None:
        if self.status != "PROCESSING":
            raise ValueError("set_result() только из PROCESSING")
        self.result = result
        self.charged_amount = charged_amount
        self.status = "DONE"

    def set_error(self, message: str) -> None:
        if self.status not in {"CREATED", "VALIDATED", "PROCESSING"}:
            raise ValueError("set_error() допускается только из CREATED/VALIDATED/PROCESSING")
        self.error_message = message
        self.status = "FAILED"

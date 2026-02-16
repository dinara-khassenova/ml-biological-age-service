from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlmodel import SQLModel, Field, Relationship

from models.enum import TaskStatus

if TYPE_CHECKING:
    from models.user import User
    from models.validation import ValidationError

# Helpers

def _validation_errors_to_json(errors: List["ValidationError"]) -> List[Dict[str, Any]]:
    return [{"field_name": e.field_name, "message": e.message} for e in errors]


def _json_safe(obj: Any) -> Any:
    """
    Гарантирует, что объект сериализуем в JSON (для JSONB).
    Лечит numpy types, pandas types и т.п.
    """
    if hasattr(obj, "item") and callable(getattr(obj, "item")):
        return obj.item()
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, tuple):
        return [_json_safe(v) for v in obj]
    return obj


class AssessmentResult(SQLModel):
    """
    Результат ML расчёта (не таблица).
    """
    biological_age: float
    factors: List[Dict[str, Any]] = Field(default_factory=list)
    validation_errors: List[Dict[str, Any]] = Field(default_factory=list)


class AssessmentTaskBase(SQLModel):
    user_id: int = Field(foreign_key="users.id", index=True)
    model_id: int = Field(default=1, foreign_key="ml_models.id", index=True)


class AssessmentTask(AssessmentTaskBase, table=True):
    __tablename__ = "assessment_tasks"

    id: Optional[int] = Field(default=None, primary_key=True)

    external_id: str = Field(index=True, unique=True)

    answers: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB().with_variant(JSON(), "sqlite"), nullable=False),
    )

    validation_errors: List[Dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB().with_variant(JSON(), "sqlite"), nullable=False),
    )

    result: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB().with_variant(JSON(), "sqlite"), nullable=False),
    )

    charged_amount: Optional[int] = Field(default=None)

    status: TaskStatus = Field(default=TaskStatus.CREATED, index=True)
    error_message: Optional[str] = Field(default=None, max_length=500)

    worker_id: Optional[str] = Field(default=None, max_length=100)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
    )

    user: "User" = Relationship(  # type: ignore
        back_populates="tasks",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    def __str__(self) -> str:
        return (
            f"Task(id={self.id}, external_id={self.external_id}, user_id={self.user_id}, "
            f"model_id={self.model_id}, status={self.status.value})"
        )

    def add_answer(self, field_name: str, value: Any) -> None:
        if self.status != TaskStatus.CREATED:
            raise ValueError("Нельзя изменять ответы после начала обработки")
        self.answers[field_name] = value

    def set_validation_result(self, is_valid: bool, errors: List["ValidationError"]) -> None:
        if self.status != TaskStatus.CREATED:
            raise ValueError("Валидацию можно сохранить только в статусе CREATED")
        self.validation_errors = _validation_errors_to_json(errors)
        self.status = TaskStatus.VALIDATED if is_valid else TaskStatus.CREATED

    def start_processing(self) -> None:
        if self.status != TaskStatus.VALIDATED:
            raise ValueError("start_processing() возможен только после успешной валидации")
        self.status = TaskStatus.PROCESSING

    def set_result(self, result: "AssessmentResult", charged_amount: int) -> None:
        if self.status != TaskStatus.PROCESSING:
            raise ValueError("set_result() только из PROCESSING")
        if charged_amount <= 0:
            raise ValueError("charged_amount должен быть > 0")

        raw = {
            "biological_age": float(result.biological_age),
            "factors": list(result.factors),
            "validation_errors": list(result.validation_errors),
        }
        self.result = _json_safe(raw)

        self.charged_amount = charged_amount
        self.status = TaskStatus.DONE

    def set_error(self, message: str) -> None:
        if self.status not in {TaskStatus.CREATED, TaskStatus.VALIDATED, TaskStatus.PROCESSING}:
            raise ValueError("set_error() допускается только из CREATED/VALIDATED/PROCESSING")
        self.error_message = message
        self.status = TaskStatus.FAILED

    class Config:
        validate_assignment = True
        arbitrary_types_allowed = True


class AssessmentTaskCreate(AssessmentTaskBase):
    answers: Dict[str, Any] = Field(default_factory=dict)


class AssessmentTaskUpdate(SQLModel):
    answers: Optional[Dict[str, Any]] = None
    status: Optional[TaskStatus] = None
    error_message: Optional[str] = None
    worker_id: Optional[str] = None

    class Config:
        validate_assignment = True


'''
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
'''

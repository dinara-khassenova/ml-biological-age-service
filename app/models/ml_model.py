from __future__ import annotations

from typing import List, Optional

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlmodel import SQLModel, Field


class MLModel(SQLModel, table=True):
    """
    ML модель (метаданные), которая хранится в БД.

    Храним только то, что должно жить в БД:
    - id
    - name
    - price_per_task
    - feature_names (список признаков)
    """

    __tablename__ = "ml_models"

    id: Optional[int] = Field(default=None, primary_key=True)

    name: str = Field(
        ...,
        index=True,
        min_length=1,
        max_length=100,
    )

    price_per_task: int = Field(default=25, gt=0)

    feature_names: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB().with_variant(JSON(), "sqlite"), nullable=False),
    )

    def __str__(self) -> str:
        return f"MLModel(id={self.id}, name={self.name}, price={self.price_per_task})"

    def validate_meta(self) -> bool:
        """
        Валидация метаданных.
        """
        if not self.feature_names:
            raise ValueError("feature_names не должен быть пустым")
        if self.price_per_task <= 0:
            raise ValueError("price_per_task должен быть > 0")
        return True

    class Config:
        validate_assignment = True
        arbitrary_types_allowed = True


'''
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
'''